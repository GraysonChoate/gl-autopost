"""X (Twitter) API v2, pay-per-use credits. OAuth 1.0a user context (keys never expire).

Secrets: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET (all from console.x.com, app with Read+Write).
Cost: ~$0.015 per post, ~$0.20 if the text contains a URL. Keep links out when possible.
"""
import time

import requests
from requests_oauthlib import OAuth1

from .common import check, env

API = "https://api.x.com/2"
CHUNK = 4 * 1024 * 1024


def configured():
    return all(env(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))


def _auth():
    return OAuth1(env("X_API_KEY"), env("X_API_SECRET"), env("X_ACCESS_TOKEN"), env("X_ACCESS_SECRET"))


def upload_video(video):
    auth, data = _auth(), video.read_bytes()
    j = check(requests.post(f"{API}/media/upload/initialize", auth=auth, json={
        "media_type": "video/mp4", "total_bytes": len(data), "media_category": "amplify_video"}, timeout=60))
    mid = (j.get("data") or j)["id"]
    for i in range(0, len(data), CHUNK):
        check(requests.post(f"{API}/media/upload/{mid}/append", auth=auth,
                            data={"segment_index": str(i // CHUNK)},
                            files={"media": ("chunk", data[i:i + CHUNK], "application/octet-stream")}, timeout=120))
    j = check(requests.post(f"{API}/media/upload/{mid}/finalize", auth=auth, timeout=60))
    info = (j.get("data") or j).get("processing_info")
    for _ in range(60):
        if not info or info.get("state") == "succeeded":
            return mid
        if info.get("state") == "failed":
            raise RuntimeError(f"X media processing failed: {info}")
        time.sleep(min(int(info.get("check_after_secs", 5)), 15))
        j = check(requests.get(f"{API}/media/upload", auth=auth, params={"command": "STATUS", "media_id": mid}, timeout=30))
        info = (j.get("data") or j).get("processing_info")
    raise RuntimeError("X media processing timed out")


def publish(video, post, cfg):
    mid = upload_video(video)
    j = check(requests.post(f"{API}/tweets", auth=_auth(), json={"text": cfg["text"], "media": {"media_ids": [mid]}}, timeout=60))
    tid = j["data"]["id"]
    return {"id": tid, "url": f"https://x.com/groundedlabs_ai/status/{tid}"}
