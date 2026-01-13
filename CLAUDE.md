# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a new Python project (kv_pet). The repository is currently in its initial state with only configuration files.

## Development Setup

This is a Python project. Once dependencies are added, typical setup would be:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Planning Workflow

Implementation plans are generated externally and stored in `.plans/current.md`.

When implementing from a plan:
1. Read `.plans/current.md` fully before starting
2. Follow implementation steps in order
3. Mark items complete with `[x]` as you finish them
4. Add notes to the Notes section for any deviations or blockers
5. Move completed plans to `.plans/archive/` when done

To start: "Read .plans/current.md and implement the plan"
To continue: "Continue with the next unchecked item"

## License

Apache License 2.0