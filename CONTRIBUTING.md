# Contributing

Read `AGENTS.md` and `docs/SECURITY.md`.
Use a topic branch and a pull request; keep unrelated changes out.

```bash
bash bin/bootstrap.sh --dev
source .venv/bin/activate
python -m pytest -q
python -m build
```

Test an installed wheel in a clean environment, not only an editable checkout:

```bash
python3 -m venv /tmp/acci-wheel-check
/tmp/acci-wheel-check/bin/python -m pip install dist/*.whl
cd /tmp
/tmp/acci-wheel-check/bin/python /absolute/path/to/acci-toolkit/scripts/smoke_installed.py
```

The CLI must include its CI templates when installed. Add regression tests for
behavior changes and document limitations instead of silently weakening checks.
Do not commit runtime data, secrets, build outputs, or credentials.

Repository visibility and an explicit license are separate requirements for
open-source distribution. The owner must approve the license and public
publication before this project is described as a completed open-source release.