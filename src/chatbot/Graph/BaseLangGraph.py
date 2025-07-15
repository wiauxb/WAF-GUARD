# base_graph.py
from abc import ABC, abstractmethod
from langchain_core.messages import messages_from_dict, convert_to_openai_messages,messages_to_dict
# from langchain_core.messages import AIMessage, HumanMessage, message_to_dict, messages_from_dict
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

class BaseLangGraph(ABC):
    def __init__(self,pool,checkpointer=False,store=False):
        self.checkpointer = checkpointer
        self.store = store
        self.pool= pool
        self.graph = self.compile()

    @abstractmethod
    def build_graph(self):
        pass

    def compile(self):
        # This method can be used to compile the graph if needed
        graph = self.build_graph()
        if self.checkpointer:
            checkpointer = PostgresSaver(self.pool)
            # checkpointer.setup()
        if self.store:
            store = PostgresStore(self.pool)
            store.setup()
        if not self.checkpointer and not self.store:
            return graph.compile()
        if self.checkpointer and not self.store:
            return graph.compile(checkpointer=checkpointer)
        if not self.checkpointer and self.store:
            return graph.compile(store=store)
        # if both checkpointer and store are enabled, return both
        if self.checkpointer and self.store:
            return graph.compile(checkpointer=checkpointer, store=store)


    def invoke(self, messages, configuration=None, callbacks=None):
        config={}
        if configuration:
            config["configurable"] = configuration
        if callbacks:
            config["callbacks"] = callbacks
        config["recursion_limit"] = 4
        formated_messages=(messages_from_dict(messages))
        openai_messages = convert_to_openai_messages(formated_messages)
        response_messages=self.graph.invoke({"messages": openai_messages},config=config)["messages"]
        # print(f"Response messages type: {type(response_messages[0])}", flush=True)
        # print(f"Response messages: {response_messages}", flush=True)
        response = []

        # iterate from the last message to the first, append the message to response until the first user message
        for message in reversed(response_messages):
            if message.type == "human":
                break
            response.append(message)
        response.reverse()

        #force the response format because of openai messages
        payload=messages_to_dict(response)
        # print(f"Payload: {payload}", flush=True)
        return payload