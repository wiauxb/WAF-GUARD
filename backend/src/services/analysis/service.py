"""
Business logic for analysing a parsed configuration.

Read-only. Reads Neo4j for graph questions (what matches, what removes what, what uses
which symbol) and PostgreSQL for source mapping (which file and line a directive came
from, through which macro calls).

Every method takes configuration_id first. See DOC.md "Analysis Routes" for the HTTP
surface and PARSER.md for how the underlying data is produced.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from shared.config import settings
from services.configmanager.storage import ConfigFileStorage

from .repository import GraphQueryRepository, SymbolQueryRepository
from .schemas import (
    DirectiveListResponse,
    DirectiveResponse,
    MacroTraceFrame,
    MacroTraceResponse,
    NodeMetadataEntry,
    NodeMetadataResponse,
    RemoverEntry,
    RemoverListResponse,
    SymbolMatch,
    SymbolSearchResponse,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """Query layer over the parsed configuration."""

    def __init__(self, db: Session, neo4j_session):
        self.db = db
        self.neo4j_session = neo4j_session
        self.storage = ConfigFileStorage(settings.STORAGE_ROOT)

    # ==================== helpers ====================

    def _graph(self, configuration_id: int) -> GraphQueryRepository:
        return GraphQueryRepository(self.neo4j_session, configuration_id)

    def _symbols(self, configuration_id: int) -> SymbolQueryRepository:
        return SymbolQueryRepository(self.db, configuration_id)

    @staticmethod
    def _to_directive(row: Dict[str, Any]) -> DirectiveResponse:
        """
        Map a Cypher row to DirectiveResponse.

        `rule_id` comes from the node's `id` property (ModSecurity's id:NNN) and is kept
        separate from `node_id` (the parser's). List properties can be absent on older
        nodes, so they default to [].

        Provenance is deliberately absent here -- see get_node_metadata().
        """
        return DirectiveResponse(
            node_id=row["node_id"],
            type=row["type"],
            args=row.get("args") or "",
            location=row.get("location"),
            virtual_host=row.get("virtual_host"),
            if_level=row.get("if_level") or 0,
            conditions=row.get("conditions") or [],
            phase=row.get("phase"),
            rule_id=row.get("rule_id"),
            tags=row.get("tags") or [],
            msg=row.get("msg"),
            constants=row.get("constants") or [],
            variables=row.get("variables") or [],
        )

    def _directive_list(
        self, configuration_id: int, rows: List[Dict[str, Any]], total: int, limit: int, offset: int
    ) -> DirectiveListResponse:
        return DirectiveListResponse(
            configuration_id=configuration_id,
            directives=[self._to_directive(r) for r in rows],
            total_count=total,
            limit=limit,
            offset=offset,
        )

    # ==================== Directive lookup ====================

    def get_directive_by_node_id(
        self, configuration_id: int, node_id: int, limit: int = 100, offset: int = 0
    ) -> DirectiveListResponse:
        """Directive by PARSER node_id.  <- GET /directives/id/{nodeid}"""
        rows, total = self._graph(configuration_id).directive_by_node_id(node_id, limit, offset)
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def get_directives_by_rule_id(
        self, configuration_id: int, rule_id: int, limit: int = 100, offset: int = 0
    ) -> DirectiveListResponse:
        """
        Directives declaring a MODSECURITY rule id.  <- GET /directives/id

        One-to-many: a chained SecRule spans several directives sharing one rule_id.
        """
        rows, total = self._graph(configuration_id).directives_by_rule_id(rule_id, limit, offset)
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def get_directives_by_tag(
        self, configuration_id: int, tag: str, limit: int = 100, offset: int = 0
    ) -> DirectiveListResponse:
        """Directives carrying a tag.  <- GET /directives/tag"""
        rows, total = self._graph(configuration_id).directives_by_tag(tag, limit, offset)
        return self._directive_list(configuration_id, rows, total, limit, offset)

    # ==================== Request simulation ====================

    def filter_directives_by_request(
        self,
        configuration_id: int,
        location: str,
        host: str,
        limit: int = 100,
        offset: int = 0,
    ) -> DirectiveListResponse:
        """
        Directives applying to a host/location, in execution order.

        <- POST /parse_http_request + POST /cypher/to_json, collapsed into one call.

        NOTE: PARSER.md defect #1 means directives inside <LocationMatch> blocks carry an
        empty location, so this under-reports heavily on configurations that use them.
        """
        rows, total = self._graph(configuration_id).directives_by_request(
            location, host, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    # ==================== Removal analysis ====================

    def get_removers_of_node(
        self, configuration_id: int, node_id: int, limit: int = 100, offset: int = 0
    ) -> RemoverListResponse:
        """
        What removed this directive, and on what grounds?  <- GET /directives/removed/{nodeid}

        Spans both identifier spaces: `node_id` is the PARSER id of the victim, while the
        criterion is either an :Id holding a MODSECURITY rule id, or a :Regex matching a
        :Tag. Only removers declared later (higher node_id) are counted.
        """
        rows, total = self._graph(configuration_id).removers_of_node(node_id, limit, offset)
        return RemoverListResponse(
            configuration_id=configuration_id,
            node_id=node_id,
            removers=[
                RemoverEntry(
                    criterion_type=r.get("criterion_type") or "",
                    criterion_value=r.get("criterion_value"),
                    directive=self._to_directive(r),
                )
                for r in rows
            ],
            total_count=total,
            limit=limit,
            offset=offset,
        )

    def get_directives_removing_rule_id(
        self, configuration_id: int, rule_id: int, limit: int = 100, offset: int = 0
    ) -> DirectiveListResponse:
        """
        SecRuleRemoveById directives targeting a rule id.  <- GET /directives/remove_by/id

        The target need not exist in this configuration — :Id nodes are created for any
        referenced rule id, including ones whose rules were never loaded.
        """
        rows, total = self._graph(configuration_id).directives_removing_rule_id(
            rule_id, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def get_directives_removing_tag(
        self, configuration_id: int, tag: str, limit: int = 100, offset: int = 0
    ) -> DirectiveListResponse:
        """
        SecRuleRemoveByTag directives matching a tag.  <- GET /directives/remove_by/tag

        Two hops via the :Regex node the parser resolves at write time. PARSER.md defect
        #4 means some Regex->Match->Tag edges are missing, so this can under-report.
        """
        rows, total = self._graph(configuration_id).directives_removing_tag(tag, limit, offset)
        return self._directive_list(configuration_id, rows, total, limit, offset)

    # ==================== Constant / variable analysis ====================

    def search_symbols(
        self, configuration_id: int, query: str, limit: int = 100, offset: int = 0
    ) -> SymbolSearchResponse:
        """
        Fulltext search over constants, variables and collections.  <- GET /search_var/{name}

        The old implementation split the query on whitespace and joined with "~" for fuzzy
        matching; that is preserved. Results are filtered by configuration because the
        cstIndex is global.
        """
        terms = [t for t in query.split() if t]
        lucene = "~ ".join(terms) + "~" if terms else query
        rows, total = self._graph(configuration_id).search_symbols(lucene, limit, offset)
        return SymbolSearchResponse(
            configuration_id=configuration_id,
            query=query,
            matches=[
                SymbolMatch(
                    name=r.get("name") or "",
                    value=r.get("value"),
                    labels=r.get("labels") or [],
                )
                for r in rows
            ],
            total_count=total,
            limit=limit,
            offset=offset,
        )

    def get_directives_using_constant(
        self,
        configuration_id: int,
        name: str,
        value: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> DirectiveListResponse:
        """Directives that read a constant/variable.  <- POST /use_node"""
        rows, total = self._graph(configuration_id).directives_using_constant(
            name, value, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def get_directives_setting_constant(
        self,
        configuration_id: int,
        name: str,
        value: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> DirectiveListResponse:
        """Directives that set or define a constant/variable.  <- POST /get_setnode"""
        rows, total = self._graph(configuration_id).directives_setting_constant(
            name, value, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    # ==================== Source mapping ====================

    def get_node_metadata(self, configuration_id: int, node_id: int) -> NodeMetadataResponse:
        """Source file/line chain for a directive.  <- GET /get_metadata/{node_id}"""
        frames = self._symbols(configuration_id).node_metadata(node_id)
        return NodeMetadataResponse(
            configuration_id=configuration_id,
            node_id=node_id,
            frames=[NodeMetadataEntry(**f) for f in frames],
        )

    def get_nodes_at_source(
        self,
        configuration_id: int,
        file_path: str,
        line_number: int,
        limit: int = 100,
        offset: int = 0,
    ) -> DirectiveListResponse:
        """Directives produced by a given configuration line.  <- POST /nodes/get_node_ids"""
        node_ids = self._symbols(configuration_id).node_ids_at_source(file_path, line_number)
        rows, total = self._graph(configuration_id).directives_by_node_ids(
            node_ids, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def get_macro_call_trace(self, configuration_id: int, node_id: int) -> MacroTraceResponse:
        """
        Full macro call stack for a directive, with the source text of each frame.

        Composed in the old chatbot rather than exposed as an endpoint
        (old/services/chatbot/Graph/uiGraph.py:153). The only analysis method that reads
        the filesystem: it takes the metadata chain, then pulls each <Macro> body and the
        `Use` site out of the extracted configuration files.
        """
        chain = self._symbols(configuration_id).node_metadata(node_id)
        if not chain:
            return MacroTraceResponse(
                configuration_id=configuration_id, node_id=node_id, frames=[], formatted=""
            )

        try:
            config_root = self.storage.get_extracted_path(configuration_id)
        except FileNotFoundError:
            logger.warning(
                "No extracted files for configuration %d; returning metadata only",
                configuration_id,
            )
            return MacroTraceResponse(
                configuration_id=configuration_id,
                node_id=node_id,
                frames=[
                    MacroTraceFrame(content="", **f) for f in chain
                ],
                formatted="",
            )

        frames: List[MacroTraceFrame] = []

        # Innermost frame: find where the macro is USED, closest to the recorded line.
        head = chain[0]
        use_line, use_content = self._extract_macro_usage(
            config_root, head["file_path"], head["macro_name"], head["line_number"]
        )
        frames.append(
            MacroTraceFrame(
                macro_name=head["macro_name"],
                file_path=head["file_path"],
                line_number=use_line or head["line_number"],
                content=use_content,
            )
        )

        # Each outer frame: the definition of the macro named by the frame inside it.
        for inner, outer in zip(chain, chain[1:]):
            def_line, def_content = self._extract_macro_definition(
                config_root, outer["file_path"], inner["macro_name"]
            )
            frames.append(
                MacroTraceFrame(
                    macro_name=inner["macro_name"],
                    file_path=outer["file_path"],
                    line_number=def_line or outer["line_number"],
                    content=def_content,
                )
            )

        formatted = f"Macro call trace for node {node_id}, {head['macro_name']}:\n\n"
        for f in frames:
            formatted += f"Line {f.line_number}: {f.file_path}\n{f.content}\n\n"

        return MacroTraceResponse(
            configuration_id=configuration_id,
            node_id=node_id,
            frames=frames,
            formatted=formatted.rstrip() + "\n",
        )

    # ---------- filesystem helpers for the macro trace ----------

    def _resolve(self, config_root: str, dump_path: str) -> Optional[str]:
        """
        Map a path as recorded in the dump onto the extracted tree.

        The dump refers to files by their location inside the WAF container
        (/etc/httpd/conf/...); everything up to and including `conf/` is replaced with
        this configuration's extracted root.
        """
        tail = dump_path.replace("\\", "/").split("/conf/")[-1]
        candidate = os.path.normpath(os.path.join(config_root, "conf", tail))
        root = os.path.normpath(config_root)
        if not candidate.startswith(root):        # defensive: no traversal out of the config
            return None
        return candidate if os.path.isfile(candidate) else None

    def _read(self, path: Optional[str]) -> List[str]:
        if not path:
            return []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()
        except OSError as e:
            logger.warning("Could not read %s: %s", path, e)
            return []

    def _extract_macro_definition(self, config_root: str, dump_path: str, macro_name: str):
        """Find `<Macro name ...>` ... `</Macro>` and return (start_line, body)."""
        lines = self._read(self._resolve(config_root, dump_path))
        start_re = re.compile(rf"<\s*Macro\s+{re.escape(macro_name)}\b.*?>", re.IGNORECASE)
        end_re = re.compile(r"</\s*Macro\s*>", re.IGNORECASE)

        body: List[str] = []
        first = None
        for i, line in enumerate(lines, start=1):
            if first is None:
                if start_re.search(line):
                    first = i
                    body.append(line)
            else:
                body.append(line)
                if end_re.search(line):
                    break
        return (first, "".join(body)) if body else (None, "")

    def _extract_macro_usage(
        self, config_root: str, dump_path: str, macro_name: str, target_line: int
    ):
        """
        Find the `Use <macro_name>` site closest to target_line.

        A macro is often used many times in one file, so proximity to the line recorded
        in symbol_table is what disambiguates — same heuristic as the old chatbot.
        """
        lines = self._read(self._resolve(config_root, dump_path))
        use_re = re.compile(rf"\bUse\s+{re.escape(macro_name)}\b", re.IGNORECASE)
        matches = [(i, l.strip()) for i, l in enumerate(lines, start=1) if use_re.search(l)]
        if not matches:
            return None, ""
        return min(matches, key=lambda m: abs(m[0] - (target_line or 0)))
