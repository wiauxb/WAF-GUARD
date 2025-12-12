"""
Log parsing utilities - adapted from logs_draft.
Parses ModSecurity audit logs into structured format.
"""
import re
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd


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
            "Local_port": int(local_port)
        }
    return {"raw_log": line}


def parse_http_request(line: str) -> Dict:
    """Parse HTTP request line into components."""
    parts = line.split(" ", 2)
    if len(parts) == 3:
        return {
            "Http_request": parts[0],
            "Request_url": parts[1],
            "Request_protocol": parts[2]
        }
    return {"raw_request": line}


def parse_payload(payload: str) -> Dict:
    """Parse payload data into a dictionary."""
    try:
        return {"payload": payload}
    except:
        return {"raw_payload": payload}


def parse_http_response(line: str) -> Dict:
    """Parse HTTP response line into components."""
    parts = line.split(" ", 2)
    if len(parts) == 3:
        return {
            "Response_protocol": parts[0],
            "Response_status_code": parts[1],
            "Response_status": parts[2]
        }
    return {"raw_response": line}


def parse_messages(messages: List[str]) -> Dict:
    """Parse messages from section H."""
    msgs = []
    for i, msg in enumerate(messages):
        if msg.startswith('Message'):
            msgs.append(f"Message {i + 1}: {msg.split('Message:', 1)[1].strip()}")
    return {"Messages": msgs}


def parse_header_line(line: str) -> Dict:
    """Parse a header line into key-value pairs."""
    if ':' in line:
        key, value = line.split(':', 1)
        return {key.strip(): value.strip()}
    return {"raw_header": line}


def transform_log_entry(entry: Dict) -> Dict:
    """Transform a single log entry into a cleaner dictionary format."""
    transformed = {}

    for key in entry.keys():
        if key == 'id':
            transformed[key] = entry[key]
            continue

        transformed[key] = []
        for i, item in enumerate(entry[key]):
            if key == 'A' and i == 0:
                transformed[key].append(parse_log_time_line(item))
            elif key == 'B' and i == 0:
                transformed[key].append(parse_http_request(item))
            elif key == 'C':
                transformed[key].append(parse_payload(item))
            elif key == 'F' and i == 0:
                transformed[key].append(parse_http_response(item))
            elif key == 'H' and item.startswith('Message'):
                if i == 0:
                    transformed[key].append(parse_messages(entry[key]))
            elif ': ' in item:
                transformed[key].append(parse_header_line(item))
            else:
                transformed[key].append(item)

        dict_new = {}
        for element in transformed[key]:
            for item in element.keys():
                dict_new[item] = element[item]
        transformed[key] = [dict_new]

    return transformed


def clean_modsecurity_logs(logs: List[Dict]) -> List[Dict]:
    """Transform ModSecurity logs into a cleaner format."""
    return [transform_log_entry(entry) for entry in logs]


def parse_log_file(file_path: Path) -> List[Dict]:
    """
    Parse ModSecurity audit log file.
    
    Args:
        file_path: Path to the audit log file
        
    Returns:
        List of parsed log entries
    """
    log_data = []
    current_log = {}
    current_section = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            match_id = re.match(r'--(\w+)-([A-Z])--', line)
            if match_id:
                log_id, section = match_id.groups()

                if section == 'A' and current_log:
                    log_data.append(current_log)
                    current_log = {}

                if 'id' not in current_log:
                    current_log['id'] = log_id
                    current_log['A'] = []
                    current_log['B'] = []
                    current_log['C'] = []
                    current_log['D'] = []
                    current_log['E'] = []
                    current_log['F'] = []
                    current_log['H'] = []
                    current_log['Z'] = []

                current_section = section
                continue

            if current_section and current_section in current_log:
                stripped_line = line.strip()
                if stripped_line:
                    if current_section == 'Z' and stripped_line.startswith('Categorie:'):
                        current_log[current_section].append(stripped_line.split(':', 1)[1].strip())
                    elif current_section == 'Z' and stripped_line.startswith('Blocked:'):
                        current_log[current_section].append('Blocked: 0')
                    elif len(stripped_line.split(':', 1)) > 1 and not stripped_line.split(':', 1)[1].strip():
                        current_log[current_section].append(f"{stripped_line.split(':', 1)[0].strip()}: empty")
                    elif current_section:
                        current_log[current_section].append(stripped_line)

    if current_log:
        log_data.append(current_log)

    return clean_modsecurity_logs(log_data)


def flatten_nested_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """Flatten nested dictionaries, keeping parent key names."""
    items = []
    for k, v in d.items():
        if k == 'C' and isinstance(v, list) and len(v) > 0:
            if 'payload' in v[0]:
                items.append(('Payloads', json.dumps(v[0].get('payload', {}))))
            continue

        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_nested_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            items.extend(flatten_nested_dict(v[0], new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def logs_to_dataframe(json_data: List[Dict]) -> pd.DataFrame:
    """Convert parsed logs to pandas DataFrame."""
    flattened_records = []

    for entry in json_data:
        flat_entry = flatten_nested_dict(entry)
        flattened_records.append(flat_entry)

    df = pd.DataFrame(flattened_records)
    df.columns = [col.replace('[]', '') for col in df.columns]

    if 'A_Time' in df.columns:
        df['Time'] = pd.to_datetime(df['A_Time'], format='%d/%b/%Y:%H:%M:%S.%f %z', errors='coerce')
        df.drop(columns=['A_Time'], inplace=True)

    return df
