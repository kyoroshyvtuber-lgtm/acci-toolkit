"""Detect technologies, build systems, tests, docs, CI config and suggested cloud runners."""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

SKIP = {".git", "node_modules", ".gradle", "build", "dist", "out", ".idea", ".vscode", ".venv", "venv",
        "__pycache__", "Pods", "DerivedData", "target", ".dart_tool", ".next", "coverage", ".expo",
        ".godot", "Library", "Temp", "Obj", "Logs"}
TEST_FILE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.(py|go)|[^/]+\.(test|spec)\.[jt]sx?|[^/]+Tests?\.(swift|kt|java|cs))$")
TEST_DIR = re.compile(r"(^|/)(tests?|__tests__|androidTest|src/test)/")
DOC = re.compile(r"(?i)^(readme|contributing|building|install|changelog|license)(\.[a-z]+)?$")
CI_FILES = (".gitlab-ci.yml", "bitrise.yml", "codemagic.yaml", "azure-pipelines.yml", "Jenkinsfile")


def _walk(root: Path, cap: int):
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP and not os.path.islink(os.path.join(dp, d)))
        for f in sorted(fns):
            yield Path(dp, f).relative_to(root).as_posix()
            n += 1
            if n >= cap:
                return


def _read(root: Path, rel: str, limit: int = 300_000) -> str:
    try:
        with open(root / rel, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def detect(root, cap: int = 50_000) -> dict:
    root = Path(root)
    files = list(_walk(root, cap))
    fset = set(files)
    by_name: dict[str, list[str]] = {}
    for f in files:
        by_name.setdefault(f.rsplit("/", 1)[-1], []).append(f)

    def named(*names):
        return [f for n in names for f in by_name.get(n, [])]

    stacks = []

    def add(stack, evidence, runner, **cmds):
        stacks.append({"stack": stack, "evidence": evidence[:5], "runner": runner,
                       **{k: v for k, v in cmds.items() if v}})

    pkg = {}
    if "package.json" in fset:
        try:
            pkg = json.loads(_read(root, "package.json")) or {}
        except ValueError:
            pkg = {}
    pkg = pkg if isinstance(pkg, dict) else {}
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    gradle = named("build.gradle", "build.gradle.kts")
    android = [g for g in gradle if re.search(r"com\.android\.(application|library)", _read(root, g))]
    gw = "./gradlew" if "gradlew" in fset else "gradle"
    xcode = sorted({f.split(".xcodeproj/")[0] + ".xcodeproj" for f in files if ".xcodeproj/" in f})
    xcws = sorted({f.split(".xcworkspace/")[0] + ".xcworkspace" for f in files
                   if ".xcworkspace/" in f and ".xcodeproj/" not in f})

    if any("sdk: flutter" in _read(root, p) for p in named("pubspec.yaml")):
        add("flutter", named("pubspec.yaml"), "ubuntu-latest (APK) / macos-latest (iOS)",
            install="flutter pub get", test="flutter test", build="flutter build apk --debug",
            artifacts="build/app/outputs/flutter-apk/*.apk")
    if "react-native" in deps:
        add("react-native", ["package.json"], "ubuntu-latest (APK) / macos-latest (iOS)",
            install="npm ci", test="npm test", build="cd android && ./gradlew assembleDebug",
            artifacts="android/app/build/outputs/apk/**/*.apk")
    if android:
        add("android", android, "ubuntu-latest", setup="JDK 17 + preinstalled Android SDK",
            test=f"{gw} testDebugUnitTest", lint=f"{gw} lintDebug", build=f"{gw} assembleDebug",
            artifacts="**/build/outputs/apk/**/*.apk")
    elif gradle or "pom.xml" in fset:
        mvn = "pom.xml" in fset
        add("jvm", gradle or ["pom.xml"], "ubuntu-latest", test="mvn -B test" if mvn else f"{gw} test",
            build="mvn -B package" if mvn else f"{gw} build", artifacts="**/target/*.jar **/build/libs/*.jar")
    xcodegen = [f for f in named("project.yml") if re.search(r"platform:\s*iOS", _read(root, f))]
    if xcode or xcws or xcodegen:
        add("ios", xcws + xcode + xcodegen, "macos-latest", setup="xcodegen generate" if xcodegen else None,
            build="xcodebuild -scheme <Scheme> -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO build",
            test="xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=<Device>'",
            artifacts="*.app (simulator); signed .ipa needs the owner's Apple certificate + profile")
    if "Package.swift" in fset:
        add("swiftpm", ["Package.swift"], "macos-latest", build="swift build", test="swift test")
    if named("project.godot"):
        add("godot", named("project.godot"), "ubuntu-latest (headless) / macos-latest (iOS)",
            setup="Matching Godot editor + export templates; configure export_presets.cfg",
            build="godot --headless --path <project> --export-debug iOS <output.zip>",
            test="Run the project's gameplay test script; import alone is not a test",
            artifacts="Xcode project for iOS; signed IPA is a separate owner-configured step")
    unity = [f for f in files if f.endswith("ProjectSettings/ProjectVersion.txt")]
    if unity:
        add("unity", unity, "owner-licensed Editor / macos with iOS Build Support",
            setup="Read ProjectVersion.txt; use the exact Editor version and a valid owner license",
            test="Unity -batchmode -projectPath <project> -runTests -testPlatform EditMode -testResults results.xml",
            build="Unity -batchmode -quit -projectPath <project> -buildTarget iOS -executeMethod AcciBuild.BuildIOS",
            artifacts="Xcode export; simulator/device validation and signing are separate")
    if pkg and "react-native" not in deps:
        scripts = pkg.get("scripts") or {}
        pm = "pnpm" if "pnpm-lock.yaml" in fset else "yarn" if "yarn.lock" in fset else "npm"
        install = {"npm": "npm ci" if "package-lock.json" in fset else "npm install",
                   "yarn": "yarn install --frozen-lockfile", "pnpm": "pnpm install --frozen-lockfile"}[pm]
        kind = "electron" if "electron" in deps else "node"
        add(kind, ["package.json"], "ubuntu-latest" + (" / windows-latest / macos-latest" if kind == "electron" else ""),
            install=install, lint=f"{pm} run lint" if "lint" in scripts else None,
            test=f"{pm} test" if "test" in scripts else None,
            build=f"{pm} run build" if "build" in scripts else None, artifacts="dist/**")
    py = [f for f in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt") if f in fset]
    if py:
        add("python", py, "ubuntu-latest",
            install="pip install -r requirements.txt" if "requirements.txt" in fset else "pip install -e .",
            lint="python -m compileall -q .", test="python -m pytest -q",
            build="python -m build" if {"pyproject.toml", "setup.py"} & fset else None, artifacts="dist/*")
    dotnet = [f for f in files if f.endswith((".sln", ".csproj", ".fsproj", ".vbproj"))]
    if dotnet:
        win = any(re.search(r"<(UseWindowsForms|UseWPF)>\s*true|net\d+\.\d+-windows", _read(root, f))
                  for f in dotnet if not f.endswith(".sln"))
        add("dotnet", dotnet, "windows-latest" if win else "ubuntu-latest", install="dotnet restore",
            test="dotnet test", build="dotnet publish -c Release -o out", artifacts="out/**")
    if "Cargo.toml" in fset:
        add("rust", ["Cargo.toml"], "ubuntu-latest", test="cargo test", build="cargo build --release",
            artifacts="target/release/*")
    if "go.mod" in fset:
        add("go", ["go.mod"], "ubuntu-latest", test="go test ./...", build="go build -o bin/ ./...")
    if "CMakeLists.txt" in fset:
        add("cmake", ["CMakeLists.txt"], "ubuntu-latest", build="cmake -S . -B build && cmake --build build",
            test="ctest --test-dir build")
    elif "Makefile" in fset and not stacks:
        add("make", ["Makefile"], "ubuntu-latest", build="make", test="make test")

    sizes = {}
    for f in files:
        try:
            sizes[f] = (root / f).stat().st_size
        except OSError:
            pass
    return {
        "root": str(root), "files": len(files), "truncated": len(files) >= cap, "bytes": sum(sizes.values()),
        "stacks": stacks,
        "docs": [f for f in files if DOC.match(f.rsplit("/", 1)[-1])][:20],
        "tests": sorted({f for f in files if TEST_FILE.search(f) or TEST_DIR.search(f)})[:50],
        "ci": [f for f in files if f.startswith(".github/workflows/") or f in CI_FILES],
        "has_git": (root / ".git").exists(),
        "top_level": sorted({f.split("/")[0] for f in files})[:40],
        "extensions": Counter((Path(f).suffix.lower() or "(none)") for f in files).most_common(12),
        "large_files": sorted(([f, s] for f, s in sizes.items() if s > 20 * 1024**2), key=lambda x: -x[1])[:20],
    }
