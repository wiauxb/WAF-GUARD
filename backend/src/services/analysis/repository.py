"""
Data access for AnalysisService. Read-only; the parser owns all writes.

- GraphQueryRepository  -> Neo4j, the directive graph
- SymbolQueryRepository -> PostgreSQL, source mapping (symbol_table / macro_* tables)

Both are scoped to one configuration, mirroring the parser's repositories.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.parser.models import MacroCall, MacroDefinition, Symbol

from . import queries as Q

logger = logging.getLogger(__name__)


class GraphQueryRepository:
    """Neo4j reads for a single configuration."""

    def __init__(self, session, configuration_id: int):
        self.session = session
        self.configuration_id = configuration_id

    def _run(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return plain dicts.

        Parameters are passed as a POSITIONAL DICT, never as **kwargs: neo4j's
        Session.run(query, parameters, **kwargs) would collide with our own parameter
        names — `$query` in SEARCH_SYMBOLS and `$name` in the constant queries both
        shadow its arguments and raise TypeError.
        """
        params = {"cid": self.configuration_id, **(params or {})}
        return [record.data() for record in self.session.run(cypher, params)]

    # ---------- staleness ----------

    def has_any_node(self) -> bool:
        """
        True if this configuration has any node in the graph.

        Backs the "marked parsed but the graph is empty" guard — a state that occurs
        when Neo4j loses its data while PostgreSQL keeps parsing_status='parsed'.
        """
        rows = self._run(Q.HAS_ANY_NODE)
        return bool(rows and rows[0].get("has_nodes"))

    # ---------- generic paginated fetch ----------

    def fetch_page(
        self,
        page_cypher: str,
        count_cypher: str,
        params: Dict[str, Any],
        limit: int,
        offset: int,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Run a list query as two statements: one page, one count.

        They are deliberately separate. Computing the total inside the page query means
        collecting every match to size it, which materialises all node properties --
        1.45 GB on a 12k-directive configuration, enough to exceed Neo4j's transaction
        memory cap. Split, the page streams (~1.4 MB, flat at any offset) and the count
        touches no properties (~0.4 MB).
        """
        rows = self._run(page_cypher, {**params, "limit": limit, "skip": offset})
        count_rows = self._run(count_cypher, params)
        total = count_rows[0]["total_count"] if count_rows else 0
        return rows, total

    # ---------- directive lookup ----------

    def directive_by_node_id(self, node_id: int, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVE_BY_NODE_ID_PAGE, Q.DIRECTIVE_BY_NODE_ID_COUNT,
            {"node_id": node_id}, limit, offset,
        )

    def directives_by_rule_id(self, rule_id: int, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_BY_RULE_ID_PAGE, Q.DIRECTIVES_BY_RULE_ID_COUNT,
            {"rule_id": rule_id}, limit, offset,
        )

    def directives_by_tag(self, tag: str, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_BY_TAG_PAGE, Q.DIRECTIVES_BY_TAG_COUNT,
            {"tag": tag}, limit, offset,
        )

    def directives_by_node_ids(self, node_ids: List[int], limit: int, offset: int):
        if not node_ids:
            return [], 0
        return self.fetch_page(
            Q.DIRECTIVES_BY_NODE_IDS_PAGE, Q.DIRECTIVES_BY_NODE_IDS_COUNT,
            {"node_ids": node_ids}, limit, offset,
        )

    # ---------- request simulation ----------

    def directives_by_request(self, location: str, host: str, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_BY_REQUEST_PAGE, Q.DIRECTIVES_BY_REQUEST_COUNT,
            {"location": location, "host": host}, limit, offset,
        )

    # ---------- removal analysis ----------

    def removers_of_node(self, node_id: int, limit: int, offset: int):
        return self.fetch_page(
            Q.REMOVERS_OF_NODE_PAGE, Q.REMOVERS_OF_NODE_COUNT,
            {"node_id": node_id}, limit, offset,
        )

    def directives_removing_rule_id(self, rule_id: int, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_REMOVING_RULE_ID_PAGE, Q.DIRECTIVES_REMOVING_RULE_ID_COUNT,
            {"rule_id": rule_id}, limit, offset,
        )

    def directives_removing_tag(self, tag: str, limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_REMOVING_TAG_PAGE, Q.DIRECTIVES_REMOVING_TAG_COUNT,
            {"tag": tag}, limit, offset,
        )

    # ---------- symbols ----------

    def search_symbols(self, query: str, limit: int, offset: int):
        """
        Fulltext search over constants / variables / collections.

        cstIndex is a GLOBAL index with no configuration_id, so both statements filter
        results by configuration -- otherwise other configurations' symbols leak through.
        """
        return self.fetch_page(
            Q.SEARCH_SYMBOLS_PAGE, Q.SEARCH_SYMBOLS_COUNT,
            {"query": query}, limit, offset,
        )

    def directives_using_constant(self, name: str, value: Optional[str], limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_USING_CONSTANT_PAGE, Q.DIRECTIVES_USING_CONSTANT_COUNT,
            {"name": name, "value": value}, limit, offset,
        )

    def directives_setting_constant(self, name: str, value: Optional[str], limit: int, offset: int):
        return self.fetch_page(
            Q.DIRECTIVES_SETTING_CONSTANT_PAGE, Q.DIRECTIVES_SETTING_CONSTANT_COUNT,
            {"name": name, "value": value}, limit, offset,
        )


class SymbolQueryRepository:
    """PostgreSQL reads for a single configuration — source mapping only."""

    def __init__(self, db: Session, configuration_id: int):
        self.db = db
        self.configuration_id = configuration_id

    def node_metadata(self, node_id: int) -> List[Dict[str, Any]]:
        """
        The (macro_name, file_path, line_number) chain for a directive.

        Replaces the old GET /get_metadata/{node_id}. Two adaptations from the old SQL:
          - macro_calls now references macro_definitions by id, so the macro name needs
            a JOIN (the old schema stored the name directly on macro_call).
          - symbol_table.node_id is VARCHAR while the graph's node_id is INTEGER, so the
            parameter is cast to str here.

        Ordered so the innermost macro frame comes first and the defining file last.
        """
        sql = text(
            """
            SELECT macro_name, file_path, line_number
            FROM (
                SELECT mc.id AS ord,
                       md.name AS macro_name,
                       st.file_path,
                       st.line_number
                  FROM macro_calls mc
                  JOIN macro_definitions md ON mc.macro_definition_id = md.id
                  JOIN symbol_table st      ON mc.symbol_id = st.id
                 WHERE mc.node_id = :node_id
                   AND mc.configuration_id = :cid
                UNION
                SELECT -1 AS ord, '/' AS macro_name, file_path, line_number
                  FROM symbol_table
                 WHERE node_id = :node_id
                   AND configuration_id = :cid
                ORDER BY ord DESC
            ) frames
            """
        )
        rows = self.db.execute(
            sql, {"node_id": str(node_id), "cid": self.configuration_id}
        ).mappings().all()
        return [dict(r) for r in rows]

    def node_ids_at_source(self, file_path: str, line_number: int) -> List[int]:
        """
        Which directives did this file:line produce?

        Replaces the old POST /nodes/get_node_ids. The `node_id IS NOT NULL` filter is
        essential: symbol_table also holds rows for macro definition and use sites,
        which carry no node_id.
        """
        sql = text(
            """
            SELECT mc.node_id AS node_id
              FROM symbol_table st
              JOIN macro_calls mc ON st.id = mc.symbol_id
             WHERE st.file_path = :fp
               AND st.line_number = :ln
               AND st.configuration_id = :cid
            UNION
            SELECT node_id
              FROM symbol_table
             WHERE file_path = :fp
               AND line_number = :ln
               AND configuration_id = :cid
               AND node_id IS NOT NULL
            """
        )
        rows = self.db.execute(
            sql, {"fp": file_path, "ln": line_number, "cid": self.configuration_id}
        ).all()
        # stored as VARCHAR; the graph wants INTEGER
        return sorted({int(r[0]) for r in rows if r[0] is not None})

    def counts(self) -> Dict[str, int]:
        """Row counts, for diagnostics."""
        return {
            "symbols": self.db.query(Symbol)
            .filter(Symbol.configuration_id == self.configuration_id).count(),
            "macro_definitions": self.db.query(MacroDefinition)
            .filter(MacroDefinition.configuration_id == self.configuration_id).count(),
            "macro_calls": self.db.query(MacroCall)
            .filter(MacroCall.configuration_id == self.configuration_id).count(),
        }
