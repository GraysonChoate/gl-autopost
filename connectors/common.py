import json
import os


def env(name, default=""):
    return os.environ.get(name, default).strip()


def check(r):
    """Raise on HTTP error or an error body; return parsed JSON (or {})."""
    try:
        j = r.json() if r.content else {}
    except Exception:
        j = {"raw": r.text[:500]}
    bad = r.status_code >= 400
    if isinstance(j, dict) and j.get("error") and not (isinstance(j["error"], dict) and j["error"].get("code") == "ok"):
        bad = True
    if bad:
        raise RuntimeError(f"{r.request.method} {r.url.split('?')[0]} -> {r.status_code} {json.dumps(j)[:600]}")
    return j
