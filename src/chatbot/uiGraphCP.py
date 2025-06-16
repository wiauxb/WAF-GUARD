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


# from langsmith import Client
from dotenv import load_dotenv
load_dotenv()
# client=Client()

class LastRulesData(TypedDict):
    content: str
    size: int
    question: str
    # columns: list[str]

API_URL = "http://fastapi:8000"

class GraphsState(AgentState):
    messages: Annotated[list[AnyMessage], add_messages]
    last_rules:LastRulesData


# tool 1: filtre règle sur base de location et host, ordonné dans l'ordre d'exécution
@tool
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
        response = requests.post(f"{API_URL}/run_cypher_to_json", json={"query": query})
        df=pd.DataFrame.from_dict(response.json()["df"])
        serialized_df = df.to_json(orient="records")
        # serialized_df = df.to_dict(orient="records")
        print("##########################  DF #######################", flush=True)
        print(df, flush=True)
        print("########################## SERIALIZED DF #######################", flush=True)
        print(serialized_df, flush=True)
        print(type(serialized_df), flush=True)
        question=last_rules_question(state["messages"])
        data=LastRulesData(
            content=serialized_df,
            size=len(df),
            question=question,
        )
        return Command(update={
        "last_rules": data,
        # update the message history
        "messages": [
            ToolMessage(
                df,
                tool_call_id=tool_call_id
            )
        ]
    })
        # return response.json()["df"]



@tool
def read_last_rules(state: Annotated[GraphsState, InjectedState]):
    """
    Tool used to get the last rules stored.

    """
    print("##################### in read_last_rules #######################", flush=True)
    data=state["last_rules"]
    str_df=data["content"]
    if str_df is None:
        print("##########################  No rules #######################", flush=True)
        return "No rules found"
    else:
        df=pd.read_json(str_df, orient="records")
        print("##########################  DF stored #######################", flush=True)
        print(df.head(), flush=True)
        print("########################## SIZE #######################", flush=True)
        print(data["size"], flush=True)
        return df





# def get_metadata(node_id:int):
#     """
#     Tool used to get the metadata of a node based on its id.

#     Args:
#     node_id (int): The id of the node to get the metadata

#     """
#     # print("in get_metadata", flush=True)
#     response = requests.get(f"{API_URL}/get_metadata/{node_id}")
#     if response.status_code != 200:
#         return response.content.decode()
#     else:
#         return response.json()["metadata"]
    
# # tool 3: get constantes information
# @tool
# def get_constant_info(constant_name:str):
#     """
#     Tool used to get the information of a constant or variable based on its name.

#     Args:
#     constant_name (str): The name of the constant to get the information

#     """
#     response = requests.get(f"{API_URL}/search_var/{constant_name}")
#     if response.status_code != 200:
#         return response.content.decode()
#     else:
#         print(response.json(), flush=True)
#         return response.json()["records"]
    
# # tool 4: get the list of directives where a constant is used
# @tool
# def get_directives_with_constant(constant_name:str):
#     """
#     Tool used to get the list of directives where a constant is used.

#     Args:
#     constant_name (str): The name of the constant to get the directives

#     """
#     # print(f"get_directives_with_constant({constant_name})", flush=True)
#     response = requests.post(f"{API_URL}/use_node", json={"var_name": constant_name})
#     if response.status_code != 200:
#         return response.content.decode()
#     else:
#         print(response.json(), flush=True)
#         return response.json()["results"]
    
# # tool 5: Get the macro call context of a node
# @tool
# def get_macro_call_trace(node_id:int):
#     """
#     Tool used to get the macro call trace of a node based on its ID.

#     Args:
#     node_id (int): The ID of the node to get the macro call trace

#     """
#     output = ""
#     call_data=get_metadata(node_id)
#     # print(call_data, flush=True)
#     use_line,use_content=extract_macro_usages(call_data[0][1],call_data[0][0],call_data[0][2])
#     output += f"Macro call trace for node {node_id}, {call_data[0][0]}:\n"
#     output += f"Line {use_line}: {call_data[0][1]}\n"
#     output+=f"{use_content}\n\n"
#     # print(output,flush=True)

#     for i in range(0, len(call_data)-1):
#         macro_line,macro_content=extract_macro_definiton(call_data[i+1][1],call_data[i][0])
#         output += f"Line {macro_line}: {call_data[i+1][1]}\n"
#         output+=f"{macro_content}\n\n"
#     # print(output)
#     return output



# def extract_macro_definiton(path: str, macro_name: str):
#     """
#     Extracts the line number and full macro definition for a given macro.

#     Args:
#         path (str): Path to the file containing the macro
#         macro_name (str): Name of the macro to extract

#     Returns:
#         tuple: (start_line_number: int, full_macro_definition: str), or (None, None) if not found
#     """
#     # Normalize path to internal representation
#     path = path.split("/conf/")[-1]
#     internal_path = "/app/conf/" + path

#     with open(internal_path, 'r') as f:
#         lines = f.readlines()

#     macro_start_re = re.compile(rf"<Macro\s+{re.escape(macro_name)}\b.*?>", re.IGNORECASE)
#     macro_end_re = re.compile(r"</Macro>", re.IGNORECASE)

#     in_macro = False
#     macro_lines = []
#     first_line_number = None

