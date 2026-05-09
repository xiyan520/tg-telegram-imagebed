#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tg_imagebed.config as config
import tg_imagebed.database.connection as db_connection
import tg_imagebed.database as database
import tg_imagebed.database.tg_auth as tg_auth_db
from tg_imagebed.database import init_database, init_system_settings, update_system_setting
from tg_imagebed.storage.base import DownloadResult, PutResult, StorageBackend


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class FakeStorageBackend(StorageBackend):
    def __init__(self):
        self.name = "fake"
        self.files = {}
        self.counter = 0

    def _store(self, content: bytes, filename: str, content_type: str) -> PutResult:
        self.counter += 1
        storage_key = f"fake-{self.counter}"
        self.files[storage_key] = {
            "content": content,
            "filename": filename,
            "content_type": content_type,
        }
        return PutResult(
            file_id=storage_key,
            file_path=storage_key,
            file_size=len(content),
            storage_backend=self.name,
            storage_key=storage_key,
            storage_meta={"stored_by": "fake"},
        )

    def put_bytes(self, *, file_content: bytes, filename: str, content_type: str, file_size: int, caption: str, source: str, username: str):
        return self._store(file_content, filename, content_type)

    def put_file(self, *, file_path: str, filename: str, content_type: str, file_size: int, caption: str, source: str, username: str):
        with open(file_path, "rb") as handle:
            return self._store(handle.read(), filename, content_type)

    def download(self, *, file_info, range_header):
        key = file_info.get("storage_key") or file_info.get("file_id")
        stored = self.files[key]
        content = stored["content"]
        return DownloadResult(
            status_code=200,
            content_type=stored["content_type"],
            headers={"Content-Length": str(len(content))},
            body=[content],
        )


class FakeStorageRouter:
    def __init__(self, backend: FakeStorageBackend):
        self.backend = backend

    def resolve_upload_backend(self, *, scene, requested_backend=None, is_admin=False):
        return self.backend.name

    def get_backend(self, name):
        return self.backend

    def get_backend_for_record(self, file_info):
        return self.backend


class SmokeRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "smoke.db")
        self.backend = FakeStorageBackend()
        self.router = FakeStorageRouter(self.backend)

        self.patches = [
            patch.object(config, "DATABASE_PATH", self.db_path),
            patch.object(db_connection, "DATABASE_PATH", self.db_path),
            patch.object(database, "DATABASE_PATH", self.db_path, create=True),
            patch.object(tg_auth_db, "DATABASE_PATH", self.db_path, create=True),
            patch("tg_imagebed.services.file_service.get_storage_router", return_value=self.router),
            patch("tg_imagebed.api.images.get_storage_router", return_value=self.router),
            patch("tg_imagebed.services.file_service.add_to_cdn_monitor", lambda *args, **kwargs: None),
        ]
        for patcher in self.patches:
            patcher.start()

        init_database()
        init_system_settings()

        import main as app_main
        self.main_db_patch = patch.object(app_main, "DATABASE_PATH", self.db_path)
        self.main_db_patch.start()
        self.app = app_main.create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if hasattr(self, "main_db_patch"):
            self.main_db_patch.stop()
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def _upload_png(self, route: str, *, headers=None):
        return self.client.post(
            route,
            data={"file": (io.BytesIO(PNG_BYTES), "pixel.png")},
            content_type="multipart/form-data",
            headers=headers or {},
        )

    def _fetch_uploaded_image(self, response_json):
        image_url = response_json["data"]["url"]
        encrypted_id = image_url.rsplit("/", 1)[-1]
        return self.client.get(f"/image/{encrypted_id}")

    def test_guest_upload_and_image_fetch(self):
        response = self._upload_png("/api/upload")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"])

        image_response = self._fetch_uploaded_image(payload)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.data, PNG_BYTES)
        self.assertEqual(image_response.mimetype, "image/png")

    def test_token_upload_full_flow(self):
        token_response = self.client.post(
            "/api/auth/token/generate",
            json={"upload_limit": 3, "expires_days": 7, "description": "smoke"},
        )
        self.assertEqual(token_response.status_code, 200)
        token = token_response.get_json()["data"]["token"]

        upload_response = self._upload_png(
            "/api/auth/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(upload_response.status_code, 200)

        verify_response = self.client.post(
            "/api/auth/token/verify",
            json={"token": token},
        )
        self.assertEqual(verify_response.status_code, 200)
        verify_payload = verify_response.get_json()
        self.assertTrue(verify_payload["valid"])
        self.assertEqual(verify_payload["data"]["upload_count"], 1)
        self.assertEqual(verify_payload["data"]["remaining_uploads"], 2)

        image_response = self._fetch_uploaded_image(upload_response.get_json())
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.data, PNG_BYTES)

    def test_token_upload_limit_exhaustion_returns_429(self):
        token_response = self.client.post(
            "/api/auth/token/generate",
            json={"upload_limit": 1, "expires_days": 7, "description": "limit"},
        )
        self.assertEqual(token_response.status_code, 200)
        token = token_response.get_json()["data"]["token"]

        first_upload = self._upload_png(
            "/api/auth/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(first_upload.status_code, 200)

        second_upload = self._upload_png(
            "/api/auth/upload",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(second_upload.status_code, 429)

    def test_admin_upload_smoke(self):
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_username"] = "admin"
            session["admin_token"] = "admin-smoke-token"

        response = self._upload_png("/api/admin/upload")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

        encrypted_id = payload["data"]["encrypted_id"]
        image_response = self.client.get(f"/image/{encrypted_id}")
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.data, PNG_BYTES)

    def test_admin_images_guest_filter_includes_web_upload_source(self):
        upload_response = self._upload_png("/api/upload")
        self.assertEqual(upload_response.status_code, 200)

        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_username"] = "admin"
            session["admin_token"] = "admin-smoke-token"

        response = self.client.get("/api/admin/images?source=guest&limit=10")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["data"]["images"]), 1)

    def test_max_file_size_change_applies_without_restart(self):
        large_png = PNG_BYTES + (b"\x00" * (int(1.5 * 1024 * 1024)))
        update_system_setting("max_file_size_mb", "1")

        too_large = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(large_png), "large.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(too_large.status_code, 400)

        update_system_setting("max_file_size_mb", "2")
        accepted = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(large_png), "large.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(accepted.status_code, 200)


if __name__ == "__main__":
    unittest.main()
