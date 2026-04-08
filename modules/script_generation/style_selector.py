import re
from core.models import ContentStyle


# ── Keyword pattern → style mapping ──────────────────────────────────────────

_STYLE_RULES: list[tuple[list[str], ContentStyle]] = [
    # Politics, elections, war, policy → journalist
    (
        ["election", "vote", "president", "government", "minister", "war",
         "military", "sanction", "treaty", "parliament", "congress", "senate",
         "climate", "inflation", "economy", "gdp", "fed", "central bank"],
        ContentStyle.JOURNALIST,
    ),
    # Tech, AI, science, space → commentary
    (
        ["ai", "artificial intelligence", "chatgpt", "openai", "elon",
         "tesla", "spacex", "apple", "google", "meta", "microsoft",
         "crypto", "bitcoin", "ethereum", "startup", "tech"],
        ContentStyle.COMMENTARY,
    ),
    # Celebrity, sports, entertainment → humorous
    (
        ["celebrity", "kardashian", "taylor swift", "beyonce", "drake",
         "nfl", "nba", "oscar", "grammy", "movie", "netflix", "viral",
         "tiktok", "meme", "trending"],
        ContentStyle.HUMOROUS,
    ),
    # Scandal, controversy, hypocrisy → roast
    (
        ["scandal", "fired", "arrested", "exposed", "caught", "leaked",
         "lawsuit", "banned", "controversy", "backlash", "cancel"],
        ContentStyle.ROAST,
    ),
]

_DEFAULT_STYLE = ContentStyle.JOURNALIST


def auto_select_style(keyword: str) -> ContentStyle:
    """
    Automatically pick the most engaging content style for a keyword.
    Falls back to JOURNALIST if no rule matches.
    """
    kw_lower = keyword.lower()
    kw_words = set(re.findall(r"\w+", kw_lower))

    for pattern_words, style in _STYLE_RULES:
        for pattern in pattern_words:
            pattern_set = set(pattern.split())
            if pattern_set.issubset(kw_words) or pattern in kw_lower:
                return style

    return _DEFAULT_STYLE


def get_style_description(style: ContentStyle) -> str:
    descriptions = {
        ContentStyle.JOURNALIST: "Factual, authoritative reporting",
        ContentStyle.COMMENTARY: "Opinionated analysis with a clear POV",
        ContentStyle.HUMOROUS: "Funny and entertaining but informative",
        ContentStyle.ROAST: "Sharp, unapologetic, mic-drop commentary",
    }
    return descriptions.get(style, "")
