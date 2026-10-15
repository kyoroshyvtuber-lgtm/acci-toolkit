"""macOS iOS checks; stdlib-only, also usable as an extracted .acci/ios.py.

Signing is opt-in, supports one app/profile, and NEVER uploads to Apple.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

SIGNING_ENV = ("IOS_P12_BASE64", "IOS_P12_PASSWORD", "IOS_PROFILE_BASE64",
               "IOS_TEAM_ID", "KEYCHAIN_PASSWORD")
METHODS = ("debugging", "release-testing", "app-store-connect")


def choose_simulator(types: dict, runtimes: dict) -> tuple[str, str]:
    available = [r for r in runtimes.get("runtimes", [])
                 if r.get("isAvailable") and ".iOS-" in r.get("identifier", "")]
    available.sort(key=lambda r: tuple(int(x) for x in r["version"].split(".")), reverse=True)
    for runtime in available:
        version = tuple(int(x) for x in runtime["version"].split("."))
        version = (version + (0, 0))[:3]
        numeric = (version[0] << 16) | (version[1] << 8) | version[2]
        phones = [d for d in types.get("devicetypes", [])
                  if d.get("productFamily") == "iPhone"
                  and d.get("minRuntimeVersion", 0) <= numeric <= d.get("maxRuntimeVersion", 0xFFFFFFFF)]
        if phones:
            return phones[-1]["identifier"], runtime["identifier"]
    raise ValueError("No compatible iPhone/iOS runtime; install an iOS simulator in Xcode")


def validate_profile(profile: dict, team: str, bundle: str, method: str,
                     now: dt.datetime | None = None) -> dict:
    if method not in METHODS:
        raise ValueError(f"export method must be one of {METHODS}")
    if not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("IOS_TEAM_ID must be the 10-character Apple team ID")
    if not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle):
        raise ValueError("A concrete reverse-DNS bundle identifier is required")
    now = now or dt.datetime.now(dt.timezone.utc)
    expires = profile.get("ExpirationDate")
    if not isinstance(expires, dt.datetime):
        raise ValueError("Profile has no expiration date")
    if expires.replace(tzinfo=dt.timezone.utc) <= now.astimezone(dt.timezone.utc):
        raise ValueError("Provisioning profile has expired")
    if team not in profile.get("TeamIdentifier", []):
        raise ValueError("Provisioning profile belongs to another team")
    ent = profile.get("Entitlements", {})
    if ent.get("com.apple.developer.team-identifier", team) != team:
        raise ValueError("Profile entitlement team does not match")
    prefix, sep, pattern = ent.get("application-identifier", "").partition(".")
    if (not sep or prefix not in profile.get("ApplicationIdentifierPrefix", [team])
            or not fnmatch.fnmatchcase(bundle, pattern)):
        raise ValueError("Bundle identifier is not permitted by the provisioning profile")
    identifier = profile.get("UUID", "")
    if not re.fullmatch(r"[A-Fa-f0-9-]{36}", identifier):
        raise ValueError("Invalid provisioning profile UUID")
    development = ent.get("get-task-allow", False)
    devices = bool(profile.get("ProvisionedDevices"))
    if profile.get("ProvisionsAllDevices"):
        raise ValueError("Enterprise profiles are not supported by this helper")
    if method == "debugging" and (not development or not devices):
        raise ValueError("debugging requires a development profile with registered devices")
    if method == "release-testing" and (development or not devices):
        raise ValueError("release-testing requires an ad-hoc distribution profile")
    if method == "app-store-connect" and (development or devices):
        raise ValueError("app-store-connect requires an App Store distribution profile")
    certificates = profile.get("DeveloperCertificates", [])
    if not certificates or not all(isinstance(c, bytes) for c in certificates):
        raise ValueError("Profile has no valid developer certificates")
    return {"uuid": identifier, "expires": expires.isoformat(),
            "certificate_sha1": [hashlib.sha1(c).hexdigest().upper() for c in certificates]}


def export_options(team: str, bundle: str, profile_uuid: str, identity: str, method: str) -> dict:
    return {"method": method, "destination": "export", "teamID": team,
            "signingStyle": "manual", "signingCertificate": identity,
            "provisioningProfiles": {bundle: profile_uuid},
            "manageAppVersionAndBuildNumber": False, "stripSwiftSymbols": True}


def inspect_ipa(path: Path, bundle: str) -> dict:
    """Integrity/identity check, NOT proof of device installation/Apple acceptance."""
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise ValueError("IPA contains a corrupt entry")
        infos = [n for n in archive.namelist()
                 if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", n)]
        if len(infos) != 1:
            raise ValueError("Expected exactly one application in IPA")
        info = plistlib.loads(archive.read(infos[0]))
        if info.get("CFBundleIdentifier") != bundle:
            raise ValueError("Exported IPA bundle identifier does not match")
        if info.get("DTPlatformName") != "iphoneos":
            raise ValueError("Exported application is not an iPhone device build")
        executable = infos[0].removesuffix("Info.plist") + info["CFBundleExecutable"]
        if executable not in archive.namelist():
            raise ValueError("IPA executable is missing")
    return {"bundle_id": bundle, "platform": "iphoneos", "sha256": sha256(path),
            "bytes": path.stat().st_size}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight(signing: bool = False) -> dict:
    tools = {name: shutil.which(name) is not None
             for name in ("xcodebuild", "xcrun", "ditto", "xcodegen", "security")}
    blockers = []
    if sys.platform != "darwin":
        blockers.append("iOS execution requires macOS with Xcode (use a macOS Actions runner)")
    blockers += [f"Missing tool: {name}" for name in ("xcodebuild", "xcrun", "ditto")
                 if not tools[name]]
    if signing:
        blockers += [f"Missing private environment value: {name}" for name in SIGNING_ENV
                     if not os.environ.get(name)]
        if not tools["security"]:
            blockers.append("Missing tool: security")
    return {"ready": not blockers, "host": sys.platform, "tools": tools,
            "mode": "signed-export" if signing else "simulator", "blockers": blockers,
            "publication": "never performed by this helper"}


class Commands:
    def __init__(self, out: Path, cwd: Path):
        self.out, self.cwd = out, cwd
        self.env = {k: v for k, v in os.environ.items()
                    if k not in SIGNING_ENV and not any(
                        x in k.upper() for x in ("TOKEN", "API_KEY", "PASSWORD"))}

    def capture(self, args: list[str], *, private: bool = False, timeout: int = 120) -> str:
        try:
            result = subprocess.run(args, cwd=self.cwd, env=self.env, capture_output=True,
                                    timeout=timeout, text=True)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{Path(args[0]).name} timed out") from exc
        if result.returncode:
            raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode})"
                               + ("" if private else f": {result.stderr[-1500:]}"))
        return result.stdout.strip()

    def run(self, args: list[str], label: str, timeout: int = 1200):
        path = self.out / f"{label}.log"
        with path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(args, cwd=self.cwd, env=self.env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                status = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError(f"{label} timed out; see {path}") from None
        print(f"{label}: exit {status}; log={path}", flush=True)
        if status:
            raise RuntimeError(f"{label} failed; see {path}")


def prepare(project: str, out: str, scheme: str, generate: bool) -> tuple[Path, Path, Commands, list[str]]:
    ready = preflight()
    if not ready["ready"]:
        raise ValueError("; ".join(ready["blockers"]))
    project_dir, output = Path(project).resolve(), Path(out).resolve()
    if not project_dir.is_dir():
        raise ValueError("Project directory does not exist")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty; use a new path for each run")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,100}", scheme):
        raise ValueError("Invalid scheme name")
    output.mkdir(parents=True, exist_ok=True)
    commands = Commands(output, project_dir)
    if generate:
        if not shutil.which("xcodegen"):
            raise ValueError("Install XcodeGen before using --generate")
        commands.run(["xcodegen", "generate"], "generate", 120)
    containers = sorted(project_dir.glob("*.xcworkspace")) or sorted(project_dir.glob("*.xcodeproj"))
    if len(containers) != 1:
        raise ValueError("Expected one .xcworkspace or .xcodeproj in the project directory")
    container = containers[0]
    args = ["xcodebuild", "-workspace" if container.suffix == ".xcworkspace" else "-project",
            str(container), "-scheme", scheme]
    return project_dir, output, commands, args


def finish(output: Path, result: dict):
    files = [p for p in output.iterdir() if p.is_file() and p.name not in ("result.json", "SHA256SUMS")]
    result["artifacts"] = [{"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size}
                           for p in sorted(files)]
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    files += [output / "result.json"]
    (output / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in sorted(files)), encoding="utf-8")


def simulator(project: str, out: str, scheme: str, generate: bool = False) -> dict:
    _, output, commands, args = prepare(project, out, scheme, generate)
    result = {"mode": "unsigned-simulator", "status": "failed", "tests": "not-run",
              "launch": "not-run", "device_installation": "not-tested", "store_upload": False}
    device = None
    try:
        commands.run(["xcodebuild", "-version"], "xcode-version", 30)
        types = json.loads(commands.capture(["xcrun", "simctl", "list", "devicetypes", "--json"]))
        runtimes = json.loads(commands.capture(["xcrun", "simctl", "list", "runtimes", "--json"]))
        device_type, runtime = choose_simulator(types, runtimes)
        device = commands.capture(["xcrun", "simctl", "create", f"ACCI-{uuid.uuid4().hex[:8]}",
                                   device_type, runtime])
        result.update(device_type=device_type, runtime=runtime)
        commands.run(["xcrun", "simctl", "boot", device], "boot", 120)
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "boot-wait", 300)
        commands.run(args + ["-sdk", "iphonesimulator", "-configuration", "Debug",
                            "-derivedDataPath", str(output / "DerivedData"),
                            "-destination", f"platform=iOS Simulator,id={device}",
                            "-resultBundlePath", str(output / "Tests.xcresult"),
                            "-parallel-testing-enabled", "NO", "CODE_SIGNING_ALLOWED=NO", "test"],
                     "tests", 1800)
        result["tests"] = "passed"
        apps = list((output / "DerivedData/Build/Products/Debug-iphonesimulator").glob("*.app"))
        apps = [p for p in apps if not p.name.endswith("-Runner.app")]
        if len(apps) != 1:
            raise ValueError("Expected one application product; adapt the scheme for multiple apps")
        app = apps[0]
        info = plistlib.loads((app / "Info.plist").read_bytes())
        bundle = info["CFBundleIdentifier"]
        if info.get("DTPlatformName") != "iphonesimulator":
            raise ValueError("Built product is not a simulator application")
        result["bundle_id"] = bundle
        commands.run(["xcrun", "simctl", "install", device, str(app)], "install", 120)
        commands.run(["xcrun", "simctl", "launch", "--terminate-running-process", device, bundle],
                     "launch", 120)
        time.sleep(3)
        commands.run(["xcrun", "simctl", "io", device, "screenshot", str(output / "simulator.png")],
                     "screenshot", 120)
        commands.run(["ditto", "-c", "-k", "--keepParent", str(app),
                      str(output / "ios-simulator-app.zip")], "package", 120)
        result.update(status="passed", launch="simctl-launch-succeeded; see XCTest and screenshot")
        return result
    finally:
        if device:
            for action in ("shutdown", "delete"):
                try:
                    commands.capture(["xcrun", "simctl", action, device], timeout=60)
                except RuntimeError:
                    result.setdefault("cleanup_warnings", []).append(f"simulator {action} failed")
        xcresult = output / "Tests.xcresult"
        if xcresult.is_dir():
            try:
                commands.run(["ditto", "-c", "-k", "--keepParent", str(xcresult),
                              str(output / "Tests.xcresult.zip")], "package-test-results", 180)
            except RuntimeError:
                result.setdefault("cleanup_warnings", []).append("could not archive xcresult")
        finish(output, result)


def signed_export(project: str, out: str, scheme: str, bundle: str, method: str,
                  generate: bool = False) -> dict:
    ready = preflight(signing=True)
    if not ready["ready"]:
        raise ValueError("; ".join(ready["blockers"]))
    _, output, commands, args = prepare(project, out, scheme, generate)
    values = {name: os.environ[name] for name in SIGNING_ENV}
    result = {"mode": "signed-device-export", "status": "failed", "method": method,
              "device_installation": "not-tested", "store_upload": False}
    profile_path, previous_profile, old_keychains = None, None, None
    with tempfile.TemporaryDirectory(prefix="acci-signing-") as tmp:
        tmpdir = Path(tmp)
        os.chmod(tmpdir, 0o700)
        keychain = tmpdir / "build.keychain-db"
        try:
            p12, mobile = tmpdir / "certificate.p12", tmpdir / "profile.mobileprovision"
            for path, key in ((p12, "IOS_P12_BASE64"), (mobile, "IOS_PROFILE_BASE64")):
                path.write_bytes(base64.b64decode("".join(values[key].split()), validate=True))
                os.chmod(path, 0o600)
            profile = plistlib.loads(commands.capture(
                ["security", "cms", "-D", "-i", str(mobile)], private=True).encode())
            checked = validate_profile(profile, values["IOS_TEAM_ID"], bundle, method)
            old_keychains = shlex.split(commands.capture(["security", "list-keychains", "-d", "user"]))
            commands.capture(["security", "create-keychain", "-p", values["KEYCHAIN_PASSWORD"],
                              str(keychain)], private=True)
            commands.capture(["security", "set-keychain-settings", "-lut", "3600", str(keychain)], private=True)
            commands.capture(["security", "unlock-keychain", "-p", values["KEYCHAIN_PASSWORD"],
                              str(keychain)], private=True)
            commands.capture(["security", "import", str(p12), "-P", values["IOS_P12_PASSWORD"],
                              "-t", "cert", "-f", "pkcs12", "-k", str(keychain),
                              "-T", "/usr/bin/codesign", "-T", "/usr/bin/security"], private=True)
            commands.capture(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:",
                              "-s", "-k", values["KEYCHAIN_PASSWORD"], str(keychain)], private=True)
            identities = commands.capture(["security", "find-identity", "-v", "-p", "codesigning",
                                           str(keychain)], private=True)
            identities = re.findall(r"\b[A-Fa-f0-9]{40}\b", identities)
            if len(identities) != 1 or identities[0].upper() not in checked["certificate_sha1"]:
                raise ValueError("Expected one valid signing identity matching the provisioning profile")
            identity = identities[0].upper()
            commands.capture(["security", "list-keychains", "-d", "user", "-s", str(keychain),
                              *old_keychains], private=True)
            profile_path = Path.home() / "Library/MobileDevice/Provisioning Profiles" / (checked["uuid"] + ".mobileprovision")
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            previous_profile = profile_path.read_bytes() if profile_path.exists() else None
            shutil.copyfile(mobile, profile_path)
            options = tmpdir / "ExportOptions.plist"
            options.write_bytes(plistlib.dumps(export_options(values["IOS_TEAM_ID"], bundle,
                                                              checked["uuid"], identity, method)))
            archive = tmpdir / "App.xcarchive"
            commands.run(args + ["-configuration", "Release", "-destination", "generic/platform=iOS",
                                 "-archivePath", str(archive), "CODE_SIGN_STYLE=Manual",
                                 f"DEVELOPMENT_TEAM={values['IOS_TEAM_ID']}",
                                 f"CODE_SIGN_IDENTITY={identity}",
                                 f"PROVISIONING_PROFILE_SPECIFIER={checked['uuid']}", "archive"],
                         "archive", 1800)
            apps = list((archive / "Products/Applications").glob("*.app"))
            if len(apps) != 1 or list(apps[0].glob("PlugIns/*.appex")):
                raise ValueError("Only a single app without extensions is supported; use per-target profiles otherwise")
            commands.run(["xcodebuild", "-exportArchive", "-archivePath", str(archive),
                          "-exportPath", str(output / "ipa"), "-exportOptionsPlist", str(options)],
                         "export", 900)
            ipas = list((output / "ipa").glob("*.ipa"))
            if len(ipas) != 1:
                raise ValueError("Expected one exported IPA")
            result["ipa"] = inspect_ipa(ipas[0], bundle)
            extracted = tmpdir / "exported"
            commands.capture(["ditto", "-x", "-k", str(ipas[0]), str(extracted)], private=True)
            exported_apps = list((extracted / "Payload").glob("*.app"))
            commands.run(["codesign", "--verify", "--deep", "--strict", str(exported_apps[0])],
                         "verify-signature", 120)
            shutil.move(str(ipas[0]), output / ipas[0].name)
            result.update(status="passed", profile_expiration=checked["expires"])
            return result
        finally:
            if old_keychains is not None:
                try:
                    commands.capture(["security", "list-keychains", "-d", "user", "-s", *old_keychains],
                                     private=True)
                except RuntimeError:
                    result.setdefault("cleanup_warnings", []).append("keychain search list restore failed")
            if keychain.exists():
                try:
                    commands.capture(["security", "delete-keychain", str(keychain)], private=True)
                except RuntimeError:
                    result.setdefault("cleanup_warnings", []).append("temporary keychain deletion failed")
            if profile_path is not None:
                if previous_profile is None:
                    profile_path.unlink(missing_ok=True)
                else:
                    profile_path.write_bytes(previous_profile)
            finish(output, result)


def _ready(args):
    result = preflight(args.signing)
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 2


def add_parsers(parser):
    sub = parser.add_subparsers(dest="ios_command", required=True)
    ready = sub.add_parser("preflight", help="readiness check; never prints secret values")
    ready.add_argument("--signing", action="store_true")
    ready.set_defaults(fn=_ready)
    for name in ("simulator", "sign"):
        cmd = sub.add_parser(name)
        cmd.add_argument("project")
        cmd.add_argument("--scheme", required=True)
        cmd.add_argument("--out", required=True)
        cmd.add_argument("--generate", action="store_true", help="run installed XcodeGen")
        if name == "sign":
            cmd.add_argument("--bundle-id", required=True)
            cmd.add_argument("--method", choices=METHODS, required=True)
            cmd.set_defaults(fn=lambda a: print(json.dumps(signed_export(
                a.project, a.out, a.scheme, a.bundle_id, a.method, a.generate), indent=2)))
        else:
            cmd.set_defaults(fn=lambda a: print(json.dumps(simulator(
                a.project, a.out, a.scheme, a.generate), indent=2)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_parsers(parser)
    args = parser.parse_args()
    try:
        sys.exit(args.fn(args) or 0)
    except (ValueError, OSError, RuntimeError, plistlib.InvalidFileException) as error:
        print(f"acci ios: {error}", file=sys.stderr)
        sys.exit(2)