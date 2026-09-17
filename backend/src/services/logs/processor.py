"""
Text formatting for the FP/TP classifier.

Ported verbatim from false_positives_classification/prepare_data.py::format_log_text —
this is the exact template the ModernBERT model in fp_model/ was fine-tuned on, so it
must not drift from it, or FP/TP accuracy degrades silently.
"""
from typing import Any, Mapping


def format_log_text(row: Mapping[str, Any]) -> str:
    """Format an extracted-features row as natural-language text for ModernBERT input."""
    messages_text = ""
    if row.get("messages") and str(row["messages"]) not in ("", "nan"):
        for msg in str(row["messages"]).split(" || "):
            messages_text += f"    - {msg}\n"

    payload_section = ""
    if row.get("payload") and str(row["payload"]) not in ("", "nan"):
        payload_section = (
            f"** In request Body:\n"
            f"    - the payload is `{row['payload']}`\n"
        )

    return (
        f"This log has this informations about the request:\n"
        f"** In request Header:\n"
        f"    - the http request method is `{row.get('request_method', '')}`\n"
        f"    - the request url is `{row.get('request_url', '')}`\n"
        f"    - the user-agent is `{row.get('user_agent', '')}`\n"
        f"** In response header\n"
        f"    - the response status code is `{row.get('response_status_code', '')}`\n"
        f"    - the response status is `{row.get('response_status', '')}`\n"
        f"** Triggered Rules:\n"
        f"    - rule IDs: {row.get('rule_ids', '')}\n"
        f"    - number of rules triggered: {row.get('rule_count', '')}\n"
        f"    - maximum severity: {row.get('max_severity', '')}\n"
        f"    - categories/tags: {row.get('tags', '')}\n"
        f"    - action: {row.get('action', '')}\n"
        f"** In Messages\n"
        f"{messages_text}"
        f"{payload_section}"
    )
