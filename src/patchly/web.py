from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+(?:\.[^\s<>\"']+)+")

FETCH_TIMEOUT = 30
MAX_FETCH_SIZE = 512 * 1024

INJECTION_PATTERNS = re.compile(
    r"(?i)(?:"
    r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions"
    r"|forget\s+(?:all\s+)?(?:previous|above|prior)"
    r"|disregard\s+(?:all\s+)?(?:previous|above|prior)"
    r"|you\s+(?:are\s+)?(?:now|are\s+free|don't\s+need\s+to)"
    r"|system\s+(?:prompt|instruction|message)"
    r"|delete\s+(?:all\s+)?files"
    r"|run\s+(?:this\s+)?command"
    r"|execute\s+(?:this\s+)?shell"
    r"|your\s+(?:new\s+)?role\s+is"
    r")",
    re.IGNORECASE,
)


def extract_urls(text: str) -> list[str]:
    return list(set(URL_PATTERN.findall(text)))


def fetch_url(url: str, timeout: int = FETCH_TIMEOUT) -> str | None:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        content = resp.text
        if len(content) > MAX_FETCH_SIZE:
            content = content[:MAX_FETCH_SIZE]
        return _html_to_text(content) if "text/html" in resp.headers.get("content-type", "") else content
    except Exception:
        return None


def _html_to_text(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize(content: str) -> str:
    stripped = INJECTION_PATTERNS.sub("[SANITIZED]", content)
    return stripped.strip()


def fetch_safe(url: str) -> dict[str, str] | None:
    raw = fetch_url(url)
    if raw is None:
        return None
    sanitized = sanitize(raw)
    return {
        "url": url,
        "content": sanitized[:MAX_FETCH_SIZE],
        "preview": sanitized[:200] + ("..." if len(sanitized) > 200 else ""),
    }
