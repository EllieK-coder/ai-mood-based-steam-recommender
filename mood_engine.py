import json

BACKLOG_MINUTES = 120   # games played less than this count as backlog
BACKLOG_BONUS = 0.1     # how much extra score backlog games get
MIN_SCORE = 0.4      # games that match the mood less than this are not recommended
EXCLUDE_APPIDS = {1938090}   # launchers and non-games: CHECK this matches "Call of Duty®" in your library.json
TAGS_TO_MATCH = 3   # a game that strongly matches this many of the mood's tags scores 1.0


def load_library():
    with open("library.json", "r", encoding="utf-8") as f:
        return json.load(f)


def clean_library(library):
    """Remove excluded entries, games without tags, and exact-name duplicates."""
    best = {}   # name -> the version of the game we keep

    for game in library:
        if game["appid"] in EXCLUDE_APPIDS:
            continue
        if not game["tags"]:
            continue

        name = game["name"]
        if name not in best or game["playtime"] > best[name]["playtime"]:
            best[name] = game

    return list(best.values())


def tag_strengths(tags):
    """Turn raw vote counts into 0-1 strengths, relative to the game's top tag."""
    if not tags:
        return {}

    top_votes = max(tags.values())
    strengths = {}
    for tag, votes in tags.items():
        strengths[tag] = round(votes / top_votes, 2)

    return strengths


def all_tags(library):
    """Every distinct tag that appears in the library, sorted alphabetically."""
    tags = set()
    for game in library:
        tags.update(game["tags"].keys())
    return sorted(tags)


def score_game(game, profile):
    """How well one game matches a mood profile, from 0 to 1."""
    strengths = tag_strengths(game["tags"])

    total = 0
    for tag, weight in profile.items():
        total += weight * strengths.get(tag, 0)

    top_weights = sorted(profile.values(), reverse=True)[:TAGS_TO_MATCH]
    return round(min(total / sum(top_weights), 1.0), 2)


def rank_library(library, profile, top_n=10):
    scored = []
    for game in library:
        match = score_game(game, profile)

        if match < MIN_SCORE:
            continue

        score = match

        if game["playtime"] < BACKLOG_MINUTES:
            score = round(score + BACKLOG_BONUS, 2)

        scored.append({
            "name": game["name"],
            "playtime": game["playtime"],
            "match": match,
            "score": score,
            "tags": sorted(game["tags"], key=game["tags"].get, reverse=True)[:5],
        })

    scored.sort(key=lambda g: g["score"], reverse=True)
    return scored[:top_n]


if __name__ == "__main__":
    library = clean_library(load_library())
    print("Games after cleaning:", len(library))

    # uncomment to see every tag you can use in a profile
    # print(all_tags(library))

    relax = {"Relaxing": 1.0, "Cozy": 0.8, "Casual": 0.6, "Atmospheric": 0.5}
    anger = {"Violent": 1.0, "Action": 0.8, "Shooter": 0.7, "Hack and Slash": 0.7, "Gore": 0.5, "Fast-Paced": 0.5}
    challenge = {"Difficult": 1.0, "Souls-like": 0.8, "Puzzle": 0.5, "Roguelike": 0.5}

    profiles = {"relax": relax, "anger": anger, "challenge": challenge}

    for mood, profile in profiles.items():
        print("\n===", mood, "===")
        for game in rank_library(library, profile):
            print(game["score"], f"(match {game['match']})", "-", game["name"], "-", game["playtime"], "min")