# base_graph.py
from abc import ABC, abstractmethod
from langchain_core.messages import messages_from_dict, convert_to_openai_messages
from langgraph.checkpoint.postgres import PostgresSaver

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
        return graph.compile(checkpointer=checkpointer)


    def invoke(self, messages, configuration=None, callbacks=None):
        config={}
        if configuration:
            config["configurable"] = configuration
        if callbacks:
            config["callbacks"] = callbacks
        formated_messages=(messages_from_dict(messages))
        openai_messages = convert_to_openai_messages(formated_messages)
        return self.graph.invoke({"messages": openai_messages},config=config)