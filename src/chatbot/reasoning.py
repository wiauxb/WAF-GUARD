from typing import Annotated, TypedDict, Literal

from langgraph.prebuilt import ToolNode,tools_condition
from langchain_core.tools import tool, StructuredTool
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import AnyMessage, add_messages
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_core.prompts.prompt import PromptTemplate
from pydantic import BaseModel,Field
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from typing import Annotated, List, Tuple, Union
from typing_extensions import TypedDict
import operator
from langgraph.prebuilt import create_react_agent

import os

from langsmith import Client
from dotenv import load_dotenv
load_dotenv()


neoGraph = Neo4jGraph(url="bolt://localhost:7687", username="neo4j", password="password")
client = Client()


class RelevantType(BaseModel):
    relevants: list[str]

class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class GraphsState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )




#####################################   TOOLS   #####################################



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
    llm = ChatOpenAI(temperature=0,model="o1-mini").with_structured_output(RelevantType)
    runnable=RELEVANT_TYPE_PROMPT|llm
    response=runnable.invoke({"question": question, "schema": list(neoGraph.structured_schema["node_props"].keys())})
    print(response.relevants)
    query=query_builder(question,response.relevants)
    print(query)
    database_reponse=neoGraph.query(query)
    print(database_reponse)
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
        persist_directory="./chromadb",  # Where to save data locally, remove if not necessary
    )
    response=vector_store.similarity_search(question)
    print(response)
    return response


tools=[database_retriever, Modsecurity_retriever]



#####################################   TOOLS HELPERS   #####################################




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
    print("Query builder")
    filtered_nodes ={}
    filtered_relationships=[]
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
    llm = ChatOpenAI(temperature=0,model="o1-mini")
    PROMPT_CYPHER=PromptTemplate(input_variables=["question","nodes","relationships"], template=CYPHER_GENERATION_TEMPLATE)
    agent=PROMPT_CYPHER|llm

    response=agent.invoke({"question": question, "nodes": filtered_nodes, "relationships": filtered_relationships})
    return response.content






#####################################   PLANNING AGENTS   #####################################


planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.""",
        ),
        ("placeholder", "{messages}"),
    ]
)
planner = planner_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(Plan)





replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
)


replanner = replanner_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(Act)


# Choose the LLM that will drive the agent
llm = ChatOpenAI(model="gpt-4-turbo-preview")
prompt = "You are a helpful assistant."
agent_executor = create_react_agent(llm, tools, prompt=prompt)




#####################################   REASONING NODES   #####################################



def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}."""
    agent_response =  agent_executor.invoke(
        {"messages": [("user", task_formatted)]}
    )
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }


def plan_step(state: PlanExecute):
    plan =  planner.invoke({"messages": [("user", state["input"])]})
    print(plan)
    return {"plan": plan.steps}


def replan_step(state: PlanExecute):
    output = replanner.invoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"








#####################################   BASIC GRAPH NODES   #####################################


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
        [("human", prompt,),("placeholder", "{messages}"),]
    )
    llm = ChatOpenAI(model="o1-mini")
    agent=llmprompt|llm.bind_tools(tools)
    response = agent.invoke({"messages":messages})
    return {"messages": [response]}  # add the response to the messages using LangGraph reducer paradigm













#####################################   REASONING WORKFLOW   #####################################

workflow = StateGraph(PlanExecute)

# Add the plan node
workflow.add_node("planner", plan_step)

# Add the execution step
workflow.add_node("agent", execute_step)

# Add a replan node
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")

# From plan we go to agent
workflow.add_edge("planner", "agent")

# From agent, we replan
workflow.add_edge("agent", "replan")

workflow.add_conditional_edges(
    "replan",
    # Next, we pass in the function that will determine which node is called next.
    should_end,
    ["agent", END],
)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile()









#####################################   BASIC GRAPH WORKFLOW   #####################################

graph = StateGraph(GraphsState)
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





#####################################   RUNNER   #####################################

# Function to invoke the compiled graph externally
def invoke_reasoning_graph(st_messages, callables=None):
    if callables is None:
        return graph_runnable.invoke({"messages": st_messages})
    # Ensure the callables parameter is a list as you can have multiple callbacks
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")

    # Invoke the graph with the current messages and callback configuration
    # return graph_runnable.invoke({"messages": st_messages}, config={"callbacks": callables})
    graph_output=app.invoke({"input": st_messages[-1].content}, config={"callbacks": callables})
    return graph_output["Response"]
