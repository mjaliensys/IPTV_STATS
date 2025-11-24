# app/classifier.py

import re
from typing import Tuple

# Patterns matched in order - first match wins
USER_AGENT_PATTERNS: list[Tuple[str, re.Pattern]] = [
    # Streaming servers
    ("streaming_server", re.compile(r"Streamer", re.IGNORECASE)),
    ("streaming_server", re.compile(r"FFmpeg", re.IGNORECASE)),

    # Mobile
    ("android", re.compile(r"Android", re.IGNORECASE)),
    ("android", re.compile(r"okhttp", re.IGNORECASE)),
    ("ios", re.compile(r"iPhone|iPad|iOS|Darwin", re.IGNORECASE)),

    # TV platforms
    ("tv", re.compile(r"SmartTV|Smart-TV|GoogleTV|Apple\s?TV|Roku|Fire\s?TV|webOS|Tizen", re.IGNORECASE)),
    ("tv", re.compile(r"LG Browser|BRAVIA|PlayStation|Xbox", re.IGNORECASE)),

    # Set-top boxes
    ("stb", re.compile(r"STB|Set-Top|MAG\d|Formuler|Tvip|BuzzTV", re.IGNORECASE)),
    ("stb", re.compile(r"Lavf", re.IGNORECASE)),  # libavformat - common in STB/embedded

    # Desktop browsers (grouped as "desktop")
    ("desktop", re.compile(r"Windows|Macintosh|Linux.*Firefox|Linux.*Chrome", re.IGNORECASE)),
    ("desktop", re.compile(r"Chrome|Firefox|Safari|Edge", re.IGNORECASE)),
]


def classify_user_agent(user_agent: str) -> str:
    """
    Classify user agent string into device category.

    Returns one of: android, ios, tv, stb, streaming_server, desktop, other
    """
    if not user_agent:
        return "other"

    for category, pattern in USER_AGENT_PATTERNS:
        if pattern.search(user_agent):
            return category

    return "other"


# Quick lookup for known exact matches (faster than regex)
KNOWN_USER_AGENTS: dict[str, str] = {}


def classify_user_agent_cached(user_agent: str) -> str:
    """
    Classify with caching for repeated user agents.
    """
    if user_agent in KNOWN_USER_AGENTS:
        return KNOWN_USER_AGENTS[user_agent]

    category = classify_user_agent(user_agent)

    # Cache if we haven't exceeded limit (prevent memory issues)
    if len(KNOWN_USER_AGENTS) < 10000:
        KNOWN_USER_AGENTS[user_agent] = category

    return category