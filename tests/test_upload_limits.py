#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import tg_imagebed.config as config
import tg_imagebed.database.connection as db_connection
import tg_imagebed.database as database
import tg_imagebed.database.tg_auth as tg_auth_db
from tg_imagebed.database import (
    create_auth_token,
    create_auth_token_with_ip_limit,
    get_connection,
    get_default_upload_token,
    get_user_token_count,
    get_active_user_tokens,
    init_database,
    init_system_settings,
    reserve_token_upload,
    release_upload_reservation,
    update_system_setting,
    upsert_tg_user,
    create_tg_session,
    count_tokens_by_ip,
)


class UploadLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.patches = [
            patch.object(config, "DATABASE_PATH", self.db_path),
            patch.object(db_connection, "DATABASE_PATH", self.db_path),
            patch.object(database, "DATABASE_PATH", self.db_path, create=True),
            patch.object(tg_auth_db, "DATABASE_PATH", self.db_path, create=True),
        ]
        for patcher in self.patches:
            patcher.start()
        init_database()
        init_system_settings()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def test_reserve_token_upload_blocks_second_reservation(self):
        token = create_auth_token(
            ip_address="127.0.0.1",
            user_agent="test-agent",
            description="single-use",
            upload_limit=1,
            expires_days=7,
        )
        self.assertIsNotNone(token)

        first = reserve_token_upload(token, daily_limit=5)
        second = reserve_token_upload(token, daily_limit=5)

        self.assertTrue(first["ok"])
        self.assertEqual(first["remaining_uploads"], 0)
        self.assertFalse(second["ok"])

        release_upload_reservation(first["reservation_key"])
        third = reserve_token_upload(token, daily_limit=5)
        self.assertTrue(third["ok"])

    def test_guest_token_ip_limit_is_atomic(self):
        results = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(8)

        def worker():
            try:
                barrier.wait()
                result = create_auth_token_with_ip_limit(
                    ip_address="10.0.0.1",
                    user_agent="parallel-test",
                    description="parallel",
                    upload_limit=3,
                    expires_days=7,
                    max_tokens_for_ip=1,
                )
                with lock:
                    results.append(result)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])

        successes = [token for token, reason in results if token]
        reasons = [reason for token, reason in results if not token]

        self.assertEqual(len(successes), 1)
        self.assertTrue(all(reason == "ip_limit" for reason in reasons))

    def test_expired_tokens_are_not_counted_as_active(self):
        now = datetime.now()
        expired_at = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        active_at = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO auth_tokens (token, ip_address, tg_user_id, expires_at, is_active, is_default_upload, description)
                VALUES (?, ?, ?, ?, 1, 1, ?)
                """,
                ("expired-token", "8.8.8.8", 42, expired_at, "expired"),
            )
            cursor.execute(
                """
                INSERT INTO auth_tokens (token, ip_address, tg_user_id, expires_at, is_active, is_default_upload, description)
                VALUES (?, ?, ?, ?, 1, 0, ?)
                """,
                ("active-token", "8.8.8.8", 42, active_at, "active"),
            )

        self.assertEqual(count_tokens_by_ip("8.8.8.8"), 1)
        self.assertEqual(get_user_token_count(42), 1)

        active_tokens = get_active_user_tokens(42)
        self.assertEqual([item["token"] for item in active_tokens], ["active-token"])
        self.assertEqual(get_default_upload_token(42), "active-token")

    def test_tg_sync_tokens_handles_unlimited_token(self):
        update_system_setting("tg_auth_enabled", "1")
        upsert_tg_user(1001, username="tester", first_name="Test", last_name="User")
        session_token = create_tg_session(1001, ip_address="127.0.0.1", user_agent="unittest")
        self.assertIsNotNone(session_token)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO auth_tokens (token, tg_user_id, expires_at, upload_limit, upload_count, is_active, description)
                VALUES (?, ?, ?, NULL, 0, 1, ?)
                """,
                ("sync-unlimited-token", 1001, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"), "unlimited"),
            )

        import main as app_main

        with patch.object(app_main, "DATABASE_PATH", self.db_path):
            app = app_main.create_app()
        app.testing = True

        client = app.test_client()
        client.set_cookie("tg_session", session_token)
        response = client.get("/api/auth/tg/sync-tokens")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["data"]["tokens"]), 1)
        token_info = payload["data"]["tokens"][0]
        self.assertEqual(token_info["token"], "sync-unlimited-token")
        self.assertEqual(token_info["remaining_uploads"], -1)
        self.assertTrue(token_info["can_upload"])


if __name__ == "__main__":
    unittest.main()
