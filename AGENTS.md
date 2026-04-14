# Agent Patterns

This project does **not** use any agentic patterns (task delegation, background agents, skill loading, etc.). It is a pure Python data pipeline with conventional scripting.

## Why no agents

- **Scope**: The project converts flomo HTML exports to structured JSONL — a deterministic data transformation problem.
- **Architecture**: Traditional Python modules with single‑responsibility functions.
- **Tooling**: Uses standard Python libraries (BeautifulSoup, duckdb, pyarrow) and shell scripts.

## What you won't find

- `task()` calls
- `background_output()` collection
- `load_skills` configuration
- `explore` / `librarian` / `oracle` agents
- Agent‑specific configuration files

## Development workflow

The project follows conventional software engineering practices:

1. **Code changes** → Edit Python files directly
2. **Testing** → Run `pytest`
3. **Validation** → Run `validate_store.py`
4. **Build** → Run `build_store.py`
5. **Deployment** → Copy scripts to target environment

## macOS Launcher note

The `Memo Sync.app` launcher uses AppleScript and swiftDialog for GUI automation, but this is conventional macOS scripting, not agentic orchestration.

## If you want to add agents

Should you decide to introduce agentic patterns later:

1. **Task delegation** → Use `task(category="deep", ...)` for complex parsing logic
2. **Parallel exploration** → Use `explore` agents for multi‑file pattern discovery
3. **External research** → Use `librarian` for flomo API documentation
4. **Architecture review** → Use `oracle` for schema design validation

But for now, the project remains agent‑free by design.
