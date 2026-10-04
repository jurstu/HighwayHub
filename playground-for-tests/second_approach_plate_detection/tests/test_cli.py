import json
from pathlib import Path

import cv2
import numpy as np

from alpr.cli import main


def test_cli_rejects_missing_dataset(tmp_path: Path, capsys: object) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"path": "missing"}))
    assert main(["--config", str(config), "--no-ocr"]) == 2


def test_cli_no_ocr_json(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "data"
    data.mkdir()
    image = np.full((300, 600, 3), 40, dtype=np.uint8)
    cv2.rectangle(image, (130, 120), (470, 200), (245, 245, 245), -1)
    cv2.rectangle(image, (130, 120), (470, 200), (10, 10, 10), 3)
    cv2.putText(image, "AB 1234", (160, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.imwrite(str(data / "car.png"), image)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"path": str(data)}))
    exit_code = main(["--config", str(config), "--no-ocr", "--json"])
    payload = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert exit_code == 0
    assert payload[0]["detected"] is True