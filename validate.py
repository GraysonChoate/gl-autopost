#!/usr/bin/env python3
"""Checks schedule.yaml before anything posts. Run: python validate.py (exit 1 on problems)."""
import re
import sys
from pathlib import Path

import yaml

BANNED = ["ai-powered", "transform", "revolutioniz", "agentic", "leverag"]
LIMITS = {"instagram": ("caption", 2200), "facebook": ("caption", 5000), "x": ("text", 280),
          "tiktok": ("caption", 2200), "youtube": ("title", 100), "linkedin": ("text", 3000)}
REQUIRED = ["id", "title", "date", "time", "video", "platforms"]


def validate(posts, root):
    out, seen = {}, set()
    for p in posts:
        pid = p.get("id", "?")
        errs = [f"missing {k}" for k in REQUIRED if not p.get(k)]
        if pid in seen:
            errs.append("duplicate id")
        seen.add(pid)
        if p.get("video") and not (Path(root) / p["video"]).exists():
            errs.append(f"video file not in repo: {p['video']}")
        src = str(p.get("source_file", ""))
        if "Explainers" in src and "_VO" not in src and not any(k in src for k in ("Overnight", "F13")):
            errs.append("explainers must use the _VO file from Finals/")
        for t in [p.get("time")] + [(c or {}).get("time") for c in (p.get("platforms") or {}).values()]:
            if t and not re.fullmatch(r"\d{2}:\d{2}", str(t)):
                errs.append(f"bad time {t!r} (use \"HH:MM\" in quotes)")
        for plat, cfg in (p.get("platforms") or {}).items():
            if plat not in LIMITS:
                errs.append(f"unknown platform {plat}")
                continue
            field, lim = LIMITS[plat]
            text = (cfg or {}).get(field, "")
            if not text:
                errs.append(f"{plat}: missing {field}")
            elif len(text) > lim:
                errs.append(f"{plat}: {field} is {len(text)} chars (max {lim})")
            blob = " ".join(str(v) for v in (cfg or {}).values()).lower()
            for w in BANNED:
                if w in blob:
                    errs.append(f"{plat}: banned word '{w}'")
            if plat == "x" and "http" in text and not cfg.get("allow_link"):
                errs.append("x: a link costs ~13x more per post; use 'link in bio' or set allow_link: true")
        if errs:
            out[pid] = errs
    return out


if __name__ == "__main__":
    root = Path(__file__).parent
    posts = (yaml.safe_load((root / "schedule.yaml").read_text()) or {}).get("posts") or []
    probs = validate(posts, root)
    for pid, errs in probs.items():
        print(f"{pid}:\n  - " + "\n  - ".join(errs))
    print("OK" if not probs else f"{len(probs)} post(s) with problems")
    sys.exit(1 if probs else 0)
