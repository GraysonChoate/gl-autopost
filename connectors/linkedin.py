"""LinkedIn company page (urn:li:organization:144086955) via Posts + Videos API.

Needs the Community Management API (w_organization_social) approved on the LinkedIn app.
Secrets: LI_CLIENT_ID, LI_CLIENT_SECRET, LI_REFRESH_TOKEN (365 days) or LI_ACCESS_TOKEN (60 days).
"""
import time

import requests

from .common import check, env

API = "https://api.linkedin.com/rest"
ORG = "urn:li:organization:144086955"


def configured():
    return bool(env("LI_ACCESS_TOKEN") or all(env(k) for k in ("LI_CLIENT_ID", "LI_CLIENT_SECRET", "LI_REFRESH_TOKEN")))


def access_token():
    if env("LI_REFRESH_TOKEN"):
        return check(requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type": "refresh_token", "refresh_token": env("LI_REFRESH_TOKEN"),
            "client_id": env("LI_CLIENT_ID"), "client_secret": env("LI_CLIENT_SECRET")}, timeout=30))["access_token"]
    return env("LI_ACCESS_TOKEN")


def escape(text):
    """LinkedIn 'little text': these characters must be backslash-escaped or the post is cut off."""
    for ch in "\\()[]{}<>|~_*@":
        text = text.replace(ch, "\\" + ch)
    return text


def publish(video, post, cfg):
    h = {"Authorization": f"Bearer {access_token()}", "LinkedIn-Version": env("LI_VERSION", "202609"),
         "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}
    data = video.read_bytes()
    init = check(requests.post(f"{API}/videos?action=initializeUpload", headers=h, json={"initializeUploadRequest": {
        "owner": ORG, "fileSizeBytes": len(data), "uploadCaptions": False, "uploadThumbnail": False}}, timeout=60))["value"]
    urn, etags = init["video"], []
    for part in init["uploadInstructions"]:
        r = requests.put(part["uploadUrl"], data=data[part["firstByte"]:part["lastByte"] + 1],
                         headers={"Content-Type": "application/octet-stream"}, timeout=300)
        check(r)
        etags.append(r.headers["etag"])
    check(requests.post(f"{API}/videos?action=finalizeUpload", headers=h, json={"finalizeUploadRequest": {
        "video": urn, "uploadToken": init.get("uploadToken", ""), "uploadedPartIds": etags}}, timeout=60))
    enc = requests.utils.quote(urn, safe="")
    for _ in range(40):
        if check(requests.get(f"{API}/videos/{enc}", headers=h, timeout=30)).get("status") == "AVAILABLE":
            break
        time.sleep(10)
    else:
        raise RuntimeError("LinkedIn video processing timed out")
    r = requests.post(f"{API}/posts", headers=h, json={
        "author": ORG, "commentary": escape(cfg["text"]), "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"title": post.get("title", ""), "id": urn}},
        "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}, timeout=60)
    check(r)
    pid = r.headers.get("x-restli-id", "")
    return {"id": pid, "url": f"https://www.linkedin.com/feed/update/{pid}"}
