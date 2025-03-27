import sys
from frontend_functions import *
import streamlit as st
import requests
import pandas as pd

API_URL = "http://fastapi:8000"

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

tab_rqst, tab_cst, tab_neighbours, tab_from_file = st.tabs(["Request", "Constant", "Neighbours", "From File"])

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
            response = requests.post(f"{API_URL}/run_cypher_to_json", json={"query": st.session_state.cypher_query})
            df = pd.DataFrame(response.json()["df"])
            st.session_state.rules_table = format_directive_table(df)
            # df = pd.DataFrame(response.json()["df"])
            # print(df.head())
            # sys.stdout.flush()

    interm = st.popover("Cypher Query", use_container_width=True)
    query_field = interm.text_area("Generated Cypher Query", st.session_state.cypher_query)
    if interm.button("Run Cypher Query", key="run_cypher_query"):
        st.session_state.cypher_query = query_field
        response = requests.post(f"{API_URL}/run_cypher_to_json", json={"query": st.session_state.cypher_query})
        df = pd.DataFrame(response.json()["df"])
        st.session_state.rules_table = format_directive_table(df)

    show_rules(st.session_state.rules_table)

with tab_cst:
    cst_name = st.text_input("Constant Name")
    if st.button("Search"):
        response = requests.get(f"{API_URL}/search_var/{cst_name}")
        if response.status_code == 200:
            # st.dataframe(response.json()["records"])
            st.session_state.cst_table = pd.DataFrame(response.json()["records"])
            st.session_state.cst_table["selected"] = False
        else:
            st.error(response.content.decode())
    
    # what is the constant: Constant, Variable, or SubVariable
    edited_cst_table = st.data_editor(
        st.session_state.cst_table,
        column_config={
            "selected": st.column_config.CheckboxColumn(
                default=False,
                pinned=True,
            )
        },
        # column_order=["selected", "name", "value", "labels"],
        disabled=["name", "value", "labels"],
        # hide_index=True,
    )

    if not edited_cst_table.empty:
        # selected = edited_cst_table[edited_cst_table["selected"]]
        # selected = selected.drop("selected", axis=1)
        selected = list(edited_cst_table.index[edited_cst_table["selected"]].map(lambda x: str(x)))
        if selected:
            sub_tabs = st.tabs(selected)
            for i, t in enumerate(sub_tabs):
                with t:
                    node = edited_cst_table.iloc[int(selected[i])]
                    

                    st.subheader("Created by")
                    
                    if pd.isna(node["value"]):
                        response = requests.post(f"{API_URL}/get_setnode", json={"var_name": node["name"]})
                    else:
                        response = requests.post(f"{API_URL}/get_setnode", json={"var_name": node["name"], "var_value": node["value"]})

                    if response.status_code == 200:
                        df = pd.DataFrame(response.json()["results"])
                        created_by = format_directive_table(df)
                        show_rules(created_by)
                    else:
                        st.error("Failed to fetch 'created by' information.")

                    st.subheader("Used by")
                    
                    if pd.isna(node["value"]):
                        response = requests.post(f"{API_URL}/use_node", json={"var_name": node["name"]})
                    else:
                        response = requests.post(f"{API_URL}/use_node", json={"var_name": node["name"], "var_value": node["value"]})
                    if response.status_code == 200:
                        df = pd.DataFrame(response.json()["results"])
                        used_by = format_directive_table(df)
                        show_rules(used_by)
                    else:
                        st.error("Failed to fetch 'used by' information.")

    # where is it defind, to which rule it belongs, to what value it is set
    # list the rules that use this constant

with tab_neighbours:
    node_id = st.text_input("Node ID")
    if st.button("Get Neighbours"):
        response = requests.post(f"{API_URL}/run_cypher", json={"query": f"MATCH (n {{node_id: {node_id}}})-[r]-(m) RETURN *"})
        graph = response.json()["html"]
        st.components.v1.html(graph, height=600)

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
    show_rules(st.session_state.from_file_table)