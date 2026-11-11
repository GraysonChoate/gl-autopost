"""TikTok Content Posting API.

mode "upload" (default, works before the audit): video lands in the TikTok app inbox as a draft;
  Grayson gets a push and taps Post (adds caption in-app). Scope video.upload.
mode "direct" (only after the Direct Post audit passes, TIKTOK_DIRECT_OK=1): posts publicly. Scope video.publish.

Secrets: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN (365 days). Access token (24h) is refreshed every run.
"""
import time

import requests

from .common import check, env

API = "https://open.tiktokapis.com/v2"


def configured():
    return all(env(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"))


def access_token():
    j = check(requests.post(f"{API}/oauth/token/", data={
        "client_key": env("TIKTOK_CLIENT_KEY"), "client_secret": env("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": env("TIKTOK_REFRESH_TOKEN")},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30))
    if j.get("refresh_token") and j["refresh_token"] != env("TIKTOK_REFRESH_TOKEN"):
        print("[tiktok] NOTE: refresh token rotated; update TIKTOK_REFRESH_TOKEN secret")
    return j["access_token"]


def _send(url, data):
    # Files under 64 MB go up as one chunk.
    check(requests.put(url, data=data, headers={
        "Content-Type": "video/mp4", "Content-Length": str(len(data)),
        "Content-Range": f"bytes 0-{len(data) - 1}/{len(data)}"}, timeout=300))


def publish(video, post, cfg):
    tok = access_token()
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    data = video.read_bytes()
    src = {"source": "FILE_UPLOAD", "video_size": len(data), "chunk_size": len(data), "total_chunk_count": 1}
    direct = cfg.get("mode") == "direct" and env("TIKTOK_DIRECT_OK") == "1"
    if direct:
        info = check(requests.post(f"{API}/post/publish/creator_info/query/", headers=h, timeout=30))["data"]
        privacy = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in info.get("privacy_level_options", []) else info["privacy_level_options"][0]
        body = {"post_info": {"title": cfg["caption"], "privacy_level": privacy,
                              "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                              "is_aigc": bool(post.get("ai_label"))},
                "source_info": src}
        j = check(requests.post(f"{API}/post/publish/video/init/", headers=h, json=body, timeout=60))["data"]
    else:
        j = check(requests.post(f"{API}/post/publish/inbox/video/init/", headers=h, json={"source_info": src}, timeout=60))["data"]
    _send(j["upload_url"], data)
    pid = j["publish_id"]
    status = ""
    for _ in range(30):
        s = check(requests.post(f"{API}/post/publish/status/fetch/", headers=h, json={"publish_id": pid}, timeout=30))["data"]
        status = s.get("status", "")
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            break
        if status == "FAILED":
            raise RuntimeError(f"TikTok failed: {s.get('fail_reason')}")
        time.sleep(10)
    return {"id": pid, "status": status, "mode": "direct" if direct else "upload",
            "url": "https://www.tiktok.com/@groundedlabs_ai",
            "action": None if direct else "Open TikTok > inbox notification > edit > paste caption > Post"}
