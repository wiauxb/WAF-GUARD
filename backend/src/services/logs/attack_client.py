"""
Step 2: Batched attack-type classification via the external model service.

POST /predict with {"logs": [text1, text2, ...]}
response       ->    {"predictions": [{"labels": [...], "probabilities": [...]}, ...]}

Ported from false_positives_classification/api/services/attack_client.py, with one change:
texts are sent in fixed-size chunks instead of one request. A single request carrying
~1000 logs made model_na drop the connection.
"""
import logging
from typing import List

import httpx

from .schemas import AttackTypeResult

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 64


async def _predict_chunk(
    texts: List[str],
    client: httpx.AsyncClient,
    model_service_url: str,
) -> List[AttackTypeResult]:
    """One request. Always returns exactly len(texts) results, fallback labels on error."""
    fallback_label = None
    try:
        response = await client.post(
            f"{model_service_url}/predict",
            json={"logs": texts},
            timeout=3600,
        )
        response.raise_for_status()
        predictions = response.json().get("predictions", [])

        results = [
            AttackTypeResult(
                labels=pred.get("labels", ["unknown"]) or ["unknown"],
                probabilities=pred.get("probabilities", []),
            )
            for pred in predictions
        ]
        if len(results) != len(texts):
            logger.error(f"model service returned {len(results)} predictions for {len(texts)} logs")
            fallback_label = "service_error"
        else:
            return results

    except httpx.ConnectError:
        fallback_label = "service_unavailable"
    except httpx.HTTPStatusError:
        fallback_label = "service_error"
    except httpx.TimeoutException:
        fallback_label = "service_timeout"
    except httpx.TransportError:
        # e.g. RemoteProtocolError when the service drops the connection mid-request
        fallback_label = "service_unavailable"

    return [AttackTypeResult(labels=[fallback_label]) for _ in texts]


async def get_attack_types_batch(
    texts: List[str],
    client: httpx.AsyncClient,
    model_service_url: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[AttackTypeResult]:
    """Classify `texts` in chunks of `batch_size`, one AttackTypeResult per text.

    Chunks are sent sequentially. A failing chunk only marks its own entries with a
    fallback label; the other chunks are unaffected. The result always has len(texts) items.
    """
    if not texts:
        return []

    results: List[AttackTypeResult] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start:start + batch_size]
        results.extend(await _predict_chunk(chunk, client, model_service_url))
    return results
