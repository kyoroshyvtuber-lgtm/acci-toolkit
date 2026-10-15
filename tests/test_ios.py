import datetime as dt
import hashlib
import plistlib
import zipfile

import pytest

from acci import ios


def profile():
    return {"UUID": "01234567-89AB-CDEF-0123-456789ABCDEF",
            "ExpirationDate": dt.datetime(2099, 1, 1),
            "TeamIdentifier": ["ABCDEFGHIJ"],
            "ApplicationIdentifierPrefix": ["ABCDEFGHIJ"],
            "DeveloperCertificates": [b"synthetic-certificate"],
            "ProvisionedDevices": ["synthetic-device"],
            "Entitlements": {"application-identifier": "ABCDEFGHIJ.dev.acci.*",
                             "com.apple.developer.team-identifier": "ABCDEFGHIJ",
                             "get-task-allow": True}}


def test_simulator_chooses_newest_available_compatible_iphone():
    types = {"devicetypes": [
        {"identifier": "old", "productFamily": "iPhone", "maxRuntimeVersion": 16 << 16},
        {"identifier": "new", "productFamily": "iPhone", "minRuntimeVersion": 18 << 16},
        {"identifier": "ipad", "productFamily": "iPad"}]}
    runtimes = {"runtimes": [
        {"identifier": "com.apple.iOS-17-0", "version": "17.0", "isAvailable": True},
        {"identifier": "com.apple.iOS-18-2", "version": "18.2", "isAvailable": True},
        {"identifier": "com.apple.iOS-99-0", "version": "99.0", "isAvailable": False}]}
    assert ios.choose_simulator(types, runtimes) == ("new", "com.apple.iOS-18-2")
    with pytest.raises(ValueError, match="No compatible"):
        ios.choose_simulator(types, {"runtimes": []})


def test_development_profile_and_export_options_do_not_upload():
    checked = ios.validate_profile(profile(), "ABCDEFGHIJ", "dev.acci.demo", "debugging")
    assert checked["certificate_sha1"] == [hashlib.sha1(b"synthetic-certificate").hexdigest().upper()]
    options = ios.export_options("ABCDEFGHIJ", "dev.acci.demo", checked["uuid"], "ABC", "debugging")
    assert options["destination"] == "export"
    assert options["provisioningProfiles"] == {"dev.acci.demo": checked["uuid"]}


@pytest.mark.parametrize("change,match", [
    ({"ExpirationDate": dt.datetime(2000, 1, 1)}, "expired"),
    ({"TeamIdentifier": ["OTHERTEAMX"]}, "another team"),
    ({"UUID": "../../bad"}, "UUID"),
    ({"DeveloperCertificates": []}, "certificates"),
    ({"ProvisionsAllDevices": True}, "Enterprise"),
])
def test_rejects_bad_profiles(change, match):
    with pytest.raises(ValueError, match=match):
        ios.validate_profile({**profile(), **change}, "ABCDEFGHIJ", "dev.acci.demo", "debugging")


def test_rejects_bundle_and_distribution_mismatch():
    with pytest.raises(ValueError, match="Bundle"):
        ios.validate_profile(profile(), "ABCDEFGHIJ", "another.app", "debugging")
    for method in ("release-testing", "app-store-connect"):
        with pytest.raises(ValueError, match=method):
            ios.validate_profile(profile(), "ABCDEFGHIJ", "dev.acci.demo", method)
    with pytest.raises(ValueError, match="export method"):
        ios.validate_profile(profile(), "ABCDEFGHIJ", "dev.acci.demo", "upload")


def test_distribution_profile_modes():
    value = profile()
    value["Entitlements"]["get-task-allow"] = False
    ios.validate_profile(value, "ABCDEFGHIJ", "dev.acci.demo", "release-testing")
    value.pop("ProvisionedDevices")
    ios.validate_profile(value, "ABCDEFGHIJ", "dev.acci.demo", "app-store-connect")


def test_ipa_inspection(tmp_path):
    path = tmp_path / "App.ipa"
    def write(platform="iphoneos"):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Payload/App.app/Info.plist", plistlib.dumps(
                {"CFBundleIdentifier": "dev.acci.demo", "CFBundleExecutable": "App",
                 "DTPlatformName": platform}))
            archive.writestr("Payload/App.app/App", b"synthetic-binary")
    write()
    assert ios.inspect_ipa(path, "dev.acci.demo")["sha256"] == ios.sha256(path)
    with pytest.raises(ValueError, match="identifier"):
        ios.inspect_ipa(path, "different.bundle")
    write("iphonesimulator")
    with pytest.raises(ValueError, match="device build"):
        ios.inspect_ipa(path, "dev.acci.demo")


def test_preflight_never_discloses_private_values(monkeypatch):
    monkeypatch.setenv("IOS_P12_PASSWORD", "synthetic-private-value")
    report = str(ios.preflight(signing=True))
    assert "synthetic-private-value" not in report
    assert "IOS_P12_BASE64" in report


def test_commands_remove_credentials_from_build_environment(tmp_path, monkeypatch):
    for key in ("IOS_P12_BASE64", "OPENAI_API_KEY", "GITHUB_TOKEN"):
        monkeypatch.setenv(key, "synthetic")
    env = ios.Commands(tmp_path, tmp_path).env
    assert not {"IOS_P12_BASE64", "OPENAI_API_KEY", "GITHUB_TOKEN"} & env.keys()