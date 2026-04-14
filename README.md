# JSONL-Extracter

A structured data pipeline that converts flomo HTML exports into a JSONL truth layer, with analytics and preview layers.

## What it does

1. **Import** — Parse flomo HTML exports (`raw/`) into structured JSONL records (`store/`)
2. **Validate** — Enforce schema constraints (C1–C11) on the truth layer
3. **Analyze** — Build DuckDB/Parquet analytics from JSONL (`analytics/`)
4. **Preview** — Generate monthly Markdown summaries (`preview/`)
5. **Sync** — macOS GUI launcher for one-click validate→build workflow

## Architecture

```
raw/                          # Source HTML exports (read‑only)
├── 2025/
│   └── flomo@isaacbao-20250101/
│       ├── IsaacBao的笔记.html
│       └── file/
│           └── 2025‑01‑01/
│               └── {hash}/
│                   └── image.png
└── 2026/
    └── ...

store/                        # JSONL truth layer
├── memos.jsonl               # Memo records
├── images.jsonl              # Image records
├── missing_images.jsonl      # Missing image records
└── images/                   # Copied image files
    └── YYYY/YYYY‑MM/{image_uid}.png

analytics/                    # Derived analytics layer
├── memos.parquet
├── images.parquet
└── warehouse.duckdb          # DuckDB database with views

preview/                      # Human‑readable preview layer
└── monthly_markdown/
    └── YYYY‑MM.md
```

## Schema

Three core tables (see [`docs/schema.md`](docs/schema.md) for full details):

### `memos.jsonl`

```json
{
  "memo_uid": "flomo‑isaacbao‑20250101‑001",
  "created_at": "2025‑01‑01T12:34:56Z",
  "body_md": "Today I learned…",
  "image_count": 2,
  "batch_label": "20250101",
  "source_relpath": "2025/flomo@isaacbao‑20250101/IsaacBao的笔记.html",
  "ordinal": 1
}
```

### `images.jsonl`

```json
{
  "image_uid": "flomo‑isaacbao‑20250101‑001‑img‑1",
  "memo_uid": "flomo‑isaacbao‑20250101‑001",
  "image_relpath": "images/2025/2025‑01/flomo‑isaacbao‑20250101‑001‑img‑1.png",
  "source_relpath": "2025/flomo@isaacbao‑20250101/file/2025‑01‑01/{hash}/image.png",
  "ordinal": 1
}
```

### `missing_images.jsonl`

```json
{
  "image_uid": "flomo‑isaacbao‑20250101‑001‑img‑2",
  "memo_uid": "flomo‑isaacbao‑20250101‑001",
  "source_relpath": "2025/flomo@isaacbao‑20250101/file/2025‑01‑01/{hash}/missing.png"
}
```

## Constraints (C1–C11)

| ID  | Constraint                                                     | Severity |
| --- | -------------------------------------------------------------- | -------- |
| C1  | `memo_uid` uniqueness                                          | ERROR    |
| C2  | `image_uid` uniqueness                                         | ERROR    |
| C3  | `image_count` matches actual referenced images                 | ERROR    |
| C4  | `images.jsonl.memo_uid` references existing memo               | ERROR    |
| C5  | `missing_images.jsonl.memo_uid` references existing memo       | ERROR    |
| C6  | Same `image_uid` not in both images and missing_images         | ERROR    |
| C7  | All path fields are relative (no absolute paths)               | ERROR    |
| C8  | `image_relpath` file exists                                    | WARNING  |
| C9  | `source_relpath` exists for images, missing for missing_images | WARNING  |
| C10 | `created_at` valid ISO‑8601                                    | ERROR    |
| C11 | `body_md` contains no frontmatter                              | WARNING  |

## Quick start

### 1. Install dependencies

```bash
pip install beautifulsoup4 duckdb pyarrow
```

### 2. Import raw exports

```bash
python scripts/build_store.py --raw-root raw --store-root store
```

### 3. Validate the store

```bash
python scripts/validate_store.py --store-root store
```

### 4. Build analytics

```bash
python scripts/build_analytics.py --store-root store --analytics-dir analytics
```

### 5. Build preview

```bash
python scripts/build_preview.py --store-root store --preview-dir preview
```

## macOS Launcher

A Spotlight‑searchable GUI app that runs validate→build in one click.

### Install

```bash
# 1. Install swiftDialog
brew install swiftdialog

# 2. Build the launcher
tools/apple/build_app.sh

# 3. Search "Memo Sync" in Spotlight, or double‑click ~/Applications/Memo Sync.app
```

### Features

- Real‑time status window with swiftDialog
- Validate Store → Build Store pipeline
- Open Cursor / Open Finder buttons
- Graceful error handling (missing swiftDialog, store directory, etc.)

## Development

### Run tests

```bash
python -m pytest tests/ -v
```

### Project structure

```
src/
├── models.py          # Dataclasses: MemoRecord, ImageRecord, MissingImageRecord
├── parser.py          # FlomoParser: HTML → markdown, batch discovery
├── writer.py          # StoreWriter: JSONL write + image copy
└── validator.py       # StoreValidator: 13 validation rules

scripts/
├── build_store.py     # CLI: raw → store
├── validate_store.py  # CLI: validate store with --strict/--summary
└── launch_memo_sync.sh # Shell helper for macOS launcher

tools/apple/
├── Memo Sync.applescript  # AppleScript source
└── build_app.sh           # Compile .app with injected project path
```

### Code style

- Python 3.11+
- Type‑checked with mypy (strict)
- Formatted with ruff
- Single‑responsibility functions
- No unnecessary comments/docstrings

## Full workflow

See [`docs/runbook.md`](docs/runbook.md) for detailed operational procedures, including full rebuild steps and troubleshooting.

## License

MIT
