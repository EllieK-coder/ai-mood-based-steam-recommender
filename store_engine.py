from mood_engine import score_game, MIN_SCORE


MIN_REVIEWS = 500   # ignore games with fewer reviews than this


def rating(game):
    """Share of positive reviews, from 0 to 1."""
    total = game["positive"] + game["negative"]
    if total == 0:
        return 0
    return round(game["positive"] / total, 2)


def rank_store(tag_results, profile, owned, top_n=10):
    """
    tag_results: {tag: fetch_tag(tag) result}, e.g. {"Space": {...}, "Colony Sim": {...}}
    profile:     the mood profile, e.g. {"Space": 1.0, "Colony Sim": 0.9}
    owned:       set of appids the user owns
    """
    candidates = {}   # appid -> info about that game

    for tag, games in tag_results.items():
        weight = profile[tag]
        for game in games.values():
            appid = game["appid"]

            if appid in owned:
                continue
            if game["positive"] + game["negative"] < MIN_REVIEWS:
                continue

            if appid not in candidates:
                candidates[appid] = {
                    "appid": appid,
                    "name": game["name"],
                    "rating": rating(game),
                    "price": int(game["price"]) / 100,
                    "tags": [],
                    "match": 0,
                }

            candidates[appid]["match"] += weight
            candidates[appid]["tags"].append(tag)

    total_weight = sum(profile[tag] for tag in tag_results)
    for game in candidates.values():
        game["match"] = round(game["match"] / total_weight, 2)

    ranked = sorted(candidates.values(), key=lambda g: (g["match"], g["rating"]), reverse=True)

    return ranked[:top_n]


def rerank_store(candidates, details, profile, top_n=5):
    """
    candidates: the result of rank_store
    details:    {appid: tags dict}, e.g. {294100: {"Colony Sim": 4108, ...}}
    profile:    the mood profile
    """
    reranked = []
    for game in candidates:
        tags = details.get(game["appid"])
        if not isinstance(tags, dict):
            continue

        match = score_game({"tags": tags}, profile)
        if match < MIN_SCORE:
            continue

        new = dict(game)
        new["match"] = match
        new["tags"] = sorted(tags, key=tags.get, reverse=True)[:5]
        reranked.append(new)

    reranked.sort(key=lambda g: (g["match"], g["rating"]), reverse=True)
    return reranked[:top_n]