#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tg_imagebed.api.tg_auth import SimpleRateLimiter
from tg_imagebed.bot.commands import (
    _is_file_owner,
    _set_pending_tokens,
    _pop_pending_tokens,
    _settoken_pending,
)
from tg_imagebed.bot.handlers import _build_reply_text
from tg_imagebed.bot_control import get_webhook_secret, build_webhook_url


class BotRuntimeTests(unittest.TestCase):
    def tearDown(self):
        _settoken_pending.clear()

    def test_webhook_secret_and_url(self):
        secret_a = get_webhook_secret("123456:ABCDEF")
        secret_b = get_webhook_secret("123456:ABCDEG")
        self.assertEqual(len(secret_a), 32)
        self.assertNotEqual(secret_a, secret_b)
        self.assertEqual(
            build_webhook_url("https://example.com", "123456:ABCDEF"),
            f"https://example.com/api/auth/tg/webhook/{secret_a}",
        )

    def test_settoken_pending_ttl(self):
        with patch("tg_imagebed.bot.commands._get_settoken_ttl_seconds", return_value=1):
            _set_pending_tokens(1001, ["token-a", "token-b"])
            self.assertEqual(_pop_pending_tokens(1001), ["token-a", "token-b"])
            self.assertIsNone(_pop_pending_tokens(1001))

            _set_pending_tokens(1002, ["token-c"])
            time.sleep(1.2)
            self.assertIsNone(_pop_pending_tokens(1002))

    def test_file_owner_prefers_tg_user_id(self):
        user = SimpleNamespace(id=42, username="alice", full_name="Alice")
        self.assertTrue(_is_file_owner({"tg_user_id": 42, "username": "other"}, user))
        self.assertFalse(_is_file_owner({"tg_user_id": 43, "username": "alice"}, user))
        self.assertTrue(_is_file_owner({"tg_user_id": None, "username": "alice"}, user))

    def test_rate_limiter_thread_safe(self):
        limiter = SimpleRateLimiter(max_requests=2, window_seconds=60)
        allowed = 0
        lock = threading.Lock()

        def worker():
            nonlocal allowed
            ok = limiter.is_allowed("same-key")
            if ok:
                with lock:
                    allowed += 1

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertLessEqual(allowed, 2)

    def test_reply_template_fallback_and_strict_mode(self):
        result = {"file_size": 1024, "encrypted_id": "enc123", "original_filename": "a.jpg"}
        url = "https://x.example/image/enc123"

        def non_strict(key: str):
            values = {
                "bot_reply_template": "bad {unknown}",
                "bot_reply_show_size": "1",
                "bot_reply_show_filename": "0",
                "bot_template_strict_mode": "0",
            }
            return values.get(key)

        text, parse_mode = _build_reply_text(result, url, "a.jpg", non_strict)
        self.assertEqual(parse_mode, "HTML")
        self.assertIn("上传成功", text)

        def strict(key: str):
            values = {
                "bot_reply_template": "bad {unknown}",
                "bot_reply_show_size": "1",
                "bot_reply_show_filename": "0",
                "bot_template_strict_mode": "1",
            }
            return values.get(key)

        strict_text, strict_mode = _build_reply_text(result, url, "a.jpg", strict)
        self.assertEqual(strict_mode, None)
        self.assertIn("模板配置错误", strict_text)


if __name__ == "__main__":
    unittest.main()
