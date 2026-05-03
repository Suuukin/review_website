# Suukin's Selection — Dev Reference

## Quick Start

```bash
uv sync            # install Python deps
make dev           # start dev server (auto-restarts on changes)
make tail-log      # watch logs
```

## Common Commands

```bash
make check     # ruff lint check
make format    # ruff format + fix
make clean     # remove __pycache__
make dev-stop  # stop the dev server
ruff format <file>  # format a Python file
ruff check --fix <file>  # fix linting issues, sort imports
```

## Server

- Dev: http://localhost:5000
- Production prefix: `/game-reviews` (behind `PrefixMiddleware`)

## Stack

- Backend: Flask 3.0 + SQLite
- Templates: Jinja2 (`.j2`)
- CSS: Bootstrap 5.3.3 (dark theme)
- Markdown: Python-Markdown + EasyMDE editor
- Python runner: `uv`
- Dev reload: `watchexec` (watches `.py`, `.j2`, `.css`)

## Data

- SQLite DB: `database.db`
- Source reviews: `reviews.yaml`, `reviews2.yaml`
- Cached Steam data: `steam_data/*.json`

## Auth

- Dev: `dev` / `welcome`
- Production: `AUTH_USER` / `AUTH_PASS` env vars
- Login via `/login`, logout via `/logout` (session-based)
