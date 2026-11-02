import json

import ollama

from mood_engine import load_library, clean_library, all_tags, rank_library, BACKLOG_MINUTES
from store_profile import find_store_games, pick_store_games

MODEL = "qwen2.5:7b"
DEBUG = False

SYNONYMS = {           # invented words the model likes -> the real Steam tag
    "Chill": "Relaxing",
    "Calming": "Relaxing",
    "Unwinding": "Relaxing",
    "Leisure": "Casual",
    "Challenge": "Difficult",
    "Hardcore": "Difficult",
    "Smash": "Destruction",
    "Angry": "Violent",
}

MOOD_TAGS = [          # only tags that describe a feeling
    # calm / comfort
    "Relaxing", "Cozy", "Casual", "Wholesome", "Atmospheric", "Beautiful",
    "Great Soundtrack", "Exploration", "Walking Simulator", "Farming Sim",
    "Life Sim", "Building", "Sandbox", "Family Friendly",
    # venting / energy
    "Action", "Fast-Paced", "Violent", "Gore", "Shooter", "FPS",
    "Hack and Slash", "Beat 'em up", "Fighting", "Destruction", "Combat",
    # challenge / focus
    "Difficult", "Souls-like", "Unforgiving", "Perma Death", "Roguelike",
    "Roguelite", "Precision Platformer", "Puzzle", "Strategy", "Tactical",
    "Competitive",
    # fear / tension
    "Horror", "Psychological Horror", "Survival Horror", "Thriller", "Survival",
    # story / feelings
    "Story Rich", "Emotional", "Choices Matter", "Mystery",
    # fun / social
    "Funny", "Comedy", "Co-op", "Online Co-Op", "Party Game", "Arcade",
    # themes / settings
    "Space", "Sci-fi", "Space Sim", "Futuristic", "Aliens",
    "Colony Sim", "Base Building", "City Builder", "Management",
    "Fantasy", "Medieval", "Post-apocalyptic", "Cyberpunk",
    "Survival", "Zombies", "Underwater",
]


def mood_tags(library):
    """The curated mood tags that actually exist in this library."""
    available = set(all_tags(library))
    return [tag for tag in MOOD_TAGS if tag in available]


def validate_profile(raw, allowed_tags):
    """Turn the model's raw JSON into a clean profile: only real tags, weights between 0 and 1."""
    if not isinstance(raw, dict):
        return {}

    profile = {}
    for tag, weight in raw.items():
        tag = SYNONYMS.get(tag, tag)
        if tag not in allowed_tags or not isinstance(weight, (int, float)):
            if DEBUG:
                print(f"[dropped invalid tag: {tag}]")
            continue
        if weight <= 0:
            if DEBUG:
                print(f"[dropped zero/negative weight: {tag}]")
            continue
        weight = min(float(weight), 1.0)
        profile[tag] = max(profile.get(tag, 0), weight)

    return profile


def mood_to_profile(mood_text, allowed_tags):
    """Ask the LLM to turn the user's words into a weighted tag profile."""
    system = (
        "You turn a player's mood into a weighted profile of Steam tags. "
        "Always choose between 5 and 8 tags. Cover the different ways the mood could be satisfied. "
        "Use ONLY tags from this list, spelled exactly as written: "
        + ", ".join(allowed_tags) + ". "
        "Give each tag a weight from 0.1 to 1.0, where 1.0 is the most important. "
        "Reply with only a JSON object.\n\n"
        "Example 1\n"
        'Mood: "I\'m bored and want to explore somewhere new"\n'
        'Profile: {"Exploration": 1.0, "Atmospheric": 0.7, "Beautiful": 0.6, '
        '"Great Soundtrack": 0.5, "Walking Simulator": 0.4, "Sandbox": 0.4}\n\n'
        "Example 2\n"
        'Mood: "I want to laugh with my friends tonight"\n'
        'Profile: {"Funny": 1.0, "Co-op": 0.9, "Party Game": 0.8, '
        '"Comedy": 0.7, "Online Co-Op": 0.6, "Casual": 0.5}'
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": mood_text},
        ],
        format="json",
        options={"num_predict": 200, "num_ctx": 8192, "temperature": 0},
    )

    try:
        raw = json.loads(response.message.content)
    except json.JSONDecodeError:
        return {}

    return validate_profile(raw, allowed_tags)


