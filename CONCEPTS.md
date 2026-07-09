# Concepts Ledger (safety precaution #5)

Running record of concepts, libraries, and functions **first introduced** on each
day. Purpose: enforce the rule that a day may only use what earlier days have
already taught — no concept before it's introduced.

**Update this every time a day is authored**, and read it before authoring a new
day (the adversarial review, #3, checks new days against it).

| Day | First introduced |
|-----|------------------|
| 001 | AI pipelines; `edge_tts.Communicate`; async/await; `subprocess`; FFmpeg (via subprocess); "black-box model" concept; slides→audio→talking-head→composite flow |
| 002 | functions (`def`, params, `return`, defaults); type hints; docstrings; string methods (`.strip/.lower/.upper/.replace/.split/.join`); f-strings + format specs; string immutability; `' '.join(text.split())` whitespace-collapse idiom; lists; dicts; `.get(k, default)`; `for` loops; list & dict comprehensions (+ `if` filter); files (`open`/`with`, `'r'`/`'w'`); `json` (`dump`/`load`/`dumps`/`loads`); `try`/`except` (`FileNotFoundError`, `JSONDecodeError`); Load→Clean→Validate→Save pattern |
| 003 | `ollama` runtime (`pip install ollama`); `ollama.chat(model, messages)`; `response["message"]["content"]`; `openai` package (`pip install openai`); `OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")`; `client.chat.completions.create()`; `response.choices[0].message.content`; `requests.post()` for raw HTTP; `POST http://localhost:11434/api/chat`; `"stream": False` (Ollama defaults to streaming NDJSON); `response.raise_for_status()`; `response.json()`; `{"role": "system"/"user"/"assistant", "content": "..."}` message format; system prompt as first message in the list; multi-turn history as a growing messages list; `input()` built-in; `while True:` loop; `break`; `continue` |
