import sys

import ollama

from mood_profile import recommend_from_library

MODEL = "qwen2.5:7b"
DEBUG = False

available_tools = {"recommend_from_library": recommend_from_library}

messages = [
    {
        "role": "system",
        "content": (
            "You are a friendly assistant that helps the user decide what to play "
            "from games they already own on Steam. "
            "When the user describes their mood or what they feel like playing, "
            "call the recommend_from_library tool and pass their mood in their own words. "
            "Then share the tool's recommendation in a friendly, natural way. "
            "Only mention games that appear in the tool's answer; never add other games. "
            "If the user only greets you or makes small talk, reply naturally without using any tools. "
            "Never name a specific game unless it came from the recommend_from_library tool in this conversation. "
            "If the user seems to want a game but you haven't used the tool, ask them how they're feeling instead."
            "Write in plain text, without Markdown formatting such as ** or numbered lists. "
        ),
    }
]


def ollama_is_running() -> bool:
    """Return True if the Ollama server is reachable, otherwise False."""
    try:
        ollama.list()
        return True
    except ConnectionError:
        return False


WANT_WORDS = ("game", "play", "recommend", "suggest", "sim", "looking for", "in mind", "in the mood")


def wants_games(text: str, previous_reply: str) -> bool:
    """Router: decide if the user wants a game suggestion, using the agent's last message as context."""
    lowered = text.lower()
    if any(word in lowered for word in WANT_WORDS):
        if DEBUG:
            print("[router: YES (keyword)]")
        return True

    check = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Decide if the user wants a game suggestion right now. "
                    "This includes: describing a mood or feeling (tired, stressed, bored, angry), "
                    "describing what kind of game they want, "
                    "or asking for or agreeing to a suggestion the assistant just offered. "
                    "Greetings, thanks and small talk without a wish to play do not count. "
                    "Reply with only YES or NO.\n\n"
                    "Examples:\n"
                    'User: "Hello" -> NO\n'
                    'User: "I had a long day and want to relax" -> YES\n'
                    'User: "I want something in space" -> YES\n'
                    'User: "I was looking for a colony sim, any ideas?" -> YES\n'
                    'Assistant: "Want me to suggest something?" User: "Sounds great, what do you have in mind?" -> YES\n'
                    'User: "Thanks, sounds good!" -> NO'
                ),
            },
            {
                "role": "user",
                "content": f'Assistant\'s last message: "{previous_reply}"\nUser\'s message: "{text}"',
            },
        ],
        options={"temperature": 0},
    )
    answer = check.message.content.strip().upper()
    if DEBUG:
        print(f"[router: {answer}]")
    return answer.startswith("YES")


def recent_user_text(limit=3):
    """The user's last few messages joined together, so follow-ups keep their context."""
    user_messages = [m["content"] for m in messages if isinstance(m, dict) and m["role"] == "user"]
    return " ".join(user_messages[-limit:])


if not ollama_is_running():
    sys.exit("I can't reach Ollama. Please start the Ollama app and try again.")

greeting = "Hello! How can I help you find a game today?"
print("AI:", greeting)
messages.append({"role": "assistant", "content": greeting})
last_reply = greeting

while True:
    user_text = input("You: ")
    if not user_text.strip():
        continue
    if user_text == "quit":
        break

    messages.append({"role": "user", "content": user_text})

    try:
        if wants_games(user_text, last_reply):
            tools = [recommend_from_library]
        else:
            tools = []

        tool_used = False

        # keep going until the model stops asking for tools
        while True:
            response = ollama.chat(model=MODEL, messages=messages, tools=tools)
            messages.append(response.message)

            if not response.message.tool_calls:
                break

            for call in response.message.tool_calls:
                tool_used = True
                name = call.function.name
                args = call.function.arguments
                if DEBUG:
                    print(f"[using {name} with {args}]")

                result = available_tools[name](**args)

                messages.append({"role": "tool", "content": result, "tool_name": name})

        # guardrail: the user wants a game, but the model skipped the tool
        if tools and not tool_used:
            mood = recent_user_text()
            if DEBUG:
                print(f"[guardrail: running the pipeline with {mood!r}]")
            reply = recommend_from_library(mood)
            messages[-1] = {"role": "assistant", "content": reply}
        else:
            reply = response.message.content

        print("AI:", reply)
        last_reply = reply

    except ConnectionError:
        print("AI: I lost the connection to Ollama. Start it again and repeat your message.")
        messages.pop()