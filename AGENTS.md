# Game Reviews Website — Agent Guide

## Project Overview

A Flask web application for publishing game reviews. Content is pulled from YAML files and Steam's API data, stored in SQLite, and rendered with Jinja2 templates. The site is deployed behind a path prefix (`/game-reviews`) in production. The site is branded as **"Suukin's Selection"**.

## Tech Stack

- **Backend:** Flask 3.0.3
- **Auth:** Session-based form authentication (login/logout via `/login` and `/logout`)
- **Templates:** Jinja2 with `.j2` extension
- **CSS Framework:** Bootstrap 5.3.3 (dark theme via `data-bs-theme="dark"`)
- **Database:** SQLite (`database.db`)
- **Production Server:** waitress 3.0.0
- **Markdown:** Python-Markdown (renders post content), EasyMDE editor (for create/edit forms)
- **JS Dependencies:** Bootstrap 5.3.3 bundle (includes Popper), EasyMDE 2.18.0

## Key Files

| File | Purpose |
|------|---------|
| `review_website.py` | Main Flask app — routes, auth, DB helpers, PrefixMiddleware |
| `schema.sql` | Database schema (posts, app_info, tags, posts_tags) |
| `init_db.py` | Initialize DB from `schema.sql` and seed a test post |
| `fill_db_posts.py` | Populate posts from `reviews.yaml` |
| `fill_db_app_info.py` | Populate app_info from Steam API data |
| `upgrade_db_tags.py` | Database migration for adding tags support |
| `fetch_appid.py` | Utility to fetch Steam app IDs |
| `steam_data_collector.py` | Collects Steam API data |
| `reviews.yaml` / `reviews2.yaml` | Source data for reviews (YAML format) |
| `steam_data/*.json` | Cached Steam API data per app_id |

## Directory Structure

```
review_website/
├── review_website.py            # Main app
├── schema.sql                   # DB schema
├── database.db                  # SQLite database
├── database_backup.db           # Backup copy of the database
├── templates/                   # Jinja2 templates (.j2)
│   ├── base.j2                  # Base layout with navbar and 3-column layout
│   ├── index.j2                 # Homepage — lists all reviews
│   ├── post.j2                  # Generic post view (non-Steam)
│   ├── steam_post.j2            # Steam game post view with header/background
│   ├── create.j2                # Create new post form (EasyMDE editor)
│   ├── edit.j2                  # Edit existing post form (EasyMDE editor)
│   ├── about.j2                 # About page
│   └── login.j2                 # Login form
├── static/
│   └── css/style.css            # Custom styles (includes EasyMDE dark theme)
│   └── images/                  # Static images (e.g., steam_logo.svg)
├── steam_data/                  # Cached Steam API JSON per app_id
├── steam.json                   # Raw Steam API data dump
├── steam_matches.json           # Matched Steam app data
├── steam_no_match.txt           # Games with no Steam match
└── ...
```

## Database Schema

### `posts`
- `id` — auto-increment PK
- `created` — timestamp
- `title` / `content` — post data (content is Markdown)
- `app_id` — Steam app ID (nullable)
- `store` — defaults to `"other"`, `"steam"` for Steam games

### `app_info`
- `app_id` — PK, matches Steam app ID
- `detailed_description`, `header_image`, `background`, `genres`, `extra` — Steam API data

### `tags` / `posts_tags`
- Many-to-many relationship between posts and tags
- `tags`: `tag_id` (PK), `title`, `color`
- `posts_tags`: `post_id`, `tag_id` (links posts to tags)

## Routes

| Route | Methods | Auth Required | Description |
|-------|---------|---------------|-------------|
| `/` | GET | No | Homepage with all posts |
| `/about` | GET | No | About page |
| `/<store>/<post_id>` | GET | No | View a single post |
| `/login` | GET, POST | No | Login form |
| `/logout` | POST | Yes (logged in) | Log out |
| `/create` | GET, POST | Yes | Create a new post |
| `/<store>/<id>/edit` | GET, POST | Yes | Edit a post |
| `/<store>/<id>/delete` | POST | Yes | Delete a post |

## Authentication

Uses **session-based form authentication**:
- Login via `/login` (GET/POST) — checks username/password against an in-memory dict
- Logout via `/logout` (POST) — clears `session['logged_in']`
- `login_required` decorator checks `session.get('logged_in')` before allowing access
- In dev: hardcoded user `dev` / `welcome`
- In production: credentials from `AUTH_USER` / `AUTH_PASS` env vars
- The "New Post" nav link renders only when the user is logged in (`session.get('logged_in')`)
- Login/Logout buttons appear in the navbar based on session state

## Deployment

### Production Mode
Set `PRODUCTION=1` environment variable to enable production mode:
- `SECRET_KEY` loaded from `SECRET_KEY` env var
- Auth credentials from `AUTH_USER` / `AUTH_PASS` env vars
- `PrefixMiddleware` wraps the app at `/game-reviews` prefix

### PrefixMiddleware
The app uses a custom WSGI middleware (`PrefixMiddleware`) that:
- Strips the `/game-reviews` prefix from incoming request paths
- Sets `SCRIPT_NAME` so `url_for()` generates correct URLs with the prefix
- This is critical — URLs in templates and redirects rely on this

### Running in Production
```
PRODUCTION=1 AUTH_USER=xxx AUTH_PASS=xxx SECRET_KEY=xxx waitress-serve --call review_website:app
```

## Template Conventions

- All templates use `.j2` extension
- `base.j2` defines the layout with:
  - Top navbar (brand "Suukin's Selection" + nav links)
  - 3-column layout: left panel (1 col), content (8 cols), right panel (1 col)
  - Left and right panels use `steam_blue` background class
  - Flash messages rendered in the content area
  - Login/Logout buttons in the navbar (right-aligned)
  - EasyMDE CSS loaded from CDN
- Child templates extend via `{% block content %}`, `{% block left_panel %}`, `{% block right_panel %}`
- Bootstrap 5 classes are used throughout
- Create and edit templates use the **EasyMDE** markdown editor

## CSS Conventions

- Custom styles in `static/css/style.css`
- Steam-inspired color scheme with `.steam_blue` (`#1b2838`)
- `.store_image` (48×48) and `.capsule_image` (460×215) for game imagery
- `.left_panel` / `.right_panel` / `.fullscreen` for layout positioning
- EasyMDE dark theme overrides for the markdown editor

## Development Workflow

### Using `uv`
Use the `uv` skill for all Python-related tasks. Instead of `pip`, `python`, or `venv`:

- **Run scripts:** `uv run script.py` (e.g., `uv run init_db.py`, `uv run fill_db_posts.py`)
- **Add dependencies:** `uv add <package>` (updates `requirements.txt` or `pyproject.toml`)
- **One-off deps:** `uv run --with requests script.py`

This avoids manual venv management and ensures reproducible environments.

## Content Rendering

- Post content is stored as **Markdown** and rendered to HTML server-side using Python-Markdown
- Enabled extensions: `tables`, `fenced_code`, `codehilite`, `toc`, `nl2br`
- The `render_markdown()` function in `review_website.py` handles this
