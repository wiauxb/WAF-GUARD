"""
Data access layer for the parser.

Two repositories, both scoped by configuration_id:

- GraphRepository  -> Neo4j, the directive graph (was old/.../neo4j_interface.py)
- SymbolRepository -> PostgreSQL, the source-mapping tables (was old/.../sql_interface.py)

Port notes:
- The old Neo4jDB built its own driver; this uses the shared connection from
  shared.database so the pool is managed in one place.
- The old PostgresDB used raw psycopg2 PREPARE statements. psycopg2 is not a
  dependency of this project (SQLAlchemy ships psycopg v3), so the same logic is
  expressed against the existing SQLAlchemy models in .models.
- Batching behaviour, batch sizes and flush order are preserved exactly, so write
  behaviour matches the old analyzer. See PARSER.md defect #4 for a consequence of
  that flush order which is deliberately NOT fixed here.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from shared.config import settings
from .core.context import Context, FileContext, MacroContext
from .core.directives import (
    DefineStr,
    Directive,
    SecRule,
    SecRuleRemoveById,
    SecRuleRemoveByTag,
)
from .core.query_factory import QueryFactory
from .models import MacroCall, MacroDefinition, Symbol

logger = logging.getLogger(__name__)

BATCH_SIZE_GENERIC = 5000
BATCH_SIZE_SMALL = 1000


class GraphRepository:
    """Neo4j writes for a single configuration."""

    def __init__(self, session, configuration_id: int):
        """
        Args:
            session: an open neo4j Session (from shared.database.get_neo4j_session)
            configuration_id: scopes every node this repository writes
        """
        self.session = session
        self.configuration_id = configuration_id
        self.generic_batch = []
        self.definestr_batch = []
        self.removebyid_batch = []
        self.removebytag_batch = []
        self.secrule_batch = []

    def query(self, query, **kwargs):
        result = self.session.run(query, **kwargs)
        return list(result)

    def add_directive(self, directive: Directive):
        """Collect a directive; flushes automatically when a batch fills."""
        if isinstance(directive, DefineStr):
            self.definestr_batch.append(directive)
        elif isinstance(directive, SecRule):
            self.secrule_batch.append(directive)
        elif isinstance(directive, SecRuleRemoveById):
            self.removebyid_batch.append(directive)
        elif isinstance(directive, SecRuleRemoveByTag):
            self.removebytag_batch.append(directive)
        else:
            self.generic_batch.append(directive)

        # Flush order preserved from the old analyzer, including the definestr-first
        # pattern on every branch.
        if len(self.definestr_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
        if len(self.removebyid_batch) >= BATCH_SIZE_SMALL:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.removebyid_batch, "removebyid")
        if len(self.removebytag_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.removebytag_batch, "removebytag")
        if len(self.secrule_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.secrule_batch, "secrule")
        if len(self.generic_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.generic_batch, "generic")

    def flush_all(self):
        for batch, kind in (
            (self.definestr_batch, "definestr"),
            (self.removebyid_batch, "removebyid"),
            (self.removebytag_batch, "removebytag"),
            (self.secrule_batch, "secrule"),
            (self.generic_batch, "generic"),
        ):
            if batch:
                logger.info("Flushing %d %s directives", len(batch), kind)
                self.flush_batch(batch, kind)

    def flush_batch(self, batch, kind: str):
        """Execute one batched insert via UNWIND."""
        if not batch:
            return

        batch_prop = []
        for d in batch:
            props = d.properties()
            props["configuration_id"] = self.configuration_id
            node_props = d.node_properties()
            node_props["configuration_id"] = self.configuration_id
            props["node_props"] = node_props
            batch_prop.append(props)
        batch.clear()

        query = QueryFactory.base_module()
        if kind == "definestr":
            query += QueryFactory.definestr_module()
        elif kind == "secrule":
            query += QueryFactory.secrule_module()
        elif kind == "removebyid":
            query += QueryFactory.removebyid_module()
        elif kind == "removebytag":
            query += QueryFactory.removebytag_module()
        else:
            query += QueryFactory.generic_module()

        self.query(query, batch=batch_prop, cid=self.configuration_id)

    def create_indexes(self):
        self.flush_all()
        self.query(QueryFactory.create_indexes())
        for stmt in QueryFactory.create_scope_indexes():
            self.query(stmt)

    def clear_configuration(self) -> int:
        """
        Delete every node belonging to this configuration, in batches.

        Replaces the old reset_neo4j() + "DROP SCHEMA public CASCADE", which wiped
        the entire database and made multi-configuration storage impossible.

        Returns:
            total nodes deleted
        """
        total = 0
        while True:
            result = self.query(
                """
                MATCH (n {configuration_id: $cid})
                WITH n LIMIT $batch
                DETACH DELETE n
                RETURN count(n) AS deleted
                """,
                cid=self.configuration_id,
                batch=settings.DELETE_BATCH_SIZE,
            )
            deleted = result[0]["deleted"] if result else 0
            total += deleted
            if deleted == 0:
                break
        if total:
            logger.info(
                "Cleared %d Neo4j nodes for configuration %d", total, self.configuration_id
            )
        return total


class SymbolRepository:
    """PostgreSQL source-mapping writes for a single configuration."""

    def __init__(self, db: Session, configuration_id: int):
        self.db = db
        self.configuration_id = configuration_id
        # macro name -> MacroDefinition.id, for this configuration only.
        # The old code deduped on macrodef.name alone, which was a GLOBAL primary key.
        # MacroDefinition is unique on (configuration_id, name), so the cache and the
        # lookup below must both be per-configuration or config B reuses config A's rows.
        self._macro_def_cache: dict[str, int] = {}

    def add_symbol(self, ctx: Context, node_id: Optional[int] = None) -> int:
        """Insert one symbol_table row for a context frame, returning its id."""
        if isinstance(ctx, FileContext):
            file_path = ctx.file_path
            line_number = ctx.line_num
        elif isinstance(ctx, MacroContext):
            file_path = ctx.definition.file_path
            line_number = ctx.definition.line_num + ctx.line_num
        else:
            raise Exception(f"Invalid context type {type(ctx)}")

        symbol = Symbol(
            configuration_id=self.configuration_id,
            node_id=str(node_id) if node_id is not None else None,
            file_path=file_path,
            line_number=line_number,
        )
        self.db.add(symbol)
        self.db.flush()  # populate symbol.id without committing
        return symbol.id

    def _get_or_create_macro_def(self, name: str, ctx: MacroContext) -> int:
        """Resolve a macro definition id, creating it on first sight."""
        if name in self._macro_def_cache:
            return self._macro_def_cache[name]

        existing = (
            self.db.query(MacroDefinition)
            .filter(
                MacroDefinition.configuration_id == self.configuration_id,
                MacroDefinition.name == name,
            )
            .first()
        )
        if existing:
            self._macro_def_cache[name] = existing.id
            return existing.id

        symbol_id = self.add_symbol(ctx.definition)
        macro_def = MacroDefinition(
            configuration_id=self.configuration_id,
            name=name,
            symbol_id=symbol_id,
        )
        self.db.add(macro_def)
        self.db.flush()
        self._macro_def_cache[name] = macro_def.id
        return macro_def.id

    def add_directive(self, directive: Directive):
        """
        Walk a directive's context chain, recording the symbol, its macro definitions
        and each macro call site. Mirrors the old PostgresDB.add_sql().
        """
        ptr_ctx = directive.Context
        first_step = True
        while ptr_ctx is not None:
            if isinstance(ptr_ctx, FileContext):
                if first_step:
                    self.add_symbol(ptr_ctx, directive.node_id)
                    first_step = False
                ptr_ctx = None
            elif isinstance(ptr_ctx, MacroContext):
                macro_def_id = self._get_or_create_macro_def(ptr_ctx.macro_name, ptr_ctx)
                if first_step:
                    self.add_symbol(ptr_ctx, directive.node_id)
                    first_step = False
                use_symbol_id = self.add_symbol(ptr_ctx.use)
                self.db.add(
                    MacroCall(
                        configuration_id=self.configuration_id,
                        node_id=str(directive.node_id),
                        macro_definition_id=macro_def_id,
                        symbol_id=use_symbol_id,
                    )
                )
                ptr_ctx = ptr_ctx.use
            else:
                # A bare Context should never appear: the scanner's fix-up loop relinks
                # every frame to a MacroContext or FileContext. The old code had no such
                # branch and would have spun forever; fail loudly instead.
                raise Exception(
                    f"Unexpected context type {type(ptr_ctx).__name__} in chain "
                    f"for node {directive.node_id}"
                )

    def clear_configuration(self) -> int:
        """
        Delete this configuration's symbol rows. macro_definitions and macro_calls
        follow via ON DELETE CASCADE on symbol_id / configuration_id.
        """
        deleted = (
            self.db.query(Symbol)
            .filter(Symbol.configuration_id == self.configuration_id)
            .delete(synchronize_session=False)
        )
        self._macro_def_cache.clear()
        if deleted:
            logger.info(
                "Cleared %d symbol rows for configuration %d", deleted, self.configuration_id
            )
        return deleted

    def counts(self) -> dict:
        """Row counts for ParseStatusResponse."""
        return {
            "total_symbols": self.db.query(Symbol)
            .filter(Symbol.configuration_id == self.configuration_id)
            .count(),
            "total_macros": self.db.query(MacroDefinition)
            .filter(MacroDefinition.configuration_id == self.configuration_id)
            .count(),
            "total_macro_calls": self.db.query(MacroCall)
            .filter(MacroCall.configuration_id == self.configuration_id)
            .count(),
        }
