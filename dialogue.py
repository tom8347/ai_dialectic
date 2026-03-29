#!/usr/bin/env python3
"""Claude Dialogue Runner — run two Claude instances in conversation."""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
import pypdf
import yaml
from rich.console import Console
from rich.text import Text

console = Console()


# ── Config loading ────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


SOURCES_ROOT = Path("sources")
AGENT_SLOTS = ["agent_a", "agent_b"]
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = pypdf.PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(errors="replace")


def load_slot_sources(slot: str) -> list[tuple[str, str]]:
    """Return list of (filename, content) for all supported files in sources/<slot>/."""
    folder = SOURCES_ROOT / slot
    if not folder.exists():
        return []
    files = sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES)
    results = []
    for f in files:
        try:
            results.append((f.name, read_file(f)))
        except Exception as e:
            console.print(f"[yellow]Warning: could not read {f}: {e}[/yellow]")
    return results


def build_system_prompt(agent: dict, slot: str) -> str:
    parts = []

    source_files = load_slot_sources(slot)
    if source_files:
        parts.append("--- Source Material ---")
        for name, content in source_files:
            parts.append(f"\n[{name}]\n{content}")
        parts.append("--- End Source Material ---\n")

    parts.append(agent["identity"])
    return "\n".join(parts)


def validate_config(cfg: dict) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set.[/red]")
        sys.exit(1)

    agents = cfg.get("agents", [])
    if len(agents) != 2:
        console.print("[red]Error: exactly 2 agents required.[/red]")
        sys.exit(1)

    for agent in agents:
        if not agent.get("model"):
            console.print(f"[red]Error: agent '{agent.get('name', '?')}' has no model.[/red]")
            sys.exit(1)


# ── Conversation state ────────────────────────────────────────────────────────

def make_state(cfg: dict, config_path: str) -> dict:
    return {
        "config_path": config_path,
        "config": cfg,
        "turns": [],
        "histories": {agent["name"]: [] for agent in cfg["agents"]},
    }


def load_state(resume_path: str) -> dict:
    with open(resume_path) as f:
        return json.load(f)


# ── Persistence ───────────────────────────────────────────────────────────────

def make_run_dir(output_dir: str, config_path: str) -> Path:
    stem = Path(config_path).stem
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = Path(output_dir) / f"{stem}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_sources_manifest(run_dir: Path, sources_used: dict[str, list[str]]) -> None:
    path = run_dir / "sources.txt"
    with open(path, "w") as f:
        f.write("Source material used in this run\n")
        f.write("=" * 40 + "\n\n")
        for slot_label, files in sources_used.items():
            f.write(f"{slot_label}:\n")
            if files:
                for fname in files:
                    f.write(f"  • {fname}\n")
            else:
                f.write("  (none)\n")
            f.write("\n")


def save_state(state: dict, run_dir: Path) -> None:
    with open(run_dir / "dialogue.json", "w") as f:
        json.dump(state, f, indent=2)

    with open(run_dir / "dialogue.txt", "w") as f:
        cfg = state["config"]
        f.write(f"Dialogue: {cfg.get('dialogue', {}).get('opening_message', '')}\n")
        f.write("=" * 72 + "\n\n")
        for turn in state["turns"]:
            f.write(f"[Turn {turn['turn']}] {turn['agent']} ({turn['model']})\n")
            f.write(f"{turn['timestamp']}\n")
            f.write("-" * 40 + "\n")
            f.write(turn["content"] + "\n\n")


# ── API call with retry ───────────────────────────────────────────────────────

def call_api(client: anthropic.Anthropic, model: str, system: str,
             messages: list) -> str:
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 2)
            console.print(f"[yellow]Rate limited. Waiting {wait}s (attempt {attempt + 1}/3)…[/yellow]")
            time.sleep(wait)
        except anthropic.APIError as e:
            console.print(f"[red]API error: {e}[/red]")
            raise

    console.print("[red]Rate limit retries exhausted.[/red]")
    raise RuntimeError("Rate limit retries exhausted")


# ── Main dialogue loop ────────────────────────────────────────────────────────

def run_dialogue(cfg: dict, state: dict, total_turns: int, run_dir: Path) -> None:
    client = anthropic.Anthropic()
    agents = cfg["agents"]
    system_prompts = {}
    sources_used = {}
    for ag, slot in zip(agents, AGENT_SLOTS):
        files = load_slot_sources(slot)
        label = f"{ag['name']} ({slot})"
        sources_used[label] = [fname for fname, _ in files]
        folder = SOURCES_ROOT / slot
        if files:
            console.print(f"[dim]{label}: loaded {len(files)} source file(s) from {folder}/[/dim]")
            for fname, _ in files:
                console.print(f"[dim]  • {fname}[/dim]")
        else:
            console.print(f"[dim]{label}: no source files in {folder}/[/dim]")
        system_prompts[ag["name"]] = build_system_prompt(ag, slot)

    save_sources_manifest(run_dir, sources_used)
    histories = state["histories"]

    # Determine starting turn and seed message
    completed = len(state["turns"])
    opening = cfg["dialogue"]["opening_message"]

    if completed == 0:
        pending_message = opening
        turn_index = 0
    else:
        last_turn = state["turns"][-1]
        pending_message = last_turn["content"]
        turn_index = completed

    console.print(f"\n[bold]Opening:[/bold] {opening}\n")

    while turn_index < total_turns:
        current = agents[turn_index % 2]
        name = current["name"]

        histories[name].append({"role": "user", "content": pending_message})

        turn_num = turn_index + 1
        label = Text(f"[Turn {turn_num}/{total_turns}] {name}", style="bold cyan" if turn_index % 2 == 0 else "bold magenta")
        console.print(label)

        try:
            reply = call_api(
                client,
                current["model"],
                system_prompts[name],
                histories[name],
            )
        except Exception as e:
            console.print(f"[red]Error on turn {turn_num}: {e}[/red]")
            answer = console.input("[yellow]Continue? (y/n): [/yellow]").strip().lower()
            if answer != "y":
                break
            turn_index += 1
            continue

        histories[name].append({"role": "assistant", "content": reply})

        state["turns"].append({
            "turn": turn_num,
            "agent": name,
            "model": current["model"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content": reply,
        })

        console.print(reply)
        console.print()

        save_state(state, run_dir)

        pending_message = reply
        turn_index += 1

    console.print(f"\n[green]Dialogue complete. Saved to {run_dir}/[/green]")


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_run(args: argparse.Namespace) -> None:
    if args.resume:
        state = load_state(args.resume)
        cfg = state["config"]
        run_dir = Path(args.resume).parent
    else:
        cfg = load_config(args.config)
        validate_config(cfg)
        out_dir = args.output or "conversations"
        run_dir = make_run_dir(out_dir, args.config)
        shutil.copy2(args.config, run_dir / "config.yaml")
        state = make_state(cfg, args.config)

    turns = args.turns or cfg.get("dialogue", {}).get("turns", 8)
    validate_config(cfg)
    run_dialogue(cfg, state, turns, run_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run two Claude instances in dialogue.")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a dialogue")
    run_p.add_argument("--config", required=False, help="Path to YAML config file")
    run_p.add_argument("--turns", type=int, help="Number of turns (overrides config)")
    run_p.add_argument("--output", help="Output directory (default: conversations/)")
    run_p.add_argument("--resume", help="Resume from a saved JSON file")

    args = parser.parse_args()

    if args.command == "run":
        if not args.resume and not args.config:
            run_p.error("--config is required unless --resume is given")
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
