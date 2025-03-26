import pandas as pd


COLUMNS_OF_INTEREST = ["node_id", "type", "args", "Location", "VirtualHost", "phase", "id", "tags", "msg"]
COLUMNS_TO_REMOVE = ["Context"]

def format_directive_table(directive_table: pd.DataFrame) -> pd.DataFrame:
    directive_table = directive_table.drop(COLUMNS_TO_REMOVE, axis=1, errors="ignore")
    existing_columns = [c for c in COLUMNS_OF_INTEREST if c in directive_table.columns]
    directive_table = pd.concat([directive_table[existing_columns], directive_table.drop(existing_columns, axis=1)], axis=1)
    return directive_table