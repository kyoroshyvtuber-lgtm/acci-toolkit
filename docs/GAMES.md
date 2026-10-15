# Game-engine profiles

Choose the engine from the **actual project**. ACCI does not convert arbitrary
apps into games or choose the owner's mechanics, assets or licensing.

```bash
acci detect /path/to/game
acci game plan /path/to/game
acci game plan /path/to/unity-game --engine unity --editor /path/to/Unity
```

Plans list requirements, missing files, command arrays and the next validation
boundary. They do not execute engines or activate licenses.

## Godot (open-source route)

Included: detection/plan, pinned standard editor installer, headless score/reset/
limit fixture, resource-pack export/launch CI and manual iOS Xcode-export template.

```bash
acci template install-godot.sh --out /tmp/install-godot.sh
bash /tmp/install-godot.sh             # editor only; no license/account
# Explicit optional large (~1.3 GB) export-template download:
bash /tmp/install-godot.sh --templates
```

Pins Godot **4.7.2 standard/non-.NET** and official release-asset SHA-256 for Linux
x86-64/macOS universal and optional templates. It does not execute a remote
install script or silently use `latest`. Match your project's version; update
hashes/workflows together when changing it. Editor/templates must match.

```bash
GODOT="$ACCI_HOME/opt/godot-4.7.2/godot"
PROJECT="$PWD/examples/godot-demo"
mkdir -p /tmp/acci-game-evidence
"$GODOT" --headless --path "$PROJECT" --import
"$GODOT" --headless --path "$PROJECT" --script tests/score_test.gd
"$GODOT" --headless --path "$PROJECT" --export-pack Linux /tmp/acci-game-evidence/game.pck
"$GODOT" --headless --main-pack /tmp/acci-game-evidence/game.pck --quit-after 2
```

This verifies import, four gameplay checks, `.pck` export and packaged headless
startup. A `.pck` needs the matching Godot runtime. It is **not** a standalone
executable, iOS app, rendering/performance test or finished game. The fixture has
no commissioned art.

For iOS:

```bash
acci template ci-godot.yml --out .github/workflows/godot.yml
acci template install-godot.sh --out .acci/install-godot.sh
```

Adapt directory/version/preset and actual gameplay tests. Configure iOS
`export_presets.cfg` with owner team/bundle ID. Godot's
[iOS guide](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_ios.html)
requires macOS/Xcode/templates and the Compatibility renderer for the simulator.
The template exports an Xcode project/archive only: add project-specific
simulator tests/launch checks, then the separate [signing boundary](IOS.md).
Godot→iOS export was not run without owner settings.

## Unity (owner installation/license)

Included: exact Editor-version detection, EditMode/PlayMode plan, nonempty/passing
NUnit checks, Editor build entry point and manual iOS Xcode-export template.

```bash
acci template AcciBuild.cs --out Assets/Editor/AcciBuild.cs
acci template games.py --out .acci/games.py
acci template ci-unity.yml --out .github/workflows/unity.yml
```

Use the exact licensed Editor, iOS Build Support, Xcode and enabled scenes.
Set `ACCI_UNITY_EXPORT` for the build method. The template needs an owner-managed
**ephemeral** macOS runner labelled `acci-unity-ephemeral`, `UNITY_EDITOR_PATH`
and explicit `ACCI_UNITY_ENABLED=true`. Only owner/default-branch manual runs.
Do not attach a persistent personal machine to untrusted public PR jobs.

Tests omit `-quit`: Unity documents that it can stop `-runTests` prematurely.
The separate export command uses `-batchmode -quit -buildTarget iOS
-executeMethod AcciBuild.BuildIOS`. Empty/failing NUnit results fail validation.
No license is purchased, activated, copied into source or bypassed.

Unity is not installed/end-to-end tested. Xcode exports still need simulator/
device validation, per-target signing and publication approval.
See [Unity command-line reference](https://docs.unity3d.com/6000.0/Documentation/Manual/EditorCommandLineArguments.html).