"""
Step 2: Batch attack-type classification via the external model service.

POST /predict with {"logs": [text1, text2, ...]}
response       ->    {"predictions": [{"labels": [...], "probabilities": [...]}, ...]}

Ported from false_positives_classification/api/services/attack_client.py.
"""
from typing import List

import httpx

from .schemas import AttackTypeResult

_FALLBACK_LABELS = {
    "connect": "service_unavailable",
    "status": "service_error",
    "timeout": "service_timeout",
}


async def get_attack_types_batch(
    texts: List[str],
    client: httpx.AsyncClient,
    model_service_url: str,
) -> List[AttackTypeResult]:
    """Send all TP texts in a single batch call and return one AttackTypeResult per text.

    On any error, every entry receives a fallback AttackTypeResult so the
    caller always gets a list of the same length as `texts`.
    """
    if not texts:
        return []

    fallback_label = None
    try:
        response = await client.post(
            f"{model_service_url}/predict",
            json={"logs": texts},
            timeout=3600,
        )
        response.raise_for_status()
        data = response.json()
        predictions = data.get("predictions", [])

        results = []
        for pred in predictions:
            results.append(
                AttackTypeResult(
                    labels=pred.get("labels", ["unknown"]) or ["unknown"],
                    probabilities=pred.get("probabilities", []),
                )
            )
        return results

    except httpx.ConnectError:
        fallback_label = _FALLBACK_LABELS["connect"]
    except httpx.HTTPStatusError:
        fallback_label = _FALLBACK_LABELS["status"]
    except httpx.TimeoutException:
        fallback_label = _FALLBACK_LABELS["timeout"]

    return [AttackTypeResult(labels=[fallback_label]) for _ in texts]
