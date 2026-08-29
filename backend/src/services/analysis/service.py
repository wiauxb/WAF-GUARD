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

from . import queries as Q
from . import urlmatch
from .repository import GraphQueryRepository, SymbolQueryRepository
from .schemas import (
    DirectiveListResponse,
    DirectiveResponse,
    DirectiveSearchQuery,
    FacetCount,
    FacetValuesResponse,
    LocationMatchEntry,
    LocationWarning,
    MacroTraceFrame,
    MacroTraceResponse,
    NodeMetadataEntry,
    NodeMetadataResponse,
    RemoverEntry,
    RemoverListResponse,
    SymbolMatch,
    SymbolSearchResponse,
    UrlMatchResponse,
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
            location_kind=row.get("location_kind"),
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

    # ==================== Combinable search ====================

    def search_directives(
        self,
        configuration_id: int,
        query: DirectiveSearchQuery,
        limit: int = 100,
        offset: int = 0,
    ) -> DirectiveListResponse:
        """
        Any combination of directive criteria, sorted by any supported column.

        Backs the Directives page. Every criterion is AND-ed; within one criterion the
        semantics follow the property -- see DirectiveSearchQuery.

        Criteria are matched against node PROPERTIES rather than the relationships that
        mirror them ($tag IN n.tags, not (n)-[:Has]->(:Tag)). That is what lets them
        combine into one MATCH, and it is cheaper too: the relationship form for
        location/host expands every directive's edge to a single shared value node.
        """
        clauses, params, empty = self._build_clauses(configuration_id, query)
        if empty:
            return self._directive_list(configuration_id, [], 0, limit, offset)

        rows, total = self._graph(configuration_id).search_directives(
            clauses, params, query.sort_by, query.sort_dir, limit, offset
        )
        return self._directive_list(configuration_id, rows, total, limit, offset)

    def _build_clauses(
        self,
        configuration_id: int,
        query: DirectiveSearchQuery,
        exclude: Optional[set] = None,
    ) -> tuple[List[str], Dict[str, Any], bool]:
        """
        Turn a query into (clauses, params, provably_empty).

        Shared by the search and by the facet counts, so a dropdown can never advertise a
        number the search would not reproduce -- they are literally the same predicates.

        `exclude` names query fields to leave out, which is what makes faceting work. For a
        facet on an OR field, its own values are excluded: adding a value WIDENS the result,
        so counting with the field's own chips applied would collapse the list to what is
        already picked and you could never add a second one. `tags` is the exception and is
        never excluded -- adding a tag NARROWS, so each candidate's count within the current
        results is exactly what picking it would give.

        `provably_empty` means a criterion resolved to nothing (a source line that produced
        no directives, a URL no container covers). The caller short-circuits instead of
        emitting `IN []`, which is a full scan that can only return nothing.
        """
        exclude = exclude or set()
        clauses: List[str] = []
        params: Dict[str, Any] = {}

        # OR-within-field: several values of a single-valued property.
        for field in ("types", "phases", "rule_ids", "msgs"):
            values = getattr(query, field)
            if values and field not in exclude:
                clauses.append(Q.CLAUSES[field])
                params[field] = values

        # Exact host/location, any of. Note "" is a legitimate value here -- it means
        # "outside any VirtualHost/Location block" -- so these must not be truthiness-
        # filtered the way the scalar criteria below are.
        #
        # A `url` contributes to the SAME location set rather than a clause of its own.
        # Two IN-sets on one property would be AND-ed, i.e. intersected, so `url` plus an
        # explicit location chip returned zero unless that chip happened to be in the URL's
        # own match set -- including the "All paths" chip the UI recommends. Merged, they
        # behave like every other multi-value field: any of them. Faceting `location`
        # therefore has to exclude BOTH, which is why they share a key here.
        if "locations" not in exclude:
            locations = list(query.locations)
            if query.url and query.url.strip():
                matched = [m.value for m in self._match_url(configuration_id, query.url)[0]]
                if not matched and not locations:
                    return clauses, params, True
                for value in matched:
                    if value not in locations:
                        locations.append(value)
            if locations:
                clauses.append(Q.CLAUSES["locations"])
                params["locations"] = locations

        if query.hosts and "hosts" not in exclude:
            clauses.append(Q.CLAUSES["hosts"])
            params["hosts"] = query.hosts

        # AND-within-field: the directive must carry every tag asked for. Never excluded --
        # see the docstring.
        if query.tags:
            clauses.append(Q.CLAUSES["tags"])
            params["tags"] = query.tags

        for field in ("node_id", "host", "location", "args_contains", "msg_contains"):
            value = getattr(query, field)
            if value is not None and value != "" and field not in exclude:
                clauses.append(Q.CLAUSES[field])
                params[field] = value

        if query.has_rule_id is not None:
            key = "has_rule_id_true" if query.has_rule_id else "has_rule_id_false"
            clauses.append(Q.CLAUSES[key])          # no parameter: the clause IS the test

        # Source line lives in PostgreSQL, so it resolves to node_ids first and joins the
        # rest of the criteria as an ordinary clause.
        if query.source is not None:
            node_ids = self._symbols(configuration_id).node_ids_at_source(
                query.source.file_path, query.source.line_number
            )
            if not node_ids:
                return clauses, params, True
            clauses.append(Q.CLAUSES["source_node_ids"])
            params["source_node_ids"] = node_ids

        return clauses, params, False

    # Which query fields a facet on each value-field must ignore. Adding a value to an OR
    # field WIDENS the result, so counting with that field's own chips applied would
    # collapse the list to what is already picked. `location` also drops `url`, because a
    # URL resolves into the same location set.
    #
    # `tag` is absent on purpose: adding a tag NARROWS, so each candidate's count within the
    # current results is exactly what picking it would give.
    _FACET_EXCLUDES = {
        "type": {"types"},
        "phase": {"phases"},
        "msg": {"msgs", "msg_contains"},
        "host": {"hosts", "host"},
        "location": {"locations", "location", "url"},
        "tag": set(),
    }

    def get_directive_values(
        self,
        configuration_id: int,
        field: str,
        q: str = "",
        limit: int = 50,
        filters: Optional[DirectiveSearchQuery] = None,
    ) -> FacetValuesResponse:
        """
        Searchable value list for one property, counted WITHIN the current filters.

        Each count answers "how many results if I add this value" -- exactly, in a single
        aggregation, because the clauses come from the same builder the search uses. A value
        whose count would be zero simply has no row and does not appear, so the list only
        ever offers choices that lead somewhere.
        """
        filters = filters or DirectiveSearchQuery()
        clauses, params, empty = self._build_clauses(
            configuration_id, filters, exclude=self._FACET_EXCLUDES.get(field, set())
        )
        rows = [] if empty else self._graph(configuration_id).directive_values(
            field, q, limit, clauses, params
        )
        return FacetValuesResponse(
            configuration_id=configuration_id,
            field=field,
            query=q,
            values=[FacetCount(**r) for r in rows],
        )

    def _match_url(self, configuration_id: int, url: str):
        """
        Shared by the URL filter and the panel: (matches, warnings, path, patterns).

        Matching runs here in Python rather than as a Cypher `=~` because Apache's
        semantics cannot be expressed there — see urlmatch's module docstring.
        """
        rows = self._graph(configuration_id).all_locations()
        patterns = urlmatch.prepare((r["value"], r["kind"], r["count"]) for r in rows)
        path = urlmatch.normalise(url)
        return urlmatch.match(path, patterns), patterns, path

    def match_url(self, configuration_id: int, url: str) -> UrlMatchResponse:
        """
        Which `<Location>` / `<LocationMatch>` blocks cover a URL from a log.

        Directives with no location apply to every path; they are excluded from `matches`
        (they would be the same block on every URL) but counted in `no_location_count`, so
        the omission is stated rather than silent.
        """
        matches, patterns, path = self._match_url(configuration_id, url)
        return UrlMatchResponse(
            configuration_id=configuration_id,
            url=url,
            path=path,
            matches=[
                LocationMatchEntry(value=m.value, kind=m.kind, count=m.count) for m in matches
            ],
            total_directives=sum(m.count for m in matches),
            no_location_count=self._graph(configuration_id).no_location_count(),
            warnings=[
                LocationWarning(value=p.value, kind=p.kind, reason=p.warning)
                for p in patterns
                if p.warning
            ],
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

        NOTE: the location/host REGEX form. `<LocationMatch>` values are themselves regexes
        now that the parser tracks them (PARSER.md defect #1, resolved), so matching them with
        `=~` is rarely what you want -- prefer the exact `locations`/`hosts` fields on
        /directives/search.
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
