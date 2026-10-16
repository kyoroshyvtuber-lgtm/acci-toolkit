#!/usr/bin/env python3
"""UI-driven Android 16 run of the packaged engine. No Apple guest involved."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PACKAGE = "dev.acci.legacyvm"


def adb(*args, check=True):
    return subprocess.run(["adb", *args], check=check, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60).stdout


def evidence():
    raw = adb("exec-out","run-as",PACKAGE,"cat","files/last-run.json",check=False)
    try: return json.loads(raw)
    except (ValueError,UnicodeDecodeError): return {}


def wait(predicate, seconds=45):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result: return result
        data = evidence()
        if data.get("error"): raise AssertionError("Native engine error: "+data["error"])
        time.sleep(.5)
    raise TimeoutError("Android evidence condition not reached: "+repr(evidence()))


def tree():
    adb("shell","uiautomator","dump","/sdcard/acci-ui.xml")
    return ET.fromstring(adb("exec-out","cat","/sdcard/acci-ui.xml"))


def find(resource_id, scroll=True):
    for attempt in range(6 if scroll else 1):
        for n in tree().iter("node"):
            if n.get("resource-id") == PACKAGE+":id/"+resource_id and n.get("enabled") == "true":
                b = list(map(int,re.findall(r"\d+",n.get("bounds",""))))
                if len(b) == 4 and b[2] > b[0] and b[3] > b[1]:
                    return ((b[0]+b[2])//2,(b[1]+b[3])//2)
        if scroll: adb("shell","input","swipe","540","1900","540","650","400")
    raise AssertionError("Visible enabled control not found: "+resource_id)


def tap(resource_id):
    x,y=find(resource_id); adb("shell","input","tap",str(x),str(y)); time.sleep(.4)


def screenshot(out,name):
    (out/(name+".png")).write_bytes(adb("exec-out","screencap","-p"))
    adb("shell","uiautomator","dump","/sdcard/acci-ui.xml")
    (out/(name+".xml")).write_bytes(adb("exec-out","cat","/sdcard/acci-ui.xml"))


def top():
    for _ in range(4): adb("shell","input","swipe","540","650","540","1950","250")
    time.sleep(.5)


def main(apk,out):
    out.mkdir(parents=True,exist_ok=True)
    try:
        adb("shell","wm","size","1080x2400"); adb("shell","wm","density","440")
        adb("install","-r",str(apk))
        adb("shell","am","start","-W","-n",PACKAGE+"/.MainActivity")
        time.sleep(1)
        screenshot(out,"00-home")
        tap("start_self_test")
        boot=wait(lambda: (d if (d:=evidence()).get("uart_boot") and d.get("frames",0)>=3 else None))
        (out/"01-boot.json").write_text(json.dumps(boot,indent=2))
        top(); screenshot(out,"01-boot")
        tap("send_test_key")
        entered=wait(lambda: (d if (d:=evidence()).get("uart_input") else None))
        (out/"02-input.json").write_text(json.dumps(entered,indent=2))
        top(); screenshot(out,"02-input")
        tap("show_log"); screenshot(out,"03-journal")
        adb("shell","input","keyevent","KEYCODE_BACK")
        tap("stop_engine")
        stopped=wait(lambda: (d if (d:=evidence()).get("frames",0)>0 and d.get("running") is False else None))
        (out/"04-stopped.json").write_text(json.dumps(stopped,indent=2))
        top(); screenshot(out,"04-stopped")
        tap("start_self_test")
        wait(lambda: evidence().get("uart_boot"))
        adb("shell","input","keyevent","KEYCODE_HOME")
        background=wait(lambda: evidence().get("running") is False)
        (out/"05-background.json").write_text(json.dumps(evidence(),indent=2))
        adb("shell","am","start","-W","-n",PACKAGE+"/.MainActivity")
        time.sleep(.5)
        find("import_profile"); screenshot(out,"06-profile")
        # Open the real system picker then cancel. No private user files exist in this AVD.
        tap("import_profile"); screenshot(out,"07-picker")
        adb("shell","input","keyevent","KEYCODE_BACK")
        time.sleep(.3)
        final = evidence()
        if final.get("ios_boot_verified") or final.get("safari_verified"):
            raise AssertionError("Unexpected iOS/Safari claim")
        proof = {
            "sdk": adb("shell","getprop","ro.build.version.sdk").decode().strip(),
            "abi": adb("shell","getprop","ro.product.cpu.abi").decode().strip(),
            "android_page_size": adb("shell","getconf","PAGE_SIZE").decode().strip(),
            "app": PACKAGE, "apk": apk.name, "uart_boot": True,"uart_input": True,
            "framebuffer_frames": entered["frames"], "stop_button": True,
            "background_stops_engine": True, "ios_boot_verified":False,
            "safari_verified":False, "physical_realme_tested":False,
        }
        if proof["sdk"] != "36" or proof["abi"] != "x86_64":
            raise AssertionError("Unexpected Android test platform")
        (out/"android-evidence.json").write_text(json.dumps(proof,indent=2)+"\n")
        print(json.dumps(proof))
    finally:
        (out/"logcat.txt").write_bytes(adb("logcat","-d","-v","threadtime",check=False))
        (out/"app-engine.log").write_bytes(adb("exec-out","run-as",PACKAGE,"cat","files/engine.log",check=False))
        (out/"app-last-run.json").write_bytes(adb("exec-out","run-as",PACKAGE,"cat","files/last-run.json",check=False))


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("apk",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();main(a.apk,a.out)