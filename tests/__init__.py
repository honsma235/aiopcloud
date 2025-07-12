import json
from pathlib import Path


def load_fixture_json(filename: str) -> dict[str, object]:
    """Load a fixture and return json."""
    path = Path(str(__package__), "responses", filename)
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture_bytes(filename: str) -> bytes:
    """Load a fixture and return bytes."""
    path = Path(str(__package__), "responses", filename)
    return path.read_bytes()
