from typing import Annotated, TypedDict, Literal

from langgraph.prebuilt import ToolNode,tools_condition
from langchain_core.tools import tool, StructuredTool
from langgraph.graph import START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_core.prompts.prompt import PromptTemplate
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

import os

from langsmith import Client
from dotenv import load_dotenv
load_dotenv()


class RelevantType(BaseModel):
    relevants: list[str]

class GraphsState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]




@tool
def database_retriever(question:str):
    """
    Tool used to answer question related to the neo4j database

    Args:
    question (str): The question to be answered

    """

    RELEVANT_TYPE_TEMPLATE="""
    Determine the relevant type of nodes to be considered when creating a Cypher to query a Neo4j database that represents WAF configuration using Apache2 and modSecurity.
    ################## QUESTION ##################
    {question}

    ################## OUTPUT ##################
    - You need to return a list of strings where each string is the name of a node type that should be considered when creating the Cypher query.
    - Keep the case of the node type as it is in the available node types.

    ################## AVAILABLE NODE TYPES ##################
    {schema}
    """

    RELEVANT_TYPE_PROMPT = PromptTemplate(input_variables=["question","schema"], template=RELEVANT_TYPE_TEMPLATE)
    llm = ChatOpenAI(temperature=0,model="gpt-4o").with_structured_output(RelevantType)
    runnable=RELEVANT_TYPE_PROMPT|llm
    response=runnable.invoke({"question": question, "schema": list(neoGraph.structured_schema["node_props"].keys())})
    # print(response.relevants)
    query=query_builder(question,response.relevants)
    # print(query)
    database_reponse=neoGraph.query(query)
    # print(database_reponse)
    return database_reponse

@tool
def Modsecurity_retriever(question:str):
    """
    Tool used to answer general questions related to modsecurity version 2.X

    Args:
    question (str): The question to be answered
    """

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = Chroma(
        collection_name="ModSecurity_documentation",
        embedding_function=embeddings,
        persist_directory="/chromadb",  # Where to save data locally, remove if not necessary
    )
    response=vector_store.similarity_search(question)
    # print(response)
    return response




def query_builder(question:str, relevant_type:list[str]):
    
    CYPHER_GENERATION_TEMPLATE = """
    ################## TASK ##################
    Task:Generate Cypher statement that query a graph database to answer the provided question. The database represents WAF configuration using Apache2 and modSecurity.
    You will be provided with the nodes and relationships available in the database schema.
    
    ################## INSTRUCTIONS ##################
    - Use only the provided relationship and nodes type in the query
    - Do not use nodes and relationships that are not required to answer the question
    - Do not include any explanations or apologies in your responses.
    - Do not include any text except the generated Cypher statement.
    - Do not include any formating, only the Cypher statement as a string.

    ################## NODES ##################
    {nodes}

    ################## RELATIONSHIPS ##################
    {relationships}

    ################## QUESTION ##################
    {question}
    """
    # print("Query builder")
    filtered_nodes ={}
    filtered_relationships=[]
    # print(neoGraph.structured_schema["node_props"])
    for key in neoGraph.structured_schema["node_props"]:
        if key in relevant_type:
            filtered_nodes[key]=neoGraph.structured_schema["node_props"][key].copy()
    print("=========  FILTERED NODES ===========")
    # print(filtered_nodes)
    for rel in neoGraph.structured_schema["relationships"]:
        if rel["start"] in relevant_type or rel["end"] in relevant_type:
             filtered_relationships.append(rel)
    print("========= FILTERED RELATIONSHIPS ===========")
    # print(filtered_relationships)
    llm = ChatOpenAI(temperature=0,model="gpt-4o")
    PROMPT_CYPHER=PromptTemplate(input_variables=["question","nodes","relationships"], template=CYPHER_GENERATION_TEMPLATE)
    agent=PROMPT_CYPHER|llm

    response=agent.invoke({"question": question, "nodes": filtered_nodes, "relationships": filtered_relationships})
    return response.content


neoGraph = Neo4jGraph(url="bolt://neo4j:7687", username="neo4j", password="password")
neoGraph.refresh_schema()
client = Client()
graph = StateGraph(GraphsState)
tools=[database_retriever, Modsecurity_retriever]



# Function to decide whether to continue tool usage or end the process
# def should_continue(state: GraphsState) -> Literal["tools", "__end__"]:
#     messages = state["messages"]
#     last_message = messages[-1]
#     if last_message.tool_calls:  # Check if the last message has any tool calls
#         return "tools"  # Continue to tool execution
#     return "__end__"  # End the conversation if no tool is needed

# Define the prompt for the model
# ontology = g.serialize(format="turtle")
# prompt=f"""
# You are an expert of WAF configuration using Apache2 and modSecurity. An ontology has been created to represent the configuration of the WAF.
# Your purpose is to answer questions about this ontology. Here is the turtle representation of the ontology:
# """
# llmprompt=ChatPromptTemplate.from_messages(
#     [("system", prompt,),("placeholder", "{messages}"),]
# )
# llm = ChatOpenAI()
# agent=llmprompt|llm






# # Core invocation of the model
def call_model(state: GraphsState):
    messages = state["messages"]
    prompt=f"""
    You are an expert of WAF configuration using Apache2 and modSecurity. You role is to support the user in answering specific or general questions about the WAF configuration.
    The configuration is represented in a graph database and use modSecurity 2.X 
    You can use the database_retiever tool to answer specific questions about the configuration.
    You must use the Modsecurity_retriever tool to answer general questions about modsecurity version 2.X
    """
    llmprompt=ChatPromptTemplate.from_messages(
        [("system", prompt,),("placeholder", "{messages}"),]
    )
    llm = ChatOpenAI(model="gpt-4o")
    agent=llmprompt|llm.bind_tools(tools)
    response = agent.invoke({"messages":messages})
    return {"messages": [response]}  # add the response to the messages using LangGraph reducer paradigm





# graph_runnable=create_react_agent(llm,state_modifier=prompt)

# Define the structure (nodes and directional edges between nodes) of the graph



# graph.add_node("tools", tool_node)
# neo4j_tools=ToolNode([db_response, relevant_type])
database_tool=ToolNode(tools)
graph.add_node("modelNode", call_model)
graph.add_node("tools", database_tool)
graph.add_conditional_edges(
    "modelNode",
    tools_condition
)

graph.add_edge("tools", "modelNode")
graph.add_edge(START, "modelNode")




# # Compile the state graph into a runnable object
graph_runnable = graph.compile()

# Function to invoke the compiled graph externally
def invoke_basic_graph(st_messages, callables=None):
    if callables is None:
        # return graph_runnable.invoke({"messages": st_messages})
        return graph_runnable.invoke({"messages": st_messages})
    # Ensure the callables parameter is a list as you can have multiple callbacks
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")

    # Invoke the graph with the current messages and callback configuration
    return graph_runnable.invoke({"messages": st_messages}, config={"callbacks": callables})












# # Add conditional logic to determine the next step based on the state (to continue or to end)
# graph.add_conditional_edges(
#     "modelNode",
#     should_continue,  # This function will decide the flow of execution
# )
# graph.add_edge("tools", "modelNode")