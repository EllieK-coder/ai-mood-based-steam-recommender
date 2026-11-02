import time

import ollama
import requests

from SteamSpy import fetch_tag, fetch_appdetails
from store_engine import rank_store, rerank_store


MODEL = "qwen2.5:7b"
DEBUG = False

def find_store_games(profile, owned):
    """Search SteamSpy for the profile's top tags, then rerank the best candidates by their real tags."""
    top_tags = sorted(profile, key=profile.get, reverse=True)[:3]

    # stage 1: cheap search by tag
    tag_results = {}
    try:
        for tag in top_tags:
            tag_results[tag] = fetch_tag(tag)
            time.sleep(1)
    except requests.RequestException as error:
        if DEBUG:
            print("[store] stage 1 failed:", error)
        return []

    candidates = rank_store(tag_results, profile, owned, top_n=10)
    if DEBUG:
        print("[store] tags:", top_tags, "| candidates:", len(candidates))

    # stage 2: real tag votes for the best 10, then rerank
    details = {}
    try:
        for game in candidates:
            details[game["appid"]] = fetch_appdetails(game["appid"]).get("tags")
            time.sleep(1)
    except requests.RequestException as error:
        if DEBUG:
            print("[store] stage 2 failed:", error)
        return candidates[:5]

    if DEBUG:
        for game in candidates:
            tags = details.get(game["appid"])
            print("[store]", game["name"], "|", type(tags).__name__, "|", list(tags)[:5] if tags else tags)

    return rerank_store(candidates, details, profile)


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
                    "The games below are from the Steam store, and the user does NOT own them. "
                    "Do not talk about the user's own library. "
                    "Suggest 1 or 2 of these games as new games to consider, "
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