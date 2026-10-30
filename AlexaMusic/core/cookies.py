# Copyright (c) 2025 @KSKOP69. All rights reserved.
# Use of this source code is governed by a proprietary license.

import asyncio
import json
import os
from urllib.parse import urlparse

import aiohttp
import aiofiles

import config
from ..logging import LOGGER

COOKIE_PATH = os.path.join("cookies", "cookies.txt")
COOKIE_SOURCE = "https://batbin.me/raw/"


async def fetch_content(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            return await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        LOGGER(__name__).error("Error fetching cookies: %s", exc)
        return ""


def _batbin_raw_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.netloc.lower().endswith("batbin.me"):
        paste_id = parsed.path.rstrip("/").split("/")[-1]
    else:
        paste_id = value.rstrip("/").split("/")[-1].split("?")[0]
    return f"{COOKIE_SOURCE}{paste_id}" if paste_id else ""


def _netscape_cookie_line(cookie: dict) -> str:
    domain = str(cookie.get("domain") or cookie.get("host") or "").strip()
    name = str(cookie.get("name") or "").strip()
    value = str(cookie.get("value") or "")
    path = str(cookie.get("path") or "/")
    if not domain or not name:
        return ""
    include_subdomains = "TRUE" if domain.startswith(".") or cookie.get("includeSubdomains") else "FALSE"
    secure = "TRUE" if cookie.get("secure") else "FALSE"
    expires = cookie.get("expirationDate", cookie.get("expires", cookie.get("expiry", 0)))
    try:
        expires = int(float(expires or 0))
    except (TypeError, ValueError):
        expires = 0
    # Netscape cookie files use -1 for session cookies.
    if cookie.get("session") or expires < 0:
        expires = 0
    return "\t".join((domain, include_subdomains, path, secure, str(expires), name, value))


def normalize_cookies(content: str) -> str:
    content = content.lstrip("\ufeff").strip()
    if not content:
        raise ValueError("The cookie source is empty.")
    if content.startswith("# Netscape HTTP Cookie File") or content.startswith("# HTTP Cookie File"):
        return content.rstrip() + "\n"
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Cookies must be Netscape format or a supported JSON cookie export.") from exc

    if isinstance(payload, dict):
        payload = payload.get("cookies", payload.get("Cookie", []))
    if not isinstance(payload, list):
        raise ValueError("JSON cookie export must contain a cookies array.")

    lines = ["# Netscape HTTP Cookie File"]
    for cookie in payload:
        if isinstance(cookie, dict):
            line = _netscape_cookie_line(cookie)
            if line:
                lines.append(line)
    if len(lines) == 1:
        raise ValueError("JSON contained no valid cookies.")
    return "\n".join(lines) + "\n"


async def save_file(content: str, file_path: str) -> str:
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        async with aiofiles.open(file_path, "w", encoding="utf-8", newline="") as file:
            await file.write(content)
        return file_path
    except OSError as exc:
        LOGGER(__name__).error("Error saving cookies file: %s", exc)
        return ""


async def save_cookies():
    source = _batbin_raw_url(str(config.COOKIES or ""))
    if not source:
        LOGGER(__name__).warning("COOKIES is not configured; keeping any existing cookies file.")
        return

    async with aiohttp.ClientSession() as session:
        content = await fetch_content(session, source)
    if not content:
        LOGGER(__name__).error("Could not download the configured cookie source.")
        return

    try:
        normalized = normalize_cookies(content)
    except ValueError as exc:
        LOGGER(__name__).error("Invalid YouTube cookies: %s", exc)
        return

    saved_path = await save_file(normalized, COOKIE_PATH)
    if saved_path and os.path.getsize(saved_path) > 0:
        LOGGER(__name__).info("Valid Netscape cookies saved to %s.", saved_path)
    else:
        LOGGER(__name__).error("Failed to save cookies file.")
