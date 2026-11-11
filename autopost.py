#!/usr/bin/env python3
"""Grounded Labs autopost: our own scheduler/poster for IG, FB, X, TikTok, YouTube, LinkedIn.

Runs on GitHub Actions every 15 min. For each APPROVED post in schedule.yaml:
  1. ~1 hour before each time slot: ntfy push to Grayson (exact file + platforms + who posts what).
  2. When due: publish on every configured platform; record in state/state.json (no doubles).
  3. Push "Posted" with links, or "FAILED" with the error. TikTok upload mode pushes "tap Post".
Platforms whose API isn't set up yet are reported as MANUAL in the heads-up and skipped.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

from connectors import linkedin, meta, tiktok, x, youtube
from validate import validate

ROOT = Path(__file__).parent
TZ = ZoneInfo("America/Chicago")
HEADS_UP_MIN = 60
LATE_LIMIT_MIN = 180
DRY = os.environ.get("DRY_RUN") == "1"
ONLY = os.environ.get("ONLY_POST", "").strip()   # run a single post id (manual test)
ONLY_PLATS = [x.strip() for x in os.environ.get("ONLY_PLATFORMS", "").split(",") if x.strip()]
NTFY = os.environ.get("NTFY_TOPIC", "").strip()
REPO = os.environ.get("GITHUB_REPOSITORY", "")

PLATFORMS = {
    "instagram": (meta.configured_ig, meta.publish_ig),
    "facebook": (meta.configured_fb, meta.publish_fb),
    "x": (x.configured, x.publish),
    "tiktok": (tiktok.configured, tiktok.publish),
    "youtube": (youtube.configured, youtube.publish),
    "linkedin": (linkedin.configured, linkedin.publish),
}


def now():
    o = os.environ.get("NOW_OVERRIDE")  # tests only
    return dt.datetime.fromisoformat(o).replace(tzinfo=TZ) if o else dt.datetime.now(TZ)


def push(title, msg, priority="default", tags=""):
    print(f"[push] {title}: {msg}")
    if DRY or not NTFY:
        return
    h = {"Title": title.encode("utf-8"), "Priority": priority}
    if tags:
        h["Tags"] = tags
    if REPO:
        h["Click"] = f"https://github.com/{REPO}/blob/main/schedule.yaml"
    try:
        requests.post(f"https://ntfy.sh/{NTFY}", data=msg.encode("utf-8"), headers=h, timeout=30)
    except Exception as e:
        print(f"[push] failed: {e}")


def due(post, plat):
    t = (post["platforms"].get(plat) or {}).get("time") or post["time"]
    return dt.datetime.strptime(f"{post['date']} {t}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def main():
    sched = yaml.safe_load((ROOT / "schedule.yaml").read_text()) or {}
    posts = sched.get("posts") or []
    problems = validate(posts, ROOT)
    state_p = ROOT / "state" / "state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    t, changed = now(), False

    for p in posts:
        pid = p["id"]
        if ONLY and pid != ONLY:
            continue
        if p.get("paused") or not p.get("approved"):
            continue
        st = state.setdefault(pid, {"headsup": {}, "results": {}})
        if problems.get(pid):
            if not st.get("invalid_alert"):
                push(f"BLOCKED: {p['title']}", "Fix schedule.yaml:\n" + "\n".join(problems[pid]), "high", "no_entry")
                st["invalid_alert"] = True
                changed = True
            continue
        video = ROOT / p["video"]

        # group platforms by time slot
        slots = {}
        for plat in p["platforms"]:
            if plat in PLATFORMS and (not ONLY_PLATS or plat in ONLY_PLATS):
                slots.setdefault(due(p, plat), []).append(plat)

        for when, plats in sorted(slots.items()):
            key = when.strftime("%H:%M")
            mins = (when - t).total_seconds() / 60

            # 1) heads-up
            if (ONLY or mins <= HEADS_UP_MIN + 20) and key not in st["headsup"] and -mins + 50 <= LATE_LIMIT_MIN:
                auto = [x for x in plats if PLATFORMS[x][0]()]
                manual = [x for x in plats if x not in auto]
                goes = max(when, t + dt.timedelta(minutes=50)) if not ONLY else t
                lines = [f"{goes:%a %b %d %I:%M %p} CT", f"File: {p.get('source_file', p['video'])}"]
                if auto:
                    lines.append("Auto-posting: " + ", ".join(auto))
                if manual:
                    lines.append("Not automated (native schedule / manual): " + ", ".join(manual))
                lines.append(f"To stop: set paused: true on {pid} in schedule.yaml, or tell Claude 'STOP {pid}'.")
                push(f"In ~{int((goes - t).total_seconds() // 60)} min: {p['title']}", "\n".join(lines), tags="alarm_clock")
                st["headsup"][key] = t.isoformat()
                changed = True

            pending = [x for x in plats if x not in st["results"] and PLATFORMS[x][0]()]
            if not pending:
                continue
            if -mins > LATE_LIMIT_MIN and not ONLY:
                if not st.get(f"late_{key}"):
                    push(f"MISSED: {p['title']}", f"{key} slot ({', '.join(pending)}) was not posted. Not auto-posting 3h+ late.", "high", "warning")
                    st[f"late_{key}"] = True
                    changed = True
                continue
            # 2) publish: only when due AND Grayson has had his heads-up for 50+ min
            #    (a post added late gets its heads-up now and goes out ~50 min later).
            warned = dt.datetime.fromisoformat(st["headsup"][key]) if key in st["headsup"] else None
            if not ONLY and (mins > 0 or warned is None or (t - warned).total_seconds() < 50 * 60):
                continue
            ok, errors, actions = [], [], []
            for plat in plats:
                if plat in st["results"] or not PLATFORMS[plat][0]():
                    continue
                cfg = p["platforms"][plat]
                try:
                    res = {"dry": True} if DRY else PLATFORMS[plat][1](video, p, cfg)
                    res["at"] = now().isoformat()
                    st["results"][plat] = res
                    ok.append(f"{plat}: {res.get('url', 'done')}")
                    if res.get("action"):
                        actions.append(f"{plat}: {res['action']}")
                except Exception as e:
                    errors.append(f"{plat}: {e}")
                    st.setdefault("errors", []).append(f"{now():%m-%d %H:%M} {plat}: {str(e)[:300]}")
                changed = True
            if actions:
                push(f"ACTION NEEDED: {p['title']}", "\n".join(actions), "high", "point_right")
            if ok:
                push(f"Posted: {p['title']}", "\n".join(ok), tags="white_check_mark")
            if errors:
                push(f"POST FAILED: {p['title']}", "\n".join(errors)[:900], "urgent", "warning")

    if changed and (not DRY or os.environ.get("DRY_SAVE_STATE") == "1"):   # dry runs never touch state
        state_p.parent.mkdir(exist_ok=True)
        state_p.write_text(json.dumps(state, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
