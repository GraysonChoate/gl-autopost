"""YouTube Shorts via YouTube Data API v3 (videos.insert, resumable).

Uploads from an unverified API project are forced PRIVATE. Until Google verifies the project,
keep YOUTUBE_VERIFIED unset: the connector stays off and Shorts are scheduled in YouTube Studio.
Secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (authorized on the GroundedLabs AI
brand channel UCAXMVkaW4QLdmwrKJW1n_Tw, NOT the personal channel), YOUTUBE_VERIFIED=1.
"""
import requests

from .common import check, env

CHANNEL = "UCAXMVkaW4QLdmwrKJW1n_Tw"


def configured():
    return all(env(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")) and env("YOUTUBE_VERIFIED") == "1"


def access_token():
    return check(requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=30))["access_token"]


def publish(video, post, cfg):
    tok = access_token()
    h = {"Authorization": f"Bearer {tok}"}
    ch = check(requests.get("https://www.googleapis.com/youtube/v3/channels", headers=h,
                            params={"part": "id", "mine": "true"}, timeout=30)).get("items", [])
    if not ch or ch[0]["id"] != CHANNEL:
        raise RuntimeError(f"YouTube token is for the wrong channel: {ch[:1]}")
    data = video.read_bytes()
    meta = {"snippet": {"title": cfg["title"][:100], "description": cfg.get("description", ""), "categoryId": "28"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": bool(post.get("ai_label"))}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos",
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={**h, "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))},
                      json=meta, timeout=60)
    check(r)
    j = check(requests.put(r.headers["Location"], data=data, headers={**h, "Content-Type": "video/mp4"}, timeout=600))
    return {"id": j["id"], "url": f"https://youtube.com/shorts/{j['id']}"}
