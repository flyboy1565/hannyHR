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
- **HR console** (`/manage/`) — a purpose-built UI for HR staff so they never
  touch the Django admin: employee CRUD, leave-type management, and per-type
  documentation items (attributes + options). Gated behind the
  `employees.can_manage_hr` permission (`is_staff` not required, so HR staff
  get zero admin access); only superusers also see the "Admin" link.
- **HR login/logout** (`/manage/login/`, `/manage/logout/`) — purpose-built
  authentication for the HR console; only accounts with the `can_manage_hr`
  permission (or superusers) can sign in.
- **Role hierarchy** — three groups control access:
  - **HR Supervisor** — full console access + ability to impersonate any non-superuser via django-hijack.
  - **HR Team Member** — can document leave and view their own team portal.
  - **IT** — Django admin access only; can view their own team portal.
- **User impersonation** (`django-hijack`) — supervisors can "View as" any
  employee from the employee list. A yellow banner shows who you're
  impersonating, with a one-click release button.
- **Team member portal** (`/manage/my-portal/`) — shows the logged-in
  employee's leave overview for the current year: total days taken,
  breakdown by leave type, and a list of individual requests.
- **Audit log** (`/manage/audit-log/`) — filterable log of all model
  changes (creates, updates, deletes) across Employee, LeaveType,
  LeaveRequest, and LeaveAttributeValue. Filterable by model, user, and
  action type.
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
| Audit trail | django-auditlog |
| User impersonation | django-hijack |
| Serving | Django dev server or Gunicorn + WhiteNoise |
| DB | SQLite or PostgreSQL (`psycopg`) |

---

## Architecture

```
User ──1──1── Employee ──1──*── LeaveRequest ──1──*── LeaveAttributeValue
                                │
                                │
LeaveType ──1──*── LeaveAttribute ──1──*── LeaveAttrOption
     │              (dynamic form fields)
     │ 1
     │ *
LeaveRequest ──1──*── LeaveAttributeValue
 (employee, dates,   value_text | value_file
  summary, status)
```

| Model | Purpose |
|---|---|
| `Employee` | Team member record; linked to a Django `User` via `OneToOneField` |
| `LeaveType` | A category of leave (Injury, Maternity, …) |
| `LeaveAttribute` | A dynamic form field: type, required, validation, condition |
| `LeaveAttrOption` | Choices for dropdown / multi-select fields |
| `LeaveRequest` | One leave event for an employee (with standard from/to dates) |
| `LeaveAttributeValue` | The recorded value(s) for an attribute on a request |

### HR role groups

| Group | Permissions |
|---|---|
| **HR Supervisor** | `can_manage_hr`, `can_hijack_users`, `can_view_team_portal`, `add_leaverequest`, `view_leaverequest`, `change_leaverequest` |
| **HR Team Member** | `can_view_team_portal`, `add_leaverequest`, `view_leaverequest` |
| **IT** | `can_view_team_portal`, `view_leaverequest` |

Superusers bypass all checks and can access everything (console, admin,
impersonation, portal). The `hr` superuser has `is_staff=False` so no admin
link is shown in the nav.

### User impersonation

Supervisors can click **"View as"** next to any employee who has a linked
user account (non-superuser). django-hijack swaps the session to that user
and shows a yellow banner with a **Release** button to return.

Permission check: `hr/hijack_permissions.py` — custom function that allows
superusers or `can_hijack_users` holders to impersonate any active,
non-superuser account.

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

Demo data is seeded automatically on container startup. To seed manually:

```bash
docker compose exec web python manage.py seed_demo
```

This creates:

### Demo accounts

| Account | Password | Role | Employee |
|---|---|---|---|
| `hr` | `hannyhr123` | Superuser | EMP-1032 — Sipho Dlamini |
| `hr.supervisor` | `supervisor123` | HR Supervisor | EMP-1033 — Naledi Mokoena |
| `hr.ops` | `hroperations123` | HR Team Member | EMP-1031 — Thandi Ndlovu |
| `it.admin` | `itadmin123` | IT | EMP-1034 — Kagiso Motlhabane |
| `alice` | `alice123` | Regular employee | EMP-1001 — Alice Moyo |

### Role permissions

