import sys
from frontend_functions import *
import streamlit as st
import requests
import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, messages_to_dict
# from websockets.asyncio.client import connect
import asyncio
from websockets.sync.client import connect
import time


API_URL = "http://fastapi:8000"
WS_URL = "ws://chatbot:8005/ws"
CHAT_URL = "http://chatbot:8005/chat"
BASIC_GRAPH=CHAT_URL+"/basic_graph"
UI_GRAPH=CHAT_URL+"/ui_graph"
REASONING_GRAPH=CHAT_URL+"/reasoning_graph"


st.set_page_config(page_title="Graph Query Interface", page_icon=":bar_chart:", layout="wide")

# Initialize session state for graph data
if "graph_data" not in st.session_state:
    st.session_state.graph_data = ""
if "metadata_array" not in st.session_state:
    st.session_state.metadata_array = []
if "cypher_query" not in st.session_state:
    st.session_state.cypher_query = ""
if "rules_table" not in st.session_state:
    st.session_state.rules_table = pd.DataFrame()
if "cst_table" not in st.session_state:
    st.session_state.cst_table = pd.DataFrame()
if "from_file_table" not in st.session_state:
    st.session_state.from_file_table = pd.DataFrame()

tab_rqst, tab_cst, tab_zoom, tab_from_file, tab_tag_id, tab_removed_by = st.tabs(["Location/Host", "Constant", "Zoom", "From File", "Tag/Id", "Removed By"])


with tab_rqst:
    col1, col2 = st.columns(2)

    # Input for HTTP request
    location = col1.text_input("Enter Location")
    host = col2.text_input("Enter Host")

    # Button to submit HTTP request
    if st.button("Submit HTTP Request"):
        response = requests.post(f"{API_URL}/parse_http_request", json={"location": location+".*", "host": host+".*"})
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            st.session_state.cypher_query = response.json()["cypher_query"]
            # Run the generated Cypher query and display the graph
            response = requests.post(f"{API_URL}/cypher/to_json", json={"query": st.session_state.cypher_query})
            df = pd.DataFrame(response.json()["df"])
            st.session_state.rules_table = format_directive_table(df)
            # df = pd.DataFrame(response.json()["df"])
            # print(df.head())
            # sys.stdout.flush()

    interm = st.popover("Cypher Query", use_container_width=True)
    query_field = interm.text_area("Generated Cypher Query", st.session_state.cypher_query)
    if interm.button("Run Cypher Query", key="run_cypher_query"):
        st.session_state.cypher_query = query_field
        response = requests.post(f"{API_URL}/cypher/to_json", json={"query": st.session_state.cypher_query})
        df = pd.DataFrame(response.json()["df"])
        st.session_state.rules_table = format_directive_table(df)

    show_rules(st.session_state.rules_table, key="rules_table")

with tab_cst:
    cst_name = st.text_input("Constant Name")
    if cst_name:
        response = requests.get(f"{API_URL}/search_var/{cst_name}")
        if response.status_code == 200:
            # st.dataframe(response.json()["records"])
            st.session_state.cst_table = pd.DataFrame(response.json()["records"])
        else:
            st.error(response.content.decode())
    
    # what is the constant: Constant, Variable, or SubVariable
    edited_cst_table = st.dataframe(
        st.session_state.cst_table,
        # column_order=["selected", "name", "value", "labels"],
        # hide_index=True,
        on_select="rerun",
        # selection_mode="single-row",
    )

    selected = [str(i) for i in edited_cst_table.selection.rows]
    if selected:
        sub_tabs = st.tabs(selected)
        for i, t in enumerate(sub_tabs):
            with t:
                node = st.session_state.cst_table.iloc[int(selected[i])]
                

                st.subheader("Created by")
                
                if pd.isna(node.get("value", None)):
                    response = requests.post(f"{API_URL}/get_setnode", json={"var_name": node["name"]})
                else:
                    response = requests.post(f"{API_URL}/get_setnode", json={"var_name": node["name"], "var_value": node["value"]})

                if response.status_code == 200:
                    df = pd.DataFrame(response.json()["results"])
                    created_by = format_directive_table(df)
                    show_rules(created_by, key=f"created_by_{selected[i]}")
                else:
                    st.error("Failed to fetch 'created by' information.")

                st.subheader("Used by")
                
                if pd.isna(node.get("value", None)):
                    response = requests.post(f"{API_URL}/use_node", json={"var_name": node["name"]})
                else:
                    response = requests.post(f"{API_URL}/use_node", json={"var_name": node["name"], "var_value": node["value"]})
                if response.status_code == 200:
                    df = pd.DataFrame(response.json()["results"])
                    used_by = format_directive_table(df)
                    show_rules(used_by, key=f"used_by_{selected[i]}")
                else:
                    st.error("Failed to fetch 'used by' information.")

    # where is it defind, to which rule it belongs, to what value it is set
    # list the rules that use this constant

