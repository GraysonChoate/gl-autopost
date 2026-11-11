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
import os
def shape(k):
    v = os.environ.get(k, "")
    return f"{k}: len={len(v)} stripped_len={len(v.strip())} has_dash={'-' in v} starts_digit={v[:1].isdigit()}"
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    print("shape", shape(k))
import hashlib, itertools
ks = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
for a, b in itertools.combinations(ks, 2):
    if os.environ.get(a) and os.environ.get(a) == os.environ.get(b):
        print("shape SAME VALUE:", a, b)
for name, (ok, fn) in checks.items():
    if not ok():
        print(f"{name}: not set up")
        continue
    try:
        print(f"{name}: OK -> {fn()}")
    except Exception as e:
        print(f"{name}: FAILED -> {e}")
