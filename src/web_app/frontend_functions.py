import sys
import pandas as pd
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import requests
import streamlit as st
import os


API_URL = os.getenv("API_URL")
COLUMNS_OF_INTEREST = ["node_id", "type", "args", "Location", "VirtualHost", "phase", "id", "tags", "msg"]
COLUMNS_TO_REMOVE = ["Context"]

def validate_id(id: str) -> bool:
    """
    Validates if the given id is a valid integer
    or a valid range in the format "start-end"
    or a list of ids separated by commas.

    Args:
        id (str): The id to validate.

    Returns:
        bool: True if the id is valid, False otherwise.
    """
    if not id:
        return False
    if "-" in id:
        start, end = [i.strip() for i in id.split("-")]
        return start.isdigit() and end.isdigit() and int(start) < int(end)
    if "," in id:
        ids = [i.strip() for i in id.split(",")]
        return all(i.isdigit() for i in ids)
    return id.isdigit()

def validate_tag(tag: str) -> bool:
    """
    Validates if the given tag is a valid string without spaces.

    Args:
        tag (str): The tag to validate.

    Returns:
        bool: True if the tag is valid, False otherwise.
    """
    if not tag:
        return False
    return " " not in tag

# modified version of function from https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/
def filter_dataframe(df: pd.DataFrame, key = None) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    if key:
        modify = st.checkbox("Add filters", key=f"add_filters_{key}")
    else:
        modify = st.checkbox("Add filters", key=f"add_filters_{hash(df.to_string())}")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        if key:
            to_filter_columns = st.multiselect("Filter dataframe on", df.columns, key=f"filter_columns_{key}")
        else:
            to_filter_columns = st.multiselect("Filter dataframe on", df.columns, key=f"filter_columns_{hash(df.to_string())}")
        for column in to_filter_columns:
            left, right = st.columns((1, 31))
            left.write("↳")
            if df[column].apply(lambda x: isinstance(x, list)).any():
                user_list_input = right.multiselect(
                    f"Values for {column}",
                    df[column].explode().fillna("No value").unique(),
                    default=list(df[column].explode().fillna("No value").unique()),
                )
                # select rows where any of the list elements are in the user input
                df = df[df[column].apply(lambda x: any(i in user_list_input for i in x) or (not x and ("No value" in user_list_input)))]
            # Treat columns with < 10 unique values as categorical
            elif is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

def format_directive_table(directive_table: pd.DataFrame) -> pd.DataFrame:
    directive_table = directive_table.drop(COLUMNS_TO_REMOVE, axis=1, errors="ignore")
    existing_columns = [c for c in COLUMNS_OF_INTEREST if c in directive_table.columns]
    directive_table = pd.concat([directive_table[existing_columns], directive_table.drop(existing_columns, axis=1)], axis=1)
    return directive_table

def show_rules(directive_table: pd.DataFrame, container: st = st, key = None):
    if directive_table.empty:
        container.dataframe(directive_table)
        container.text("No rules found")
        return
    filtered = filter_dataframe(directive_table, key=key)
    edited_dirs = container.dataframe(
        filtered,
        on_select="rerun",
        selection_mode="multi-row",
        hide_index=True,
        key=f"directives_dataframe_{key}")
    container.text(f"{len(filtered)} rules found")

    selected = filtered.iloc[edited_dirs.selection.rows]['node_id'].map(lambda x: str(x)).tolist()
    if selected:
        sub_tabs = container.tabs(selected)
        for i, t in enumerate(sub_tabs):
            with t:
                response = requests.get(f"{API_URL}/get_metadata/{selected[i]}")
                # print(response.json(),flush=True)
                metadata = pd.DataFrame(response.json()["metadata"], columns=["call_macro", "file_path", "line_number"])
                container.dataframe(metadata, hide_index=True)