with tab_zoom:
    node_id = st.text_input("Node ID")
    if node_id:
        st.subheader("The directive:")
        response = requests.get(f"{API_URL}/directives/id/{node_id}")
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            df = pd.DataFrame(response.json()["results"])
            directive = format_directive_table(df)
            show_rules(directive, key=f"zoom_directive_{node_id}")
        st.subheader("Zoom:")
        response = requests.post(f"{API_URL}/cypher/run", json={"query": f"MATCH (n {{node_id: {node_id}}})-[r]-(m) RETURN *"})
        graph = response.json()["html"]
        st.components.v1.html(graph, height=600)

    # show metadata
        response = requests.get(f"{API_URL}/get_metadata/{node_id}")
        if response.status_code == 200:
            metadata = pd.DataFrame(response.json()["metadata"], columns=["call_macro", "file_path", "line_number"])
            st.dataframe(metadata, hide_index=True)
        else:
            st.error(response.content.decode())

with tab_from_file:
    # inputs for file name and line number
    file_name = st.text_input("Enter File Name")
    line_number = st.text_input("Enter Line Number")

    # Button to submit file request
    if st.button("Submit File Request"):
        response = requests.post(f"{API_URL}/get_node_ids", json={"file_path": file_name, "line_num": line_number})
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            df = pd.DataFrame(response.json()["results"])
            st.session_state.from_file_table = format_directive_table(df)

    show_rules(st.session_state.from_file_table, key="from_file_table")





def send_message_to_websocket(message):
    print("in sending function", flush=True)
    with connect(WS_URL) as websocket:
        websocket.send(message)
        # for message in websocket:
        #     # response = websocket.recv()
        #     # st.write(response)
        #     print("in Loop", flush=True)
        #     yield message

with tab_tag_id:
    col1, col2 = st.columns([0.1, 0.9])
    search_type = col1.selectbox("Search by", ["Id", "Tag"])
    search_value = col2.text_input(f"Enter {search_type}")

    if search_value:
        if search_type == "Id":
            if not validate_id(search_value):
                st.error("Invalid ID format. Please enter a valid ID.")
                can_request = False
            else:
                can_request = True
        else:
            if not validate_tag(search_value):
                st.error("Invalid tag format. Please enter a valid tag.")
                can_request = False
            else:
                can_request = True
        if can_request:

            st.subheader(f"RemoveBy{search_type}")
            response = requests.get(f"{API_URL}/directives/remove_by/{search_type.lower()}", json={search_type.lower(): search_value})
            if response.status_code != 200:
                st.error(response.content.decode())
            else:
                df = pd.DataFrame(response.json()["results"])
                removeby = format_directive_table(df)
                show_rules(removeby, key=f"removeby_{search_type.lower()}")

            st.subheader(f"Directives with {search_type}")
            response = requests.get(f"{API_URL}/directives/{search_type.lower()}", json={search_type.lower(): search_value})
            if response.status_code != 200:
                st.error(response.content.decode())
            else:
                df = pd.DataFrame(response.json()["results"])
                directives = format_directive_table(df)
                show_rules(directives, key=f"directives_{search_type.lower()}")

with tab_removed_by:
    nodeid = st.text_input("node_id of the node removed")
    if nodeid:
        st.subheader("The directive:")
        response = requests.get(f"{API_URL}/directives/id/{nodeid}")
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            df = pd.DataFrame(response.json()["results"])
            directive = format_directive_table(df)
            show_rules(directive, key=f"directive_{nodeid}")
        
        response = requests.get(f"{API_URL}/directives/removed/{nodeid}")
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            df = pd.DataFrame(response.json()["results"])
            criterions_types = df["criterion_type"].unique()
            for type in criterions_types:
                st.subheader(f"Directives that removed based on a {type}")
                df_type = df[df["criterion_type"] == type]
                criterion_values = df_type["criterion_value"].unique()
                for value in criterion_values:
                    st.subheader(f"Criterion Value: {value}")
                    directive_jsons = df_type[df_type["criterion_value"] == value]["directive"].tolist()
                    df_dirs = pd.DataFrame(directive_jsons)
                    # Show the directives for this type and value
                    show_rules(format_directive_table(df_dirs), key=f"removed_by_{type}_{value}")
            # removers = format_directive_table(df)
            # show_rules(removers)
