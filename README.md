# gl-autopost

**Running the posting? Start here: [docs/OPERATOR-GUIDE.md](docs/OPERATOR-GUIDE.md)** · Template for a new post: [templates/post.yaml](templates/post.yaml)

Grounded Labs' own posting system (replaces paid schedulers). Runs free on GitHub Actions.

| File | What it does |
|---|---|
| `schedule.yaml` | The calendar. One entry per post. `approved: true` = Grayson OK'd it. `paused: true` stops it. |
| `videos/` | Exact upload files (make them with `tools/prep_video.sh`). |
| `autopost.py` | Every 15 min: 1-hour heads-up push → publish when due → "Posted"/"FAILED" push. |
| `validate.py` | Blocks bad posts: missing file, non-VO explainer, banned words, too-long captions, links on X. |
| `connectors/` | One file per platform: `meta.py` (IG+FB), `x.py`, `tiktok.py`, `youtube.py`, `linkedin.py`. |
| `state/state.json` | What already went out, so nothing double-posts. |
| `tools/auth.py` | One-time sign-ins that write tokens straight into repo secrets. |

## Safety rules built in
- Nothing posts unless `approved: true`.
- Every slot gets a heads-up push; a post never goes out less than 50 min after its heads-up.
- Over 3 h late → no post, "MISSED" alert instead.
- A platform with no keys is skipped and shown as "manual" in the heads-up.
- Manual run from the Actions tab defaults to dry run.

## Platform status
| Platform | Connector | Goes live when |
|---|---|---|
| Instagram, Facebook | built | Meta app created + `tools/auth.py meta` |
| X | built | X dev app + credits + 4 keys in secrets |
| TikTok | built (upload mode: draft lands in inbox, tap Post) | TikTok app approved + `tools/auth.py tiktok`; public auto-post after Direct Post audit (`TIKTOK_DIRECT_OK=1`) |
| YouTube | built | Google verifies the project → `tools/auth.py youtube` + `YOUTUBE_VERIFIED=1` |
| LinkedIn | built | Community Management API approved → `tools/auth.py linkedin` |

## Secrets (Settings → Secrets and variables → Actions)
`NTFY_TOPIC` · `META_PAGE_TOKEN` `FB_PAGE_ID` `IG_USER_ID` · `X_API_KEY` `X_API_SECRET` `X_ACCESS_TOKEN` `X_ACCESS_SECRET` ·
`TIKTOK_CLIENT_KEY` `TIKTOK_CLIENT_SECRET` `TIKTOK_REFRESH_TOKEN` `TIKTOK_DIRECT_OK` ·
`YT_CLIENT_ID` `YT_CLIENT_SECRET` `YT_REFRESH_TOKEN` `YOUTUBE_VERIFIED` · `LI_CLIENT_ID` `LI_CLIENT_SECRET` `LI_REFRESH_TOKEN`

## Test a post
Actions → autopost → Run workflow → `only_post` = the id, `only_platforms` = e.g. `x`, `dry_run` = 0 (only with Grayson's OK).
