# 1. pip install requests  (in the terminal)
# 2. import requests
# 3. use requests.get() on: https://steamspy.com/api.php
#    with params={"request": "tag", "tag": "Roguelike"}
# 4. turn the response into Python data with .json()
# 5. print it, then figure out how to print just the first 5 game names
import json

import requests


def fetch_tag(tag: str) -> dict:
    """Return every game SteamSpy has for this tag, as {appid: game_data}."""
    response = requests.get(
        "https://steamspy.com/api.php",
        params={"request": "tag", "tag": tag},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

def find_games_by_tag(tag: str) -> str:
    """Find Steam games that have a given tag, such as Roguelike or Relaxing."""
    response = requests.get(
        "https://steamspy.com/api.php",
        params={"request": "tag", "tag": tag}
    )
    data = response.json()
    games = list(data.values())

    results = []
    for game in games[:5]:
        results.append({"name": game["name"], "positive": game["positive"]})

    return str(results)

if __name__ == "__main__":
    import time
    from mood_engine import load_library
    from store_engine import rank_store

    profile = {"Space": 1.0, "Colony Sim": 0.9, "Base Building": 0.8}
    owned = {game["appid"] for game in load_library()}

    tag_results = {}
    for tag in profile:
        tag_results[tag] = fetch_tag(tag)
        print(f"{tag}: {len(tag_results[tag])} games")
        time.sleep(1)   # be polite to SteamSpy's rate limit

    for game in rank_store(tag_results, profile, owned):
        print(game["match"], game["rating"], game["price"], "-", game["name"], game["tags"])
