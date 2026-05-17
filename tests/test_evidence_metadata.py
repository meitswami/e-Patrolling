"""Evidence integrity metadata helpers."""

import tempfile
from pathlib import Path

from evidence.metadata import build_chain_entry, sha256_file


def test_sha256_file_roundtrip():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(b"patrol-evidence-test")
        path = Path(tmp.name)
    try:
        digest = sha256_file(path)
        assert digest is not None
        assert len(digest) == 64
    finally:
        path.unlink(missing_ok=True)


def test_build_chain_entry_includes_hash():
    entry = build_chain_entry(
        collector="test",
        model="keyword_v1",
        screenshot_path="evidence/x.png",
        screenshot_hash="abc",
    )
    assert entry["integrity"] == "sha256"
    assert entry["screenshot_sha256"] == "abc"
