"""
Log analysis and classification service.

Two-step pipeline:
  1. Local fine-tuned ModernBERT model -> false_positive / true_positive per log.
  2. True-positive entries only -> external attack-type model service (model_na).
"""
import asyncio
import tempfile
import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
import pandas as pd
from fastapi import UploadFile

from .storage import LogSessionStorage
from .fp_classifier import FPClassifier
from .attack_client import get_attack_types_batch
from .schemas import (
    LogClassificationResponse,
    LogCategoryResponse,
    FilteredLogsResponse,
    CategoryDetailsResponse,
    LogDetailResponse,
    LogEntryResponse,
    LogFilter,
    LogAnalysisSessionResponse,
)
from shared.config import settings

logger = logging.getLogger(__name__)


def _build_categories(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate true-positive entries by attack_type.labels. FP entries have no category."""
    categories: Dict[str, Dict[str, Any]] = {}
    for i, e in enumerate(entries):
        attack_type = e.get("attack_type")
        if not attack_type:
            continue
        labels = attack_type.get("labels") or []
        label = ", ".join(labels) if labels else "unknown"
        if label not in categories:
            categories[label] = {"category": label, "count": 0, "log_indices": []}
        categories[label]["count"] += 1
        categories[label]["log_indices"].append(i)
    return categories


def _categories_with_percentage(
    categories: Dict[str, Dict[str, Any]], total: int
) -> List[LogCategoryResponse]:
    items = sorted(categories.values(), key=lambda c: c["count"], reverse=True)
    return [
        LogCategoryResponse(
            category=c["category"],
            count=c["count"],
            percentage=(c["count"] / total * 100) if total > 0 else 0,
            log_indices=c["log_indices"],
        )
        for c in items
    ]


class LogAnalysisService:
    """Business logic for two-step log analysis and classification"""

    def __init__(
        self,
        classifier: FPClassifier,
        http_client: httpx.AsyncClient,
        model_service_url: str = None,
        batch_size: int = None,
        storage_root: str = None,
    ):
        self.storage = LogSessionStorage(storage_root or settings.STORAGE_ROOT)
        self.classifier = classifier
        self.http_client = http_client
        self.model_service_url = model_service_url or settings.LOG_MODEL_SERVICE_URL
        self.batch_size = batch_size or settings.LOG_CLASSIFIER_BATCH_SIZE

    async def classify_logs(
        self,
        user_id: int,
        file: UploadFile,
        configuration_id: Optional[int] = None
    ) -> LogClassificationResponse:
        """
        Process and classify a log file end to end.

        1. Validate file
        2. Create session
        3. Step 1: local FP/TP classification (all entries)
        4. Step 2: attack-type classification (true positives only)
        5. Store results in JSON file
        6. Return summary
        """
        if self.classifier is None:
            raise RuntimeError(
                "FP/TP model is not loaded. Populate backend/src/storage/models/fp_model/ "
                "and restart the backend."
            )

        max_size = 500 * 1024 * 1024  # 500MB
        if file.size and file.size > max_size:
            raise ValueError("File too large (max 500MB)")

        # Real ModSecurity audit logs show up under several names depending on rotation and
        # anonymization: audit.log, modsec_audit.log, *_audit.anon.log, audit.log.1, ...
        # so this checks for "audit" + ".log" anywhere in the name rather than the exact
        # substring "audit.log", which rejected the anonymized OWASP CRS dataset entirely.
        valid_extensions = file.filename.endswith('.san') or file.filename.endswith('.txt')
        audit_log_pattern = 'audit' in file.filename and '.log' in file.filename

        if not (valid_extensions or audit_log_pattern):
            raise ValueError("File must be .san, .txt, or an audit *.log file")

        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest() if file_content else None

        session_data = self.storage.create_session(
            user_id=user_id,
            filename=file.filename,
            configuration_id=configuration_id,
            file_size=len(file_content) if file_content else None,
            file_hash=file_hash
        )
        session_id = session_data["session_id"]

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
                tmp.write(file_content)
                tmp_path = Path(tmp.name)

            # Step 1: local FP/TP model, off the event loop
            logger.info(f"Classifying (FP/TP) log file for session {session_id}")
            loop = asyncio.get_event_loop()
            raw_results: List[Dict[str, Any]] = await loop.run_in_executor(
                None, self.classifier.predict, tmp_path, self.batch_size
            )

            entries: List[Dict[str, Any]] = []
            fp_count = 0
            tp_count = 0

            if raw_results:
                tp_indices = [
                    i for i, r in enumerate(raw_results) if r["prediction"] == "true_positive"
                ]
                tp_texts = [raw_results[i]["_text"] for i in tp_indices]

                # Step 2: attack-type model, true positives only
                logger.info(f"Sending {len(tp_texts)} true-positive logs to attack-type service")
                attack_results = await get_attack_types_batch(
                    tp_texts, self.http_client, self.model_service_url
                )
                for idx, attack_type in zip(tp_indices, attack_results):
                    raw_results[idx]["_attack_type"] = attack_type.model_dump()

                for r in raw_results:
                    entry = LogEntryResponse(
                        parsed=r["_parsed"],
                        features=r["_features"],
                        prediction=r["prediction"],
                        confidence=r["confidence"],
                        fp_probability=r["fp_probability"],
                        tp_probability=r["tp_probability"],
                        attack_type=r.get("_attack_type"),
                    )
                    entries.append(entry.model_dump())
                    if entry.prediction == "false_positive":
                        fp_count += 1
                    else:
                        tp_count += 1

            categories = _build_categories(entries)
            categories_list = _categories_with_percentage(categories, len(entries))

            self.storage.add_entries(
                session_id,
                entries,
                [c.model_dump() for c in categories_list],
                fp_count,
                tp_count,
            )
            self.storage.update_session_status(session_id, status="completed")

            return LogClassificationResponse(
                session_id=session_id,
                filename=file.filename,
                total_logs=len(entries),
                false_positives=fp_count,
                true_positives=tp_count,
                categories=categories_list,
            )

        except Exception as e:
            logger.error(f"Error processing logs: {e}", exc_info=True)
            self.storage.update_session_status(session_id, status="failed", error_message=str(e))
            raise RuntimeError(f"Failed to process logs: {str(e)}")

        finally:
            if tmp_path and tmp_path.exists():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def get_log_by_transaction(
        self,
        session_id: str,
        transaction_id: str
    ) -> Optional[LogDetailResponse]:
        """Get detailed log entry by transaction ID"""
        entry = self.storage.get_entry_by_transaction_id(session_id, transaction_id)

        if not entry:
            return None

        return LogDetailResponse(
            session_id=session_id,
            transaction_id=transaction_id,
            log=LogEntryResponse.model_validate(entry),
        )

    def get_filtered_logs(
        self,
        session_id: str,
        filters: LogFilter
    ) -> FilteredLogsResponse:
        """Apply filters (prediction / category / time range / feature columns) to a session"""
        session_data = self.storage.get_session(session_id)

        if not session_data:
            raise ValueError("Session not found")

        entries = [LogEntryResponse.model_validate(e) for e in session_data.get("entries", [])]
        original_total = len(entries)

        out = entries

        if filters.prediction:
            out = [e for e in out if e.prediction == filters.prediction]

        if filters.category:
            out = [
                e for e in out
                if e.attack_type and any(filters.category in lbl for lbl in e.attack_type.labels)
            ]

        if filters.start_time or filters.end_time:
            def _ts(e: LogEntryResponse):
                return pd.to_datetime(
                    e.features.timestamp,
                    format='%d/%b/%Y:%H:%M:%S.%f %z',
                    errors='coerce',
                    utc=True,
                )

            if filters.start_time:
                start = pd.Timestamp(filters.start_time, tz='UTC') if filters.start_time.tzinfo is None else pd.Timestamp(filters.start_time)
                out = [e for e in out if (t := _ts(e)) is not None and not pd.isna(t) and t >= start]
            if filters.end_time:
                end = pd.Timestamp(filters.end_time, tz='UTC') if filters.end_time.tzinfo is None else pd.Timestamp(filters.end_time)
                out = [e for e in out if (t := _ts(e)) is not None and not pd.isna(t) and t <= end]

        for cf in filters.columns:
            column_name = cf.get('name')
            filter_value = cf.get('value')
            filter_type = cf.get('type', 'exact')

            filtered = []
            for e in out:
                val = getattr(e.features, column_name, None)
                if val is None:
                    continue
                val_str = str(val)
                if filter_type == 'contains' and str(filter_value) in val_str:
                    filtered.append(e)
                elif filter_type == 'exact' and val_str == str(filter_value):
                    filtered.append(e)
                elif filter_type == 'greater_than':
                    try:
                        if float(val_str) > float(filter_value):
                            filtered.append(e)
                    except ValueError:
                        pass
                elif filter_type == 'less_than':
                    try:
                        if float(val_str) < float(filter_value):
                            filtered.append(e)
                    except ValueError:
                        pass
            out = filtered

        filtered_dicts = [e.model_dump() for e in out]
        categories = _build_categories(filtered_dicts)
        categories_list = _categories_with_percentage(categories, len(out))

        return FilteredLogsResponse(
            session_id=session_id,
            total_logs=original_total,
            filtered_logs=len(out),
            categories=categories_list,
            results=out,
        )

    def get_category_details(
        self,
        session_id: str,
        category: str,
        log_indices: List[int],
        limit: int = 100,
        offset: int = 0
    ) -> CategoryDetailsResponse:
        """Get detailed logs for a specific category"""
        session_data = self.storage.get_session(session_id)
        if not session_data:
            raise ValueError("Session not found")

        entries = session_data.get("entries", [])
        page_indices = log_indices[offset:offset + limit]

        category_logs = [
            LogEntryResponse.model_validate(entries[idx])
            for idx in page_indices
            if 0 <= idx < len(entries)
        ]

        return CategoryDetailsResponse(
            session_id=session_id,
            category=category,
            total_count=len(log_indices),
            logs=category_logs,
        )

    def get_user_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[LogAnalysisSessionResponse]:
        """Get all analysis sessions for a user"""
        sessions = self.storage.get_user_sessions(user_id, limit, offset)

        return [
            LogAnalysisSessionResponse(
                id=0,
                session_id=s["session_id"],
                user_id=s["user_id"],
                configuration_id=s.get("configuration_id"),
                filename=s["filename"],
                file_size=s.get("file_size"),
                status=s["status"],
                total_logs=s.get("total_logs"),
                false_positives=s.get("false_positives"),
                true_positives=s.get("true_positives"),
                error_message=s.get("error_message"),
                created_at=s["created_at"],
                completed_at=s.get("completed_at"),
                categories=s.get("categories"),
            )
            for s in sessions
        ]

    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a session (with authorization check)"""
        return self.storage.delete_session(session_id, user_id)
