# Claude Dialogue Runner

Run two Claude instances in conversation with each other.

## Setup

### 1. Enter the dev environment

```bash
direnv allow   # first time only
```

### 2. Set your API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Run a dialogue from a config file
python dialogue.py run --config examples/math_debate.yaml

# Override the number of turns
python dialogue.py run --config examples/math_debate.yaml --turns 6

# Specify an output directory
python dialogue.py run --config examples/math_debate.yaml --output conversations/

# Resume an interrupted dialogue
python dialogue.py run --resume conversations/math_debate_2024-01-01_120000.json
```

Output is saved to `conversations/` as a timestamped `.json` + `.txt` pair, written after every turn.

## Config format

```yaml
dialogue:
  opening_message: "Your question or topic here."
  turns: 8

agents:
  - name: SomeName        # display name only — doesn't affect source loading
    model: claude-opus-4-5
    identity: "You are ..."

  - name: AnotherName
    model: claude-sonnet-4-5
    identity: "You are ..."
```

- **name**: used for display and transcripts only — change it freely
- **identity**: the system prompt / character description for this agent
- **model**: any valid Anthropic model identifier

## Source material

Drop `.txt`, `.md`, or `.pdf` files into the agent slot folders:

```
sources/
  agent_a/    ← source material for the first agent in config
  agent_b/    ← source material for the second agent in config
```

Files are loaded alphabetically and prepended to the agent's system prompt. The folders are fixed (`agent_a`, `agent_b`) so you can freely change agent names and identities without moving files around. At startup the tool prints which files each agent loaded.

## Example

```bash
python dialogue.py run --config examples/math_debate.yaml --turns 4
```
