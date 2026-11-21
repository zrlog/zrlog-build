import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.maven.bundle import check_bundle


LIBRARY = "org/example/sample/1.0.0/sample-1.0.0"
LIBRARY_ATTACHMENTS = tuple(LIBRARY + suffix for suffix in (".pom", ".jar", "-sources.jar", "-javadoc.jar"))
PARENT_POM = "org/example/parent/1.0.0/parent-1.0.0.pom"


class MavenBundleTest(unittest.TestCase):
    def write_bundle(self, path, attachments, *, bad_checksum=False, extra_file=False, javadoc_index=True):
        with zipfile.ZipFile(path, "w") as bundle:
            for name in attachments:
                data = b"fixture"
                if name.endswith("-javadoc.jar"):
                    document = io.BytesIO()
                    with zipfile.ZipFile(document, "w") as javadoc:
                        page = "index.html" if javadoc_index else "other.html"
                        javadoc.writestr(page, "API documentation")
                    data = document.getvalue()
                bundle.writestr(name, data)
                for algorithm in ("md5", "sha1", "sha256", "sha512"):
                    checksum = "bad" if bad_checksum else hashlib.new(algorithm, data).hexdigest()
                    bundle.writestr(name + "." + algorithm, checksum)
            if extra_file:
                bundle.writestr("_remote.repositories", "unwanted local metadata")

    def test_single_module_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle.zip"
            self.write_bundle(bundle, LIBRARY_ATTACHMENTS)
            self.assertEqual({"attachments": 4, "checksums": 16}, check_bundle(bundle, LIBRARY_ATTACHMENTS))

    def test_reactor_bundle_requires_the_exact_attachments(self):
        attachments = (PARENT_POM, *LIBRARY_ATTACHMENTS)
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle.zip"
            self.write_bundle(bundle, attachments)
            self.assertEqual({"attachments": 5, "checksums": 20}, check_bundle(bundle, attachments))
            with self.assertRaisesRegex(ValueError, "Unexpected bundle content"):
                check_bundle(bundle, (PARENT_POM,))
            self.write_bundle(bundle, LIBRARY_ATTACHMENTS)
            with self.assertRaisesRegex(ValueError, "Unexpected bundle content"):
                check_bundle(bundle, attachments)

    def test_rejects_bad_checksums_unexpected_files_and_missing_javadoc_index(self):
        cases = (
            ({"bad_checksum": True}, "Bad checksum"),
            ({"extra_file": True}, "Unexpected bundle content"),
            ({"javadoc_index": False}, "Missing Javadoc index"),
        )
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle.zip"
            for options, error in cases:
                with self.subTest(options=options):
                    self.write_bundle(bundle, LIBRARY_ATTACHMENTS, **options)
                    with self.assertRaisesRegex(ValueError, error):
                        check_bundle(bundle, LIBRARY_ATTACHMENTS)
