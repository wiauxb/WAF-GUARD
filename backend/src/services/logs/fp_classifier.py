"""
Step 1: FP/TP classification, via the fp_classifier service (fine-tuned ModernBERT).

The model runs in its own container (see fp_classifier/ and the fp_classifier_na service in
docker-compose.yaml). This module parses the log file, extracts features, formats the text
the model was trained on, and calls the service for the prediction.
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

import httpx

from .parser import parse_log_file, transform_entry
from .features import extract_features_from_entry
from .processor import format_log_text

logger = logging.getLogger(__name__)


class FPClassifierUnavailable(RuntimeError):
    """The fp_classifier service cannot be reached or returned an error."""


class FPClassifier:
    """Parses logs locally and classifies them through the fp_classifier service."""

    def __init__(self, service_url: str, http_client: httpx.AsyncClient) -> None:
        self.service_url = service_url.rstrip("/")
        self.http_client = http_client

    async def is_available(self) -> bool:
        try:
            r = await self.http_client.get(f"{self.service_url}/health", timeout=5)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except (httpx.HTTPError, ValueError):
            return False

    @staticmethod
    def _prepare(log_file: Path):
        """Parse + extract features + format text. CPU/IO bound, run off the event loop."""
        raw_entries = parse_log_file(log_file)
        transformed = [transform_entry(e) for e in raw_entries]
        features = [extract_features_from_entry(e) for e in transformed]
        texts = [format_log_text(f) for f in features]
        return transformed, features, texts

    async def _predict_texts(self, texts: List[str], batch_size: int) -> List[Dict]:
        preds: List[Dict] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                r = await self.http_client.post(
                    f"{self.service_url}/predict", json={"texts": batch}, timeout=3600
                )
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise FPClassifierUnavailable(
                    f"fp_classifier service error {e.response.status_code}: {e.response.text[:200]}"
                ) from e
            except httpx.HTTPError as e:
                raise FPClassifierUnavailable(
                    f"Cannot reach fp_classifier service at {self.service_url}: {e!r}"
                ) from e

            got = r.json().get("predictions", [])
            if len(got) != len(batch):
                raise FPClassifierUnavailable(
                    f"fp_classifier returned {len(got)} predictions for {len(batch)} texts"
                )
            preds.extend(got)
        return preds

    async def predict(self, log_file: Path, batch_size: int = 16) -> List[Dict]:
        """Parse a raw ModSecurity log file and return per-entry prediction dicts.

        Each dict contains:
            _parsed   : full transform_entry() output (sections A/B/C/F/H/I/J)
            _features : the 26 fields from extract_features_from_entry()
            _text     : formatted NL text (used for the step-2 attack classification)
            prediction, confidence, fp_probability, tp_probability
        """
        loop = asyncio.get_running_loop()
        transformed, features, texts = await loop.run_in_executor(None, self._prepare, log_file)
        if not texts:
            return []

        preds = await self._predict_texts(texts, batch_size)

        return [
            {
                "_parsed": transformed[i],
                "_features": features[i],
                "_text": texts[i],
                "prediction": p["prediction"],
                "confidence": p["confidence"],
                "fp_probability": p["fp_probability"],
                "tp_probability": p["tp_probability"],
            }
            for i, p in enumerate(preds)
        ]
