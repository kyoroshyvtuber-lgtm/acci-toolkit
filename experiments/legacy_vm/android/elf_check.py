#!/usr/bin/env python3
"""Small ELF64 audit: exact machine, Android linker and 16KB PT_LOAD alignment."""
import hashlib
from pathlib import Path
import struct


def inspect(path, machine, *, shared=False, bundled=()):
    data = Path(path).read_bytes()
    if data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("expected little-endian ELF64")
    e_type, actual_machine = struct.unpack_from("<HH", data, 16)
    if e_type != 3 or actual_machine != machine:
        raise ValueError("unexpected ELF type/machine")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    if phentsize != 56 or phnum > 128:
        raise ValueError("invalid program table")
    loads, interpreter, dynamic = [], None, None
    for n in range(phnum):
        kind, flags, offset, address, _, size, memory, align = struct.unpack_from("<IIQQQQQQ", data, phoff+n*56)
        if offset + size > len(data):
            raise ValueError("ELF segment outside file")
        if kind == 1:
            if align < 16384 or address % align != offset % align:
                raise ValueError("native LOAD segment is not 16KB-compatible")
            loads.append((offset, address, size, align))
        if kind == 3:
            interpreter = data[offset:offset+size].rstrip(b"\0").decode("ascii")
        if kind == 2:
            dynamic = (offset, size)
    invalid_interpreter = interpreter is not None if shared else interpreter != "/system/bin/linker64"
    if not loads or not dynamic or invalid_interpreter:
        raise ValueError("not the expected Android shared library / PIE executable")
    needed, strtab = [], None
    for at in range(dynamic[0], dynamic[0]+dynamic[1], 16):
        tag, value = struct.unpack_from("<QQ", data, at)
        if tag == 0: break
        if tag == 1: needed.append(value)
        if tag == 5: strtab = value
    if strtab is None:
        raise ValueError("no dynamic strings")
    location = next((offset+strtab-address for offset,address,size,_ in loads if address <= strtab < address+size), None)
    if location is None:
        raise ValueError("unmapped strings")
    libraries = []
    for value in needed:
        start = location + value
        end = data.find(b"\0", start, min(start+1024, len(data)))
        if end < start: raise ValueError("invalid library name")
        libraries.append(data[start:end].decode("ascii"))
    allowed = {"libc.so", "libm.so", "libdl.so", "libz.so", "liblog.so", "libandroid.so"}
    if set(libraries) - allowed - set(bundled):
        raise ValueError("unbundled or non-system dependencies: " + repr(libraries))
    return {"sha256": hashlib.sha256(data).hexdigest(), "machine": actual_machine,
            "interpreter": interpreter, "load_alignments": [x[3] for x in loads],
            "needed": libraries, "bytes": len(data)}