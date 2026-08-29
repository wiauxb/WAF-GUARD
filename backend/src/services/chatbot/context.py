"""
Per-conversation runtime context, and the session plumbing the tools need.

A conversation is pinned to ONE configuration when it is created, and every tool call in it
resolves against that configuration — never the user's current active one. That is what
makes an old conversation still answer about the configuration it was actually about;
reading the active config at call time meant revisiting a thread silently changed its
answers.

The binding travels as LangGraph's typed context (`context_schema` on create_agent, then
`context=` at invoke), NOT in the message state: it is per-invocation input, so it must not
be checkpointed alongside the conversation history.
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass

from shared.database import get_neo4j_session, get_postgres_session
from services.analysis.service import AnalysisService
from services.configmanager.models import Configuration

logger = logging.getLogger(__name__)

# Tool results re-enter the model's context window on every subsequent turn, so they are
# capped hard. A `search_directives` that returned 1,000 rows of 10 KB `args` would exhaust
# the window in a single call.
DEFAULT_LIMIT = 20
MAX_LIMIT = 50


@dataclass
class ChatContext:
    """What every tool in a conversation resolves against."""
    configuration_id: int
    user_id: int


class ConfigurationUnavailable(Exception):
    """
    The bound configuration cannot be queried.

    Raised inside the session helper and turned into a SENTENCE by the tool wrapper rather
    than propagated: an exception ends the agent's turn, whereas a message lets it explain
    the problem to the user and, where sensible, carry on.
    """


@contextmanager
def analysis_for(configuration_id: int):
    """
    An AnalysisService bound to one configuration, with its own short-lived sessions.

    Tools run inside the request but outside FastAPI's dependency injection, so they cannot
    receive the request-scoped session. Each opens and closes its own, the same way
    ParserService does for its background work.

    Also enforces the guard the HTTP layer applies in `get_analysis_configuration_id`:
    unknown, unparsed, or parsed-but-empty are all reported rather than returning silently
    wrong (empty) answers.
    """
    db = get_postgres_session()
    neo4j_session = None
    try:
        config = db.query(Configuration).filter(Configuration.id == configuration_id).first()
        if config is None:
            raise ConfigurationUnavailable(
                f"Configuration {configuration_id} does not exist."
            )
        if config.parsing_status != "parsed":
            raise ConfigurationUnavailable(
                f"Configuration '{config.name}' is not parsed (status: "
                f"{config.parsing_status}), so it cannot be queried yet."
            )

        neo4j_session = get_neo4j_session()
        service = AnalysisService(db, neo4j_session)

        # Marked parsed but the graph is gone — a real split-brain, since PostgreSQL keeps
        # parsing_status independently of Neo4j. Without this the tools would confidently
        # report zero of everything.
        if not service._graph(configuration_id).has_any_node():
            raise ConfigurationUnavailable(
                f"Configuration '{config.name}' is marked parsed but its graph is empty; "
                f"it needs re-parsing."
            )

        yield service, config
    finally:
        if neo4j_session is not None:
            try:
                neo4j_session.close()
            except Exception:
                logger.warning("Failed to close neo4j session in a chatbot tool", exc_info=True)
        db.close()


def clamp(limit: int | None) -> int:
    """Keep a tool's result set inside the context budget whatever the model asks for."""
    if not limit or limit < 1:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def as_list(v) -> list:
    """
    Coerce a list-ish tool argument into a list.

    Models routinely pass a bare string where a list is declared — `locations: ""` instead
    of `locations: [""]` — and strict validation turns that into a failed tool call the
    agent has to notice and retry. Since a single value is an unambiguous one-element list,
    accepting it costs nothing and removes a whole class of wasted round trip.

    `None` stays empty; note "" is a MEANINGFUL value (outside every block), so it must
    become [""] rather than being dropped as falsy.
    """
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    return [v]


def compact_directive(d) -> dict:
    """
    One directive, trimmed for the model.

    `args` is the expensive field — up to 10 KB on a single SecRule — so it is truncated.
    Both identifier spaces are carried and NAMED, because they overlap numerically and
    confusing them is the likeliest way for an answer to be quietly wrong.
    """
    args = d.args or ""
    return {
        "node_id": d.node_id,                       # parser id, on every directive
        "rule_id": d.rule_id,                       # ModSecurity id:NNN, may be null
        "type": d.type,
        "phase": d.phase,
        "host": d.virtual_host or "(global)",
        "location": d.location or "(all paths)",
        "location_kind": d.location_kind,
        "tags": d.tags[:6],
        "msg": d.msg,
        "args": args[:300] + ("…" if len(args) > 300 else ""),
    }
