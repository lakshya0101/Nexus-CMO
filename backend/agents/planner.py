"""
Planner Agent — Content Strategy

Responsibilities:
  - Read unprocessed signals from Scout
  - Decide: what to post, which platform, what format, what time
  - Apply rate-limits and platform best practices
  - Avoid duplicates and topic repetition
  - Create content plans in SQLite

Runs: After Scout completes
"""

import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / "socialflow.db"

# Platform content format mapping
PLATFORM_FORMATS = {
    "linkedin": {"max_chars": 3000, "supports_image": True, "supports_carousel": True},
    "x": {"max_chars": 280, "supports_image": True, "supports_carousel": False},
    "discord": {"max_chars": 2000, "supports_image": True, "supports_carousel": False},
    "instagram": {"max_chars": 2200, "supports_image": True, "supports_carousel": True},
    "reddit": {"max_chars": 40000, "supports_image": False, "supports_carousel": False},
    "facebook": {"max_chars": 63206, "supports_image": True, "supports_carousel": True},
}

# Default rate-limits (overridden by brand_config if set)
DEFAULT_LIMITS = {
    "linkedin": {"daily_cap": 2, "windows": [11, 23]},
    "x": {"daily_cap": 5, "windows": None},
    "discord": {"daily_cap": 10, "windows": None},
    "instagram": {"daily_cap": 3, "windows": None},
    "reddit": {"daily_cap": 1, "windows": None},
    "facebook": {"daily_cap": 3, "windows": None},
}


def init_plans_table():
    """Create content_plans table."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('''CREATE TABLE IF NOT EXISTS content_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        platform TEXT NOT NULL,
        content_type TEXT NOT NULL,
        priority INTEGER DEFAULT 5,
        scheduled_hour INTEGER,
        status TEXT DEFAULT 'planned',
        brief TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (signal_id) REFERENCES signals(id)
    )''')
    conn.commit()
    conn.close()


def get_todays_plan_count(platform: str) -> int:
    """How many plans already created for this platform today."""
    conn = sqlite3.connect(str(DB_PATH))
    today = date.today().isoformat()
    count = conn.execute(
        "SELECT COUNT(*) FROM content_plans WHERE platform = ? AND DATE(created_at) = ?",
        (platform, today)
    ).fetchone()[0]
    conn.close()
    return count


def get_todays_post_count(platform: str) -> int:
    """How many posts already sent for this platform today."""
    conn = sqlite3.connect(str(DB_PATH))
    today = date.today().isoformat()
    count = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE platform = ? AND status = 'posted' AND DATE(published_at) = ?",
        (platform, today)
    ).fetchone()[0]
    conn.close()
    return count


def create_plan(signal_id: int, platform: str, content_type: str,
                priority: int = 5, scheduled_hour: int = None, brief: str = ""):
    """Create a content plan entry."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO content_plans (signal_id, platform, content_type, priority, scheduled_hour, brief) VALUES (?, ?, ?, ?, ?, ?)",
        (signal_id, platform, content_type, priority, scheduled_hour, brief)
    )
    conn.commit()
    conn.close()


