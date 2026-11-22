import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "plugin"


class PluginBuildTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.resources = self.root / "src/main/resources"
        self.resources.mkdir(parents=True)
        (self.resources / "plugin.properties").write_text("shortName=example\nversion=dev\n")
        (self.resources / "preview-image.svg").write_text("<svg/>")
        (self.root / "pom.xml").write_text("<project>\n  <version>4.2.0-SNAPSHOT</version>\n</project>\n")
        self.calls = self.root / "maven.log"
        self.output = self.root / "github-output"
        self.artifacts = self.root / "download/plugin"
        self.env = {
            **os.environ,
            "ARTIFACT_BUCKET": "example-bucket",
            "ARTIFACT_ENDPOINT": "https://publish.example",
            "BUILD_NUMBER": "38",
            "CALLS": str(self.calls),
            "GITHUB_OUTPUT": str(self.output),
            "PATH": f"{self.root}:{os.environ['PATH']}",
            "PLUGIN_PACKAGE_PREVIEW": "true",
            "PLUGIN_NATIVE_SKIP_TESTS": "false",
        }
        self.executable("java", "exit 0")
        self.executable("uname", '''if [[ "$1" == "-m" ]]; then
  printf "%s\\n" "${MOCK_MACHINE:-x86_64}"
else
  printf "%s\\n" "${MOCK_SYSTEM:-Linux}"
fi''')
        self.executable("dpkg", "echo arm64")
        self.executable("mvnw", '''printf "%s\\n" "$*" >> "$CALLS"
if [[ " $* " == *" clean "* ]]; then
  rm -rf target
elif [[ " $* " == *" -Pnative "* && " $* " == *" package "* ]]; then
  mkdir -p target
  printf native > "target/example${MOCK_EXTENSION:-}"
fi''')
        self.executable("aws", 'printf "%s\\n" "$@" > aws.log')

    def executable(self, name, body):
        path = self.root / name
        path.write_text("#!/usr/bin/env bash\nset -eu\n" + body + "\n")
        path.chmod(0o755)

    def run_script(self, name, *args):
        return subprocess.run(
            ["bash", SCRIPTS / f"{name}.sh", *args],
            check=True, cwd=self.root, env=self.env, capture_output=True, text=True,
        )

    def test_jar_cleans_before_metadata_and_uses_caller_maven_profile(self):
        self.run_script("build-jar", self.artifacts, "-B", "-ntp")
        self.assertEqual(self.calls.read_text().splitlines(), [
            "-B -ntp clean",
            f"-B -ntp -PnodeBuild package assembly:single -DoutputDirectory={self.artifacts}",
        ])
        self.assertEqual(self.artifacts.joinpath("example.properties").read_text(),
                         "shortName=example\nversion=4.2.38\n")
        self.assertEqual(self.artifacts.joinpath("example.svg").read_text(), "<svg/>")

    def test_core_build_info_resolves_version_without_maven_prompts(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run([
            "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "Fixture",
        ], cwd=self.root, check=True)
        self.executable("mvnw", '''
[[ "$*" == "-B -q help:evaluate -Dexpression=project.version -DforceStdout" ]]
printf '4.2.0-SNAPSHOT'
''')

        self.run_script("core/build-info")

        properties = self.resources.joinpath("conf.properties").read_text().splitlines()
        self.assertIn("version=4.2.0", properties)
        self.assertIn("buildNumber=1", properties)

    def test_native_keeps_agent_sequence_optional_preview_and_outputs(self):
        self.env["PLUGIN_PACKAGE_PREVIEW"] = "false"
        self.env["PLUGIN_NATIVE_SKIP_TESTS"] = "true"
        self.resources.joinpath("preview-image.svg").unlink()
        self.run_script("build-native", self.artifacts)
        self.assertEqual(self.calls.read_text().splitlines(), [
            "clean", "-PnodeBuild package",
            "-Pnative -DskipNativeTests -Dagent exec:exec@java-agent -U",
            "-Pnative -DskipNativeTests package",
        ])
        artifact = self.artifacts / "example-Linux-arm64.bin"
        self.assertEqual(artifact.read_text(), "native")
        self.assertFalse(self.artifacts.joinpath("example.svg").exists())
        self.assertEqual(dict(line.split("=", 1) for line in self.output.read_text().splitlines()), {
            "artifact_file": str(artifact),
            "artifact_name": "example",
            "artifact_version": "4.2.38",
            "artifact_architecture": "Linux-arm64",
        })

    def test_native_keeps_tests_enabled_by_default(self):
        self.env.pop("PLUGIN_NATIVE_SKIP_TESTS")
        self.run_script("build-native", self.artifacts, "-B", "-ntp")
        self.assertEqual(self.calls.read_text().splitlines(), [
            "-B -ntp clean", "-B -ntp -PnodeBuild package",
            "-B -ntp -Pnative -Dagent exec:exec@java-agent -U",
            "-B -ntp -Pnative package",
        ])

    def test_native_staging_preserves_windows_extension_and_macos_name(self):
        for system, machine, source_extension, architecture, file_extension in (
            ("Darwin", "arm64", "", "Darwin-arm64", ".bin"),
            ("MINGW64_NT", "x86_64", ".exe", "Windows-x86_64", ".exe"),
        ):
            with self.subTest(system=system):
                self.env["MOCK_SYSTEM"] = system
                self.env["MOCK_MACHINE"] = machine
                self.env["MOCK_EXTENSION"] = source_extension
                self.run_script("build-native", self.artifacts)
                artifact = self.artifacts / f"example-{architecture}{file_extension}"
                self.assertEqual(artifact.read_text(), "native")

    def test_upload_generates_checksum_for_the_final_binary(self):
        self.artifacts.mkdir(parents=True)
        self.artifacts.joinpath("example.bin").write_bytes(b"processed")
        self.run_script("upload-bin", self.artifacts.parent, "plugin")
        self.assertEqual(self.artifacts.joinpath("example.bin.md5").read_text(),
                         hashlib.md5(b"processed").hexdigest() + "  example.bin\n")
        self.assertEqual(self.root.joinpath("aws.log").read_text().splitlines()[:5], [
            "s3", "cp", str(self.artifacts), "s3://example-bucket/plugin/", "--recursive",
        ])


if __name__ == "__main__":
    unittest.main()
