"""Automatic license-plate detection and recognition."""

from .detector import PlateDetector
from .pipeline import ALPRPipeline

__all__ = ["ALPRPipeline", "PlateDetector"]
