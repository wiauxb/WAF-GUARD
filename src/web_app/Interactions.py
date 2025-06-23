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

tab_rqst, tab_cst, tab_zoom, tab_from_file, tab_chatbot = st.tabs(["Request", "Constant", "Zoom", "From File", "Chatbot"])


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


with tab_chatbot:
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        # graph=st.radio("Select Graph", ["Basic", "Reasoning","UI tools"], horizontal=False)
        graph=st.radio("Select Graph", ["UI tools"], horizontal=False)
    with col2:
        c=st.container()
        # Initialize messages in session state if not already
        if "messages" not in st.session_state:
            st.session_state["messages"] = [AIMessage(content="How can I help you?")]
 
        # Render the chat messages
        for msg in st.session_state.messages:
            if isinstance(msg, AIMessage):
                c.chat_message("assistant").write(msg.content)
            if isinstance(msg, HumanMessage):
                c.chat_message("user").write(msg.content)
 
        # Take user input and process it through the selected graph
        if prompt := st.chat_input():
            st.session_state.messages.append(HumanMessage(content=prompt))
            # st.chat_message("user").write(prompt)
 
            with c.chat_message("user"):
                st.markdown(prompt)
 
            with c.chat_message("assistant"),st.container():
                
 
                    # Convert messages to the format expected by the API
                messages = []
                for message in st.session_state.messages:
                    if isinstance(message, HumanMessage):
                        messages.append({"role": "user", "content": message.content})
                    elif isinstance(message, AIMessage):
                        messages.append({"role": "assistant", "content": message.content})
                # messages.append({"role": "user", "content": prompt})
                payload = {"messages": messages_to_dict(st.session_state.messages)}
                print(payload, flush=True)
 
                with st.spinner("Analyzing..."):
                    if graph == "Basic":
                        response = requests.post(BASIC_GRAPH, json=payload).json()
                    elif graph == "Reasoning":
                        response = requests.post(REASONING_GRAPH, json=payload).json()
                    elif graph == "UI tools":
                        response = requests.post(UI_GRAPH, json=payload).json()
                    last_msg = AIMessage(content=response["messages"][-1]["content"],kwargs=response["messages"][-1]["additional_kwargs"])
                    st.write(last_msg.content)
            
            st.session_state.messages.append(last_msg)