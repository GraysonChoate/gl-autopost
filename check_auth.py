#!/usr/bin/env python3
"""Verify each configured platform's keys without posting anything."""
from connectors import linkedin, meta, tiktok, x, youtube

checks = {
    "x": (x.configured, x.whoami),
    "meta": (meta.configured_ig, lambda: "token present"),
    "tiktok": (tiktok.configured, lambda: tiktok.access_token() and "token refresh OK"),
    "youtube": (youtube.configured, lambda: youtube.access_token() and "token refresh OK"),
    "linkedin": (linkedin.configured, lambda: linkedin.access_token() and "token OK"),
}
for name, (ok, fn) in checks.items():
    if not ok():
        print(f"{name}: not set up")
        continue
    try:
        print(f"{name}: OK -> {fn()}")
    except Exception as e:
        print(f"{name}: FAILED -> {e}")
