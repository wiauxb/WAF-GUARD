"""
Log parsing utilities.
Parses ModSecurity audit logs into structured format.

Ported from false_positives_classification/parse_owasp.py: captures ALL `Message:`
lines from section H (the old parser only kept the first one), and also handles
sections I (request body, production WAF) and J (upload info, production WAF).
"""
import re
from typing import Dict, List
from pathlib import Path


def parse_log_time_line(line: str) -> Dict:
    """Parse the first line of section A into components."""
    pattern = r'\[(.*?)\] (\S+) (\S+) (\d+) (\S+) (\d+)'
    match = re.match(pattern, line)

    if match:
        time, transaction_id, remote_address, remote_port, local_address, local_port = match.groups()
        return {
            "Time": time,
            "Transaction_id": transaction_id,
            "Remote_address": remote_address,
            "Remote_port": int(remote_port),
            "Local_address": local_address,
            "Local_port": int(local_port),
        }
    return {"raw_log": line}


def parse_http_request(line: str) -> Dict:
    """Parse HTTP request line into components."""
    parts = line.split(" ", 2)
    if len(parts) == 3:
        return {
            "Http_request": parts[0],
            "Request_url": parts[1],
            "Request_protocol": parts[2],
        }
    return {"raw_request": line}


def parse_http_response(line: str) -> Dict:
    """Parse HTTP response line into components."""
    parts = line.split(" ", 2)
    if len(parts) == 3:
        return {
            "Response_protocol": parts[0],
            "Response_status_code": parts[1],
            "Response_status": parts[2],
        }
    return {"raw_response": line}


def parse_header_line(line: str) -> Dict:
    """Parse a header line into key-value pairs."""
    if ':' in line:
        key, value = line.split(':', 1)
        return {key.strip(): value.strip()}
    return {"raw_header": line}


def parse_log_file(file_path: Path) -> List[Dict]:
    """
    Parse a ModSecurity audit log file into a list of raw structured entries
    (one dict of section -> list[str] per transaction, keyed 'A'..'J').
    """
    entries: List[Dict] = []
    current_log: Dict = {}
    current_section = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match_id = re.match(r'--(\w+)-([A-Z])--', line)
            if match_id:
                log_id, section = match_id.groups()

                if section == 'A' and current_log:
                    entries.append(current_log)
                    current_log = {}

                if 'id' not in current_log:
                    current_log = {
                        'id': log_id, 'A': [], 'B': [], 'C': [], 'D': [], 'E': [],
                        'F': [], 'H': [], 'I': [], 'J': [], 'Z': [],
                    }

                current_section = section
                continue

            if current_section and current_section in current_log:
                stripped = line.strip()
                if stripped:
                    current_log[current_section].append(stripped)

    if current_log:
        entries.append(current_log)

    return entries


def transform_entry(entry: Dict) -> Dict:
    """Transform a single raw parsed entry into a structured dict (sections A-J)."""
    result = {"id": entry["id"]}

    # Section A: timestamp + connection metadata
    result["A"] = parse_log_time_line(entry["A"][0]) if entry.get("A") else {}

    # Section B: HTTP request line + request headers
    b_data: Dict = {}
    if entry.get("B"):
        b_data.update(parse_http_request(entry["B"][0]))
        for line in entry["B"][1:]:
            b_data.update(parse_header_line(line))
    result["B"] = b_data

    # Section C: payload
    result["C"] = {"payload": "\n".join(entry["C"])} if entry.get("C") else {}

    # Section F: HTTP response + response headers
    f_data: Dict = {}
    if entry.get("F"):
        f_data.update(parse_http_response(entry["F"][0]))
        for line in entry["F"][1:]:
            f_data.update(parse_header_line(line))
    result["F"] = f_data

    # Section H: ALL messages and metadata (capture everything)
    h_messages: List[str] = []
    h_metadata: Dict = {}
    for line in entry.get("H", []):
        if line.startswith("Message:"):
            h_messages.append(line)
        elif line.startswith("Apache-Error:"):
            continue  # skip duplicated Apache-Error lines
        elif ':' in line:
            key, value = line.split(':', 1)
            h_metadata[key.strip()] = value.strip()
    result["H"] = {"Messages": h_messages, **h_metadata}

    # Section I: request body (production WAF)
    result["I"] = {"body": "\n".join(entry["I"])} if entry.get("I") else {}

    # Section J: upload info (production WAF)
    result["J"] = {"upload_info": "\n".join(entry["J"])} if entry.get("J") else {}

    return result


def clean_modsecurity_logs(logs: List[Dict]) -> List[Dict]:
    """Transform a list of raw parsed entries into their structured form."""
    return [transform_entry(entry) for entry in logs]
