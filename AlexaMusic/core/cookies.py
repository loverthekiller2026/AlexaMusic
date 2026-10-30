# Copyright (c) 2025 @KSKOP69. All rights reserved.
# Use of this source code is governed by a proprietary license.

import json
import os
import stat

import aiofiles

from ..logging import LOGGER

# Render Secret Files are read-only. Normalize the private source into /tmp,
# never into a tracked repository path.
COOKIE_SOURCE_ENV = "COOKIE_FILE"
COOKIE_OUTPUT_PATH = "/tmp/alexamusic-cookies.txt"


def normalize_cookies(content: str) -> str:
    content = content.lstrip("\ufeff").strip()
    if not content:
        raise ValueError("The cookie file is empty.")

    if content.startswith("# Netscape HTTP Cookie File") or content.startswith("# HTTP Cookie File"):
        lines = [line for line in content.splitlines() if line.strip()]
        cookie_lines = [
            line for line in lines
            if not line.lstrip().startswith("#") and len(line.split("\t")) >= 7
        ]
        if not cookie_lines:
            raise ValueError("Netscape cookie file contains no valid cookie records.")
        return "\n".join(lines) + "\n"

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
        if not isinstance(cookie, dict):
            continue
        domain = str(cookie.get("domain") or cookie.get("host") or "").strip()
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "")
        path = str(cookie.get("path") or "/")
        if not domain or not name:
            continue
        include_subdomains = "TRUE" if domain.startswith(".") or cookie.get("includeSubdomains") else "FALSE"
        secure = "TRUE" if cookie.get("secure") else "FALSE"
        expires = cookie.get("expirationDate", cookie.get("expires", cookie.get("expiry", 0)))
        try:
            expires = int(float(expires or 0))
        except (TypeError, ValueError):
            expires = 0
        if cookie.get("session") or expires < 0:
            expires = 0
        lines.append("\t".join((domain, include_subdomains, path, secure, str(expires), name, value)))

    if len(lines) == 1:
        raise ValueError("JSON contained no valid cookies.")
    return "\n".join(lines) + "\n"


def cookiefile() -> str | None:
    """Return the private normalized cookie path, or None when not configured."""
    return COOKIE_OUTPUT_PATH if os.path.isfile(COOKIE_OUTPUT_PATH) and os.path.getsize(COOKIE_OUTPUT_PATH) > 0 else None


async def save_cookies():
    source_path = str(os.getenv(COOKIE_SOURCE_ENV, "") or "").strip()
    if not source_path:
        LOGGER(__name__).warning(
            "COOKIE_FILE is not configured; YouTube will run without authentication cookies."
        )
        return

    if not os.path.isfile(source_path):
        LOGGER(__name__).error("COOKIE_FILE does not point to a readable file.")
        return

    try:
        async with aiofiles.open(source_path, "r", encoding="utf-8") as file:
            content = await file.read()
        normalized = normalize_cookies(content)
        os.makedirs(os.path.dirname(COOKIE_OUTPUT_PATH), exist_ok=True)
        async with aiofiles.open(COOKIE_OUTPUT_PATH, "w", encoding="utf-8", newline="") as file:
            await file.write(normalized)
        os.chmod(COOKIE_OUTPUT_PATH, stat.S_IRUSR | stat.S_IWUSR)
        LOGGER(__name__).info("Private YouTube cookies loaded from COOKIE_FILE.")
    except (OSError, UnicodeError, ValueError) as exc:
        LOGGER(__name__).error("Could not load YouTube cookies: %s", exc)