def plan_signal(signal: Dict) -> List[Dict]:
    """Decide what to do with a signal — which platforms, formats, and priority based on Opportunity Score.

    Returns list of plan dicts created.
    """
    plans = []
    title = signal.get("title", "")
    signal_type = signal.get("signal_type", "news")
    score = signal.get("score", 0) or 0
    relevance = signal.get("relevance_score", 0) or 0.0

    # Retrieve or calculate Opportunity Score (0-100) and Label
    opp_score = signal.get("opportunity_score")
    opp_label = signal.get("opportunity_label")
    if opp_score is None or opp_label is None:
        from agents.scout import calculate_opportunity_score
        opp_score, opp_label, _ = calculate_opportunity_score(signal)

    # Calculate deterministic priority (1-10 scale) based on Opportunity Score
    # Ensures higher opportunity score receives higher priority while preserving existing bounds
    calculated_priority = min(10, max(1, round(opp_score / 10)))

    # High-opportunity / High-relevance news (Opportunity >= 60, Relevance > 0.3, or Score > 100)
    # -> Multi-platform distribution: LinkedIn (11 AM window) + X + Discord
    if signal_type == "news" and (opp_score >= 60 or relevance > 0.3 or score > 100):
        for platform, hour in [("discord", None), ("linkedin", 11), ("x", None)]:
            limits = DEFAULT_LIMITS.get(platform, {})
            cap = limits.get("daily_cap", 5)
            current = get_todays_plan_count(platform) + get_todays_post_count(platform)
            if current < cap:
                create_plan(
                    signal_id=signal["id"],
                    platform=platform,
                    content_type="ai-news",
                    priority=calculated_priority,
                    scheduled_hour=hour,
                    brief=f"[{opp_label} Opp: {opp_score}/100] News post about: {title}"
                )
                plans.append({"platform": platform, "type": "ai-news", "priority": calculated_priority})

    # Moderate-opportunity news (Opportunity >= 40 or Relevance > 0.1) -> Discord only
    elif signal_type == "news" and (opp_score >= 40 or relevance > 0.1):
        current = get_todays_plan_count("discord") + get_todays_post_count("discord")
        if current < DEFAULT_LIMITS["discord"]["daily_cap"]:
            discord_priority = max(1, calculated_priority - 2)
            create_plan(
                signal_id=signal["id"],
                platform="discord",
                content_type="ai-news",
                priority=discord_priority,
                brief=f"[{opp_label} Opp: {opp_score}/100] Quick news drop: {title}"
            )
            plans.append({"platform": "discord", "type": "ai-news", "priority": discord_priority})

    # Repo and release signals -> Discord + LinkedIn (3x/week) + Reddit
    elif signal_type in ("repo", "release"):
        repo_priority = max(7, calculated_priority)
        for platform in ["discord", "linkedin", "reddit"]:
            limits = DEFAULT_LIMITS.get(platform, {})
            cap = limits.get("daily_cap", 5)
            current = get_todays_plan_count(platform) + get_todays_post_count(platform)
            if current < cap:
                create_plan(
                    signal_id=signal["id"],
                    platform=platform,
                    content_type="repo-promo",
                    priority=repo_priority,
                    brief=f"[{opp_label} Opp: {opp_score}/100] Promote repo: {title}"
                )
                plans.append({"platform": platform, "type": "repo-promo", "priority": repo_priority})

    return plans


async def run():
    """Main planner run — process unprocessed signals."""
    from agents.scout import get_unprocessed_signals, mark_processed

    init_plans_table()
    print(f"[Planner] Starting at {datetime.now().strftime('%H:%M:%S')}")

    signals = get_unprocessed_signals(limit=15)
    print(f"[Planner] Processing {len(signals)} unprocessed signals")

    total_plans = 0
    processed_ids = []

    for signal in signals:
        plans = plan_signal(signal)
        total_plans += len(plans)
        processed_ids.append(signal["id"])
        if plans:
            platforms = ", ".join(p["platform"] for p in plans)
            print(f"[Planner] Signal '{signal['title'][:50]}' → {platforms}")

    if processed_ids:
        mark_processed(processed_ids)

    print(f"[Planner] Done — {total_plans} plans created from {len(signals)} signals")
    return total_plans


def get_pending_plans(limit: int = 20) -> List[Dict]:
    """Get planned content that hasn't been created yet."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT cp.*, s.title as signal_title, s.url as signal_url, s.summary as signal_summary,
               s.source as signal_source
        FROM content_plans cp
        JOIN signals s ON cp.signal_id = s.id
        WHERE cp.status = 'planned'
        ORDER BY cp.priority DESC, cp.created_at ASC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_plan_completed(plan_id: int):
    """Mark a plan as completed (content created)."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("UPDATE content_plans SET status = 'completed' WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()
