#!/usr/bin/env python3
"""Grounded Labs autopost: heads-up + publish for IG and FB Reels.

Runs on GitHub Actions cron. Reads schedule.yaml, sends a push 1 hour before
each post (ntfy), publishes when due, posts first comments, then records
results in state/state.json and pushes a confirmation or an error alert.

Secrets (GitHub Actions):
  META_PAGE_TOKEN   long-lived Page access token (never-expiring)
  FB_PAGE_ID        Facebook Page id
  IG_USER_ID        Instagram business account id
  NTFY_TOPIC        private ntfy.sh topic name for push notifications
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

ROOT = Path(__file__).parent
TZ = ZoneInfo("America/Chicago")
GRAPH = "https://graph.facebook.com/v25.0"
RUPLOAD = "https://rupload.facebook.com"
HEADS_UP_MIN = 60          # send heads-up this many minutes before
LATE_LIMIT_MIN = 180       # don't publish if more than 3h late (alert instead)
DRY = os.environ.get("DRY_RUN") == "1"

TOKEN = os.environ.get("META_PAGE_TOKEN", "")
PAGE_ID = os.environ.get("FB_PAGE_ID", "")
IG_ID = os.environ.get("IG_USER_ID", "")
NTFY = os.environ.get("NTFY_TOPIC", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "")


def now():
    return dt.datetime.now(TZ)


def load_state():
    p = ROOT / "state" / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_state(s):
    (ROOT / "state" / "state.json").write_text(json.dumps(s, indent=2, sort_keys=True))


def push(title, msg, priority="default", tags=""):
    print(f"[push] {title}: {msg}")
    if DRY or not NTFY:
        return
    headers = {"Title": title.encode("utf-8"), "Priority": priority}
    if tags:
        headers["Tags"] = tags
    if REPO:
        headers["Click"] = f"https://github.com/{REPO}/blob/main/schedule.yaml"
    requests.post(f"https://ntfy.sh/{NTFY}", data=msg.encode("utf-8"), headers=headers, timeout=30)


def check(r):
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text[:500]}
    if r.status_code >= 400 or (isinstance(j, dict) and "error" in j):
        raise RuntimeError(f"{r.status_code} {json.dumps(j)[:500]}")
    return j


# ---------------- Instagram Reels (resumable upload) ----------------
def publish_ig(video: Path, caption: str, ai_label: bool, first_comment: str):
    j = check(requests.post(f"{GRAPH}/{IG_ID}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "is_ai_generated": "true" if ai_label else "false",
        "access_token": TOKEN}, timeout=60))
    cid = j["id"]
    data = video.read_bytes()
    check(requests.post(f"{RUPLOAD}/ig-api-upload/v25.0/{cid}", data=data, headers={
        "Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(len(data))}, timeout=300))
    for _ in range(60):  # wait up to ~10 min for processing
        s = check(requests.get(f"{GRAPH}/{cid}", params={
            "fields": "status_code,status", "access_token": TOKEN}, timeout=30))
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG processing error: {s}")
        time.sleep(10)
    else:
        raise RuntimeError("IG processing timed out")
    pub = check(requests.post(f"{GRAPH}/{IG_ID}/media_publish", data={
        "creation_id": cid, "access_token": TOKEN}, timeout=60))
    media_id = pub["id"]
    if first_comment:
        check(requests.post(f"{GRAPH}/{media_id}/comments", data={
            "message": first_comment, "access_token": TOKEN}, timeout=60))
    link = check(requests.get(f"{GRAPH}/{media_id}", params={
        "fields": "permalink", "access_token": TOKEN}, timeout=30)).get("permalink", "")
    return {"id": media_id, "url": link}


# ---------------- Facebook Page Reels ----------------
def publish_fb(video: Path, caption: str, first_comment: str):
    j = check(requests.post(f"{GRAPH}/{PAGE_ID}/video_reels", data={
        "upload_phase": "start", "access_token": TOKEN}, timeout=60))
    vid = j["video_id"]
    data = video.read_bytes()
    check(requests.post(f"{RUPLOAD}/video-upload/v25.0/{vid}", data=data, headers={
        "Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(len(data)),
        "Content-Type": "application/octet-stream"}, timeout=300))
    check(requests.post(f"{GRAPH}/{PAGE_ID}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": caption, "access_token": TOKEN}, timeout=60))
    post_id = None
    for _ in range(36):  # wait up to ~6 min for the reel to go live
        s = check(requests.get(f"{GRAPH}/{vid}", params={
            "fields": "status,post_id,permalink_url", "access_token": TOKEN}, timeout=30))
        st = (s.get("status") or {})
        if st.get("video_status") == "error":
            raise RuntimeError(f"FB processing error: {s}")
        post_id = s.get("post_id")
        if (st.get("publishing_phase") or {}).get("status") == "complete" and post_id:
            break
        time.sleep(10)
    if first_comment and post_id:
        check(requests.post(f"{GRAPH}/{post_id}/comments", data={
            "message": first_comment, "access_token": TOKEN}, timeout=60))
    return {"id": vid, "post_id": post_id, "url": f"https://www.facebook.com/reel/{vid}"}


def due_time(p):
    return dt.datetime.strptime(f"{p['date']} {p['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def main():
    sched = yaml.safe_load((ROOT / "schedule.yaml").read_text()) or {}
    posts = sched.get("posts", [])
    state = load_state()
    t = now()
    changed = False

    for p in posts:
        pid = p["id"]
        st = state.setdefault(pid, {})
        when = due_time(p)
        mins = (when - t).total_seconds() / 60
        video = ROOT / p["video"]
        plats = [x for x in p.get("platforms", []) if x in ("instagram", "facebook")]
        if p.get("paused"):
            continue

        # 1) heads-up ~1 hour before
        if 0 < mins <= HEADS_UP_MIN + 20 and not st.get("headsup"):
            problem = "" if video.exists() else " ⚠️ VIDEO FILE MISSING"
            push(f"In ~{int(mins)} min: {p['title']}",
                 f"{when:%a %b %d %I:%M %p} CT on {', '.join(plats)}\n"
                 f"File: {p.get('source_file', p['video'])}{problem}\n"
                 f"Caption: {p['ig_caption'][:140]}...\n"
                 f"Reply to Claude 'STOP {pid}' or 'swap {pid}' to change it.",
                 tags="alarm_clock")
            st["headsup"] = t.isoformat()
            changed = True

        # 2) publish when due
        if mins <= 0 and not st.get("done"):
            if -mins > LATE_LIMIT_MIN:
                if not st.get("late_alert"):
                    push(f"MISSED: {p['title']}", f"{pid} was due {when:%I:%M %p} and was not posted. Not auto-posting this late.", "high", "warning")
                    st["late_alert"] = True
                    changed = True
                continue
            results, errors = st.setdefault("results", {}), []
            for plat in plats:
                if plat in results:
                    continue
                try:
                    if DRY:
                        results[plat] = {"dry": True}
                    elif plat == "instagram":
                        results[plat] = publish_ig(video, p["ig_caption"], p.get("ai_label", False), p.get("ig_first_comment", ""))
                    elif plat == "facebook":
                        results[plat] = publish_fb(video, p.get("fb_caption", p["ig_caption"]), p.get("fb_first_comment", ""))
                except Exception as e:  # keep going; alert at the end
                    errors.append(f"{plat}: {e}")
                changed = True
            if errors:
                st["errors"] = errors
                push(f"POST FAILED: {p['title']}", "\n".join(errors)[:900], "high", "warning")
            else:
                st["done"] = t.isoformat()
                links = "\n".join(f"{k}: {v.get('url','')}" for k, v in results.items())
                push(f"Posted: {p['title']}", links or "done", tags="white_check_mark")

    if changed:
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
