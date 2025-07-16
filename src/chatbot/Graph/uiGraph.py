from typing import Annotated, TypedDict, Literal

from langgraph.prebuilt import ToolNode,tools_condition
from langchain_core.tools import tool, StructuredTool, InjectedToolCallId
from langgraph.graph import START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_core.prompts.prompt import PromptTemplate
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import requests
import re
import pandas as pd
from langgraph.prebuilt import InjectedState
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from langgraph.prebuilt.chat_agent_executor import AgentState
from langchain_core.messages import messages_from_dict, convert_to_openai_messages
from langchain_core.load import dumpd, dumps, load, loads
import os
from Graph.BaseLangGraph import BaseLangGraph
from db.files import get_current_config_file


# from langsmith import Client
from dotenv import load_dotenv
load_dotenv()
# client=Client()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")


API_URL = "http://fastapi:8000"

class UIGraph(BaseLangGraph):

    class GraphsState(AgentState):
        messages: Annotated[list[AnyMessage], add_messages]


    @staticmethod
    def get_tools():
        return [
            UIGraph.filter_rule,
            UIGraph.get_constant_info,
            UIGraph.get_directives_with_constant,
            UIGraph.get_macro_call_trace,
            UIGraph.removed_by,
        ]

    # tool 1: filtre règle sur base de location et host, ordonné dans l'ordre d'exécution
    @tool
    @staticmethod
    def filter_rule(location:str, host:str, tool_call_id: Annotated[str,InjectedToolCallId], state: Annotated[GraphsState, InjectedState]):
        """
        Tool used to filter rules of the configuration based on location and host. The arguments are used in cypher query with regex

        Args:
        location (str): The regex used to filter the location. If the request is not clear or do not explicitly ask for exact match, use .* to match all Location that contain the string
        host (str): The regex used to filter the host. If the request is not clear or do not explicitly ask for exact match, use .* to match all

        """
        print("##################################################################################", flush=True)
        print(f"filter_rule({location}, {host})", flush=True)
        response = requests.post(f"{API_URL}/parse_http_request", json={"location": location, "host": host})
        if response.status_code != 200:
            return response.content.decode()
        else:
            query = response.json()["cypher_query"]
            # Run the generated Cypher query and display the graph
            response = requests.post(f"{API_URL}/cypher/to_json", json={"query": query})

            return response.json()["df"]
        

    @tool
    @staticmethod
    def removed_by(node_id):
        """
        Tool used to get the list of directives that removed a node based on its id.
        Args:
        node_id (int): The id of the node to get the directives

        """
        response = requests.get(f"{API_URL}/directives/removed/{node_id}")
        if response.status_code != 200:
            return response.content.decode()
        else:
            return response.json()["results"]


    @staticmethod
    def get_metadata(node_id:int):
        """
        Tool used to get the metadata of a node based on its id.

        Args:
        node_id (int): The id of the node to get the metadata

        """
        # print("in get_metadata", flush=True)
        response = requests.get(f"{API_URL}/get_metadata/{node_id}")
        if response.status_code != 200:
            return response.content.decode()
        else:
            return response.json()["metadata"]
        
    # tool 3: get constantes information
    @staticmethod
    @tool
    def get_constant_info(constant_name:str):
        """
        Tool used to get the list of constants and variables inside the configuration that contain constant_name.

        Args:
        constant_name (str): The name of the constant to find

        """
        response = requests.get(f"{API_URL}/search_var/{constant_name}")
        if response.status_code != 200:
            return response.content.decode()
        else:
            print(response.json(), flush=True)
            return response.json()["records"]
        
    # tool 4: get the list of directives where a constant is used
    @staticmethod
    @tool
    def get_directives_with_constant(constant_name:str):
        """
        Tool used to get the list of directives where a constant is used.

        Args:
        constant_name (str): The name of the constant to get the directives

        """
        # print(f"get_directives_with_constant({constant_name})", flush=True)
        response = requests.post(f"{API_URL}/use_node", json={"var_name": constant_name})
        if response.status_code != 200:
            return response.content.decode()
        else:
            print(response.json(), flush=True)
            return response.json()["results"]
        
    # tool 5: Get the macro call context of a node
    @staticmethod
    @tool
    def get_macro_call_trace(node_id:int):
        """
        Tool used to get the macro call trace of a node based on its ID.

        Args:
        node_id (int): The ID of the node to get the macro call trace

        """
        output = ""
        call_data=UIGraph.get_metadata(node_id)
        # print(call_data, flush=True)
        use_line,use_content=UIGraph.extract_macro_usages(call_data[0][1],call_data[0][0],call_data[0][2])
        output += f"Macro call trace for node {node_id}, {call_data[0][0]}:\n"
        output += f"Line {use_line}: {call_data[0][1]}\n"
        output+=f"{use_content}\n\n"
        # print(output,flush=True)

        for i in range(0, len(call_data)-1):
            macro_line,macro_content=UIGraph.extract_macro_definiton(call_data[i+1][1],call_data[i][0])
            output += f"Line {macro_line}: {call_data[i+1][1]}\n"
            output+=f"{macro_content}\n\n"
        print(output,flush=True)
        return output


    @staticmethod
    def extract_macro_definiton(path: str, macro_name: str):
        """
        Extracts the line number and full macro definition for a given macro.

        Args:
            path (str): Path to the file containing the macro
            macro_name (str): Name of the macro to extract

        Returns:
            tuple: (start_line_number: int, full_macro_definition: str), or (None, None) if not found
        """
        # Normalize path to internal representation
        path = path.split("/conf/")[-1]
        internal_path = "conf/" + path

        macro_start_re = re.compile(rf"<Macro\s+{re.escape(macro_name)}\b.*?>", re.IGNORECASE)
        macro_end_re = re.compile(r"</Macro>", re.IGNORECASE)

        in_macro = False
        macro_lines = []
        first_line_number = None

        f = get_current_config_file(internal_path)
        for i, line in enumerate(f, start=1):
            if not in_macro:
                if macro_start_re.search(line):
                    in_macro = True
                    first_line_number = i
                    macro_lines.append(line)
            else:
                macro_lines.append(line)
                if macro_end_re.search(line):
                    break

        if macro_lines:
            return first_line_number, ''.join(macro_lines)
        else:
            return None, None
        
    @staticmethod
    def extract_macro_usages(filepath, macro_name, target_line):
        path=filepath.split("/conf/")[-1]
        internal_path="conf/"+path
        usage_re = re.compile(rf"\bUse\s+{re.escape(macro_name)}\b", re.IGNORECASE)
        matches = []

        f = get_current_config_file(internal_path)
        for lineno, line in enumerate(f, start=1):
            if usage_re.search(line):
                matches.append((lineno, line.strip()))
        
        closest = min(matches, key=lambda x: abs(x[0] - target_line))
        print(closest, flush=True)
        return closest
        

    # Core invocation of the model
    @staticmethod
    def call_model(state: GraphsState):
        messages = state["messages"]
        if "last_rules" in state.keys():
            print(state["last_rules"], flush=True)
        prompt=f"""
        You are the WAF-ssistant an expert of WAF configuration using Apache2 and modSecurity. 
        You role is to support the user in answering specific questions about the current WAF configuration.
        The configuration has been parsed and stored in a NEO4j and postGres database.
        The tool get_macro_call_trace returns apache2 configuration lines, you need to properly format the output of the tool to be displayed in markdown. If needed add your comments before or after the code block.
        """
        llmprompt=ChatPromptTemplate.from_messages(
            [("system", prompt,),("placeholder", "{messages}"),]
        )
        try:
            llm = ChatOpenAI(model="o3-mini-2025-01-31")
            agent=llmprompt|llm.bind_tools(UIGraph.get_tools())
            response = agent.invoke({"messages":messages})
            return {"messages": [response]}  # add the response to the messages using LangGraph reducer paradigm
        except Exception as e:
            print(f"Error in call_model: {e}", flush=True)
            return {"messages": [{"role": "assistant", "content": str(e)}]}
        
        








    def build_graph(self):
        # return super().build_graph()
        
        graph = StateGraph(UIGraph.GraphsState)
        
        graph.add_node("tools", ToolNode(UIGraph.get_tools()))
        graph.add_node("modelNode", UIGraph.call_model)
        graph.add_conditional_edges(
            "modelNode",
            tools_condition
        )
        graph.add_edge("tools", "modelNode")
        graph.add_edge(START, "modelNode")
        return graph
