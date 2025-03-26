import pandas as pd
import requests
import streamlit as st


API_URL = "http://fastapi:8000"
COLUMNS_OF_INTEREST = ["node_id", "type", "args", "Location", "VirtualHost", "phase", "id", "tags", "msg"]
COLUMNS_TO_REMOVE = ["Context"]

def format_directive_table(directive_table: pd.DataFrame) -> pd.DataFrame:
    directive_table = directive_table.drop(COLUMNS_TO_REMOVE, axis=1, errors="ignore")
    existing_columns = [c for c in COLUMNS_OF_INTEREST if c in directive_table.columns]
    directive_table = pd.concat([directive_table[existing_columns], directive_table.drop(existing_columns, axis=1)], axis=1)
    directive_table["selected"] = False
    return directive_table

def show_rules(directive_table: pd.DataFrame, container: st = st):
    if directive_table.empty:
        container.dataframe(directive_table)
        container.text("No rules found")
        return
    do_not_edit = directive_table.columns.to_list()
    do_not_edit.remove("selected")
    edited_dirs = container.data_editor(
        directive_table,
        column_config={
            "selected": st.column_config.CheckboxColumn(
                default=False,
                pinned=True,
            )
        },
        disabled=do_not_edit,
        hide_index=True)
    container.text(f"{len(directive_table)} rules found")

    if not edited_dirs.empty:
        selected = edited_dirs[edited_dirs["selected"]]['node_id'].map(lambda x: str(x)).tolist()
        if selected:
            sub_tabs = container.tabs(selected)
            for i, t in enumerate(sub_tabs):
                with t:
                    response = requests.get(f"{API_URL}/get_metadata/{selected[i]}")
                    metadata = pd.DataFrame(response.json()["metadata"], columns=["call_macro", "file_path", "line_number"])
                    container.dataframe(metadata, hide_index=True)
