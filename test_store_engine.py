from store_engine import rating, rank_store, rerank_store

def make_store_game(appid, name="Test Game", positive=900, negative=100, price="999"):
    return {"appid": appid, "name": name, "positive": positive, "negative": negative, "price": price}


def make_candidate(appid, name="Test Game", rating=0.9):
    return {"appid": appid, "name": name, "rating": rating, "price": 9.99, "tags": ["Space"], "match": 0.5}



def test_owned_games_are_excluded():
    # Arrange
    owned_game = make_store_game(1, name="Owned")
    new_game = make_store_game(2, name="New")
    tag_results = {"Space": {"1": owned_game, "2": new_game}}
    profile = {"Space": 1.0}

    # Act
    result = rank_store(tag_results, profile, owned={1})

    # Assert
    names = [g["name"] for g in result]
    assert names == ["New"]


def test_rating_is_share_of_positive():
    game = make_store_game(1, positive=900, negative=100)

    assert rating(game) == 0.9


def test_rating_with_no_reviews_is_zero():
    game = make_store_game(1, positive=0, negative=0)

    assert rating(game) == 0


def test_games_with_few_reviews_are_excluded():
    small_game = make_store_game(1, name="Small", positive=10, negative=5)
    big_game = make_store_game(2, name="Big")
    tag_results = {"Space": {"1": small_game, "2": big_game}}
    profile = {"Space": 1.0}

    result = rank_store(tag_results, profile, owned=set())

    names = [g["name"] for g in result]
    assert names == ["Big"]


def test_game_in_more_tag_lists_ranks_first():
    game_a = make_store_game(1, name="A")
    game_b = make_store_game(2, name="B")
    tag_results = {
        "Space": {"1": game_a, "2": game_b},
        "Colony Sim": {"1": game_a},
    }
    profile = {"Space": 1.0, "Colony Sim": 1.0}

    result = rank_store(tag_results, profile, owned=set())

    assert result[0]["name"] == "A"
    assert result[0]["match"] == 1.0


def test_rating_breaks_ties():
    good = make_store_game(1, name="Good", positive=950, negative=50)
    okay = make_store_game(2, name="Okay", positive=700, negative=300)
    tag_results = {"Space": {"1": okay, "2": good}}
    profile = {"Space": 1.0}

    result = rank_store(tag_results, profile, owned=set())

    names = [g["name"] for g in result]
    assert names == ["Good", "Okay"]


def test_price_is_converted_from_cents():
    game = make_store_game(1, price="2999")
    tag_results = {"Space": {"1": game}}
    profile = {"Space": 1.0}

    result = rank_store(tag_results, profile, owned=set())

    assert result[0]["price"] == 29.99


def test_weakly_tagged_game_is_dropped():
    # Arrange
    strong = make_candidate(1, name="Strong")
    weak = make_candidate(2, name="Weak")
    details = {
        1: {"Space": 1000, "Colony Sim": 900},
        2: {"Action": 1000, "Space": 10},
    }
    profile = {"Space": 1.0, "Colony Sim": 1.0}

    # Act
    result = rerank_store([strong, weak], details, profile)

    # Assert
    names = [g["name"] for g in result]
    assert names == ["Strong"]


def test_game_without_details_is_dropped():
    game = make_candidate(1)
    details = {}
    profile = {"Space": 1.0}

    result = rerank_store([game], details, profile)

    assert result == []


def test_game_with_empty_tags_is_dropped():
    game = make_candidate(1)
    details = {1: []}
    profile = {"Space": 1.0}

    result = rerank_store([game], details, profile)

    assert result == []


def test_tags_are_replaced_with_real_top_tags():
    game = make_candidate(1)
    details = {1: {"Colony Sim": 900, "Space": 1000}}
    profile = {"Space": 1.0, "Colony Sim": 1.0}

    result = rerank_store([game], details, profile)

    assert result[0]["tags"] == ["Space", "Colony Sim"]


def test_better_match_ranks_first():
    okay = make_candidate(1, name="Okay")
    best = make_candidate(2, name="Best")
    details = {
        1: {"Space": 1000, "Colony Sim": 300},
        2: {"Space": 1000, "Colony Sim": 900},
    }
    profile = {"Space": 1.0, "Colony Sim": 1.0}

    result = rerank_store([okay, best], details, profile)

    names = [g["name"] for g in result]
    assert names == ["Best", "Okay"]


def test_original_candidate_is_not_changed():
    game = make_candidate(1)
    details = {1: {"Space": 1000, "Colony Sim": 900}}
    profile = {"Space": 1.0, "Colony Sim": 1.0}

    rerank_store([game], details, profile)

    assert game["match"] == 0.5
    assert game["tags"] == ["Space"]