"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigurationError, load_data_path
from .ocr import EasyOCRBackend
from .pipeline import ALPRPipeline, is_exact_match


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect and recognize license plates in configured images.")
    parser.add_argument("--config", type=Path, default=Path("pathToData.json"))
    parser.add_argument("--output-dir", type=Path, help="save annotated images and rectified crops")
    parser.add_argument("--no-ocr", action="store_true", help="detect plates without loading EasyOCR")
    parser.add_argument("--gpu", action="store_true", help="let EasyOCR use a CUDA GPU")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data_path = load_data_path(args.config.resolve())
        backend = None if args.no_ocr else EasyOCRBackend(gpu=args.gpu)
        pipeline = ALPRPipeline(ocr=backend)
        results = pipeline.process_directory(data_path)
    except ConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output_dir:
        for result in results:
            pipeline.save_debug(result, args.output_dir.resolve())
    if args.as_json:
        payload = [
            {
                "file": result.path.name,
                "detected": result.detected,
                "text": result.text,
                "confidence": round(result.confidence, 4),
                "detector_score": round(result.detector_score, 4),
                "expected": result.expected,
                "match": is_exact_match(result) if result.expected is not None and result.text else None,
                "error": result.error,
            }
            for result in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(f"Dataset: {data_path}")
        print(f"{'FILE':<18} {'DETECTED':<9} {'TEXT':<14} {'OCR':>6} {'EXPECTED':<14} STATUS")
        for result in results:
            if result.expected is not None and result.text:
                status = "MATCH" if is_exact_match(result) else "MISS"
            else:
                status = result.error or "OK"
            print(
                f"{result.path.name:<18} {str(result.detected):<9} {result.text or '-':<14} "
                f"{result.confidence:>6.2f} {result.expected or '-':<14} {status}"
            )
        labeled = [result for result in results if result.expected is not None]
        detected = sum(result.detected for result in results)
        matches = sum(is_exact_match(result) for result in labeled)
        print(f"Detected {detected}/{len(results)}; exact OCR matches {matches}/{len(labeled)}")
    return 0 if all(result.detected for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
