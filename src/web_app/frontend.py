import streamlit as st
import requests
import pandas as pd

API_URL = "http://fastapi:8000"
COLUMNS_OF_INTEREST = ["node_id", "type", "args", "Location", "VirtualHost", "phase", "id", "tags", "msg"]
COLUMNS_TO_REMOVE = ["Context"]

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

tab1, tab2, tab3 = st.tabs(["Queries", "Request", "Constant"])

with tab1:
    header = st.container()
    col1, col2 = header.columns(2)
    res1, res2 = st.columns(2, vertical_alignment="top")

    with col1:
        # Input for Cypher query
        cypher_query = st.text_area("Enter Cypher Query")

        # Button to submit Cypher query
        if st.button("Run Cypher Query"):
            response = requests.post(f"{API_URL}/run_cypher", json={"query": cypher_query})
            st.session_state.graph_data = response.json()["html"]

    with col2:
        c = st.container()
        c1, c2 = c.columns((.75, .25), vertical_alignment="bottom")
        # Input for node ID to fetch metadata
        node_id = c1.text_input("Enter Node ID")

        # Button to fetch metadata
        if c2.button("Fetch Metadata"):
            response = requests.get(f"{API_URL}/get_metadata/{node_id}")
            metadata = response.json()
            st.session_state.metadata_array = metadata["metadata"]

    with res1:
        st.components.v1.html(st.session_state.graph_data, height=600)
    with res2:
        st.table(st.session_state.metadata_array)

with tab2:
    col1, col2 = st.columns(2)

    # Input for HTTP request
    location = col1.text_input("Enter Location")
    host = col2.text_input("Enter Host")

    # Button to submit HTTP request
    if st.button("Submit HTTP Request"):
        response = requests.post(f"{API_URL}/parse_http_request", json={"location": location, "host": host})
        if response.status_code != 200:
            st.error(response.content.decode())
        else:
            st.session_state.cypher_query = response.json()["cypher_query"]
            # Run the generated Cypher query and display the graph
            response = requests.post(f"{API_URL}/run_cypher_to_json", json={"query": st.session_state.cypher_query})
            df = pd.DataFrame(response.json()["df"])
            df = df.drop(COLUMNS_TO_REMOVE, axis=1)
            df = pd.concat([df[COLUMNS_OF_INTEREST], df.drop(COLUMNS_OF_INTEREST, axis=1)], axis=1)
            st.session_state.rules_table = df
            # df = pd.DataFrame(response.json()["df"])
            # print(df.head())
            # sys.stdout.flush()

    interm = st.popover("Cypher Query", use_container_width=True)
    query_field = interm.text_area("Generated Cypher Query", st.session_state.cypher_query)
    if interm.button("Run Cypher Query", key="run_cypher_query"):
        st.session_state.cypher_query = query_field
        response = requests.post(f"{API_URL}/run_cypher_to_json", json={"query": st.session_state.cypher_query})
        df = pd.DataFrame(response.json()["df"])
        df = df.drop(COLUMNS_TO_REMOVE, axis=1)
        df = pd.concat([df[COLUMNS_OF_INTEREST], df.drop(COLUMNS_OF_INTEREST, axis=1)], axis=1)
        st.session_state.rules_table = df

    # st.table(st.session_state.rules_table)
    st.dataframe(st.session_state.rules_table, hide_index=True)
    st.text(f"{len(st.session_state.rules_table)} rules found")

with tab3:
    # what is the constant: Constant, Variable, or SubVariable
    # where is it defind, to which rule it belongs, to what value it is set
    # list the rules that use this constant
    pass