"""Instagram Reels + Facebook Page Reels via Meta Graph API (free; 30 API posts / 24h)."""
import time

import requests

from .common import check, env

GRAPH = "https://graph.facebook.com/v25.0"
RUPLOAD = "https://rupload.facebook.com"


def _tok():
    return env("META_PAGE_TOKEN")


def configured_ig():
    return bool(_tok() and env("IG_USER_ID"))


def configured_fb():
    return bool(_tok() and env("FB_PAGE_ID"))


def publish_ig(video, post, cfg):
    tok, ig = _tok(), env("IG_USER_ID")
    j = check(requests.post(f"{GRAPH}/{ig}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": cfg["caption"],
        "share_to_feed": "true", "is_ai_generated": "true" if post.get("ai_label") else "false",
        "access_token": tok}, timeout=60))
    cid = j["id"]
    data = video.read_bytes()
    check(requests.post(f"{RUPLOAD}/ig-api-upload/v25.0/{cid}", data=data, headers={
        "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(data))}, timeout=300))
    for _ in range(60):
        s = check(requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=30))
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG processing error: {s}")
        time.sleep(10)
    else:
        raise RuntimeError("IG processing timed out")
    media_id = check(requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60))["id"]
    if cfg.get("first_comment"):
        check(requests.post(f"{GRAPH}/{media_id}/comments", data={"message": cfg["first_comment"], "access_token": tok}, timeout=60))
    link = check(requests.get(f"{GRAPH}/{media_id}", params={"fields": "permalink", "access_token": tok}, timeout=30)).get("permalink", "")
    return {"id": media_id, "url": link}


def publish_fb(video, post, cfg):
    tok, page = _tok(), env("FB_PAGE_ID")
    vid = check(requests.post(f"{GRAPH}/{page}/video_reels", data={"upload_phase": "start", "access_token": tok}, timeout=60))["video_id"]
    data = video.read_bytes()
    check(requests.post(f"{RUPLOAD}/video-upload/v25.0/{vid}", data=data, headers={
        "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(data)),
        "Content-Type": "application/octet-stream"}, timeout=300))
    check(requests.post(f"{GRAPH}/{page}/video_reels", data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": cfg["caption"], "access_token": tok}, timeout=60))
    post_id = None
    for _ in range(36):
        s = check(requests.get(f"{GRAPH}/{vid}", params={"fields": "status,post_id", "access_token": tok}, timeout=30))
        st = s.get("status") or {}
        if st.get("video_status") == "error":
            raise RuntimeError(f"FB processing error: {s}")
        post_id = s.get("post_id")
        if (st.get("publishing_phase") or {}).get("status") == "complete" and post_id:
            break
        time.sleep(10)
    if cfg.get("first_comment") and post_id:
        check(requests.post(f"{GRAPH}/{post_id}/comments", data={"message": cfg["first_comment"], "access_token": tok}, timeout=60))
    return {"id": vid, "post_id": post_id, "url": f"https://www.facebook.com/reel/{vid}"}
