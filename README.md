# Steam Game Picker Agent

A conversational AI agent that helps you decide what to play on Steam. You tell it how you feel in your own words, and it recommends 1–3 games from your own Steam library, putting games you've never played first.

Built in Python as a hands-on project to learn how AI agents work under the hood: tool calling, the agent loop, routing, and prompt design. It is built **without an agent framework**, so every part of the loop is visible in the code.

> **Status:** v1 complete: mood-based recommendations from your own Steam library work end to end. Next: v2, discovering new games from the Steam store.

## Features

- **Natural conversation:** a quick introduction and small talk about your day; game suggestions only come when you ask for them.
- **Mood-based recommendations:** describe how you feel in your own words ("I had a long day", "I want to smash something") and the agent turns it into matching Steam tags to find games that fit.
- **Your own library, backlog first:** recommendations come only from games you own, and games you've never or barely played get a boost, so forgotten games resurface.
- **Grounded picks:** code ranks your library and the LLM only chooses from the top candidates, so it never guesses which games you own.
- **Validated LLM output:** the mood profile is checked against real Steam tags; invented tags and invalid weights are dropped.
- **Tool calling:** when the user describes a mood, the model calls `recommend_from_library(mood)`, which runs the whole recommendation pipeline and returns the result.
- **Router + guardrail:** a keyword check and a lightweight YES/NO model call decide whether the user wants a game. If they do and the model skips the tool, code runs the recommendation pipeline itself, so the agent never names a game it didn't get from your library.
- **Agent loop:** the model can request tools, receive their results, and continue until it produces a final answer.
- **Error handling:** clear messages instead of crashes when the library hasn't been built, or when Ollama isn't running or stops mid-chat.
- **Runs locally:** uses [Ollama](https://ollama.com) with a local model, so there are no cloud AI services or AI costs (only a free Steam Web API key is needed).
- **Tested:** 18 pytest tests cover scoring, ranking, library cleaning and profile validation, without needing the model or the network.
- **Debug mode:** `DEBUG` flags in `main.py` and `mood_profile.py` show router decisions, tool calls and candidate lists.




## Example conversation

```
AI: Hello! How can I help you find a game today?
You: Hello i had a long day today and i am looking to relax
AI: Since you had a long day and want to relax, you might enjoy playing Planet Coaster. It's a great simulation game where you can design and manage your own theme park, which can be a fun and creative way to unwind. Alternatively, you could try Disney Dreamlight Valley, a charming game with cute characters and a peaceful atmosphere that might be just what you need to relax.
You: Do you have any sci-fi space colony sims?
AI: For a sci-fi space colony simulation, you might enjoy RimWorld. It offers a unique blend of resource management and survival elements, giving you a taste of what it's like to run a space colony. If you're looking for a more advanced experience, Oxygen Not Included is also a great choice. Its intricate systems and creative challenges will transport you to a sci-fi setting where you manage resources and survival in a colony.
You: Sounds great thank you!
AI: You're welcome! I hope you have a fantastic time playing RimWorld or Oxygen Not Included. If you need any more recommendations, feel free to ask!
You: quit
```


## How it works

```
User message
     │
     ▼
Router (YES/NO): is the user asking for a game?
     │
     ├── NO  → the model replies normally, no tools
     │
     └── YES → the model can call recommend_from_library(mood)
                    │
                    ▼
   ┌─ recommend_from_library ─────────────────────────────┐
   │ 1. Mood → profile (LLM, JSON, validated)             │
   │      "long day, want to relax"                       │
   │      → {Relaxing: 1.0, Casual: 0.6, ...}             │
   │ 2. Rank the library (pure Python)                    │
   │      tag strengths × weights, minimum match 0.4,     │
   │      +0.1 bonus for unplayed games                   │
   │ 3. Final pick (LLM)                                  │
   │      chooses 1–3 of the top 5 and explains why       │
   └──────────────────────────────────────────────────────┘
                    │
                    ▼
        The agent replies with the recommendation
```

The LLM never sees the whole library: code does the ranking, and the model only interprets the mood and chooses from the top candidates. This keeps every recommendation grounded in games the user actually owns.

The conversation history (`messages` list) is the agent's memory: every user message, model reply and tool result is appended to it and sent with each request.

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Chat loop, system prompt, router and agent loop; calls `recommend_from_library` when the user describes a mood || `main.py` | Chat loop, system prompt, router and agent loop; calls `recommend_from_library` when the user describes a mood |
| `mood_profile.py` | LLM steps: mood → validated tag profile, and the final pick of 1–3 games; `recommend_from_library` combines the whole pipeline |
| `mood_engine.py` | Pure Python: library cleaning, tag strengths, scoring, minimum threshold and backlog bonus |
| `build_library.py` | Builds the local `library.json` cache: owned games + SteamSpy tags with vote counts |
| `steam_library.py` | Fetches the user's owned games and playtime from the Steam Web API |
| `SteamSpy.py` | SteamSpy tag search, to be reused for the store fallback |
| `test_mood_engine.py`, `test_mood_profile.py` | 18 pytest tests for the pure functions |
| `test_connection.py` | Minimal check that Ollama is running and responding |

## Setup

**Requirements:** Python 3.10+, [Ollama](https://ollama.com), and a Steam account.

1. **Install Ollama and pull the model:**
   ```
   ollama pull qwen2.5:7b
   ```
2. **Clone the repo and create a virtual environment:**
   ```
   git clone https://github.com/EllieK-coder/first-ai-agent.git
   cd first-ai-agent
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   ```
3. **Add your Steam details** in a `.env` file in the project folder:
   ```
   STEAM_API_KEY=your-key
   STEAM_ID=your-17-digit-steam-id
   ```
   - Get a free API key at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey).
   - Your Steam ID is the 17-digit number starting with `7656119` (Steam → your name → Account details).
   - In Steam's privacy settings, set **Game details** to **Public**.
4. **Build your library** (once; takes a few minutes because of API rate limits):
   ```
   python build_library.py
   ```
5. **Run the agent:**
   ```
   python main.py
   ```
   Type `quit` to exit. Set `DEBUG = True` in `main.py` or `mood_profile.py` to see router decisions, tool calls and candidate lists.
6. **Run the tests:**
   ```
   pytest
   ```
## Challenges and lessons learned

- **Small models over-use tools.** With a 3B-parameter model, the agent originally searched for games even when the user just said "hi", and sometimes printed tool calls as plain text. Instructions in the system prompt alone did not fix this. Adding a separate **router** step, a single YES/NO question that small models handle well, solved it.
- **Deterministic parts belong in code.** The opening greeting is printed by the program, not generated by the model, so it is consistent every time.
- **External data is messy.** SteamSpy tags include games that only weakly match (action games under "Relaxing"). Tag vote counts are now normalised into 0–1 strengths per game, and a minimum match score filters out weak fits.
- **Treat model output as untrusted.** When asked to pick from 312 Steam tags, the model regularly invented tags ("Chill", "Angry", "Challenging"). Every tag is validated against the real list. Clamping bad weights was itself a bug: zero/negative weights meaning "avoid this" were being raised to 0.1, so they are now rejected instead.
- **Model size matters for structured output.** Same three moods, temperature 0:

  | | llama3.2 (3B) | qwen2.5 (7B) |
  |---|---|---|
  | Invented tags dropped | 7 | 1 |
  | Real tags kept (relax / anger / challenge) | 1 / 5 / 2 | 3 / 7 / 5 |

- **A smaller, curated tag list beats a long one.** Offering all 312 library tags let the model pick visual or setting tags (`Cute`, `Dark`) that describe how a game looks, not how it feels. A curated list of ~50 mood tags fixed the choices and made the prompt much shorter.
- **Examples beat rules.** The prompt asked for 4–8 tags but the model returned 2–3. Adding two worked examples (few-shot prompting) produced full 6–7 tag profiles.
- **Separate the pipeline steps.** The LLM never sees the whole library: code ranks the games, and the model only chooses from the top five and explains its choice. This keeps answers grounded in games the user actually owns.
- **Better prompts can expose scoring bugs.** Fuller profiles made results shorter, because scores were normalised by the weight of *all* tags, an implicit AND ("must match everything"). Moods are an OR ("cozy farming or a quiet drive"), so scores are now normalised by the top 3 weights.
- **Fail fast, fail friendly.** The agent checks once at startup that Ollama is reachable and exits with a clear message if not. During a chat, a lost connection is caught, the unanswered message is removed from the history, and the user can simply retry. Empty input is ignored in code rather than sent to the model, which would otherwise invent a reply.
- **Prompt rules are not guarantees.** The system prompt said "never name a game the tool didn't return", but when the router wrongly said NO, the model still invented games the user doesn't own (Factorio, Kerbal Space Program). The fix was in code: a keyword check before the LLM router, and a guardrail that runs the pipeline itself if the model skips the tool.
- **Give the model facts, or it fills gaps with fiction.** When the final pick only saw game names, it described SimCity 4 as a "sci-fi metropolis" to match the request. Passing each candidate's top Steam tags grounded the descriptions, and adding theme tags (Space, Sci-fi, Colony Sim) let "sci-fi base-building" find RimWorld.
- **Retrieve, then rerank.** Tag searches are cheap but imprecise (an ant-colony game appeared under "Space"). The top 10 candidates are reranked using their real tag votes, so 10 extra API calls make results precise without fetching details for thousands of games.
- **Real data finds bugs tests can't.** The mood list said `Base Building`, but Steam's tag is `Base-Building`, so the tag was silently dropped from every profile. And a temporary `MIN_SCORE = 1.1` left in one file quietly emptied every result in another: temporary changes need a revert checklist.

## Roadmap

**Goal for v1:** the user describes a mood in their own words ("I want to relax", "I need to release some anger"), and the agent recommends 1–3 games from their own library, prioritising the forgotten backlog. ✅ Done.
### v1: done ✅
- [x] Chat loop with conversation memory
- [x] Tool calling + hand-written agent loop
- [x] Router step so tools are only used when relevant
- [x] SteamSpy tag search tool
- [x] Fetch owned games and playtime from the Steam Web API
- [x] Cache the library with tags and vote counts in `library.json`
- [x] Clean the library: skip test servers / launcher entries, drop untagged games, merge exact-name duplicates
- [x] Normalise tag vote counts into a 0–1 strength per game
- [x] Scoring: rank owned games against a weighted mood profile (normalised by the top 3 weights)
- [x] Backlog bonus for unplayed / barely played games
- [x] Minimum score threshold, so weak matches are not recommended
- [x] Mood → profile: LLM turns the user's words into weighted tags as JSON, limited to a curated list of mood tags that exist in the library
- [x] Validate model output: drop invented tags and zero/negative weights, map common synonyms to real tags
- [x] **Final pick:** LLM chooses 1–3 games from the top candidates only and explains why
- [x] **Agent wiring:** `recommend_from_library(mood)` as a tool in the chat agent (qwen2.5:7b), with empty input ignored in code
- [x] **Backlog nudge in the final pick:** make the model include an unplayed game when one fits, and reply in plain text
- [x] **Error handling:** clear messages instead of crashes when `library.json` is missing, when Ollama isn't running at startup, and when Ollama stops mid-chat (the agent keeps running)
- [x] **Tests:** 18 pytest tests for the pure functions: tag strengths, scoring and the score cap, threshold, backlog bonus, sorting, library cleaning, and profile validation (no model or network needed)
- [x] **Router context + guardrail:** the router sees the agent's last message, obvious requests are caught by a keyword check, and code runs the pipeline if the model skips the tool
- [x] **Theme tags** (Space, Sci-fi, Colony Sim…) in the mood list, and each candidate's top tags passed to the final pick
- [x] **README:** setup (Steam API key and ID), how to run, an example conversation

### v2: discovering new games

**Goal:** when nothing you own fits, or when you ask for something new, recommend games from the Steam store that you don't own yet.

- [x] **Store engine:** `fetch_tag` (with timeout) and `rank_store`: search SteamSpy for the profile's top tags, exclude owned games and games with few reviews, rank by tag overlap with rating as tie-breaker (7 tests)
- [x] **Store fallback:** when no owned game passes the threshold, use the store engine in `recommend_from_library`, with a fixed intro in code saying the games aren't owned
- [x] Guardrails for the new path: store results passed to the final pick with their tags, API failures and timeouts handled
- [x] **Store engine:** `fetch_tag` (with timeout) and `rank_store`: search SteamSpy for the profile's top tags, exclude owned games and games with few reviews, rank by tag overlap with rating as tie-breaker (7 tests)
- [x] **Store fallback:** when no owned game passes the threshold, search SteamSpy and exclude games the user already owns
- [x] Guardrails for the new path: store results passed to the final pick with their tags, API failures and timeouts handled
- [x] **Rerank store candidates:** fetch real tag votes for the top 10 (SteamSpy `appdetails`) and score them with `score_game`; if the details calls fail, fall back to the unreranked top 5
- [ ] **`find_new_games(mood)`** as a second tool, reusing the mood profile
- [ ] **Owned or new:** ask "a game you own, or something new?" only when the user hasn't said; default to the library
- [ ] `get_game_details` (short description) from the Steam store; price already comes from SteamSpy

### After v2

**Recommendation quality**
- [ ] Treat themes as requirements: when the user names a setting (space, fantasy), filter candidates to games with that tag instead of relying on the prompt
- [ ] Negative weights (e.g. `Horror: -0.8` for "relax") to push down games with the wrong feel
- [ ] Handle different editions of the same game (e.g. Skyrim and Skyrim Special Edition)
- [ ] Follow-up question for ambiguous moods ("reflexes or strategy?")
- [ ] Evaluation set of moods with expected results; extend the model comparison

**Users, privacy and security**
- [ ] **Onboarding:** accept a Steam profile link, custom name or 17-digit ID at startup and resolve it (`ResolveVanityURL`), so users never edit config files
- [ ] **Multiple users:** Steam ID as a parameter everywhere; one library file per user
- [ ] **Split data:** a shared game catalog (tags, not personal data) separate from each user's library (owned games and playtime, personal data)
- [ ] **Retention:** user library data expires after 10 days and is rebuilt on next use
- [ ] **Delete my data** command that removes a user's data immediately
- [ ] **Data minimisation:** store only what scoring needs (appid, playtime)
- [ ] **Privacy note:** what is stored, where, for how long, and how to delete it
- [ ] **Security:** API key only in `.env` (never logged or committed), validate user input before API calls, timeouts on all requests, treat model output as untrusted
- [ ] Clear errors for private profiles and invalid IDs

**Learning from feedback (the machine-learning extension)**
- [ ] Log every recommendation as a structured record: mood profile, games shown, user reaction
- [ ] Use the LLM to turn free-form replies ("meh, not that one") into clean labels: liked / rejected / unsure
- [ ] Implicit feedback: compare playtime before and after a recommendation on the next library refresh
- [ ] Learn per-user tag weights from explicit + implicit feedback, instead of hand-tuning them
- [ ] Privacy: store profiles and tags, not the raw mood sentence; feedback logs follow the same retention and delete-my-data rules; let users turn logging off

**Maintenance**
- [ ] Incremental library refresh (only fetch tags for new games, resume after a crash)
- [ ] Config for model names and thresholds; logging instead of prints
- [ ] Updated architecture diagram

### Stretch
- [ ] Semantic search with embeddings over game descriptions
- [ ] Simple web UI
- [ ] "Sign in through Steam" (OpenID) instead of typing a Steam ID, if it ever becomes a hosted app

## Tech

Python · Ollama (qwen2.5:7b; llama3.2 for comparison) · Steam Web API · SteamSpy API · requests · pytest