#     for i, line in enumerate(lines, start=1):
#         if not in_macro:
#             if macro_start_re.search(line):
#                 in_macro = True
#                 first_line_number = i
#                 macro_lines.append(line)
#         else:
#             macro_lines.append(line)
#             if macro_end_re.search(line):
#                 break

#     if macro_lines:
#         return first_line_number, ''.join(macro_lines)
#     else:
#         return None, None
    

# def extract_macro_usages(filepath, macro_name, target_line):
#     path=filepath.split("/conf/")[-1]
#     internal_path="/app/conf/"+path
#     usage_re = re.compile(rf"\bUse\s+{re.escape(macro_name)}\b", re.IGNORECASE)
#     matches = []

#     with open(internal_path, 'r') as f:
#         for lineno, line in enumerate(f, start=1):
#             if usage_re.search(line):
#                 matches.append((lineno, line.strip()))
    
#     closest = min(matches, key=lambda x: abs(x[0] - target_line))
#     print(closest, flush=True)
#     return closest
    

# Core invocation of the model
def call_model(state: GraphsState):
    messages = state["messages"]
    if "last_rules" in state.keys():
        print(state["last_rules"], flush=True)
    prompt=f"""
    You are the WAF-ssistant an expert of WAF configuration using Apache2 and modSecurity. 
    You role is to support the user in answering specific questions about the current WAF configuration.
    The configuration has been parsed and stored in a NEO4j and postGres database.
    """
    llmprompt=ChatPromptTemplate.from_messages(
        [("system", prompt,),("placeholder", "{messages}"),]
    )
    # commands = [tools_by_name[tool_call["name"]].invoke(tool_call) for tool_call in tool_calls]
    try:
        llm = ChatOpenAI(model="gpt-4o-mini")
        agent=llmprompt|llm.bind_tools(tools)
        response = agent.invoke({"messages":messages})
        return {"messages": [response]}  # add the response to the messages using LangGraph reducer paradigm
    except Exception as e:
        print(f"Error in call_model: {e}", flush=True)
        return {"messages": [{"role": "assistant", "content": str(e)}]}
    

def last_rules_question(messages):
    # messages = state["messages"]
    print("##########################   IN LAST RULES QUESTION #######################", flush=True)
    prompt=f"""
    You're povided with a conversation history between a user and an assistant in the langgraph framework. The last message is a tool call that retrieved a dataframe from an external data source and stored it in the assistant's memory.
    Given the conversation history, generate a standalone natural language question that summarizes the user's original intent which led to the current data retrieval.
    This question should be concise, contextually complete, and independent from the previous messages. Assume the question will be stored as metadata to describe a DataFrame extracted from a database.
    """
    llmprompt=ChatPromptTemplate.from_messages(
        [("system", prompt,),("placeholder", "{messages}"),]
    )
    llm = ChatOpenAI(model="gpt-4o-mini")
    agent=llmprompt|llm
    response = agent.invoke({"messages":messages})
    print("##########################  LAST RULES QUESTION #######################", flush=True)
    print(response, flush=True)
    return response["content"]  # add the response to the messages using LangGraph reducer paradigm
    













# tools=[filter_rule, get_constant_info, get_directives_with_constant,get_macro_call_trace]
# writing_tools=[filter_rule]
# reading_tools=[read_last_rules]
tools=[filter_rule, read_last_rules]

def invoke_graph(st_messages, callables=None):
    connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

    with ConnectionPool(
        # Example configuration
        conninfo="host=postgres port=5432 dbname=chatbot user=admin password=password",
        max_size=20,
        kwargs=connection_kwargs,
    ) as pool:
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()


        graph = StateGraph(GraphsState)
        
        # graph.add_node("reading_tools", ToolNode(reading_tools))
        # graph.add_node("writing_tools", ToolNode(writing_tools))
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("modelNode", call_model)
        graph.add_conditional_edges(
            "modelNode",
            tools_condition
        )
        # graph.add_edge("reading_tools", "modelNode")
        # graph.add_edge("writing_tools", "modelNode")
        graph.add_edge(START, "modelNode")
        graph_runnable = graph.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "2"}}
        # prompt=f"""
        #     You are the WAF-ssistant an expert of WAF configuration using Apache2 and modSecurity. 
        #     You role is to support the user in answering specific questions about the current WAF configuration.
        #     The configuration has been parsed and stored in a NEO4j and postGres database.
        #     """
        # graph=create_react_agent(
        #     tools=tools,
        #     model=ChatOpenAI(model="gpt-4o-mini"),
        #     prompt=prompt,
        #     state_schema=GraphsState,
        # )
        
        # print("########################## ST_MESSGAGE #######################", flush=True)
        # print(st_messages, flush=True)
        
        
        # print("########################## BASE_MESSAGE #######################", flush=True)
        messages=(messages_from_dict(st_messages))
        # print(messages, flush=True)

        print("#################################### OPEN_AI_MESSAGE #####################################", flush=True)
        openai_messages=convert_to_openai_messages(messages)
        print(openai_messages, flush=True)

        if callables is None:
            return graph_runnable.invoke({"messages": openai_messages},config=config)
            # return graph.invoke({"messages": messages},config=config)
        # Ensure the callables parameter is a list as you can have multiple callbacks
        if not isinstance(callables, list):
            raise TypeError("callables must be a list")

        # Invoke the graph with the current messages and callback configuration
        return graph.invoke({"messages": st_messages}, config={"callbacks": callables})