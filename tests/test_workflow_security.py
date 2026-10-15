from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_example_policy_is_disabled_and_workflow_has_independent_gates():
    import json
    # Do not prohibit the OWNER from enabling the live policy later.
    policy = json.loads((ROOT / "acci/templates/agent.example.json").read_text())
    assert policy["enabled"] is False and policy["provider"] == "" and policy["model"] == ""
    workflow = load(".github/workflows/agent.yml")
    assert set(workflow["on"]) == {"workflow_dispatch", "issues"}
    gate = workflow["jobs"]["propose"]["if"]
    assert "vars.ACCI_AGENT_ENABLED == 'true'" in gate
    assert "github.actor == github.repository_owner" in gate
    assert "github.event.repository.default_branch" in gate
    assert "acci:run" in gate
    assert workflow["permissions"] == {"contents": "read"}


def test_validation_has_no_provider_or_signing_secrets_or_write_permission():
    workflow = load(".github/workflows/agent.yml")
    for name in ("validate", "validate-ios"):
        job = workflow["jobs"][name]
        assert "write" not in str(job.get("permissions", {}))
        assert "secrets." not in str(job)
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/checkout"):
                assert step["with"]["persist-credentials"] == "false"
        assert "agent apply" in str(job)
    publish = workflow["jobs"]["publish"]
    assert set(publish["needs"]) == {"propose", "validate", "validate-ios"}
    assert "secrets." not in str(publish)
    assert "agent publish" in str(publish)
    assert "pytest" not in str(publish) and "xcodebuild" not in str(publish)
    assert workflow["jobs"]["propose"]["outputs"]["artifact_id"] == "${{ steps.upload.outputs.artifact-id }}"
    for name in ("validate", "validate-ios", "publish"):
        job = workflow["jobs"][name]
        downloads = [step for step in job["steps"] if step.get("uses", "").startswith("actions/download-artifact")]
        assert len(downloads) == 1
        assert downloads[0]["with"]["artifact-ids"] == "${{ needs.propose.outputs.artifact_id }}"
        assert "name" not in downloads[0]["with"]
        assert "--expected-sha256" in str(job)
        assert "${{ needs.propose.outputs.bundle_sha256 }}" in str(job)


def test_signing_is_manual_default_branch_owner_and_visibility_gated():
    for path in (".github/workflows/ios-device.yml", "acci/templates/ci-ios-sign.yml"):
        workflow = load(path)
        assert set(workflow["on"]) == {"workflow_dispatch"}
        job = workflow["jobs"]["export"]
        assert job["environment"] == "apple-signing"
        assert "vars.ACCI_IOS_SIGNING_ENABLED == 'true'" in job["if"]
        assert "github.actor == github.repository_owner" in job["if"]
        assert "default_branch" in job["if"]
        assert "inputs.acknowledge_artifact_visibility" in job["if"]
        assert workflow["permissions"] == {"contents": "read"}
        assert "ACCI_MODEL_KEY" not in str(workflow)
        assert "app-store-connect" in str(workflow["on"])  # export method, not publication
        assert "altool" not in str(workflow) and "iTMSTransporter" not in str(workflow)


def test_unsigned_templates_never_receive_signing_material():
    for path in ("acci/templates/ci-ios.yml", "examples/ci-demo/.github/workflows/ios.yml",
                 ".github/workflows/ios-validation.yml"):
        workflow = load(path)
        assert "secrets." not in str(workflow)
        assert workflow["permissions"] == {"contents": "read"}


def test_copied_ios_helper_does_not_drift():
    assert (ROOT / "examples/ci-demo/.acci/ios.py").read_bytes() == (ROOT / "acci/ios.py").read_bytes()


def test_unity_only_runs_on_an_explicit_trusted_ephemeral_runner():
    workflow = load("acci/templates/ci-unity.yml")
    assert set(workflow["on"]) == {"workflow_dispatch"}
    job = workflow["jobs"]["export"]
    assert "acci-unity-ephemeral" in job["runs-on"]
    assert "ACCI_UNITY_ENABLED" in job["if"] and "default_branch" in job["if"]
    assert "github.actor == github.repository_owner" in job["if"]