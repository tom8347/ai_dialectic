# Claude Dialogue Runner — Project Context

## What this is

A CLI tool that runs two Claude instances in conversation with each other. Each agent has an independent context window and system prompt. The only information shared between agents is the most recent reply, passed as a new user message to the other agent's history.

## Entry point

`dialogue.py` — single file, ~280 lines. All logic lives here.

## Running a dialogue

```bash
python dialogue.py run --config examples/ai_doom.yaml
python dialogue.py run --config examples/ai_doom.yaml --turns 6
python dialogue.py run --resume conversations/ai_doom_2026-03-28_161523/dialogue.json
```

## Config format

```yaml
dialogue:
  opening_message: "The question or topic."
  turns: 20

agents:
  - name: Display Name     # display only — change freely
    model: claude-opus-4-6
    identity: "System prompt / character description."

  - name: Another Name
    model: claude-opus-4-6
    identity: "System prompt / character description."
```

Agent names are for display and transcripts only. Identities and models can be changed freely per run.

## Source material

Drop `.txt`, `.md`, or `.pdf` files into:

```
sources/
  agent_a/    ← read by the first agent in config
  agent_b/    ← read by the second agent in config
```

Folders are positional (not name-based) so agent identities can change without moving files. Files are loaded alphabetically and prepended to the system prompt under `--- Source Material ---`.

## Output structure

Each run produces a timestamped subfolder:

```
conversations/
  <config-stem>_<YYYY-MM-DD_HHMMSS>/
    dialogue.txt     — human-readable transcript
    dialogue.json    — full state: config, all turns with metadata, both message histories
    config.yaml      — copy of the config used
    sources.txt      — list of source files loaded per agent
```

Files are written after every turn so interrupted runs preserve all completed turns. Resume with `--resume`.

## Dependencies

All from nixpkgs — no pip/venv needed:
- `anthropic` — Anthropic Python SDK
- `pyyaml` — config parsing
- `rich` — terminal output
- `pypdf` — PDF text extraction

## Dev environment

```bash
direnv allow    # first time
export ANTHROPIC_API_KEY=sk-ant-...
```

## Key design decisions

- **Stateless API calls**: no sessions, no shared state between turns beyond the explicit message lists
- **Separate histories**: each agent has its own `messages` list; they never merge
- **No hardcoded models**: model string passed directly to the API — any valid identifier works
- **Neutral identity**: setting a minimal identity (e.g. "Respond directly to what was said.") gives near-vanilla Claude behaviour without imposing a character
- **Single file**: all logic in `dialogue.py` — no modules, no classes unless added later
