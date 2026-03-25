#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tg_imagebed.storage.backends.telegram import TelegramBackend


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

JPEG_BYTES = b"\xff\xd8\xff\xe0" + (b"\x00" * 32)


def _response(payload):
    resp = Mock()
    resp.ok = True
    resp.json.return_value = payload
    return resp


class TelegramBackendUploadModeTests(unittest.TestCase):
    def setUp(self):
        self.backend = TelegramBackend(name="telegram", bot_token="token", chat_id=123456)

    def test_png_put_file_uses_send_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "transparent.png"
            path.write_bytes(PNG_BYTES)

            with patch.object(self.backend, "_get_file_path", return_value="documents/file_1.png"):
                self.backend._session.post = Mock(
                    return_value=_response(
                        {"ok": True, "result": {"message_id": 10, "document": {"file_id": "doc-file-id"}}}
                    )
                )

                result = self.backend.put_file(
                    file_path=str(path),
                    filename="transparent.png",
                    content_type="image/png",
                    file_size=len(PNG_BYTES),
                    caption="png upload",
                    source="web_upload",
                    username="tester",
                )

        self.assertIsNotNone(result)
        self.assertEqual(result.file_id, "doc-file-id")
        called_url = self.backend._session.post.call_args.args[0]
        self.assertTrue(called_url.endswith("/sendDocument"))

    def test_jpeg_put_bytes_uses_send_photo(self):
        with patch.object(self.backend, "_get_file_path", return_value="photos/file_2.jpg"):
            self.backend._session.post = Mock(
                return_value=_response(
                    {"ok": True, "result": {"message_id": 11, "photo": [{"file_id": "photo-file-id"}]}}
                )
            )

            result = self.backend.put_bytes(
                file_content=JPEG_BYTES,
                filename="sample.jpg",
                content_type="image/jpeg",
                file_size=len(JPEG_BYTES),
                caption="jpeg upload",
                source="web_upload",
                username="tester",
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.file_id, "photo-file-id")
        called_url = self.backend._session.post.call_args.args[0]
        self.assertTrue(called_url.endswith("/sendPhoto"))


if __name__ == "__main__":
    unittest.main()
