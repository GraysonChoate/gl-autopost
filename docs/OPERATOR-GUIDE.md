# GL Posting Pipeline — Operator Guide (Brandon)
You run Grounded Labs' posting. Grayson hands you **content** (video + caption). You put it in the pipeline. The pipeline posts it, pings your phone, and tells you if anything breaks.

## 1. One-time setup (15 min)
1. Accept Grayson's GitHub invite to **github.com/GraysonChoate/gl-autopost**.
2. Install the **ntfy** app (iPhone/Android) → Subscribe → topic **`gl-1716093c1d53`**. Every heads-up, "Posted", "FAILED" alert lands here.
3. Read the rules (section 6). That's it. You never need passwords or API keys.

## 2. Weekly routine (~20 min/week)
Every **Thursday**, load next Mon–Sun.
1. **Get content from Grayson**: video file + caption (+ keyword like AUDIT/PDF/FIX).
2. **Upload the video**: repo → `videos/` folder → **Add file → Upload files** → drop the .mp4 → *Commit changes*.
   - Name it lowercase-with-dashes: `every-pdf.mp4`.
   - **Must be under 25 MB** (GitHub's browser upload limit). Bigger? Run it through free **HandBrake** → preset *Fast 1080p30* → audio AAC 128 kbps, or ask Claude to compress it.
3. **Add the post**: open `schedule.yaml` → pencil (Edit) → paste the block from `templates/post.yaml` under `posts:` → fill it in → *Commit changes*.
   - A green check appears on the commit within ~1 min = schedule is valid. Red X = open it, it says exactly what's wrong (missing file, banned word, caption too long, link on X).
4. **Get the OK**: send Grayson the title/date/caption. When he says yes, change `approved: false` → `approved: true` and commit. **Nothing posts without this.**
5. Done. 1 hour before each post your phone gets a heads-up. After it posts you get links.

## 3. When things change
| Need | Do this |
|---|---|
| Stop a post | `schedule.yaml` → set `paused: true` on it → commit (works until it has posted) |
| Swap the video | Upload the new file with the same name into `videos/` (replace) |
| Move the date/time | Edit `date:` / `time:` → commit |
| "FAILED" alert | Open the alert → it names the platform + reason. Post that one platform by hand (section 5) and tell Grayson |
| "MISSED" alert | It was 3+ hours late and was skipped on purpose. Post by hand or reschedule |
| Test without posting | Repo → **Actions → autopost → Run workflow** (dry_run = 1 is default; it posts nothing) |

## 4. What posts automatically today
| Platform | Status | What you do |
|---|---|---|
| X | Auto (once keys fixed) | Nothing |
| Instagram + Facebook | Auto once Meta token is added | Nothing |
| TikTok | Waiting on TikTok approval. After: video lands in TikTok **inbox** → you get "ACTION NEEDED" → open TikTok, tap the draft, paste caption, Post (1 min) | Until approved: schedule by hand |
| YouTube | Waiting on Google verification | Schedule by hand in YouTube Studio |
| LinkedIn | Waiting on LinkedIn API approval | Schedule by hand |
The heads-up push lists which platforms are automatic and which are "manual" for every post.

## 5. Posting by hand (fallback)
- **YouTube**: studio.youtube.com → make sure the channel is **GroundedLabs AI** (not Grayson's personal) → Create → Upload → title/description → *Not made for kids* → Visibility → **Schedule** → date, 12:00 PM.
- **TikTok**: tiktok.com/tiktokstudio/upload → upload → caption → **Schedule** (max 10 days ahead) → 12:00 PM. AI label on if AI person.
- **LinkedIn**: Grounded Labs page (admin view) → Start a post → video → text → clock icon → date + 11:30 AM. **Check it says "Posting <right date>" before you hit Schedule.**
- **Meta (IG+FB) / X**: only if the pipeline fails: business.facebook.com → Create reel (posts to both) / x.com → Post → schedule icon.

## 6. Rules (non-negotiable)
1. Nothing goes public without Grayson's OK (`approved: true`).
2. Explainers: only the `_VO` (narration) files from `Social/Explainers/Finals/` (Overnight Shift + F13 are the exceptions).
3. Use Grayson's caption as written. No hype words: AI-powered, transform, revolutionize, agentic, leverage (the checker blocks them).
4. AI label ON only when an AI person/avatar is on screen.
5. X posts: no links (costs 13x). Write "link in bio".
6. Never put passwords or keys in the repo. Keys live only in GitHub Secrets (Grayson).
7. One post per day per platform. Don't stack two on the same day.
8. Deletes only when Grayson asks.

## 7. Posting times (Central)
X 9:00 AM · LinkedIn 11:30 AM · IG, FB, TikTok, YouTube 12:00 PM. Every day incl. weekends.

## 8. Who to ask
Grayson (content + OKs). Claude in the "GL Social Media Manager" project (anything technical: "the pipeline failed", "add a platform", "compress this video").
