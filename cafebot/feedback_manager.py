"""Feedback persistence — JSON-based storage for user ratings and comments."""

import json
import os
from datetime import datetime, timezone

FEEDBACK_FILE = os.path.join("data", "feedback.json")


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)


def load_feedback() -> list[dict]:
    """Load all feedback entries from disk."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_feedback(entries: list[dict]) -> None:
    """Save feedback entries to disk."""
    _ensure_dir()
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def add_feedback(
    user_id: str,
    user_name: str | None,
    rating: int,
    comment: str = "",
) -> None:
    """Append a new feedback entry."""
    entries = load_feedback()
    entry = {
        "user_id": user_id,
        "user_name": user_name,
        "rating": rating,
        "comment": comment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    entries.append(entry)
    save_feedback(entries)


def update_last_feedback_comment(user_id: str, comment: str) -> bool:
    """Update the most recent feedback entry for a user with a comment."""
    entries = load_feedback()
    # Find the last entry for this user
    for i in range(len(entries) - 1, -1, -1):
        if str(entries[i].get("user_id")) == str(user_id):
            entries[i]["comment"] = comment
            save_feedback(entries)
            return True
    return False


def get_feedback_summary() -> str:
    """Return a formatted summary of all feedback for admin viewing."""
    entries = load_feedback()
    if not entries:
        return "No feedback collected yet."

    lines = ["\n  --- User Feedback ---"]
    total_rating = 0
    for e in entries:
        name = e.get("user_name") or e.get("user_id", "Unknown")
        rating = e.get("rating", 0)
        comment = e.get("comment", "")
        ts = e.get("timestamp", "")
        stars = "⭐" * rating
        lines.append(f"\n  User: {name}")
        lines.append(f"    Rating: {stars} ({rating}/5)")
        if comment:
            lines.append(f"    Comment: {comment}")
        if ts:
            lines.append(f"    Time: {ts}")
        total_rating += rating

    avg = total_rating / len(entries)
    lines.append(f"\n  Average Rating: {avg:.1f}/5 ({len(entries)} reviews)")
    lines.append("  ---------------------")
    return "\n".join(lines)


def get_average_rating() -> float:
    """Return average rating across all feedback."""
    entries = load_feedback()
    if not entries:
        return 0.0
    return sum(e.get("rating", 0) for e in entries) / len(entries)
