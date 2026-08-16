"""
Scout Agent — Intelligence Gathering

Responsibilities:
  - Fetch AI news from Hacker News API + RSS feeds
  - Scan InBharat GitHub repos for new releases
  - Identify trending topics
  - Store signals in SQLite for Planner agent

Runs: 8 AM, 2 PM, 8 PM daily (via orchestrator)
"""

import re
import json
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import httpx

# AI relevance keywords
AI_KEYWORDS = [
    r'\bAI\b', r'\bartificial intelligence\b', r'\bLLM\b', r'\bGPT\b',
    r'\bClaude\b', r'\bAnthropic\b', r'\bOpenAI\b', r'\bGemini\b',
    r'\bmachine learning\b', r'\bdeep learning\b', r'\bneural net',
    r'\bNLP\b', r'\bRAG\b', r'\btransformer\b', r'\bfine-tun',
    r'\bprompt\b', r'\bchatbot\b', r'\bautonomous agent',
    r'\bcomputer vision\b', r'\bMLOps\b', r'\bvector',
    r'\bembedding\b', r'\bOllama\b', r'\bHugging\s*Face\b',
    r'\bMistral\b', r'\bLlama\b', r'\bStable\s*Diffusion\b',
    r'\bMidjourney\b', r'\bCopilot\b', r'\bCodex\b',
]
AI_PATTERN = re.compile('|'.join(AI_KEYWORDS), re.IGNORECASE)

# Audience fit keywords for builders, developers, founders, AI practitioners
AUDIENCE_KEYWORDS = [
    r'\bopen[- ]source\b', r'\bgithub\b', r'\brepo\b', r'\brelease\b',
    r'\bframework\b', r'\blibrary\b', r'\bdeveloper\b', r'\bengineer\b',
    r'\bbuilder\b', r'\bstartup\b', r'\bfounder\b', r'\btool\b',
    r'\bagent\b', r'\brag\b', r'\bbenchmark\b', r'\bweights\b',
    r'\bapi\b', r'\barchitecture\b', r'\bdeploy\b', r'\binference\b',
    r'\bmodel\b', r'\bpython\b', r'\brust\b', r'\bcuda\b'
]
AUDIENCE_PATTERN = re.compile('|'.join(AUDIENCE_KEYWORDS), re.IGNORECASE)

# Engagement triggers: questions, announcements, comparisons, listicles
ENGAGEMENT_TRIGGERS = [
    r'\bshow hn\b', r'\blaunch\b', r'\brelease\b', r'\bannouncing\b',
    r'\bhow to\b', r'\bwhy\b', r'\bvs\b', r'\bguide\b', r'\btutorial\b',
    r'\bbreakthrough\b', r'\bfastest\b', r'\bnew\b', r'\bfree\b',
    r'\?\s*$', r'\b\d+\b'
]
ENGAGEMENT_PATTERN = re.compile('|'.join(ENGAGEMENT_TRIGGERS), re.IGNORECASE)

DB_PATH = Path(__file__).parent.parent / "socialflow.db"


# ============== OPPORTUNITY SCORING (Nexus CMO) ==============
"""
Conceptual Scoring Model:
  Opportunity Score =
    Relevance              30% (AI & tech keyword density / domain alignment)
    Trend Momentum         25% (Upvotes/stars velocity and source freshness)
    Audience Fit           20% (Alignment with builders, developers & founders)
    Engagement Potential   15% (Hook strength, headline structure & optimal length)
    Content Gap            10% (Novelty vs recent post history)

Label Mapping:
  90–100 = "Exceptional"
  75–89  = "High"
  60–74  = "Promising"
  40–59  = "Moderate"
  0–39   = "Low"
"""

def get_opportunity_label(score: int) -> str:
    """Map a 0-100 Opportunity Score to a human-readable label."""
    if score >= 90:
        return "Exceptional"
    elif score >= 75:
        return "High"
    elif score >= 60:
        return "Promising"
    elif score >= 40:
        return "Moderate"
    else:
        return "Low"


