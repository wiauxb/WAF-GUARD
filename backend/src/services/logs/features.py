"""
Feature extraction from parsed ModSecurity log entries.

Ported from false_positives_classification/extract_features.py. Turns a
parser.transform_entry() output into the flat 26-field dict the FP/TP model and
the analysis UI both key off.
"""
import re
from typing import Dict, List

SEVERITY_ORDER = {"CRITICAL": 4, "ERROR": 3, "WARNING": 2, "NOTICE": 1}


def parse_message_fields(message_line: str) -> Dict:
    """Extract structured fields from a single `Message:` line."""
    rule_id = re.findall(r'\[id "(\d+)"\]', message_line)
    msg = re.findall(r'\[msg "(.*?)"\]', message_line)
    severity = re.findall(r'\[severity "(.*?)"\]', message_line)
    data = re.findall(r'\[data "(.*?)"\]', message_line)
    tags = re.findall(r'\[tag "(.*?)"\]', message_line)
    matched_at = re.findall(r'at (\S+)\.', message_line)
    is_access_denied = message_line.startswith("Message: Access denied")

    return {
        "rule_id": rule_id[0] if rule_id else None,
        "msg": msg[0] if msg else None,
        "severity": severity[0] if severity else None,
        "data": data[0] if data else None,
        "tags": tags,
        "matched_at": matched_at[0] if matched_at else None,
        "is_access_denied": is_access_denied,
    }


def extract_features_from_entry(entry: Dict) -> Dict:
    """Extract a flat feature dict from a single transform_entry() output."""
    a = entry.get("A", {})
    b = entry.get("B", {})
    c = entry.get("C", {})
    f = entry.get("F", {})
    h = entry.get("H", {})

    messages_raw: List[str] = h.get("Messages", [])
    parsed_msgs = [parse_message_fields(m) for m in messages_raw]

    rule_ids = list({m["rule_id"] for m in parsed_msgs if m["rule_id"]})
    severities = list({m["severity"] for m in parsed_msgs if m["severity"]})
    tags = list({t for m in parsed_msgs for t in m["tags"]})
    msgs = [m["msg"] for m in parsed_msgs if m["msg"]]
    matched_data = [m["data"] for m in parsed_msgs if m["data"]]
    matched_locations = list({m["matched_at"] for m in parsed_msgs if m["matched_at"]})
    has_access_denied = any(m["is_access_denied"] for m in parsed_msgs)

    max_sev = (
        max(severities, key=lambda s: SEVERITY_ORDER.get(s, 0), default="NONE")
        if severities else "NONE"
    )

    action = h.get("Action", "")
    webapp_info = h.get("WebApp-Info", "")

    return {
        "transaction_id": a.get("Transaction_id", ""),
        "timestamp": a.get("Time", ""),
        "remote_address": a.get("Remote_address", ""),
        "request_method": b.get("Http_request", ""),
        "request_url": b.get("Request_url", ""),
        "request_protocol": b.get("Request_protocol", ""),
        "host": b.get("Host", ""),
        "user_agent": b.get("User-Agent", ""),
        "cookie": b.get("Cookie", ""),
        "payload": c.get("payload", ""),
        "response_status_code": f.get("Response_status_code", ""),
        "response_status": f.get("Response_status", ""),
        "rule_ids": "|".join(sorted(rule_ids)),
        "rule_count": len(rule_ids),
        "severities": "|".join(sorted(severities)),
        "max_severity": max_sev,
        "tags": "|".join(sorted(tags)),
        "messages": " || ".join(msgs),
        "matched_data": " || ".join(matched_data),
        "matched_locations": "|".join(sorted(matched_locations)),
        "has_bot_rule": "444444" in rule_ids,
        "has_access_denied": has_access_denied,
        "action": action,
        "webapp_info": webapp_info,
        "h_raw": " || ".join(messages_raw),
    }
