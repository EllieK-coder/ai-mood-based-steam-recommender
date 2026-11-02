import time

import ollama
import requests

from SteamSpy import fetch_tag
from store_engine import rank_store

MODEL = "qwen2.5:7b"

def find_store_games(profile, owned):
    """Search SteamSpy for the profile's top tags and rank games the user doesn't own."""
    top_tags = sorted(profile, key=profile.get, reverse=True)[:3]

    tag_results = {}
    try:
        for tag in top_tags:
            tag_results[tag] = fetch_tag(tag)
            time.sleep(1)
    except requests.RequestException:
        return []

    return rank_store(tag_results, profile, owned, top_n=5)

def pick_store_games(mood_text, candidates):
    """Let the LLM suggest 1-2 store games the user doesn't own, using only the given facts."""
    lines = []
    for game in candidates[:5]:
        tags = ", ".join(game["tags"])
        percent = round(game["rating"] * 100)
        if game["price"] == 0:
            price = "free"
        else:
            price = f"${game['price']:.2f}"
        lines.append(f"- {game['name']} | {price} | {percent}% positive reviews | tags: {tags}")

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You help the user find a game to play. "
                    "Nothing in the user's own Steam library fits their mood, "
                    "so the games below are from the Steam store and the user does NOT own them. "
                    "Start by saying briefly that nothing in their library fits, "
                    "then suggest 1 or 2 of these games as new games to consider, "
                    "with one or two sentences each on why they fit the mood. "
                    "Mention the price. "
                    "Only suggest games from the list. "
                    "Describe a game only using its tags and what it is generally known for; never invent features. "
                    "Write in plain text, without Markdown."
                ),
            },
            {
                "role": "user",
                "content": f'Mood: "{mood_text}"\nStore games:\n' + "\n".join(lines),
            },
        ],
        options={"temperature": 0.3},
    )
    return response.message.content