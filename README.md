# gl-autopost

Free posting pipeline for Grounded Labs (Instagram + Facebook Reels), run by GitHub Actions.

- `schedule.yaml` — what posts when (edit to add / pause / swap)
- `videos/` — the exact files that get posted
- `autopost.py` — runs every 15 min: 1-hour heads-up push → publish when due → first comments → confirmation or error push
- `state/state.json` — what already went out (so nothing double-posts)

Notifications: ntfy.sh push to Grayson's phone (topic in the `NTFY_TOPIC` secret).

TikTok, YouTube, X, LinkedIn: still scheduled natively in each platform's own scheduler until their API approvals come through.
