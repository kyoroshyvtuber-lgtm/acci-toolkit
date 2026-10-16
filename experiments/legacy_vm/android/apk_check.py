#!/usr/bin/env python3
"""Cross-check packaged native bytes with the audited build identity."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from elf_check import inspect


def check(apk, output):
    with zipfile.ZipFile(apk) as z:
        if z.testzip() is not None: raise ValueError("APK ZIP CRC failure")
        identity=json.loads(z.read("assets/generated/build-identity.json"))
        for abi,machine in [("arm64-v8a",183),("x86_64",62)]:
            name=f"lib/{abi}/libacci_qemu.so"
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=identity["native"][abi]["sha256"]:
                raise ValueError("packaged native engine differs")
            if z.getinfo(name).compress_type != zipfile.ZIP_DEFLATED:
                raise ValueError("native library must be extracted from compressed APK")
            with tempfile.TemporaryDirectory() as tmp:
                file=Path(tmp)/"engine";file.write_bytes(data);inspect(file,machine)
        if hashlib.sha256(z.read("assets/generated/smoke.elf")).hexdigest()!=identity["guest_sha256"]:
            raise ValueError("packaged guest differs")
        if hashlib.sha256(z.read("assets/generated/keymaps/en-us")).hexdigest()!=identity["keymap_sha256"]:
            raise ValueError("packaged keymap differs")
        notices=z.read("assets/generated/licenses.txt").decode()
        if "GNU GENERAL PUBLIC LICENSE" not in notices or "GLib" not in notices and "glib" not in notices:
            raise ValueError("missing bundled license notice")
    evidence={"apk":apk.name,"bytes":apk.stat().st_size,
        "sha256":hashlib.sha256(apk.read_bytes()).hexdigest(),"zip_crc":True,
        "both_native_engines_match":True,"native_16kb_load_alignment":True,
        "guest_matches":True,"licenses_bundled":True,"identity":identity}
    output.write_text(json.dumps(evidence,indent=2)+"\n");print(json.dumps(evidence))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("apk",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();check(a.apk,a.output)