def _estimate_content_gap(title: str) -> float:
    """Estimate content gap (1.0 = highly novel, 0.2 = recently saturated)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        recent_posts = conn.execute(
            "SELECT content FROM posts ORDER BY created_at DESC LIMIT 15"
        ).fetchall()
        conn.close()

        if not recent_posts:
            return 0.9  # Fresh repository / high gap

        title_words = set(re.findall(r'\b\w{4,}\b', title.lower()))
        if not title_words:
            return 0.8

        overlap_count = 0
        for (post_content,) in recent_posts:
            post_words = set(re.findall(r'\b\w{4,}\b', (post_content or "").lower()))
            if len(title_words.intersection(post_words)) >= 2:
                overlap_count += 1

        if overlap_count == 0:
            return 1.0
        elif overlap_count <= 2:
            return 0.70
        else:
            return 0.35
    except Exception:
        return 0.80


def calculate_opportunity_score(signal: Dict) -> Tuple[int, str, Dict[str, float]]:
    """
    Calculate a deterministic 0-100 Opportunity Score for a signal.
    
    Returns:
        (total_score: int, label: str, breakdown: Dict[str, float])
    """
    title = signal.get("title", "") or ""
    summary = signal.get("summary", "") or ""
    full_text = f"{title} {summary}".strip()
    score_val = signal.get("score", 0) or 0
    signal_type = signal.get("signal_type", "news")
    source = signal.get("source", "") or ""

    # 1. Relevance (30% weight, max 30.0 pts)
    rel_raw = signal.get("relevance_score")
    if rel_raw is None or rel_raw == 0.0:
        rel_raw = _compute_relevance(full_text)
    relevance_norm = min(1.0, max(0.0, float(rel_raw)))
    relevance_pts = relevance_norm * 30.0

    # 2. Trend Momentum (25% weight, max 25.0 pts)
    if signal_type in ("repo", "release") or source.lower() == "github":
        momentum_norm = min(1.0, max(0.60, (score_val / 100.0) if score_val else 0.75))
    else:
        if score_val >= 250:
            momentum_norm = 1.0
        elif score_val >= 100:
            momentum_norm = 0.75 + (score_val - 100) / 600.0
        elif score_val >= 30:
            momentum_norm = 0.40 + (score_val - 30) / 200.0
        else:
            momentum_norm = max(0.15, score_val / 100.0)
    trend_momentum_pts = min(1.0, max(0.0, momentum_norm)) * 25.0

    # 3. Audience Fit (20% weight, max 20.0 pts)
    aud_matches = len(AUDIENCE_PATTERN.findall(full_text))
    if signal_type in ("repo", "release") or "github" in source.lower():
        aud_norm = min(1.0, 0.65 + (aud_matches * 0.12))
    else:
        aud_norm = min(1.0, 0.30 + (aud_matches * 0.15))
    audience_fit_pts = aud_norm * 20.0

    # 4. Engagement Potential (15% weight, max 15.0 pts)
    eng_matches = len(ENGAGEMENT_PATTERN.findall(title))
    title_len = len(title)
    len_bonus = 0.20 if (30 <= title_len <= 90) else 0.05
    eng_norm = min(1.0, 0.35 + (eng_matches * 0.15) + len_bonus)
    engagement_pts = eng_norm * 15.0

    # 5. Content Gap (10% weight, max 10.0 pts)
    gap_norm = _estimate_content_gap(title)
    content_gap_pts = gap_norm * 10.0

    # Total combined score (0-100)
    total_pts = relevance_pts + trend_momentum_pts + audience_fit_pts + engagement_pts + content_gap_pts
    final_score = int(round(max(0.0, min(100.0, total_pts))))
    label = get_opportunity_label(final_score)

    breakdown = {
        "relevance": round(relevance_pts, 1),
        "trend_momentum": round(trend_momentum_pts, 1),
        "audience_fit": round(audience_fit_pts, 1),
        "engagement_potential": round(engagement_pts, 1),
        "content_gap": round(content_gap_pts, 1),
    }

    return final_score, label, breakdown


def enrich_signal_with_opportunity(signal: Dict) -> Dict:
    """Enrich a signal dictionary with Opportunity Score, label, and breakdown."""
    score, label, breakdown = calculate_opportunity_score(signal)
    return {
        **signal,
        "opportunity_score": score,
        "opportunity_label": label,
        "opportunity_breakdown": breakdown,
    }


def init_signals_table():
    """Create signals table if not exists."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('''CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT,
        summary TEXT,
        score INTEGER DEFAULT 0,
        relevance_score REAL DEFAULT 0.0,
        source_date TEXT,
        fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        processed INTEGER DEFAULT 0,
        signal_type TEXT DEFAULT 'news'
    )''')
    conn.execute('''CREATE INDEX IF NOT EXISTS idx_signals_url ON signals(url)''')
    conn.commit()
    conn.close()


def signal_exists(url: str) -> bool:
    """Check if a signal with this URL already exists."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT 1 FROM signals WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def save_signal(source: str, title: str, url: str, summary: str = "",
                score: int = 0, signal_type: str = "news"):
    """Save a signal to the database."""
    if signal_exists(url):
        return False
    relevance = _compute_relevance(title + " " + summary)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO signals (source, title, url, summary, score, relevance_score, source_date, signal_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (source, title, url, summary, score, relevance, datetime.now().isoformat(), signal_type)
    )
    conn.commit()
    conn.close()
    return True


def _compute_relevance(text: str) -> float:
    """Compute AI relevance score 0-1 based on keyword density."""
    matches = AI_PATTERN.findall(text)
    words = len(text.split())
    if words == 0:
        return 0.0
    return min(1.0, len(matches) / max(words * 0.05, 1))


async def fetch_hackernews(max_stories: int = 15) -> List[Dict]:
    """Fetch top stories from Hacker News API, filtered for AI relevance."""
    signals = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=15.0
            )
            story_ids = resp.json()[:50]  # Check top 50, keep max_stories
        except Exception as e:
            print(f"Scout: HN API error: {e}")
            return signals

        for story_id in story_ids:
            if len(signals) >= max_stories:
                break
            try:
                resp = await client.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10.0
                )
                item = resp.json()
                if not item or item.get("type") != "story":
                    continue

                title = item.get("title", "")
                url = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                score = item.get("score", 0)

                # Filter: AI-relevant OR high score
                if AI_PATTERN.search(title) or score > 200:
                    saved = save_signal(
                        source="HackerNews",
                        title=title,
                        url=url,
                        summary=title,
                        score=score,
                        signal_type="news"
                    )
                    if saved:
                        signals.append({"title": title, "url": url, "score": score})
            except Exception:
                continue

    return signals


async def fetch_github_repos(username: str = "inbharatai") -> List[Dict]:
    """Scan GitHub user for new repos and releases."""
    signals = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://api.github.com/users/{username}/repos?sort=created&per_page=10",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=15.0
            )
            repos = resp.json()
        except Exception as e:
            print(f"Scout: GitHub API error: {e}")
            return signals

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        for repo in repos:
            if repo.get("fork"):
                continue
            created = repo.get("created_at", "")
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if dt > cutoff:
                    url = repo["html_url"]
                    saved = save_signal(
                        source="GitHub",
                        title=f"New repo: {repo['name']}",
                        url=url,
                        summary=repo.get("description", "") or "",
                        score=repo.get("stargazers_count", 0),
                        signal_type="repo"
                    )
                    if saved:
                        signals.append({"title": repo["name"], "url": url, "type": "repo"})
            except (ValueError, KeyError):
                continue

        # Check latest releases for each repo
        for repo in repos[:5]:
            try:
                resp = await client.get(
                    f"https://api.github.com/repos/{username}/{repo['name']}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=10.0
                )
                if resp.status_code != 200:
                    continue
                release = resp.json()
                published = release.get("published_at", "")
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if dt > datetime.now(timezone.utc) - timedelta(hours=24):
                    tag = release.get("tag_name", "")
                    url = release.get("html_url", "")
                    saved = save_signal(
                        source="GitHub",
                        title=f"Release: {repo['name']} {tag}",
                        url=url,
                        summary=release.get("body", "")[:300],
                        score=0,
                        signal_type="release"
                    )
                    if saved:
                        signals.append({"title": f"{repo['name']} {tag}", "url": url, "type": "release"})
            except Exception:
                continue

    return signals


async def run():
    """Main scout run — fetch all signal sources."""
    init_signals_table()
    print(f"[Scout] Starting at {datetime.now().strftime('%H:%M:%S')}")

    hn_signals = await fetch_hackernews(max_stories=10)
    print(f"[Scout] HackerNews: {len(hn_signals)} new signals")

    gh_signals = await fetch_github_repos()
    print(f"[Scout] GitHub: {len(gh_signals)} new signals")

    total = len(hn_signals) + len(gh_signals)
    print(f"[Scout] Done — {total} new signals stored")
    return total


def get_unprocessed_signals(limit: int = 20) -> List[Dict]:
    """Get unprocessed signals for the Planner agent, enriched and ranked by Opportunity Score."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM signals WHERE processed = 0 ORDER BY relevance_score DESC, score DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    signals = [enrich_signal_with_opportunity(dict(r)) for r in rows]
    # Rank by opportunity_score descending so highest opportunities are planned first
    signals.sort(key=lambda s: s.get("opportunity_score", 0), reverse=True)
    return signals


def mark_processed(signal_ids: List[int]):
    """Mark signals as processed by the Planner."""
    conn = sqlite3.connect(str(DB_PATH))
    placeholders = ",".join("?" * len(signal_ids))
    conn.execute(f"UPDATE signals SET processed = 1 WHERE id IN ({placeholders})", signal_ids)
    conn.commit()
    conn.close()
