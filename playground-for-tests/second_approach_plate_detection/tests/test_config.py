import json
from pathlib import Path

import pytest

from alpr.config import ConfigurationError, discover_images, load_data_path, load_labels


def test_configuration_discovery_and_labels(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "B.PNG").write_bytes(b"image")
    (data / "a.jpg").write_bytes(b"image")
    (data / "ignored.txt").write_text("no")
    (data / "plates.json").write_text(json.dumps({"plates": [{"file": "a.jpg", "plate": "AB 123"}]}))
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"path": "data"}))

    assert load_data_path(config) == data
    assert [path.name for path in discover_images(data)] == ["a.jpg", "B.PNG"]
    assert load_labels(data) == {"a.jpg": "AB 123"}


@pytest.mark.parametrize("document", [{}, {"path": 42}, []])
def test_invalid_configuration_schema(tmp_path: Path, document: object) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps(document))
    with pytest.raises(ConfigurationError):
        load_data_path(config)


def test_empty_dataset_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="no supported images"):
        discover_images(tmp_path)
