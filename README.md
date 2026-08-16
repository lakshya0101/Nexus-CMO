# Nexus CMO

**Your Personal Social CMO Network**

Nexus CMO is an AI marketing command center that combines market intelligence, opportunity scoring, strategic planning, content generation, review, publishing, and analytics through a multi-agent CMO network.

---

## Table of Contents

- [The Problem](#the-problem)
- [How Nexus CMO Works](#how-nexus-cmo-works)
- [The Six-Agent CMO Network](#the-six-agent-cmo-network)
- [Opportunity Radar — Deterministic Scoring](#opportunity-radar--deterministic-scoring)
- [AI Providers](#ai-providers)
- [Content Generation](#content-generation)
- [Media & Visual AI](#media--visual-ai)
- [The Command Center UI](#the-command-center-ui)
- [API Reference](#api-reference)
- [Data Model](#data-model)
- [Automation & Scheduling](#automation--scheduling)
- [Security & Safety](#security--safety)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)

---

## The Problem

Running social media marketing well means constantly:

- Monitoring trends across multiple sources
- Figuring out which signals are actually worth acting on
- Deciding what platform and format fit a given opportunity
- Writing content that matches each platform's voice and constraints
- Reviewing that content for quality, safety, and brand fit
- Scheduling and publishing it at the right time
- Tracking what happened afterward, and learning from it

In most teams, this work is spread across a trend-tracking tool, a doc for briefs, a design tool, a scheduler, and a spreadsheet for results — with a person manually gluing every step together.

Nexus CMO collapses that chain into a single pipeline, run by a network of purpose-built agents:

```
MARKET SIGNAL
      ↓
OPPORTUNITY RADAR
      ↓
AI CMO NETWORK  (Scout → Planner → Creator → Reviewer → Publisher → Analyst)
      ↓
CONTENT
      ↓
PUBLISH
      ↓
ANALYTICS
      ↓
LEARN
```

Every signal that comes in is scored, prioritized, turned into a content plan, written, reviewed, (optionally) published, and measured — with the reasoning behind each decision kept transparent, rather than a black-box LLM judgment call.

---

## How Nexus CMO Works

At the center of Nexus CMO is a FastAPI backend (`backend/main.py`) that:

- Serves the single-page Command Center UI (`frontend/index.html`)
- Exposes REST endpoints for the pipeline, content generation, accounts, media, and configuration
- Owns a SQLite database (`socialflow.db`) that stores signals, content plans, posts, accounts, assets, and analytics
- Runs an APScheduler instance that fires the agent pipeline on a fixed daily schedule, and also lets you trigger any stage on demand from the dashboard or the API

The six agents (Scout, Planner, Creator, Reviewer, Publisher, Analyst) live in `backend/agents/` and are coordinated by `backend/agents/orchestrator.py`, which runs them in sequence and tracks live pipeline status for the UI.

---

## The Six-Agent CMO Network

The pipeline is a strict sequence: **Scout → Planner → Creator → Reviewer → Publisher → Analyst**, coordinated by `orchestrator.run_full_pipeline()`.

### Scout — Trend Intelligence (`agents/scout.py`)

Scout gathers raw market signals from two live sources:

- **Hacker News** — pulls top stories from the official Firebase API, keeping stories that either match an AI/tech keyword pattern (GPT, LLM, RAG, transformer, embeddings, and similar terms) or have a high score (> 200 points), even if not AI-specific.
- **GitHub** — scans a configured GitHub user/org's public repos for new repositories created in the last 7 days, and checks each repo's latest release for anything published in the last 24 hours.

Every fetched item is deduplicated by URL and written to the `signals` table with a computed **relevance score** (0–1, based on AI-keyword density in the title/summary). Scout also exposes `calculate_opportunity_score()`, which enriches each signal with a full Opportunity Score breakdown (see below) so the Planner can rank signals before acting on them. Processed signals are flagged so they aren't re-planned.

### Planner — Content Strategy (`agents/planner.py`)

Planner reads Scout's unprocessed, opportunity-ranked signals and decides:

- **Which platforms** to target, using per-platform character limits and capabilities (`PLATFORM_FORMATS`: LinkedIn, X, Discord, Instagram, Reddit, Facebook)
- **How much to post**, enforcing daily caps per platform (`DEFAULT_LIMITS`) so no channel gets flooded
- **What priority** the resulting content plan gets — priority is derived directly from the Opportunity Score (`priority = min(10, max(1, round(opportunity_score / 10)))`), so a 92/100 opportunity outranks a 45/100 one automatically, without an LLM guessing at "what's hot"

Routing logic (as implemented):

| Signal condition | Behavior |
|---|---|
| News, Opportunity ≥ 60 (or relevance > 0.3, or raw score > 100) | Multi-platform push: Discord + LinkedIn (11 AM window) + X |
| News, Opportunity ≥ 40 (or relevance > 0.1) | Discord only, at reduced priority |
| Repo / release signal | Discord + LinkedIn + Reddit, at boosted priority (minimum 7) |

Each plan is written to `content_plans` with a signal reference, platform, content type, priority, and a human-readable brief (e.g. `[High Opp: 82/100] News post about: ...`).

### Creator — Content Generation (`agents/creator.py`)

Creator turns pending plans into drafts:

- Builds a prompt per plan using platform- and content-type-specific templates (`PLATFORM_PROMPTS`) — separate instructions exist for `ai-news` and `repo-promo` content across LinkedIn, X, Discord, and Reddit, each tuned to that platform's length and tone conventions
- Injects the brand voice (tone, banned phrases) from `brand_config`, and prepends a list of banned filler phrases (e.g. "game-changer," "dive deep," "cutting-edge") that the model is instructed to avoid
- Calls the configured AI provider through an injected `ai_generate_fn` (wired to `generate_content_ai` in `main.py`), so the Creator agent itself is provider-agnostic
- Cleans the raw model output — stripping `<think>` blocks, markdown code fences, and "Here's your post:"-style preambles
- Saves the result as a `draft` row in `posts`

If no AI function is supplied, Creator falls back to a plain templated post built from the signal's title/summary/URL, so the pipeline never silently fails.

### Reviewer — Quality & Compliance (`agents/reviewer.py`)

Every draft passes through a deterministic, regex-based gate before it can go out:

1. **Credential leak check** — blocks the post outright if it matches API-key, token, or password patterns (OpenAI `sk-...`, GitHub `ghp_...`, Slack `xoxb-...`, etc.)
2. **Metadata leak check** — blocks posts that accidentally include internal pipeline fields (`approval_level:`, `risk_score:`, stray JSON/YAML)
3. **Fabricated-claim check** — flags (does not block) unverified superlatives and statistics like "95% improvement" or "millions of users"
4. **Brand voice check** — flags corporate clichés ("game-changer," "synergy," "move the needle")
5. **Length check** — flags content exceeding the platform's max character count
6. **Minimum length check** — blocks anything under 20 characters as unusable

Decision logic: any credential or metadata match is an automatic **block**. Three or more accumulated warnings send the post to manual **review**. Anything else with zero or few warnings is **auto-approved**, with the warnings attached as notes for visibility. This keeps quality/safety review deterministic and auditable rather than dependent on an LLM's judgment call.

### Publisher — Distribution (`agents/publisher.py`)

Publisher picks up `approved` posts and ships them:

- For most platforms, it uses **Playwright browser automation** (`automation.py` / `automation_extended.py`) — loading a saved session, typing the content into the platform's native composer, attaching media if present, and clicking post
- For **Discord**, it posts via a webhook (stored, encrypted, in the `accounts` table) instead of a browser, since Discord doesn't require a full login flow
- Failed posts are retried at the next publish window and marked with an error message rather than silently dropped; a missing session produces a clear "login required" failure rather than a crash

Publishing can happen automatically at scheduled windows, or on demand via the dashboard/API for a single post.

### Analyst — Performance & Learning (`agents/analyst.py`)

Analyst closes the loop:

- Aggregates daily posting stats per platform and status (draft/approved/posted/failed/review/blocked)
- Computes a daily and 7-day rolling **success rate** (`posted / (posted + failed)`)
- Surfaces the most recently published posts for the dashboard
- Its output feeds the `/api/pipeline/analytics` endpoint and the Performance page in the UI

Nexus CMO does not currently feed Analyst's output back into Planner's scoring automatically — that link is manual today (a human reviewing the Performance page and adjusting strategy), not an autonomous feedback loop.

---

## Opportunity Radar — Deterministic Scoring

The Opportunity Radar is what makes Nexus CMO's prioritization **transparent and reproducible** instead of "the AI decided this was trending." Every signal gets a 0–100 score computed from five weighted, code-defined factors — no LLM is involved in this calculation:

```
Opportunity Score = round(
    Relevance             (max 30 pts)
  + Trend Momentum        (max 25 pts)
  + Audience Fit          (max 20 pts)
  + Engagement Potential  (max 15 pts)
  + Content Gap           (max 10 pts)
)
```

| Factor | Weight | What it measures | How it's computed |
|---|---|---|---|
| **Relevance** | 30 pts | How on-topic the signal is for an AI/tech audience | Density of AI-related keywords (GPT, LLM, RAG, transformer, embeddings, etc.) in the title + summary |
| **Trend Momentum** | 25 pts | How much real-world traction the signal already has | Hacker News score is scaled non-linearly (bigger jumps above 100–250 points); GitHub repos/releases start from a higher floor since star counts accrue more slowly than HN votes |
| **Audience Fit** | 20 pts | Whether the signal speaks to builders, developers, and founders | Matches against terms like "open-source," "framework," "API," "benchmark," "deploy" — with a higher baseline for GitHub-sourced signals |
| **Engagement Potential** | 15 pts | Whether the headline itself is likely to hook a reader | Presence of hooks like "Show HN," "Launch," "vs," a question mark, or a number, plus a bonus for an optimal title length (30–90 characters) |
| **Content Gap** | 10 pts | Whether this topic is fresh or already covered | Compares the signal's title against the last 15 published posts; word overlap with 3+ recent posts drags the score down, zero overlap maxes it out |

The final integer score maps to a human-readable label:

| Score | Label |
|---|---|
| 90–100 | Exceptional |
| 75–89 | High |
| 60–74 | Promising |
| 40–59 | Moderate |
| 0–39 | Low |

**Why this matters:** the score and its five-part breakdown are stored and displayed alongside every signal, so you can see *exactly* why something ranked where it did — and the same signal will always score the same way, run after run. This score then drives Planner's priority directly (`priority = min(10, max(1, round(score / 10)))`), so higher-opportunity signals are guaranteed to be planned and surfaced ahead of lower ones, without relying on an LLM's inconsistent notion of "what's trending."

---

## AI Providers

Content generation is provider-agnostic. `generate_content_ai()` in `main.py` reads `AI_PROVIDER` from the environment and routes to one of four backends:

| Provider | Env var | Model used | Notes |
|---|---|---|---|
| **Ollama** (default) | `AI_PROVIDER=ollama` | `OLLAMA_MODEL` (default `qwen3:8b`) via `OLLAMA_URL` | Free, local, no API key. Strips `<think>` reasoning tags automatically. Raises a clear error if Ollama isn't running. |
| **OpenAI** | `AI_PROVIDER=openai` | `gpt-4o` | Requires `OPENAI_API_KEY`. Distinguishes invalid-key vs. no-credit errors. |
| **Anthropic** | `AI_PROVIDER=anthropic` | `claude-haiku-4-5-20251001` | Requires `ANTHROPIC_API_KEY`. |
| **Google Gemini** | `AI_PROVIDER=gemini` | `gemini-3.6-flash` | Requires `GEMINI_API_KEY`. |

If `AI_PROVIDER` doesn't match `anthropic`, `gemini`, or `ollama`, the code falls back to the OpenAI path. Each provider function raises an informative `HTTPException` (missing key, invalid key, insufficient credit) rather than failing silently.

Image generation is separate and always goes through OpenAI's image API (configurable via `IMAGE_MODEL`, default `gpt-image-1.5`), used for carousel slide art.

No API keys are ever returned by any endpoint — `/api/config` only reports whether each key is *configured* (boolean), never its value.

---

## Content Generation

### `POST /api/generate` — general content

Accepts:

```json
{
  "topic": "string",
  "platform": "linkedin | instagram | twitter",
  "content_type": "post | carousel | reel | thread",
  "slides": 5,
  "custom_instructions": "optional string"
}
```

The backend builds a platform-aware prompt (tone tips per platform, format instructions per content type), sends it to the configured AI provider, and returns the generated text with a timestamp.

### `POST /api/generate-carousel` — image + text carousel

Generates slide copy as structured JSON (headline, body, image prompt per slide) via the text model, then generates one AI image per slide, saving each locally under `/uploads` and returning the full slide set plus a caption.

### `POST /api/generate-video` / `POST /api/generate-reel` — Kling AI video

Video generation is powered by the `KlingAI` class in `main.py`, which calls Kling's `text2video`, `image2video`, `avatar`, and `lip-sync` endpoints (requires `KLING_API_KEY`). `generate-reel` first writes a script via the text provider, then submits a vertical (9:16) video generation job and returns a `task_id` you poll via `GET /api/video-status/{task_id}`.

### `POST /api/generate-avatar` / `POST /api/generate-avatar-with-script` — talking avatar video

Combines a user photo (or uploaded image) with either a supplied script or a generated one, and produces a lip-synced avatar video job through Kling AI.

All generation endpoints that produce media save files under `backend/uploads/`, served at `/uploads/...`.

---

## Media & Visual AI

Beyond the Kling-based video pipeline, Nexus CMO has three additional visual/media systems:

- **HeyGen integration** (`heygen_adapter.py`, `heygen_routes.py`) — treats HeyGen as a native, browser-automated video generation engine (not a bolt-on script). Jobs move through a defined state machine (`draft → queued → generating → completed → failed → ready_for_distribution`), tracked in `heygen_jobs.json`. Once a video is registered as an asset, `generate_platform_variants()` produces platform-specific distribution metadata (aspect ratio, max duration, caption style) for Instagram, YouTube, LinkedIn, X, Discord, Reddit, and article embeds.
- **Visual content briefs** (`visual_content_routes.py`) — generates carousel packs, quote cards, thumbnails, story frames, AI image prompts, and full "creative packs" by shelling out to an external `visual-brief-generator.sh` script (expected outside this repo, under `openclaw-engine/scripts/`) and registering the resulting file as an asset. If that script isn't present, these endpoints return a clear 500 error rather than failing silently.
- **Asset inventory** (`asset_inventory.py`) — a lightweight digital asset manager. Every generated video, image, or brief — regardless of source — is registered with metadata (type, source, campaign, topic, tags) so it can be tracked, queried, and routed into the platform-specific `content_queue`.
- **Brand Kit** (`brand_kit.py`) — stores brand colors, fonts, tone, forbidden visual styles, per-platform hashtag sets, a CTA template, and a product list, all of which get pulled into content and image-generation prompts so output stays on-brand.

---

## The Command Center UI

The frontend (`frontend/index.html`) is a single-file React app (loaded via CDN, no build step) styled as a dark, cinematic operations dashboard rather than a simple form-based content generator. Confirmed sections, grouped as they appear in the nav:

**Command Center**
- **Overview** — live stats (signals discovered, opportunities found, content generated, network status), the current top Opportunity Score with its five-factor breakdown, an animated Agent Network diagram showing each agent's live status, recent intelligence, and a content pipeline preview.
- **Opportunity Radar** — the full ranked list of scored signals, each with its score, label, and factor breakdown.
- **Agent Network** — a detailed view of all six agents with role descriptions and live status (Active / Monitoring / Ready).

**Content**
- **Create Content** — the general-purpose generator (`/api/generate`)
- **Carousel Maker** — multi-slide carousel generation with style presets (Modern, Bold, Colorful, Minimal)
- **Video/Reel Maker** — script + Kling AI video generation with duration, aspect ratio, and style controls
- **Avatar Videos** — talking-avatar generation from a photo, with voice and tone options
- **Content Library** — the full posts queue (draft/approved/posted/failed) with status indicators

**Analytics**
- **Performance** — daily and weekly stats sourced from the Analyst agent

**System**
- **Accounts** — connect/manage credentials and login state per platform
- **Settings** — AI provider and API key configuration

The visual language leans into the "AI marketing command center" framing intentionally: a dark theme with an electric-blue accent, a radar-style opportunity score visualization, an animated multi-node agent graph, and live status badges — rather than a plain content-generation form.

---

## API Reference

All endpoints are served from `backend/main.py` unless otherwise noted. Interactive docs are available at `/docs` (FastAPI's built-in Swagger UI) once the server is running.

### Health / Frontend

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the Command Center UI |
| GET | `/api/health` | Basic liveness check |

### Pipeline

| Method | Path | Description |
|---|---|---|
| POST | `/api/pipeline/run` | Runs the full pipeline (Scout → Planner → Creator → Reviewer) in the background; publishing is skipped by default so content lands in the review queue |
| GET | `/api/pipeline/status` | Current pipeline run state (`running`, `current_agent`, `last_run`, `last_result`, `error`) |
| GET | `/api/pipeline/queue` | Content queue, filterable by `status_filter` and `platform` |
| POST | `/api/pipeline/approve/{post_id}` | Manually approve a draft/review post |
| POST | `/api/pipeline/reject/{post_id}` | Mark a post as blocked |
| POST | `/api/pipeline/publish/{post_id}` | Publish a specific approved post immediately, in the background |
| GET | `/api/pipeline/signals` | Recent Scout signals, enriched with Opportunity Score |
| GET | `/api/pipeline/analytics` | Today's + this week's stats from the Analyst agent |

Example — approve a reviewed post:

```bash
curl -X POST http://localhost:8000/api/pipeline/approve/42
# → {"status": "approved", "post_id": 42}
```

### Content Generation

| Method | Path | Description |
|---|---|---|
| POST | `/api/generate` | General post/carousel-brief/reel-script/thread text generation |
| POST | `/api/generate-carousel` | Full carousel: slide copy + AI-generated slide images |
| POST | `/api/generate-video` | Kling AI text-to-video or image-to-video |
| GET | `/api/video-status/{task_id}` | Poll a Kling video generation job |
| POST | `/api/generate-reel` | Script + vertical video for Reels/Shorts |
| POST | `/api/generate-avatar` | Talking avatar video from a photo + script/audio |
| POST | `/api/generate-avatar-with-script` | Generate a speaking script for avatar video |
| POST | `/api/upload-avatar-photo` | Upload a source photo for avatar generation |
| POST | `/api/upload-audio` | Upload custom audio for lip-sync |

### Posts

| Method | Path | Description |
|---|---|---|
| GET | `/api/posts` | List posts, filterable by `status` and `platform` |
| POST | `/api/posts` | Create a post (draft or scheduled) |
| PUT | `/api/posts/{post_id}` | Update content, status, or schedule |
| DELETE | `/api/posts/{post_id}` | Delete a post and cancel any scheduled job |
| POST | `/api/posts/{post_id}/publish` | Publish immediately via standard automation |
| POST | `/api/posts/{post_id}/publish-extended` | Publish via the extended platform set (Facebook, Reddit, Medium, Substack, HeyGen, email platforms) |

### Accounts

| Method | Path | Description |
|---|---|---|
| GET | `/api/accounts` | List connected accounts (credentials never returned) |
| POST | `/api/accounts` | Add/update encrypted credentials for a platform |
| POST | `/api/accounts/{platform}/login` | Log in via Playwright (LinkedIn, Instagram, X) and persist the session |
| POST | `/api/accounts/{platform}/login-extended` | Log in via the extended platform set |
| POST | `/api/accounts/{platform}/check` | Verify an existing session is still valid |
| DELETE | `/api/accounts/{platform}` | Remove an account and its saved session |

### Media

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Generic media file upload |
| POST | `/api/upload-avatar-photo` | Avatar source photo upload |
| POST | `/api/upload-audio` | Audio upload for lip-sync |

### Configuration

| Method | Path | Description |
|---|---|---|
| GET | `/api/config` | Which providers/keys are configured (booleans only) |
| POST | `/api/config` | Update provider/key configuration at runtime |

### Sub-routers

These are mounted separately and prefixed accordingly:

| Prefix | File | Purpose |
|---|---|---|
| `/api/brand` | `brand_kit.py` | Brand colors, fonts, tone, hashtags, products, logo upload |
| `/api/analytics` | `analytics_store.py` | Post-publish performance metrics, weekly summaries, top content types/pillars |
| `/api/visual` | `visual_content_routes.py` | Visual brief generation (carousels, quote cards, thumbnails, creative packs) |
| `/api/heygen` | `heygen_routes.py` | HeyGen job lifecycle, asset registration, platform distribution, content queue |
| `/api/openclaw` | `openclaw_bridge.py` | External bridge for pushing pre-approved content into Nexus CMO's publishing layer |

---

## Data Model

Nexus CMO uses SQLite (`backend/socialflow.db`), created automatically on first run. Key tables:

**`signals`** (Scout's output) — `id`, `source`, `title`, `url`, `summary`, `score`, `relevance_score`, `source_date`, `fetched_at`, `processed`, `signal_type` (`news` / `repo` / `release`).

**`content_plans`** (Planner's output) — `id`, `signal_id`, `platform`, `content_type`, `priority`, `scheduled_hour`, `status` (`planned` / `completed`), `brief`, `created_at`.

**`posts`** (Creator/Reviewer/Publisher's shared table) — `id`, `platform`, `content_type`, `content`, `media_paths`, `scheduled_time`, `status` (`draft` → `approved`/`review`/`blocked` → `posted`/`failed`), `post_id` (external URL/ID once published), `error_message`, `created_at`, `published_at`.

**`accounts`** — `id`, `platform`, `username`, `password_encrypted` (Fernet), `is_logged_in`, `last_login`. For Discord, the encrypted field stores the webhook URL instead of a password.

**`brand_config`** — brand name, tagline, color palette, fonts, tone, forbidden visual styles, per-platform hashtag sets, CTA template, product list.

**`assets`** / **`content_queue`** / **`campaigns`** (`asset_inventory.py`) — the digital asset manager backing HeyGen videos and visual briefs, and the platform-specific distribution queue that feeds off it.

**`post_metrics`** / **`weekly_metrics`** / **`content_insights`** (`analytics_store.py`) — the performance-tracking schema: per-post engagement metrics (impressions, reach, likes, comments, shares, saves, video views, computed engagement rate), weekly rollups, and content-type/pillar performance rankings.

---

## Automation & Scheduling

Scheduling is handled by APScheduler, configured in `main.py`'s `lifespan` startup hook. Jobs fire on a fixed daily cron schedule; nothing runs continuously in the background beyond these triggers:

| Time | Job | What it does |
|---|---|---|
| 8:07 AM | `daily_pipeline_morning` | Full pipeline (Scout → Planner → Creator → Reviewer), publishing skipped so content lands in the review queue |
| 2:00 PM | `afternoon_scout` | Scout only — refreshes signals mid-day |
| 11:00 AM | `publish_11am` | Publishes all currently-approved posts |
| 11:00 PM | `publish_11pm` | Publishes all currently-approved posts |
| 11:30 PM | `daily_analyst` | Generates the daily analytics report |

Any stage can also be triggered manually — `POST /api/pipeline/run` for the full pipeline, or by calling the individual agent's `run()` function. Individually scheduled posts (created via `POST /api/posts` with a `scheduled_time`) get their own one-off APScheduler `DateTrigger` job, which is restored on server restart from any `posts` rows still in `scheduled` status.

Nexus CMO's agents are **scheduled, triggerable jobs** — not continuously running autonomous processes. Each run completes and exits; nothing is "always thinking" between runs.

---

## Security & Safety

- All platform credentials are encrypted at rest with **Fernet** (`cryptography` library) using a key generated on first run and stored in `.secret_key` — never commit this file.
- `.env` and `.secret_key` are both listed in `.gitignore`; API keys should live only in your local `.env`, never in source control.
- The Reviewer agent's credential/metadata leak gates run on every piece of generated content before it can be approved, catching accidentally-embedded API keys, tokens, or internal pipeline metadata.
- Publishing (both scheduled and on-demand) only acts on posts already in `approved` status — content generated by Creator always lands as a `draft` and must clear Reviewer (or a human, via `/api/pipeline/approve`) first.
- No endpoint returns raw API keys or account passwords; `/api/config` and `/api/accounts` report configuration/connection state only.

---

## Getting Started

### Requirements

- **Python 3.10+**
- No Node.js or npm required — the frontend is a single static HTML file that loads React from a CDN at runtime.
- [Playwright](https://playwright.dev/python/) Chromium browser (installed via a one-time `playwright install` step, see below)
- Optional: a local [Ollama](https://ollama.ai) install if you want free, local text generation instead of a cloud provider

### Clone

```bash
git clone https://github.com/lakshya0101/Nexus-CMO.git
cd Nexus-CMO
```

### Configure

```bash
cp .env.example .env
# Edit .env: choose AI_PROVIDER (ollama | openai | anthropic | gemini)
# and add the matching API key if you're not using ollama
```

### Run

The included `start.sh` handles virtual environment creation, dependency installation, and first-time Playwright browser setup automatically:

```bash
chmod +x start.sh
./start.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium

cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

- **Dashboard:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

On first launch, Nexus CMO creates `socialflow.db`, starts the scheduler, and begins running the six-agent pipeline on the schedule described above. You can also trigger a run immediately from the Command Center's "Run Pipeline" action or via `POST /api/pipeline/run`.

### Connecting a platform

For LinkedIn, Instagram, or X: add credentials via the **Accounts** page (or `POST /api/accounts`), then trigger login (`POST /api/accounts/{platform}/login`) with a visible browser the first time, so you can complete any 2FA/security checks manually. The session is saved and reused for subsequent headless publishing. Discord only needs a webhook URL, not a login.

---

## Project Structure

```
Nexus-CMO/
├── backend/
│   ├── main.py                    # FastAPI app, routes, AI providers, scheduler
│   ├── automation.py              # Playwright automation: LinkedIn, Instagram, X
│   ├── automation_extended.py     # Facebook, Reddit, Medium, Substack, Discord, HeyGen, email
│   ├── analytics_store.py         # Post-publish metrics schema + /api/analytics routes
│   ├── asset_inventory.py         # Digital asset manager + content distribution queue
│   ├── brand_kit.py                # Brand identity config + /api/brand routes
│   ├── visual_content_routes.py   # Visual brief generation + /api/visual routes
│   ├── heygen_adapter.py          # HeyGen job state machine + browser automation
│   ├── heygen_routes.py           # /api/heygen routes
│   ├── openclaw_bridge.py         # External publish bridge + /api/openclaw routes
│   ├── requirements.txt
│   └── agents/
│       ├── scout.py               # Signal ingestion + Opportunity Score
│       ├── planner.py             # Prioritization + platform routing
│       ├── creator.py             # AI content generation
│       ├── reviewer.py            # Safety/quality gates
│       ├── publisher.py           # Distribution (Playwright + Discord webhook)
│       ├── analyst.py             # Performance tracking
│       └── orchestrator.py        # Pipeline coordination
├── frontend/
│   └── index.html                 # Command Center UI (React via CDN, single file)
├── configs/                        # Reserved for future config files
├── .env.example
└── start.sh                        # One-command setup + run
```
