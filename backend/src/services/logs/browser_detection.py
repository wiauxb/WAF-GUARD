"""Non-browser client detection.

Client policy: the WAF protects a web application, not an API, so every
legitimate request comes from a browser. Any request from a non-browser client
is treated as an attack (true positive), as a deterministic override applied
after the FP/TP model's prediction.

Ported from false_positives_classification/browser_detection.py (commit 63167c1,
2026-10-16) and its config.py constants.
"""
from typing import Any, Dict, Optional

# WAF rule IDs flagging a non-browser client (Approach WAF)
NON_BROWSER_RULES = {
    "2000607",  # Header missing <User-Agent>
    "2000633",  # Not a browser (Accept-Encoding)
}

# WAF messages flagging a non-browser client
NON_BROWSER_MSGS = [
    "header missing <user-agent>",
    "not a browser",
]

# Z-section category set by the WAF for non-browser clients
NON_BROWSER_WAF_CATEGORY = "not_browser"

# Rendering-engine tokens every real browser User-Agent carries
BROWSER_ENGINE_TOKENS = ["applewebkit", "gecko/", "trident/"]

# Known scanner/malicious user-agents (TP)
PROD_SCANNER_UAS = [
    "zgrab", "keydrop", "custom-asynchttpclient", "l9explore",
    "masscan", "nmap", "modatscanner", "python-requests", "go-http-client",
    "curl/", "sqlmap", "nikto", "nuclei", "dirbuster", "gobuster",
]

# User-Agent tokens of bots, crawlers, headless browsers and HTTP libraries
NON_BROWSER_UA_TOKENS = PROD_SCANNER_UAS + [
    "bot", "crawl", "spider", "slurp", "headless", "phantomjs", "selenium",
    "puppeteer", "playwright", "python", "wget", "libwww", "okhttp", "java/",
    "apache-httpclient", "axios", "node-fetch", "postman", "scan", "censys",
    "expanse", "facebookexternalhit", "chatgpt", "claude", "perplexity",
]


def _str(value: Any) -> str:
    """Normalise a feature value (str, NaN, None) to a plain string."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value)


def non_browser_reason(row: Dict[str, Any]) -> Optional[str]:
    """Return why the request comes from a non-browser client, or None if it looks
    like a browser.

    `row` is the feature dict from extract_features_from_entry(). WAF-provided
    signals are checked first, then the User-Agent.
    """
    categories = _str(row.get("waf_categories")).lower().split("|")
    if NON_BROWSER_WAF_CATEGORY in categories:
        return "WAF category not_browser"

    rule_ids = _str(row.get("rule_ids")).split("|")
    if any(r in NON_BROWSER_RULES for r in rule_ids):
        return "WAF non-browser rule"

    messages = _str(row.get("messages")).lower()
    if any(m in messages for m in NON_BROWSER_MSGS):
        return "WAF non-browser message"

    ua = _str(row.get("user_agent")).strip().strip("'\"").lower()
    if not ua:
        return "empty User-Agent"
    if not ua.startswith("mozilla/5.0"):
        return "User-Agent is not a browser"
    if any(t in ua for t in NON_BROWSER_UA_TOKENS):
        return "bot/tool User-Agent"
    if not any(t in ua for t in BROWSER_ENGINE_TOKENS):
        return "User-Agent without browser engine"
    return None


def is_waf_signal(reason: str) -> bool:
    """True if the reason comes from the WAF itself rather than the User-Agent."""
    return reason.startswith("WAF")
