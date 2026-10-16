#!/usr/bin/env python3
"""Exercise the real QEMU CPU, PL110 framebuffer and PL050 input, not iOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time


class Rfb:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.settimeout(10)
        self.s.connect(str(path))
        if self.read(12) != b"RFB 003.008\n":
            raise ValueError("unexpected RFB version")
        self.s.sendall(b"RFB 003.008\n")
        security = self.read(self.u8())
        if 1 not in security:
            raise ValueError("private socket did not offer unauthenticated local RFB")
        self.s.sendall(b"\1")
        if self.u32() != 0:
            raise ValueError("RFB security failed")
        self.s.sendall(b"\1")
        self.w, self.h = struct.unpack(">HH", self.read(4))
        self.read(16)
        self.read_bounded(self.u32(), 4096)
        self.resize(self.w, self.h)
        # 32bpp, depth24, little endian, true colour, R16 G8 B0.
        self.s.sendall(b"\0\0\0\0" + struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
        self.s.sendall(struct.pack(">BBHii", 2, 0, 2, 0, -223))

    def read(self, n):
        result = bytearray()
        while len(result) < n:
            piece = self.s.recv(n - len(result))
            if not piece:
                raise EOFError("RFB closed")
            result.extend(piece)
        return bytes(result)

    def read_bounded(self, n, limit):
        if n > limit:
            raise ValueError("RFB field too large")
        return self.read(n)

    def u8(self):
        return self.read(1)[0]

    def u32(self):
        return struct.unpack(">I", self.read(4))[0]

    def resize(self, w, h):
        if not (1 <= w <= 2048 and 1 <= h <= 2048):
            raise ValueError("frame size out of range")
        self.w, self.h = w, h
        self.pixels = bytearray(w * h * 4)

    def frame(self):
        self.s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, self.w, self.h))
        while True:
            kind = self.u8()
            if kind == 2:  # bell
                continue
            if kind == 3:  # bounded cut text, never evaluated
                self.read(3)
                self.read_bounded(self.u32(), 65536)
                continue
            if kind != 0:
                raise ValueError(f"unexpected RFB message {kind}")
            self.read(1)
            count = struct.unpack(">H", self.read(2))[0]
            if count > 1024:
                raise ValueError("too many rectangles")
            for _ in range(count):
                x, y, w, h, encoding = struct.unpack(">HHHHi", self.read(12))
                if encoding == -223:
                    self.resize(w, h)
                    continue
                if encoding != 0 or x + w > self.w or y + h > self.h:
                    raise ValueError("unsupported or out-of-bounds rectangle")
                for row in range(h):
                    start = ((y + row) * self.w + x) * 4
                    self.pixels[start:start + w * 4] = self.read(w * 4)
            return

    def key(self, keysym, down):
        self.s.sendall(struct.pack(">BBHI", 4, bool(down), 0, keysym))

    def save(self, path):
        from PIL import Image
        Image.frombytes("RGB", (self.w, self.h), bytes(self.pixels), "raw", "BGRX").save(path)


def wait_for(predicate, process, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        if process.poll() is not None:
            raise RuntimeError(f"emulator exited {process.returncode}")
        time.sleep(0.1)
    raise TimeoutError("engine did not produce the required evidence")


def main(binary, guest, output):
    binary, guest, output = Path(binary).resolve(), Path(guest).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    empty = output / "empty"
    empty.mkdir(exist_ok=True)
    rfb_path = output / "rfb.sock"
    if len(os.fsencode(rfb_path)) > 100:
        raise ValueError("socket path too long")
    uart = output / "serial.txt"
    command = [
        str(binary), "-M", "versatilepb", "-m", "64M", "-accel", "tcg,thread=single",
        "-kernel", str(guest), "-nodefaults", "-nic", "none",
        "-display", "none", "-vnc", "unix:" + str(rfb_path),
        "-monitor", "none", "-serial", "file:" + str(uart), "-L", str(empty), "-no-reboot",
    ]
    client = None
    with (output / "engine.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_for(lambda: uart.exists() and b"ACCI_VM_BOOT_OK" in uart.read_bytes(), process)
            wait_for(rfb_path.exists, process)
            client = Rfb(rfb_path)
            client.frame()
            if (client.w, client.h) != (640, 480):
                raise AssertionError(f"expected 640x480 guest, received {client.w}x{client.h}")
            client.save(output / "01-boot.png")
            before = hashlib.sha256(client.pixels).hexdigest()
            # A key must traverse RFB -> QEMU -> emulated PL050 -> guest code.
            client.key(ord("a"), True)
            client.key(ord("a"), False)
            wait_for(lambda: b"ACCI_INPUT_OK" in uart.read_bytes(), process)
            time.sleep(0.2)
            client.frame()
            client.save(output / "02-input.png")
            after = hashlib.sha256(client.pixels).hexdigest()
            if before == after:
                raise AssertionError("input marker arrived but the framebuffer did not change")
            evidence = {
                "schema": 1, "guest": "self-authored ARM926 smoke test", "ios": False,
                "safari": False, "engine_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "guest_sha256": hashlib.sha256(guest.read_bytes()).hexdigest(),
                "frame": [client.w, client.h], "uart_boot": True, "uart_input": True,
                "frame_changed_after_key": True, "frame_before_sha256": before,
                "frame_after_sha256": after, "host": "Linux x86_64",
            }
            (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
        finally:
            if client:
                client.s.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            rfb_path.unlink(missing_ok=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("binary")
    p.add_argument("guest")
    p.add_argument("output")
    args = p.parse_args()
    main(args.binary, args.guest, args.output)