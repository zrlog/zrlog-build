"""Validate a local Maven Central bundle against its expected attachment paths."""

from collections.abc import Iterable
import hashlib
import io
from pathlib import Path
import zipfile


def check_bundle(path: Path, expected_attachments: Iterable[str]) -> dict[str, int]:
    attachments = set(expected_attachments)
    algorithms = ("md5", "sha1", "sha256", "sha512")
    checksums = {name + "." + algorithm for name in attachments for algorithm in algorithms}
    expected = attachments | checksums

    with zipfile.ZipFile(path) as bundle:
        names = {name for name in bundle.namelist() if not name.endswith("/")}
        if names != expected:
            raise ValueError(f"Unexpected bundle content: missing={expected - names}, extra={names - expected}")

        for name in attachments:
            data = bundle.read(name)
            if not data:
                raise ValueError(f"Empty attachment: {name}")
            for algorithm in algorithms:
                if bundle.read(name + "." + algorithm).decode().strip() != hashlib.new(algorithm, data).hexdigest():
                    raise ValueError(f"Bad checksum: {name}")
            if name.endswith("-javadoc.jar"):
                with zipfile.ZipFile(io.BytesIO(data)) as javadoc:
                    if "index.html" not in javadoc.namelist():
                        raise ValueError(f"Missing Javadoc index: {name}")

    return {"attachments": len(attachments), "checksums": len(checksums)}
