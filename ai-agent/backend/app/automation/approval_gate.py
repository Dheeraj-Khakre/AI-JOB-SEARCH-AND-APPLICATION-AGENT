"""Durable, time-limited, single-use application approval tokens."""

import hashlib
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.exceptions import InvalidApprovalTokenError


class ApplicationApprovalGate:
    """Persists approval records and enforces exact-once token consumption."""

    def __init__(self, database_path: str | None = None):
        target = database_path or str(
            Path(settings.DATA_DIR) / "db" / "application_approvals.sqlite3"
        )
        self.database_path = target
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS application_approvals (
                    approval_id TEXT PRIMARY KEY,
                    token_hash TEXT UNIQUE,
                    preview_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_at TEXT,
                    consumed_at TEXT,
                    consumed INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _preview_hash(preview: dict[str, Any]) -> str:
        import json

        serialized = json.dumps(
            preview,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_pending(self, approval_id: str, preview: dict[str, Any]) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.APPROVAL_TOKEN_EXPIRY_SECONDS
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO application_approvals (
                    approval_id, token_hash, preview_hash, expires_at, status
                ) VALUES (?, NULL, ?, ?, 'PENDING')
                """,
                (
                    approval_id,
                    self._preview_hash(preview),
                    expires_at.isoformat()
                )
            )

    def approve(self, approval_id: str, preview: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT preview_hash, expires_at, consumed, status
                FROM application_approvals
                WHERE approval_id = ?
                """,
                (approval_id,)
            ).fetchone()
            if not row:
                raise InvalidApprovalTokenError("Approval request was not found.")
            preview_hash, expires_at, consumed, status = row
            if status != "PENDING" or consumed:
                raise InvalidApprovalTokenError("Approval request is no longer pending.")
            if preview_hash != self._preview_hash(preview):
                raise InvalidApprovalTokenError(
                    "Application preview changed after review."
                )
            if datetime.fromisoformat(expires_at) <= now:
                connection.execute(
                    "UPDATE application_approvals SET status = 'EXPIRED' "
                    "WHERE approval_id = ?",
                    (approval_id,)
                )
                raise InvalidApprovalTokenError("Approval request expired.")

            token = f"hitl_{secrets.token_urlsafe(32)}"
            connection.execute(
                """
                UPDATE application_approvals
                SET token_hash = ?, approved_at = ?, status = 'APPROVED'
                WHERE approval_id = ?
                """,
                (self._token_hash(token), now.isoformat(), approval_id)
            )
            return token

    def consume(
        self,
        approval_id: str,
        token: str,
        preview: dict[str, Any]
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT token_hash, preview_hash, expires_at, consumed, status
                FROM application_approvals
                WHERE approval_id = ?
                """,
                (approval_id,)
            ).fetchone()
            if not row:
                raise InvalidApprovalTokenError("Approval request was not found.")
            token_hash, preview_hash, expires_at, consumed, status = row
            if status != "APPROVED" or consumed:
                raise InvalidApprovalTokenError(
                    "Approval token is unavailable or already consumed."
                )
            if preview_hash != self._preview_hash(preview):
                raise InvalidApprovalTokenError(
                    "Application preview changed after approval."
                )
            if not token or not token.startswith("hitl_"):
                raise InvalidApprovalTokenError("Invalid human approval token.")
            if self._token_hash(token) != token_hash:
                raise InvalidApprovalTokenError("Approval token is invalid.")
            if datetime.fromisoformat(expires_at) <= now:
                raise InvalidApprovalTokenError("Approval token expired.")

            cursor = connection.execute(
                """
                UPDATE application_approvals
                SET consumed = 1, consumed_at = ?, status = 'CONSUMED'
                WHERE approval_id = ? AND consumed = 0
                """,
                (now.isoformat(), approval_id)
            )
            if cursor.rowcount != 1:
                raise InvalidApprovalTokenError(
                    "Approval token was already consumed."
                )
