# Course Website (`docs/`)

A static site to take the course in a browser: watch lesson videos (YouTube),
and open each exercise/project in Google Colab. It uses **no build step and no
server** — just HTML/CSS/JS — so it runs on GitHub Pages for free and uses almost
none of your computer's processor (video streams from YouTube; exercises run on
Colab's compute, not yours).

## Files

| File | Purpose |
|---|---|
| `index.html`, `style.css`, `app.js` | The site itself (vanilla JS, no dependencies) |
| `course.json` | Generated manifest of all 100 days → lessons/exercises/project |
| `videos.json` | **You edit this** — maps each lesson to its YouTube video ID |

`course.json` is produced by `../tools/build_site_manifest.py` — don't edit it by hand.

## Preview locally

```bash
cd docs
python3 -m http.server 8137
# open http://localhost:8137
```

## Add a lesson's video

### Automated (recommended)

Once a lesson is rendered to `00_pipeline/final/<lesson_id>_final.mp4`, one command
uploads it to YouTube (unlisted), writes the returned ID into `videos.json`, and
regenerates the manifest:

```bash
python tools/youtube_upload.py day_001_lesson_01   # one lesson
python tools/youtube_upload.py --day 1             # all 5 lessons of a day
python tools/youtube_upload.py --all-local         # every rendered final/*.mp4
```

Credentials come from a gitignored `.env` (`YOUTUBE_REFRESH_TOKEN`,
`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`). The refresh token must carry the
`https://www.googleapis.com/auth/youtube.upload` scope.

Add `--push` to also commit and push `docs/` so a GitHub Pages site updates with
no further steps (uses your git remote, or a `GITHUB_TOKEN` env var if set):

```bash
python tools/youtube_upload.py --day 1 --push
```

Or skip your machine entirely: **[`../00_pipeline/render_and_publish_colab.ipynb`](../00_pipeline/render_and_publish_colab.ipynb)**
renders, uploads, **and pushes the site** fully on Colab — give it a GitHub token
(Colab Secret `GITHUB_TOKEN`, fine-grained, *Contents: read/write*) and one
`render_and_publish(day, lesson)` call updates your live site with nothing run locally.

### Manual

1. Render the lesson (`../00_pipeline/RENDERING.md`) → `00_pipeline/final/<lesson_id>_final.mp4`.
2. Upload that MP4 to YouTube as **Unlisted**.
3. Copy the video ID from its URL (`youtube.com/watch?v=`**`THIS_PART`**).
4. Put it in `videos.json`, e.g. `"day_001_lesson_01": "dQw4w9WgXcQ"`.
5. `python3 tools/build_site_manifest.py`, then refresh the page.

Lessons without an ID show a "not rendered yet" placeholder, so you can ship the
site and fill videos in over time.

## Deploy to GitHub Pages (free hosting)

1. Commit and push `docs/` to the `main` branch.
2. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a
   branch → Branch: `main` / folder: `/docs` → Save.**
3. After a minute the course is live at
   `https://<your-user>.github.io/<repo>/` — open it from any browser, anywhere.

> "Open in Colab" buttons open the notebooks straight from this GitHub repo, so
> the repo must be **public** (or you must be signed in to a Google account with
> access). Notebooks must be committed and pushed to `main`.

## Progress tracking

Checkboxes (lesson watched / exercise done / project / day complete) are saved in
your browser's `localStorage` — private to that browser, nothing is uploaded.
