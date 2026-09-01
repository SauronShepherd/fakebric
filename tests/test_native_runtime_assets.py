import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_jvm_runtime_uses_immutable_base_images():
    dockerfile = (ROOT / "runtime" / "Dockerfile").read_text(encoding="utf-8")
    assert "eclipse-temurin:11-jre-noble@sha256:c55276a409ff48855ce7011fda07da527c41d57cc63b3381533fb7fea3ae027a" in dockerfile
    assert "python:3.11-slim@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0" in dockerfile
    assert "FAKEBRIC_NATIVE_EXECUTION_ENABLED=false" in dockerfile


def test_native_runtime_is_separate_and_checksum_locked():
    dockerfile = (ROOT / "runtime" / "native.Dockerfile").read_text(encoding="utf-8")
    assert "eclipse-temurin:17.0.20_8-jre-jammy@sha256:e17d77fb030dd4b642dc078d048a5fb9efcb3676ee20305d905949105a6ccd5a" in dockerfile
    assert "SPARK_VERSION=3.5.5" in dockerfile
    assert "GLUTEN_VERSION=1.6.0" in dockerfile
    assert "GLUTEN_SHA256=90f9ec6ac964bcd73893c661a9133e46afc46f8b2fa9e17c647fb3939b8b6d43" in dockerfile
    assert "sha512sum -c -" in dockerfile
    assert "sha256sum -c -" in dockerfile
    assert "FAKEBRIC_NATIVE_EXECUTION_ENABLED=false" in dockerfile
    assert "gluten-velox-bundle-spark3.5_2.12-linux_amd64-1.6.0.jar" in dockerfile
    assert "GLUTEN_BUNDLE_JAR=/opt/gluten/gluten-velox-bundle.jar" in dockerfile


def test_native_smoke_uses_approved_plugin_without_changing_default():
    smoke = (ROOT / "runtime" / "native_smoke.py").read_text(encoding="utf-8")
    assert 'GLUTEN_PLUGIN = "org.apache.gluten.GlutenPlugin"' in smoke
    assert 'GLUTEN_SHUFFLE = "org.apache.spark.shuffle.sort.ColumnarShuffleManager"' in smoke
    assert '"spark.plugins", GLUTEN_PLUGIN' in smoke
    assert '"spark.shuffle.manager", GLUTEN_SHUFFLE' in smoke
    assert '"NATIVE_INIT_FAILED"' in smoke
    assert "WholeStageTransformer" in smoke
    lock = json.loads((ROOT / "runtime-1.3.lock.json").read_text(encoding="utf-8"))
    assert lock["native"]["enabledByDefault"] is False
    assert lock["native"]["defaultMode"] == "jvm"
    assert lock["native"]["status"] == "plugin-smoke-validated"
    assert lock["native"]["pluginClass"] == "org.apache.gluten.GlutenPlugin"


def test_preliminary_native_sbom_tracks_locked_components():
    sbom = json.loads((ROOT / "runtime" / "native-sbom.spdx.json").read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    packages = {package["name"]: package for package in sbom["packages"]}
    assert packages["Apache Spark"]["versionInfo"] == "3.5.5"
    assert packages["Apache Gluten"]["versionInfo"] == "1.6.0"
    assert packages["Velox"]["versionInfo"] == "34338bfe5a95c895c90bb8fbbe2dfeeb04466087"
    checksums = {item["algorithm"]: item["checksumValue"] for item in packages["Apache Gluten"]["checksums"]}
    assert checksums["SHA256"] == "90f9ec6ac964bcd73893c661a9133e46afc46f8b2fa9e17c647fb3939b8b6d43"


def test_native_artifact_checksums_file_contains_both_hashes():
    content = (ROOT / "runtime" / "native-artifact-checksums.txt").read_text(encoding="utf-8")
    assert "90f9ec6ac964bcd73893c661a9133e46afc46f8b2fa9e17c647fb3939b8b6d43" in content
    assert "b087e962bc244d3ba4b687a953ca508182f43da962a7674d68bd9727191d6a6d124b843acefd70836cdd00647d35a45ffacd20c8989237e0d8c92c4289093a5c" in content
