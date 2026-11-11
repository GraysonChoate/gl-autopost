#!/usr/bin/env python3
"""One-time sign-ins that turn an app approval into repo secrets. Run on Grayson's Mac.

  python3 tools/auth.py meta       # needs META_APP_ID, META_APP_SECRET, and a short-lived user token from Graph API Explorer
  python3 tools/auth.py tiktok     # needs TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET
  python3 tools/auth.py youtube    # needs YT_CLIENT_ID, YT_CLIENT_SECRET (sign in as the GroundedLabs AI brand channel)
  python3 tools/auth.py linkedin   # needs LI_CLIENT_ID, LI_CLIENT_SECRET

Values are read with getpass (not echoed) and written straight into GitHub secrets with `gh secret set`.
Nothing is printed or saved to disk. Redirect URI to register in each app: https://groundedlabs.ai/
"""
import getpass
import secrets
import subprocess
import sys
import urllib.parse as up

import requests

REPO = "GraysonChoate/gl-autopost"
REDIRECT = "https://groundedlabs.ai/"


def ask(name):
    return getpass.getpass(f"{name}: ").strip()


def put(name, value):
    subprocess.run(["gh", "secret", "set", name, "-R", REPO, "--body", value], check=True)
    print(f"  saved secret {name}")


def code_from_redirect(url):
    print("\n1) Open this link, sign in as Grounded Labs, approve:\n\n" + url + "\n")
    back = input("2) Paste the full address you land on (starts with https://groundedlabs.ai/?code=...): ").strip()
    q = up.parse_qs(up.urlparse(back).query)
    if "code" not in q:
        sys.exit(f"No code in that address: {q}")
    return q["code"][0]


def meta():
    app_id, app_secret = ask("META_APP_ID"), ask("META_APP_SECRET")
    print("Graph API Explorer > app GL Autopost > User token with: pages_show_list, pages_read_engagement,"
          " pages_manage_posts, instagram_basic, instagram_content_publish, instagram_manage_comments, business_management")
    short = ask("short-lived user token")
    long_user = requests.get("https://graph.facebook.com/v25.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
        "fb_exchange_token": short}, timeout=30).json()["access_token"]
    pages = requests.get("https://graph.facebook.com/v25.0/me/accounts", params={
        "fields": "id,name,access_token,instagram_business_account", "access_token": long_user}, timeout=30).json()["data"]
    page = next(p for p in pages if "grounded" in p["name"].lower())
    print(f"Page: {page['name']} ({page['id']})")
    put("META_PAGE_TOKEN", page["access_token"])   # page token from a long-lived user token never expires
    put("FB_PAGE_ID", page["id"])
    put("IG_USER_ID", page["instagram_business_account"]["id"])


def tiktok():
    key, sec = ask("TIKTOK_CLIENT_KEY"), ask("TIKTOK_CLIENT_SECRET")
    url = "https://www.tiktok.com/v2/auth/authorize/?" + up.urlencode({
        "client_key": key, "scope": "user.info.basic,video.upload,video.publish", "response_type": "code",
        "redirect_uri": REDIRECT, "state": secrets.token_hex(8)})
    code = code_from_redirect(url)
    j = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": key, "client_secret": sec, "code": code, "grant_type": "authorization_code",
        "redirect_uri": REDIRECT}, timeout=30).json()
    if "refresh_token" not in j:
        sys.exit(f"TikTok error: {j}")
    put("TIKTOK_CLIENT_KEY", key); put("TIKTOK_CLIENT_SECRET", sec); put("TIKTOK_REFRESH_TOKEN", j["refresh_token"])


def youtube():
    cid, sec = ask("YT_CLIENT_ID"), ask("YT_CLIENT_SECRET")
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + up.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code", "access_type": "offline",
        "prompt": "consent", "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"})
    print("When Google asks which account/channel: pick GroundedLabs AI (not your personal channel).")
    code = code_from_redirect(url)
    j = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": cid, "client_secret": sec, "redirect_uri": REDIRECT,
        "grant_type": "authorization_code"}, timeout=30).json()
    if "refresh_token" not in j:
        sys.exit(f"Google error: {j}")
    put("YT_CLIENT_ID", cid); put("YT_CLIENT_SECRET", sec); put("YT_REFRESH_TOKEN", j["refresh_token"])
    print("Leave YOUTUBE_VERIFIED unset until Google verifies the project (uploads would be private).")


def linkedin():
    cid, sec = ask("LI_CLIENT_ID"), ask("LI_CLIENT_SECRET")
    url = "https://www.linkedin.com/oauth/v2/authorization?" + up.urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT, "state": secrets.token_hex(8),
        "scope": "w_organization_social r_organization_social"})
    code = code_from_redirect(url)
    j = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code", "code": code, "client_id": cid, "client_secret": sec,
        "redirect_uri": REDIRECT}, timeout=30).json()
    if "access_token" not in j:
        sys.exit(f"LinkedIn error: {j}")
    put("LI_CLIENT_ID", cid); put("LI_CLIENT_SECRET", sec)
    if j.get("refresh_token"):
        put("LI_REFRESH_TOKEN", j["refresh_token"])
    else:
        put("LI_ACCESS_TOKEN", j["access_token"]); print("No refresh token: access token lasts 60 days; rerun before it expires.")


if __name__ == "__main__":
    {"meta": meta, "tiktok": tiktok, "youtube": youtube, "linkedin": linkedin}[sys.argv[1]]()