def pick_games(mood_text, candidates):
    """Let the LLM choose 1-3 games from the ranked candidates and explain why."""
    top = candidates[:5]

    lines = []
    for game in top:
        tags = ", ".join(game["tags"])
        if game["playtime"] < BACKLOG_MINUTES:
            lines.append(f"- {game['name']} | owned but never or barely played | tags: {tags}")
        else:
            hours = round(game["playtime"] / 60, 1)
            lines.append(f"- {game['name']} | played {hours} hours | tags: {tags}")

    candidate_text = "\n".join(lines)
    if DEBUG:
        print(candidate_text)

    system = (
        "You are a friendly assistant that recommends Steam games the player already owns. "
        "Recommend 1 to 3 games ONLY from the list you are given. "
        "Each game's tags are listed. Describe a game only using its tags and what it is generally known for; never invent features. "
        "If a game does not match part of the request (for example a theme), say so honestly. "
        "If the user asks for a specific theme or setting (for example space or sci-fi), only recommend games whose tags include that theme. "
        "For each game, write 1-2 sentences on why it fits the player's mood. "
        "If a game is marked as never or barely played, mention that they already own it "
        "and haven't really tried it yet. "
        "Do not mention scores, hours or other numbers from the list. "
        "If any game marked as never or barely played fits the mood, include at least one of them in your picks. "
        "Write in plain text, without Markdown formatting such as ** or numbered lists."
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"My mood: {mood_text}\n\nGames I own:\n{candidate_text}"},
        ],
        options={"temperature": 0.3},
    )

    return response.message.content
def find_new_games(mood: str) -> str:
    """Suggest new games from the Steam store that the user does not own yet.
    Use this ONLY when the user explicitly asks for new games, games they don't own,
    or something to buy."""
    try:
        raw = load_library()
    except FileNotFoundError:
        return "Your library hasn't been built yet. Run build_library.py first."

    profile = mood_to_profile(mood, MOOD_TAGS)
    if not profile:
        return "I couldn't work out what kind of game fits that mood."

    owned = {game["appid"] for game in raw}
    store = find_store_games(profile, owned)
    if not store:
        return "I couldn't find anything in the store for that mood right now."

    intro = "Here are some games from the Steam store you don't own yet:\n\n"
    return intro + pick_store_games(mood, store)



def recommend_from_library(mood: str) -> str:
    """Recommend games the user already owns that fit their mood, for example
    'I want to relax' or 'I'm angry and want to smash something'. Use this by default."""
    try:
        raw = load_library()
        library = clean_library(raw)
    except FileNotFoundError:
        return "Your library hasn't been built yet. Run build_library.py first."

    tags = mood_tags(library)

    profile = mood_to_profile(mood, tags)
    if not profile:
        return "I couldn't work out what kind of game fits that mood."

    ranked = rank_library(library, profile)
    if not ranked:
        owned = {game["appid"] for game in raw}
        store = find_store_games(profile, owned)
        if not store:
            return "Nothing in your library fits that mood right now, and I couldn't find anything in the store either."
        intro = "Nothing in your library fits that mood right now, but here are some games from the Steam store you don't own yet:\n\n"
        return intro + pick_store_games(mood, store)

    return pick_games(mood, ranked)


def find_new_games(mood: str) -> str:
    """Suggest new games from the Steam store that the user does not own yet.
    Use this ONLY when the user explicitly asks for new games, games they don't own,
    or something to buy."""
    try:
        raw = load_library()
    except FileNotFoundError:
        return "Your library hasn't been built yet. Run build_library.py first."

    profile = mood_to_profile(mood, MOOD_TAGS)
    if not profile:
        return "I couldn't work out what kind of game fits that mood."

    owned = {game["appid"] for game in raw}
    store = find_store_games(profile, owned)
    if not store:
        return "I couldn't find anything in the store for that mood right now."

    intro = "Here are some games from the Steam store you don't own yet:\n\n"
    return intro + pick_store_games(mood, store)


if __name__ == "__main__":
    print(recommend_from_library("I had a long day and just want to relax"))
    print(recommend_from_library("I'm so angry I want to smash something"))
    print(recommend_from_library("asdfgh"))
    print(find_new_games("I want a cozy farming game"))