"""
Agent construction.

Built with `langchain.agents.create_agent`, which the LangChain v1 docs call "the new
standard for building agents in LangChain, replacing langgraph.prebuilt.create_react_agent"
— the entry point this used to use. What that buys here, concretely:

  - `context_schema` + ToolRuntime, so a conversation's configuration reaches every tool
    as typed per-invocation input rather than being smuggled through message state;
  - middleware, of which SummarizationMiddleware is not optional for this workload —
    directive tool results are bulky and a long investigation would otherwise walk off the
    end of the context window mid-conversation.
"""

import logging

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_openai import ChatOpenAI

from shared.config import settings
from services.chatbot.context import ChatContext
from services.chatbot.prompts.agent_prompts import get_system_prompt
from services.chatbot.tools.registry import get_tools_for_categories

logger = logging.getLogger(__name__)


def build_ui_graph_v1(checkpointer, model_name: str = None, temperature: float = None):
    """
    The WAF analysis agent.

    Args:
        checkpointer: LangGraph saver; the conversation history lives here, keyed by
            thread_id.
        model_name: defaults to settings.OPENAI_MODEL.
        temperature: defaults to settings.CHATBOT_TEMPERATURE.

    Returns:
        A compiled agent. Invoke it with BOTH a thread and a context:

            agent.invoke(
                {"messages": [...]},
                config={"configurable": {"thread_id": thread_id}},
                context=ChatContext(configuration_id=..., user_id=...),
            )

        The thread_id selects the conversation; the context selects the configuration its
        tools resolve against. Omitting the context leaves the tools with nothing to query.
    """
    model_name = model_name or settings.OPENAI_MODEL
    temperature = settings.CHATBOT_TEMPERATURE if temperature is None else temperature

    model = ChatOpenAI(model=model_name, temperature=temperature)

    return create_agent(
        model=model,
        tools=get_tools_for_categories(["waf"]),
        system_prompt=get_system_prompt("ui_graph_v1"),
        context_schema=ChatContext,
        checkpointer=checkpointer,
        middleware=[
            # Compresses older turns once the history grows, keeping the recent exchange
            # intact. Without it a handful of directive searches fills the window and the
            # conversation starts failing rather than degrading.
            SummarizationMiddleware(
                model=model,
                keep=("messages", settings.CHATBOT_KEEP_MESSAGES),
            ),
        ],
    )
