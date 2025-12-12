"""
Log processing utilities for normalization and formatting.
Adapted from logs_draft setup.py.
"""
import pandas as pd
from typing import Dict, List, Tuple


# Standard features expected in logs
FEATURES = [
    'A_Transaction_id', 'Time', 'A_Remote_address', 'A_Remote_port', 
    'A_Local_address', 'A_Local_port', 'B_User-Agent', 'B_Http_request', 
    'B_Request_url', 'Payloads', 'F_Response_status_code', 'F_Response_status', 
    'H_Messages', 'Z_Categories'
]


def format_row(row: pd.Series) -> str:
    """
    Format a log row into a text description suitable for LLM processing.
    
    Args:
        row: DataFrame row with log data
        
    Returns:
        Formatted text description of the log
    """
    messages = []
    if isinstance(row['H_Messages'], str) and row['H_Messages'] != 'empty':
        try:
            messages = eval(row['H_Messages'])
        except:
            messages = ["empty"]
    elif isinstance(row['H_Messages'], list):
        messages = row['H_Messages']

    messages_formatted = []
    for message in messages:
        parts = message.split('[msg "')
        if len(parts) > 1:
            msg_part = parts[0]
            id_part = parts[1].split('"]')[0] if '"]' in parts[1] else ''
            messages_formatted.append(f'- `{msg_part}` with information `{id_part}`')
    
    messages_text = '\n'.join(messages_formatted)
    
    # Check if row['Payloads'] is nan
    if not pd.isna(row['Payloads']):
        return (
            f'This log has this informations about the request:\n'
            f'** In request Header:\n'
            f'    - the http request method is `{row["B_Http_request"]}`\n'
            f'    - the request url is `{row["B_Request_url"]}`\n'
            f'    - the user-agent is `{row["B_User-Agent"]}`\n'
            f'** In response header\n'
            f'    - the response status code is `{row["F_Response_status_code"]}`\n'
            f'    - the response status is `{row["F_Response_status"]}`\n'
            f'** In Messages\n'
            f'{messages_text}\n'
            f'** In request Body:\n'
            f'    - the payload is `{row["Payloads"]}`\n'
        )
    else:
        return (
            f'This log has this informations about the request:\n'
            f'** In request Header:\n'
            f'    - the http request method is `{row["B_Http_request"]}`\n'
            f'    - the request url is `{row["B_Request_url"]}`\n'
            f'    - the user-agent is `{row["B_User-Agent"]}`\n'
            f'** In response header\n'
            f'    - the response status code is `{row["F_Response_status_code"]}`\n'
            f'    - the response status is `{row["F_Response_status"]}`\n'
            f'** In Messages\n'
            f'{messages_text}\n'
        )


def format_tags(row: pd.Series) -> List[str]:
    """
    Extract message tags from log row.
    
    Args:
        row: DataFrame row with log data
        
    Returns:
        List of message tags
    """
    messages = []
    if isinstance(row['H_Messages'], str) and row['H_Messages'] != 'empty':
        try:
            messages = eval(row['H_Messages'])
        except:
            messages = ["empty"]
    elif isinstance(row['H_Messages'], list):
        messages = row['H_Messages']

    msg_tags = []
    for message in messages:
        parts = message.split('[msg "')
        if len(parts) > 1:
            id_part = parts[1].split('"]')[0] if '"]' in parts[1] else ''
            msg_tags.append(id_part)
    
    return msg_tags


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize log DataFrame for processing.
    
    Args:
        df: Raw DataFrame from parsed logs
        
    Returns:
        Normalized DataFrame with consistent columns and formatting
    """
    # Ensure all expected features exist
    for feature in FEATURES:
        if feature not in df.columns:
            df[feature] = "empty"
    
    df_new = df.copy()
    
    # Convert response status code to numeric
    df_new['F_Response_status_code'] = pd.to_numeric(
        df_new['F_Response_status_code'], 
        errors='coerce'
    ).astype('Int64')
    
    df_new = df_new.fillna("empty")
    
    # Create formatted log and tags
    df_new['Formatted_Log'] = df_new.apply(format_row, axis=1)
    df_new['msgtags'] = df_new.apply(format_tags, axis=1)

    for col in df_new.columns:
        if len(col) > 2 and col[0].isupper() and col[1] == '_' and col[2].islower():
            # rename the column by adding prefix SYNTAXE_ERROR to the column name
            col = "SYNTAXE_ERROR_" + col
    
    # Normalize column names
    df_new.columns = [
        f"{col[0]}_{''.join(col[2:]).replace('-', '_').lower()}" 
        if len(col) > 2 and col[0].isupper() and col[1] == '_' 
        else col.lower() 
        for col in df_new.columns
    ]
    
    return df_new


def create_feature_target_sets(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Create feature (X) and target (y) sets for classification.
    
    Args:
        df: Normalized DataFrame
        
    Returns:
        Tuple of (X, y) where X is formatted logs and y is categories
    """
    X = df['formatted_log']
    y = df.get('z_categories', pd.Series(['Unknown'] * len(df)))
    
    return X, y


def compute_marginals(probabilities: Dict[str, float]) -> Dict[str, float]:
    """
    Compute marginal probabilities for individual categories.
    
    Args:
        probabilities: Dict mapping category combinations to probabilities
        
    Returns:
        Dict mapping individual categories to marginal probabilities
    """
    marginals = {}
    for combo, p in probabilities.items():
        if p == 0.0:
            continue
        labels = [label.strip() for label in combo.split(',') if label.strip()]
        for label in labels:
            marginals[label] = marginals.get(label, 0.0) + p
    return marginals


def normalize_probabilities(probabilities: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize probabilities to sum to 1.
    
    Args:
        probabilities: Dict of probabilities
        
    Returns:
        Normalized probabilities
        
    Raises:
        ValueError: If total probability is zero or negative
    """
    total = sum(probabilities.values())
    if total <= 0.0:
        raise ValueError("Total probability is zero or negative; cannot normalize.")
    return {combo: (p / total if p != 0.0 else 0.0) for combo, p in probabilities.items()}


def pretty_probabilities(probabilities: Dict[str, float]) -> List[Dict[str, float]]:
    """
    Format probabilities for display.
    
    Args:
        probabilities: Raw probability dictionary
        
    Returns:
        List containing formatted probability dictionary sorted by value
    """
    try:
        normalized = normalize_probabilities(probabilities)
    except ValueError as e:
        print(f"Normalization error: {e}")
        normalized = probabilities

    marginals = compute_marginals(normalized)

    total_m = sum(marginals.values())
    if total_m > 0.0:
        marginals = {cat: prob / total_m for cat, prob in marginals.items()}

    sorted_marginals = dict(sorted(marginals.items(), key=lambda item: item[1], reverse=True))

    return [sorted_marginals]