| Capability | `hr` | `hr.supervisor` | `hr.ops` | `it.admin` | `alice` |
|---|:---:|:---:|:---:|:---:|:---:|
| Django admin (`/admin/`) | - | - | - | ✅ | - |
| HR console (`/manage/`) | ✅ | ✅ | - | - | - |
| Overview (leave types) | ✅ | ✅ | - | - | - |
| Create / edit leave types | ✅ | ✅ | - | - | - |
| Document leave (`/new/`) | ✅ | ✅ | ✅ | - | - |
| Leave requests list | ✅ | ✅ | ✅ | - | - |
| Employee list + "View as" | ✅ | ✅ | - | - | - |
| Audit log | ✅ | ✅ | - | - | - |
| Team portal (`/my-portal/`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| User impersonation (hijack) | ✅ | ✅ | - | - | - |

- **`hr`** is a Django superuser with `is_staff=False` (no admin link shown, but
  passes all permission checks). Has an employee record so the portal works.
- **`hr.supervisor`** belongs to the **HR Supervisor** group — full console
  access, can impersonate any non-superuser.
- **`hr.ops`** belongs to the **HR Team Member** group — can document leave
  and view their own portal, but cannot manage leave types or employees.
- **`it.admin`** belongs to the **IT** group — has `is_staff=True` for Django
  admin access, but no HR console access. Can view their own portal.
- **`alice`** is a plain user — portal access only (linked to EMP-1001).

Log in at **http://localhost:8050**:

| URL | Purpose |
|---|---|
| `/manage/login/` | HR login (purpose-built, not Django admin) |
| `/manage/` | HR dashboard — stats, quick tasks, recent records |
| `/manage/employees/` | Employee list with "View as" impersonation buttons |
| `/manage/leave-types/` | Leave type management |
| `/manage/my-portal/` | Team member portal — personal leave overview |
| `/manage/audit-log/` | System-wide audit trail (supervisors only) |
| `/new/` | Document a leave (pick employee + type → tailored form) |
| `/requests/` | Filterable list of all leave records |
| `/admin/` | Django admin (superusers only) |

### Choosing the server mode

The entrypoint picks the server based on `DEBUG` in `.env`:

| `DEBUG` | Server |
|---|---|
| `True` (default) | Django dev server (auto-reload) |
| `False` | Gunicorn (3 workers) + WhiteNoise for static files |

Override workers with `GUNICORN_WORKERS` in `.env`.

## Theme & appearance

hannyHR ships a light theme by default and switches to **dark mode
automatically** when your OS is set to dark (`prefers-color-scheme`), so at
first visit you get whichever looks right for your machine — no config
needed.

- The whole palette is expressed as CSS custom properties
  (`--bg`, `--surface`, `--text`, …) in
  `static/css/styles.css:1`; components reference tokens, never raw hex.
- Auto dark mode lives in a `@media (prefers-color-scheme: dark)` block
  (`styles.css:61`). You can pin a side with the little **sun/moon** button
  in the top bar — the choice is saved in `localStorage` and applied
  before first paint (no flash of the wrong theme).
- The boot snippet in `templates/base.html` reads the saved preference and
  sets `data-theme` on `<html>` in `<head>`, before the stylesheet loads.

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
| `SEED_DEMO` | `False` | Set to `True` to auto-seed demo data on startup |

---

## Tests

```bash
# Docker:
docker compose exec web python manage.py test

# Local:
.venv/bin/python manage.py test
```

30 tests cover:
- Field-type mapping, validation rules, conditional required logic (hidden vs. visible), value save/reload round-trips, and the full create/edit HTTP flows
- HR console access gating, employee CRUD, leave-type/attribute/option create+edit+delete flows
- HR authentication (login/logout, permission checks)

---

## Project layout

```
hr/                  HR console: mixins, forms, views, urls, tests
                     hijack_permissions.py — custom impersonation access check
config/              settings, URL routing
employees/           Employee model (with user OneToOneField) + admin
leave/               EAV engine: models, dynamic forms, views, admin, tests
templates/           base, dashboard, select, form, list, detail, login,
                     audit_log, team_portal
static/              CSS + conditional-visibility / rich-text JS
docker-compose*.yml  SQLite and PostgreSQL stacks
docker-entrypoint.sh migrate → seed_demo → collectstatic → serve
```

## Roadmap ideas

- Employee self-service submission (requires an approval workflow)
- Exports (CSV/PDF) of leave records
- S3-compatible storage for attachments
- Notification emails to managers/support groups
- Leave balance/accrual tracking per employee