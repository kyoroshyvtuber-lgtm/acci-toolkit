from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_parse_and_have_jobs():
    paths = (list((ROOT / "acci/templates").glob("ci-*.yml"))
             + list((ROOT / ".github/workflows").glob("*.yml"))
             + list((ROOT / "examples/ci-demo/.github/workflows").glob("*.yml")))
    assert len(paths) >= 10
    for path in paths:
        data = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        assert isinstance(data.get("on"), dict), path
        assert isinstance(data.get("jobs"), dict) and data["jobs"], path
        for job in data["jobs"].values():
            assert job.get("runs-on"), path
            assert job.get("steps"), path


def test_readme_local_links_exist():
    for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", (ROOT / "README.md").read_text()):
        if "://" not in target:
            assert (ROOT / target).is_file(), target