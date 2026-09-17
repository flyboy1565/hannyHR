# AGENTS.md

## Project

hannyHR — a Django tool that records **why** employees took leave. Leave types
and their documentation items are fully configurable by HR via an
EAV (Entity–Attribute–Value) pattern; the tailored fill-out form is generated
at request time from those definitions.

## Stack

- Django 6 / Python 3.12 (Pillow-free; files stored on disk under `media/`)
- Server-rendered templates, hand-rolled CSS (no framework), no JS build step
- SQLite (default) or PostgreSQL via `psycopg`; Gunicorn + WhiteNoise for prod
- Rich text is a zero-dependency contenteditable widget (no markdown)

## Run it

```bash
cp .env.example .env                 # then edit as needed
python manage.py migrate
python manage.py seed_demo           # superuser hr / hannyhr123 + sample data
python manage.py runserver           # → http://localhost:8000
```

Docker alternative: `docker compose up` serves on port **8050**; compose
postgres file uses host port **5433**.

## Tests & checks

```bash
.venv/bin/python manage.py test                  # all apps
.venv/bin/python manage.py test leave             # EAV engine only
.venv/bin/python manage.py test hr                # HR console only
.venv/bin/python manage.py check                  # Django system checks
```

No linter/formatter config lives in this repo. Match existing style if you add
machinery (we don't add lint hooks on this project yet).

## Architecture

```
LeaveType ──1──*── LeaveAttribute ──1──*── LeaveAttrOption
LeaveRequest ──1──*── LeaveAttributeValue (value_text | value_file)
```

- `leave/` — EAV engine: models, dynamic forms, views, admin, tests.
- `employees/` — `Employee` model + admin; holds the `can_manage_hr` permission.
- `hr/` — HR console (no admin required): mixins, forms, views, urls, tests.
- `config/` — settings, URL routing (`/manage/` → `hr.urls`, `/` → `leave.urls`).

## Conventions

- **HR console access** is gated behind `employees.can_manage_hr` (superuser
  also passes); HR staff are intentionally NOT `is_staff`, so they have zero
  admin access. `HRConsoleMixin` enforces this on every console view.
- **Auth** is purpose-built, not admin-based: `hr:login` / `hr:logout`
  (`HRAuthenticationForm` refuses anyone who can't run the console),
  `LOGIN_URL`/`LOGIN_REDIRECT_URL` point there. Redirects land on the HR
  dashboard, never Django admin. Keep it that way — no `admin:login` in new code.
- Templates extend `templates/base.html`; blocks: `title`, `extra_head`,
  `content`, `extra_js`. Build new templates from an existing one in the same
  feature area.
- Theming uses CSS custom properties defined in `static/css/styles.css`;
  components reference tokens, never raw hex. The theme boot snippet lives in
  `base.html` `<head>` (applies saved `localStorage` theme before first paint).
- Forms use CSS classes `form-input`, `field`, `form-actions`, buttons
  `btn btn-primary` / `btn-ghost` / `btn-sm`, cards `card form-card`.
- Dynamic leave forms: revisit `leave/forms.py` and `leave/views.py` — the
  formset-based attribute collection drives the conditional visibility JS.

## Gotchas

- `media/` and `staticfiles/` are generated/served dirs — don't edit them; CSS
  and JS live in `static/`.
- `seed_demo` is idempotent (safe to re-run).
- When editing settings or URLs, run `python manage.py check` to catch wiring
  errors, and add `hr`/`leave` test coverage for auth behavior.