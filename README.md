# hannyHR

An HR documentation tool for recording **why** team members took leave. Uses the
[EAV (Entity–Attribute–Value)](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model)
pattern so HR can define, per leave type, exactly which documentation items are
collected — and which ones are required.

Leave types are fully configurable by HR — e.g. **Injury**, **Maternity**,
**Paternity**, **Death in the Family** — and each generates a tailored form at
fill-out time, so the tool never hard-codes a leave reason.

---

## Features

- **Dynamic forms** — HR defines attributes per leave type; the form is generated at request time from those definitions.
- **9 supported field types**: text, textarea, rich text, number, date, yes/no, dropdown, multi-select, file upload.
- **Required/optional items** — HR marks any item as *required* (must be completed).
- **Conditional fields** — show/hide items based on the value of another field (e.g. "Accident report number" only appears when the injury is work-related).
- **Validation rules** — min/max (numbers & dates), length & regex (text), max file size.
- **Leave record view** — read-only page listing every documented item and its value, plus uploaded attachments.
- **Filterable request list** — filter by leave type or employee.
- **Django admin** — full UI for managing employees, leave types, and their attributes.
- **Two deployment options** — SQLite (zero-config default) or PostgreSQL, via Docker Compose.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django 6 (Python 3.12) |
| EAV engine | Custom (`leave` app) |
| Templates | Server-rendered Django templates |
| Styling | Hand-rolled CSS (no framework) |
| Rich text | Zero-dependency contenteditable widget |
| Serving | Django dev server or Gunicorn + WhiteNoise |
| DB | SQLite or PostgreSQL (`psycopg`) |

---

## Architecture

```
LeaveType (entity) ──1──*── LeaveAttribute ──1──*── LeaveAttrOption
     │                                              (choices for select/multiselect)
     │ 1
     │ *
LeaveRequest ──1──*── LeaveAttributeValue
 (employee, dates,   value_text | value_file
  summary, status)
```

| Model | EAV role | Purpose |
|---|---|---|
| `LeaveType` | Entity | A category of leave (Injury, Maternity, …) |
| `LeaveAttribute` | Attribute | A dynamic form field: type, required, validation, condition |
| `LeaveAttrOption` | Attribute options | Choices for dropdown / multi-select fields |
| `LeaveRequest` | Entity instance | One leave event for an employee (with standard from/to dates) |
| `LeaveAttributeValue` | Value | The recorded value(s) for an attribute on a request |

### Defining a dynamic field

Every `LeaveAttribute` belongs to a `LeaveType` and stores:

- `field_type` — one of `text`, `textarea`, `richtext`, `number`, `date`, `boolean`, `select`, `multiselect`, `file`
- `required` — HR sign-off item the request must include
- `validation_rules` (JSON) — e.g.

```json
{"min": 1, "max": 30}                              // number / date bounds
{"min_length": 2, "max_length": 500, "regex": "^[A-Z]"}  // text
{"max_size_mb": 10}                                // file uploads
```

- `condition` (JSON) — conditional display:

```json
{"depends_on": "injury_type", "operator": "equals", "value": "work_related"}
{"depends_on": "injury_type", "operator": "in", "value": ["work_related", "sports"]}
```

Supported operators: `equals`, `not_equals`, `in`. Hidden fields are also
skipped server-side, so a *required* conditional field never blocks the form
when its condition isn't met.

### Where the logic lives

- **Form builder**: `leave/forms.py` → `LeaveDynamicForm`
- **Persistence**: `leave/forms.py` → `save_dynamic_values()`
- **Views**: `leave/views.py` (type dashboard, request create/edit/detail, list)
- **Admin**: `leave/admin.py` + `employees/admin.py`

---

## Prerequisites

- **Option A — Docker (recommended):** Docker Engine 24+ and Docker Compose v2.
- **Option B — Local:** Python 3.12.

---

## Option A: Docker Compose

Build the image once:

```bash
docker compose build
```

### A1. SQLite (default, zero-config)

```bash
docker compose up -d
```

Opens on **http://localhost:8050** (host port `8050`, so it won't clash with
other projects). The SQLite file and uploaded media live in
`./db.sqlite3` / the `media_data` volume.

### A2. PostgreSQL

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d
```

The override adds a `db` service (PostgreSQL 16, host port `5433`) with a
healthcheck, and points the web container at it via `DB_ENGINE=postgres`,
`POSTGRES_HOST=db`. Data persists in the `pgdata` volume.

### First run (either DB)

```bash
docker compose exec web python manage.py seed_demo
```

This creates a superuser `hr / hannyhr123` plus sample employees and four leave
types (Injury, Maternity, Paternity, Death in the Family) with realistic
attributes and conditional logic.

Log in at **http://localhost:8050**:

| URL | Purpose |
|---|---|
| `/` | HR dashboard — leave types & recent records |
| `/admin/` | Configure employees, leave types, attributes |
| `/new/` | Document a leave (pick employee + type → tailored form) |
| `/requests/` | Filterable list of all leave records |

### Choosing the server mode

The entrypoint picks the server based on `DEBUG` in `.env`:

| `DEBUG` | Server |
|---|---|
| `True` (default) | Django dev server (auto-reload) |
| `False` | Gunicorn (3 workers) + WhiteNoise for static files |

Override workers with `GUNICORN_WORKERS` in `.env`.

### Useful commands

```bash
docker compose logs -f web          # follow logs
docker compose down                 # stop (keeps DB volumes)
docker compose down -v              # stop and delete volumes (data loss!)
docker compose exec web python manage.py test leave
```

---

## Option B: Run locally (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                # then edit as needed
python manage.py migrate
python manage.py seed_demo
python manage.py runserver          # → http://localhost:8000
```

Connect to a real PostgreSQL instead of SQLite by editing `.env`:

```text
DB_ENGINE=postgres
POSTGRES_DB=hannyhr
POSTGRES_USER=hannyhr
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

> Port note: this repo's compose files use **8050** (web) and **5433**
> (postgres) because `8000`/`5432` are commonly occupied. Edit the
> `ports:` mappings in `docker-compose*.yml` if you prefer the standard ports.

---

## Configuration reference (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `DEBUG` | `True` | `True` → dev server, `False` → gunicorn |
| `SECRET_KEY` | dev key | **Change in production.** |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `DB_ENGINE` | `sqlite` | `sqlite` or `postgres` |
| `DB_NAME` | `db.sqlite3` | Path to sqlite file (relative to repo root) |
| `POSTGRES_DB/_USER/_PASSWORD` | `hannyhr` | Used when `DB_ENGINE=postgres` |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `localhost` / `5432` | `db` / `5432` under compose |
| `GUNICORN_WORKERS` | `3` | Gunicorn process count (docker only) |

---

## Tests

```bash
# Docker:
docker compose exec web python manage.py test leave

# Local:
.venv/bin/python manage.py test leave
```

10 tests cover field-type mapping, validation rules, conditional required
logic (hidden vs. visible), value save/reload round-trips, and the full
create/edit HTTP flows.

---

## Project layout

```
config/            settings, URL routing
employees/         Employee model + admin
leave/             EAV engine: models, dynamic forms, views, admin, tests
templates/         base, dashboard, select, form, list, detail
static/            CSS + conditional-visibility / rich-text JS
docker-compose*.yml  SQLite and PostgreSQL stacks
docker-entrypoint.sh migrate → collectstatic → serve
```

## Roadmap ideas

- Employee self-service submission (requires an approval workflow)
- Exports (CSV/PDF) of leave records
- S3-compatible storage for attachments
- Notification emails to managers/support groups