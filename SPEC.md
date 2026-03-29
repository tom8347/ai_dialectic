# Claude Dialogue Runner — Build Spec

Build a Python CLI tool that runs two Claude instances in conversation with each other. The project should be simple, readable, and self-contained.

## Core behaviour

- Each "agent" is defined by a config block containing: a name, a model string, a system prompt (identity description), and optionally a list of source material files
- The tool runs a back-and-forth dialogue for a configurable number of turns, maintaining a separate message history for each agent
- Each agent only sees what is explicitly passed to it — its own history plus the other agent's most recent message
- The opening message/topic is provided by the user at runtime

## CLI interface

```
python dialogue.py run --config my_dialogue.yaml --turns 10 --output conversations/
python dialogue.py run --config my_dialogue.yaml --turns 10 --resume conversations/my_dialogue_2024-01-01.json
```

## Config file format (YAML)

```yaml
dialogue:
  opening_message: "Is mathematics discovered or invented? Give your opening position."
  turns: 8

agents:
  - name: Platonist
    model: claude-opus-4-5
    identity: "You are a committed Platonist philosopher. Mathematical objects exist
      independently of human minds and physical reality. Be concise — 3 sentences max."
    sources:
      - sources/plato_meno.txt
      - sources/hardy_apology.txt

  - name: Formalist
    model: claude-sonnet-4-5
    identity: "You are a strict formalist. Mathematics is a game of symbols with
      no inherent meaning. Be concise — 3 sentences max. Respond directly to what was just said."
    sources:
      - sources/hilbert_foundations.txt
```

## Source material handling

- At the start of each agent's system prompt, prepend any source files as a clearly labelled block: `--- Source Material ---` followed by file contents
- If a source file doesn't exist, warn and skip rather than crashing

## Conversation storage

- Save the full dialogue to a timestamped JSON file in the output directory on completion (and after each turn, so it survives interruption)
- JSON structure should store: config used, each turn with agent name, model, timestamp, and message content, plus both agents' full internal histories
- Also write a human-readable `.txt` transcript alongside the JSON

## Models

- The model string is passed directly to the Anthropic API — no hardcoded list, so any valid model identifier works
- Validate at startup that the Anthropic API key is available and that both model strings are non-empty

## Dependencies

- `anthropic` (official Python SDK)
- `pyyaml`
- `rich` for terminal output (coloured agent names, turn counter)
- Nothing else

## Error handling

- Catch API errors per turn and print a clear message without crashing — allow the user to abort or continue
- If rate limited, wait and retry up to 3 times with backoff

## Deliverables

- `dialogue.py` — main entry point
- `README.md` — setup instructions (virtualenv, pip install, API key, example run)
- An example config file `examples/math_debate.yaml`
- A `sources/` directory with a placeholder `.gitkeep`

Keep the code straightforward — prioritise readability over cleverness. No classes needed if functions suffice. The whole thing should fit comfortably in a single `dialogue.py` file under ~250 lines.
