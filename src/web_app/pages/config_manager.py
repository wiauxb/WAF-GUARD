import shutil
import sys
import streamlit as st
import zipfile
import uuid
import time
from pathlib import Path
import hashlib
import pandas as pd
import requests

UPLOADED_LOCATION = "/shared/uploaded"
API_URL = "http://fastapi:8000"

def process_config_archive(uploaded_file, nickname=None):
    response = requests.post(f"{API_URL}/store_config", data={"config_nickname": nickname}, files={"file": uploaded_file})
    if response.status_code != 200:
        st.error("Failed to store config.")
        st.error(response.content.decode())
        return False
    new_config_id = response.json()["config_id"]

    if not dump_config(new_config_id, uploaded_file):
        return False

    return True

def check_duplicate_name(name):
    response = requests.get(f"{API_URL}/configs")
    if response.status_code != 200:
        st.error("Failed to fetch existing configs.")
        st.error(response.content.decode())
        return False
    configs = response.json()["configs"]
    print(configs)
    sys.stdout.flush()
    for _id, conf_name, *_rest in configs:
        if conf_name == name:
            return True
    return False

def new_config_form():
    col_text, col_btn = st.columns([4, 1])
    with col_text:
        name = st.text_input(
            "Name",
            placeholder="Enter a name for the config file",
            label_visibility="collapsed",
            help="Enter a name for the config file.",
        )
    uploaded_file = st.file_uploader(
        "Upload Config File",
        type=["zip"],
        label_visibility="collapsed",
    help="Upload a zip file containing the config files you want to parse.",
    )
    with col_btn:
        if st.button("Submit", use_container_width=True):
            if not name:
                st.error("Please enter a name for the config file.")
            elif check_duplicate_name(name):
                st.error("A config with this name already exists. Please choose a different name.")
            elif process_config_archive(uploaded_file, name):
                st.success("Config files processed successfully.")
                return True
            else:
                st.error("Failed to process config files.")
                return False


def select_config(id):
        response = requests.get(f"{API_URL}/configs/selected")
        
        if response.status_code != 200:
            # Update the selected config
            response = requests.post(f"{API_URL}/configs/select/{id}")
            return
            
        selected_config = response.json()["selected_config"]
        
        # No configuration is selected yet
        if selected_config is None:
            response = requests.post(f"{API_URL}/configs/select/{id}")
            return

        # The config_id is at index 1 in the returned tuple
        old_selected = selected_config[1]

        if old_selected != id:
            # Update the selected config
            response = requests.post(f"{API_URL}/configs/select/{id}")
        st.rerun()

def react_to_select_config(configs):
    rows = st.session_state.selected_config.selection.rows
    if rows:
        selected_index = configs.index[rows[0]]
        # select_config(selected_index)

def show_existing_configs():
    existing_configs = requests.get(f"{API_URL}/configs")
    if existing_configs.status_code == 200:
        configs = pd.DataFrame(existing_configs.json()["configs"], columns=["id", "name", "parsed", "created_at"])
        configs.set_index("id", inplace=True)
        styled_confs = configs
        response = requests.get(f"{API_URL}/configs/selected")
        if response.status_code == 200:
            selected_config = response.json()["selected_config"][1]
            if selected_config is not None:
                styled_confs = configs.style.set_properties(subset=pd.IndexSlice[selected_config, :], **{'background-color': '#FFC34D4D'})
        st.session_state.selected_config = st.dataframe(
            styled_confs,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True)
        react_to_select_config(configs)
        if st.session_state.selected_config.selection.rows:
            return configs.index[st.session_state.selected_config.selection.rows[0]], configs.iloc[st.session_state.selected_config.selection.rows[0]]["name"]
    else:
        st.error("Failed to fetch existing configs.")
        st.error(existing_configs.content.decode())
    return None

