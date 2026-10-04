"""Configuration and dataset discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class ConfigurationError(ValueError):
    """Raised for an invalid configuration or dataset."""


def load_data_path(config_path: Path) -> Path:
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {config_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"cannot read configuration {config_path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("path"), str):
        raise ConfigurationError("configuration must contain a string 'path'")
    raw_path = Path(document["path"]).expanduser()
    data_path = raw_path if raw_path.is_absolute() else config_path.parent / raw_path
    data_path = data_path.resolve()
    if not data_path.is_dir():
        raise ConfigurationError(f"dataset directory not found: {data_path}")
    return data_path


def discover_images(data_path: Path) -> list[Path]:
    images = sorted(
        (path for path in data_path.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )
    if not images:
        raise ConfigurationError(f"no supported images found in: {data_path}")
    return images


def load_labels(data_path: Path) -> dict[str, str]:
    labels_path = data_path / "plates.json"
    if not labels_path.exists():
        return {}
    try:
        document: Any = json.loads(labels_path.read_text(encoding="utf-8"))
        records = document["plates"]
        if not isinstance(records, list):
            raise TypeError("'plates' is not a list")
        labels: dict[str, str] = {}
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("file"), str) or not isinstance(record.get("plate"), str):
                raise TypeError("each label requires string 'file' and 'plate' fields")
            labels[record["file"]] = record["plate"]
        return labels
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ConfigurationError(f"invalid labels file {labels_path}: {exc}") from exc
