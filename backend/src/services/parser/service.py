"""
Business logic for configuration parsing.

Parses a configuration's Apache dump and populates Neo4j (the directive graph) and
PostgreSQL (the symbol / macro tables). Exposes no query API — reading the parsed
result belongs to AnalysisService.

See PARSER.md for how the parser works and the defects carried over from the old
implementation.
"""

import logging
import traceback
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import get_neo4j_session, get_postgres_session
from services.configmanager.repository import ConfigurationRepository
from services.configmanager.storage import ConfigFileStorage

from .core.dump_parser import parse_compiled_config
from .models import Symbol
from .repository import GraphRepository, SymbolRepository
from .schemas import ParseRequest, ParseResponse, ParseStatusResponse

logger = logging.getLogger(__name__)

# Status values used on configurations.parsing_status
NOT_PARSED = "not_parsed"
PARSING = "parsing"
PARSED = "parsed"
ERROR = "error"


class ParserService:
    """Orchestrates parsing for a configuration."""

    def __init__(self, db: Session):
        self.db = db
        self.config_repo = ConfigurationRepository(db)
        self.storage = ConfigFileStorage(settings.STORAGE_ROOT)

    # ==================== Public API ====================

    def parse_configuration(
        self,
        configuration_id: int,
        background_tasks=None,
        options: Optional[ParseRequest] = None,
    ) -> ParseResponse:
        """
        Schedule a parse and return immediately (202).

        Args:
            configuration_id: configuration to parse
            background_tasks: FastAPI BackgroundTasks; if omitted the parse runs inline
                (useful for scripts and tests)
            options: ParseRequest; force_reparse overrides the already-parsing guard

        Raises:
            ValueError: configuration not found
            FileNotFoundError: no dump on disk (upload never completed)
            RuntimeError: already parsing and force_reparse not set
        """
        options = options or ParseRequest()

        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")

        # Fail fast if the dump or extracted tree is missing, rather than in the
        # background where the caller cannot see it.
        self.storage.get_dump_path(configuration_id)
        self.storage.get_extracted_path(configuration_id)

        if config.parsing_status == PARSING and not options.force_reparse:
            raise RuntimeError(
                f"Configuration {configuration_id} is already being parsed. "
                f"Use force_reparse to override."
            )

        # Commit 'parsing' BEFORE returning, otherwise the client's first poll races
        # this write and reports the previous status.
        config.parsing_status = PARSING
        config.parsing_error = None
        self.config_repo.update(config)

        if background_tasks is not None:
            background_tasks.add_task(self._run_parse, configuration_id)
        else:
            self._run_parse(configuration_id)

        return ParseResponse(
            configuration_id=configuration_id,
            parsing_status=PARSING,
            parsing_error=None,
            parsed_at=config.parsed_at,
        )

    def get_parsing_status(self, configuration_id: int) -> ParseStatusResponse:
        """Current status, with row counts once parsing has completed."""
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")

        response = ParseStatusResponse(
            configuration_id=configuration_id,
            parsing_status=config.parsing_status,
            parsing_error=config.parsing_error,
            parsed_at=config.parsed_at,
        )

        if config.parsing_status == PARSED:
            symbol_repo = SymbolRepository(self.db, configuration_id)
            counts = symbol_repo.counts()
            response.total_symbols = counts["total_symbols"]
            response.total_macros = counts["total_macros"]
            response.total_macro_calls = counts["total_macro_calls"]
            response.total_directives = self._count_directives(configuration_id)

        return response

    def reparse_configuration(
        self, configuration_id: int, background_tasks=None
    ) -> ParseResponse:
        """Clear existing parsed data, then parse again."""
        self.clear_parsed_data(configuration_id)
        return self.parse_configuration(
            configuration_id,
            background_tasks=background_tasks,
            options=ParseRequest(force_reparse=True),
        )

    def clear_parsed_data(self, configuration_id: int) -> bool:
        """
        Delete this configuration's parsed data from both databases and reset its status.

        Scoped by configuration_id — unlike the old analyzer, which dropped the whole
        PostgreSQL schema and every Neo4j node before each run.
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")

        clear_configuration_data(self.db, configuration_id)

        config.parsing_status = NOT_PARSED
        config.parsing_error = None
        config.parsed_at = None
        self.config_repo.update(config)

        return True

    # ==================== Background worker ====================

    def _run_parse(self, configuration_id: int) -> None:
        """
        Parse and populate. Runs in a FastAPI BackgroundTask.

        Deliberately a plain `def`, not `async def`, so Starlette runs it in a threadpool
        instead of blocking the event loop for the duration of the parse.

        Opens its own database sessions: BackgroundTasks run *after* the response, by
        which point the request-scoped session has been committed and closed.

        Never raises — failures are recorded in parsing_error.
        """
        db = get_postgres_session()
        neo4j_session = None
        try:
            config_repo = ConfigurationRepository(db)
            storage = ConfigFileStorage(settings.STORAGE_ROOT)

            config = config_repo.get_by_id(configuration_id)
            if not config:
                logger.error("Configuration %d vanished before parsing", configuration_id)
                return

            dump_path = storage.get_dump_path(configuration_id)
            config_root = storage.get_extracted_path(configuration_id)

            logger.info("Parsing configuration %d from %s", configuration_id, dump_path)

            neo4j_session = get_neo4j_session()
            graph_repo = GraphRepository(neo4j_session, configuration_id)
            symbol_repo = SymbolRepository(db, configuration_id)

            # A re-run must not stack on top of previous data.
            graph_repo.clear_configuration()
            symbol_repo.clear_configuration()
            db.commit()

            directives = parse_compiled_config(dump_path, config_root)
            logger.info(
                "Parsed %d directives for configuration %d", len(directives), configuration_id
            )

            for directive in directives:
                graph_repo.add_directive(directive)
                symbol_repo.add_directive(directive)

            graph_repo.create_indexes()  # flushes remaining batches first
            db.commit()

            config = config_repo.get_by_id(configuration_id)
            config.parsing_status = PARSED
            config.parsing_error = None
            config.parsed_at = datetime.utcnow()
            config_repo.update(config)

            logger.info("Finished parsing configuration %d", configuration_id)

        except Exception as e:
            logger.error(
                "Parsing failed for configuration %d: %s", configuration_id, e, exc_info=True
            )
            db.rollback()
            try:
                # Do not leave a half-written graph behind.
                if neo4j_session is not None:
                    GraphRepository(neo4j_session, configuration_id).clear_configuration()
                SymbolRepository(db, configuration_id).clear_configuration()
                db.commit()
            except Exception:
                logger.error("Cleanup after failed parse also failed", exc_info=True)
                db.rollback()

            try:
                config_repo = ConfigurationRepository(db)
                config = config_repo.get_by_id(configuration_id)
                if config:
                    config.parsing_status = ERROR
                    config.parsing_error = _format_error(e)
                    config.parsed_at = None
                    config_repo.update(config)
            except Exception:
                logger.error("Could not record parsing error", exc_info=True)

        finally:
            if neo4j_session is not None:
                neo4j_session.close()
            db.close()

    # ==================== Helpers ====================

    def _count_directives(self, configuration_id: int) -> int:
        """
        Number of directives parsed.

        Every directive writes exactly one symbol row carrying its node_id; the other
        rows in the chain (macro definition and use sites) have node_id NULL.
        """
        return (
            self.db.query(func.count(func.distinct(Symbol.node_id)))
            .filter(
                Symbol.configuration_id == configuration_id,
                Symbol.node_id.isnot(None),
            )
            .scalar()
            or 0
        )


def clear_configuration_data(db: Session, configuration_id: int) -> None:
    """
    Delete a configuration's parsed data from both databases.

    Module-level so ConfigManagerService can call it when deleting a configuration
    without importing ParserService. PostgreSQL cascades handle the symbol tables when
    the configuration row itself is deleted, but nothing else clears Neo4j.
    """
    neo4j_session = get_neo4j_session()
    try:
        GraphRepository(neo4j_session, configuration_id).clear_configuration()
    finally:
        neo4j_session.close()

    SymbolRepository(db, configuration_id).clear_configuration()
    db.commit()


def _format_error(e: Exception) -> str:
    """Compact error summary for parsing_error (a TEXT column, but keep it readable)."""
    tb = traceback.format_exc(limit=5)
    return f"{type(e).__name__}: {e}\n{tb}"[:4000]
