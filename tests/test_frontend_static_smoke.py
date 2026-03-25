#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from werkzeug.serving import make_server

import tg_imagebed.config as config
import tg_imagebed.database as database
import tg_imagebed.database.connection as db_connection
import tg_imagebed.database.tg_auth as tg_auth_db
from tg_imagebed.database import init_database, init_system_settings


class FrontendStaticSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        static_index = Path(config.STATIC_FOLDER) / "index.html"
        if not static_index.exists():
            raise unittest.SkipTest("frontend static build not found, run `cd frontend && npm run generate` first")

        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.temp_dir.name) / "frontend-smoke.db")
        cls.patches = [
            patch.object(config, "DATABASE_PATH", cls.db_path),
            patch.object(db_connection, "DATABASE_PATH", cls.db_path),
            patch.object(database, "DATABASE_PATH", cls.db_path, create=True),
            patch.object(tg_auth_db, "DATABASE_PATH", cls.db_path, create=True),
        ]
        for patcher in cls.patches:
            patcher.start()

        init_database()
        init_system_settings()

        import main as app_main

        cls.main_db_patch = patch.object(app_main, "DATABASE_PATH", cls.db_path)
        cls.main_db_patch.start()

        cls.app = app_main.create_app()
        cls.server = make_server("127.0.0.1", 0, cls.app)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.session = requests.Session()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "session"):
            cls.session.close()
        if hasattr(cls, "server"):
            cls.server.shutdown()
        if hasattr(cls, "server_thread"):
            cls.server_thread.join(timeout=5)
        if hasattr(cls, "main_db_patch"):
            cls.main_db_patch.stop()
        if hasattr(cls, "patches"):
            for patcher in reversed(cls.patches):
                patcher.stop()
        if hasattr(cls, "temp_dir"):
            cls.temp_dir.cleanup()

    def test_html_routes_and_assets_are_served(self):
        html_routes = [
            "/",
            "/guest",
            "/docs",
            "/album",
            "/me",
            "/setup",
            "/admin",
            "/admin/dashboard",
            "/admin/images",
            "/admin/settings",
            "/admin/storage",
            "/admin/tokens",
            "/admin/galleries",
            "/admin/announcements",
            "/admin/seo",
            "/gallery-site",
            "/gallery-site/admin",
            "/gallery-site/admin/login",
            "/gallery-site/admin/settings",
            "/gallery-site/galleries",
            "/g/demo-token",
            "/galleries/demo-token",
            "/galleries/demo-token/demo-item",
            "/gallery-site/admin/galleries/demo",
            "/gallery-site/galleries/demo",
        ]
        asset_candidates = set()

        for route in html_routes:
            with self.subTest(route=route):
                response = self.session.get(self.base_url + route, timeout=5)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers.get("Content-Type", ""))
                self.assertIn('<div id="__nuxt"></div>', response.text)
                self.assertIn("/_nuxt/", response.text)
                self.assertIn("__NUXT__", response.text)
                self.assertIn('href="/favicon.ico"', response.text)
                asset_candidates.update(re.findall(r'(?:href|src)="(/_nuxt/[^"]+)"', response.text))

        self.assertGreaterEqual(len(asset_candidates), 2)

        for route in sorted(asset_candidates):
            with self.subTest(asset=route):
                response = self.session.get(self.base_url + route, timeout=10)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content)

        for route in ["/favicon.ico", "/robots.txt", "/manifest.json"]:
            with self.subTest(static=route):
                response = self.session.get(self.base_url + route, timeout=5)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content)

    def test_frontend_bootstrap_apis_are_available(self):
        api_routes = {
            "/api/health": {"status", "timestamp", "version"},
            "/api/setup/status": {"need_setup"},
            "/api/public/settings": {"success", "data"},
            "/api/announcement": {"success", "data"},
            "/api/stats": {"success", "data"},
            "/api/recent": {"success", "files", "page", "limit", "has_more"},
            "/api/info": {"domain", "storage_type", "total_files"},
            "/api/bot/status": {"enabled", "state", "token_config"},
        }

        for route, expected_keys in api_routes.items():
            with self.subTest(api=route):
                response = self.session.get(self.base_url + route, timeout=5)
                self.assertEqual(response.status_code, 200)
                self.assertIn("application/json", response.headers.get("Content-Type", ""))
                payload = response.json()
                self.assertTrue(expected_keys.issubset(payload.keys()))


if __name__ == "__main__":
    unittest.main()
