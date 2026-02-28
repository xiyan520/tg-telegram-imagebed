#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Device and browser fingerprint helpers."""

from __future__ import annotations

import re
from typing import Dict


_GENERIC_DEVICE_NAMES = {
    "",
    "web",
    "desktop",
    "android",
    "ios",
    "unknown",
    "current-browser",
    "browser",
}


def _extract_version(user_agent: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, user_agent, re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip()
    return ""


def _guess_os_name(user_agent: str) -> str:
    ua = user_agent.lower()
    if "windows nt" in ua or "windows" in ua:
        return "Windows"
    if "iphone" in ua or "ipad" in ua or "ipod" in ua or "ios" in ua:
        return "iOS"
    if "android" in ua:
        return "Android"
    if "macintosh" in ua or "mac os x" in ua:
        return "macOS"
    if "cros" in ua:
        return "ChromeOS"
    if "linux" in ua:
        return "Linux"
    return "Unknown OS"


def _guess_browser_name_and_version(user_agent: str) -> tuple[str, str]:
    ua = user_agent.lower()

    if "edg/" in ua or "edge/" in ua or "edga/" in ua or "edgios/" in ua:
        return "Edge", _extract_version(user_agent, [r"(?:Edg|Edge|EdgA|EdgiOS)/([\d\.]+)"])
    if "opr/" in ua or "opera" in ua:
        return "Opera", _extract_version(user_agent, [r"(?:OPR|Opera)/([\d\.]+)"])
    if "samsungbrowser/" in ua:
        return "Samsung Internet", _extract_version(user_agent, [r"SamsungBrowser/([\d\.]+)"])
    if "firefox/" in ua or "fxios/" in ua:
        return "Firefox", _extract_version(user_agent, [r"(?:Firefox|FxiOS)/([\d\.]+)"])
    if "micromessenger/" in ua:
        return "WeChat", _extract_version(user_agent, [r"MicroMessenger/([\d\.]+)"])
    if "ucbrowser/" in ua:
        return "UC Browser", _extract_version(user_agent, [r"UCBrowser/([\d\.]+)"])
    if "qqbrowser/" in ua:
        return "QQ Browser", _extract_version(user_agent, [r"QQBrowser/([\d\.]+)"])
    if "msie " in ua or "trident/" in ua:
        return "Internet Explorer", _extract_version(user_agent, [r"MSIE\s([\d\.]+)", r"rv:([\d\.]+)"])

    # Safari must be checked before Chrome fallback when Version/... exists.
    if "safari/" in ua and "chrome/" not in ua and "crios/" not in ua:
        return "Safari", _extract_version(user_agent, [r"Version/([\d\.]+)"])

    if "chrome/" in ua or "crios/" in ua:
        return "Chrome", _extract_version(user_agent, [r"(?:Chrome|CriOS)/([\d\.]+)"])

    return "Unknown Browser", ""


def _guess_platform(os_name: str) -> str:
    if os_name == "iOS":
        return "ios"
    if os_name == "Android":
        return "android"
    if os_name in {"Windows", "macOS", "Linux", "ChromeOS"}:
        return "desktop"
    return "web"


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """Parse user agent into normalized os/browser/platform fields."""
    ua = str(user_agent or "").strip()
    os_name = _guess_os_name(ua)
    browser_name, browser_version = _guess_browser_name_and_version(ua)
    return {
        "os_name": os_name,
        "browser_name": browser_name,
        "browser_version": browser_version,
        "platform": _guess_platform(os_name),
    }


def build_device_label(os_name: str, browser_name: str) -> str:
    safe_os = str(os_name or "").strip() or "Unknown OS"
    safe_browser = str(browser_name or "").strip() or "Unknown Browser"
    return f"{safe_os} · {safe_browser}"


def is_generic_device_name(device_name: str) -> bool:
    value = str(device_name or "").strip()
    lowered = value.lower()
    if lowered in _GENERIC_DEVICE_NAMES:
        return True
    if re.match(r"^(desktop|web|android|ios|unknown)\s*[·\-]\s*[a-z]{2}(?:-[a-z]{2})?$", lowered):
        return True
    return lowered.endswith(" browser")


def normalize_device_name(device_name: str, parsed_ua: Dict[str, str]) -> str:
    """Return preferred device name; fallback to parsed OS+browser label."""
    raw = str(device_name or "").strip()
    if raw and not is_generic_device_name(raw):
        return raw[:120]
    return build_device_label(parsed_ua.get("os_name"), parsed_ua.get("browser_name"))[:120]