def dump_config(config_id, uploaded_file):
    uploaded_file.seek(0)
    files = {'file': uploaded_file}
    response = requests.post(f"{API_URL}/get_dump", files=files)
    if response.status_code != 200:
        st.error("Failed to get config dump.")
        st.error(response.content.decode())
        return False
    # store the dump
    dump = response.json()["dump"]
    response = requests.post(f"{API_URL}/store_dump", json={"config_id": config_id, "dump": dump})
    if response.status_code != 200:
        st.error("Failed to store config dump.")
        st.error(response.content.decode())
        return False
    return True


def parse_config(config_id):
    response = requests.get(f"{API_URL}/configs/selected")
    if response.status_code != 200:
        st.error("Failed to fetch selected config.")
        st.error(response.content.decode())
        return
    selected_config = response.json()["selected_config"][1]
    response = requests.post(f"{API_URL}/database/export/{selected_config}")
    if response.status_code != 200:
        st.error("Failed to export database.")
        st.error(response.content.decode())
        return
    response = requests.post(f"{API_URL}/configs/parse/{config_id}")
    if response.status_code == 200:
        select_config(config_id)
        st.success("Config parsed successfully.")
    else:
        st.error("Failed to parse config.")
        st.error(response.content.decode())
    

@st.dialog("Delete Config")
def confirm_delete_config(selected):
    if not selected:
        st.error("Please select a config to delete.")
        return
    st.text(f"Are you sure you want to delete the config: {selected[1]} ?")
    bt1, bt2 = st.columns(2)
    with bt1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with bt2:
        if st.button("Delete", use_container_width=True):
            response = requests.delete(f"{API_URL}/configs/{selected[0]}")
            if response.status_code == 200:
                st.success("Config deleted successfully.")
                st.rerun()
            else:
                st.error("Failed to delete config.")
                st.error(response.content.decode())

def load_parsing_data(selected):
    if not selected:
        st.error("Please select a config to load parsing data.")
        return
    response = requests.get(f"{API_URL}/configs/parse/{selected[0]}")
    if response.status_code != 200:
        st.error("Failed to fetch parsing data.")
        st.error(response.content.decode())
        return
    parsed_data = response.json()
    if not parsed_data["parsed"]:
        st.error("Parsing data not available for this config. Please parse before loading.")
        return

    response = requests.get(f"{API_URL}/configs/selected")
    if response.status_code != 200:
        st.error("Failed to fetch selected config.")
        st.error(response.content.decode())
        return
    selected_config = response.json()["selected_config"]
    if selected_config is not None and selected_config[1] == selected[0]:
        st.success("Parsing data already loaded for this config.")
        return

    response = requests.post(f"{API_URL}/database/export/{selected_config[1]}")
    if response.status_code != 200:
        st.error("Failed to export active data.")
        st.error(response.content.decode())
        return

    response = requests.post(f"{API_URL}/database/import/{selected[0]}")
    if response.status_code != 200:
        st.error("Failed to import parsing data.")
        st.error(response.content.decode())
        return

    #If we reach here, the parsing data was loaded successfully
    select_config(selected[0])

st.set_page_config(page_title="Config Manager", layout="wide")

st.header("Known Configs")
# Add legend for loaded config
col1, col2 = st.columns([1, 20])
with col1:
    st.markdown('<div style="width: 30px; height: 30px; background-color: #FFC34D4D; border-radius: 0.5rem; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="width: 30px; height: 30px; background-color: #ff4b4b4d; border-radius: 0.5rem; margin-up: 10px;"></div>', unsafe_allow_html=True)
with col2:
    st.text("Loaded config for analysis")
    st.text("Selection for interaction")
selected = show_existing_configs()

# Create three columns for buttons
button_col1, button_col2, button_col3 = st.columns(3)

with button_col1:
    if st.button("Load Existing Parsing data", use_container_width=True):
        load_parsing_data(selected)
        
with button_col2:
    if st.button("Parse & Load Config", use_container_width=True):
        if selected:
            parse_config(selected[0])
        else:
            st.error("Please select a config to parse.")
            
with button_col3:
    if st.button("Delete Config", use_container_width=True):
        confirm_delete_config(selected)
        
st.header("Add New Config")
if new_config_form():
    st.rerun()