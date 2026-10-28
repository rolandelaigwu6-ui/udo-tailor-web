# AGENTS.md

## Project
Tailor Fashion Advertisement Web Application. A simple catalogue where the tailor uploads designs and visitors browse, like, and contact the tailor directly. Not e-commerce.

## Development rules
- Keep it simple. No customer auth, cart, checkout, payment processing, or customer dashboards. A protected admin overview for catalogue management and activity reporting is allowed.
- Only admin/tailor account is protected.
- Use Flask, SQLAlchemy, SQLite (migratable to PostgreSQL), Jinja2, Bootstrap.
- Use environment variables for secrets. Never commit `.env`.
- Server-side validation for all inputs.
- Protect admin routes with authentication.

## Architecture
- App factory in `app/__init__.py`.
- Blueprints: `public`, `admin`.
- Models: Admin, Clothing, ClothingImage, SiteSettings, Visitor, ClothingActivity, Achievement, ClientShowcase.
- Config via `config.py` reading env vars.
- Versioned Alembic migrations in `migrations/versions`; apply with `init-db`, never mutate schemas during normal startup.
- Uploads stored in configurable UPLOAD_FOLDER; safe filenames via uuid.
- Free Render deployment uses external PostgreSQL and Supabase image storage; local SQLite/uploads remain supported for development. Never configure a paid service/disk without explicit user authorization.
- Migrations and storage initialization run before Gunicorn. Enable PostgreSQL row-level security to protect all application tables from anonymous Data API access. Keep server credentials and environment-file backups out of Git.
- Proxy headers are trusted only when explicitly configured for the deployment.

## Security
- CSRF protection via Flask-WTF on all forms.
- Passwords hashed with werkzeug.security.
- Rate limit admin login.
- Sanitize filenames; allow only approved image extensions; enforce size limit.
- Escape output in templates (Jinja autoescape).
- Visitor emails are personal data: admin-only, never exposed publicly.
- No browser fingerprinting or invasive tracking; visitor identity is voluntary.
- No plaintext operational secrets or fallback production credentials in repo. Production startup requires a random signing key and explicit admin credentials.
- Delete generated image files only after the database commit succeeds; preserve shared references and bundled assets.

## Commands
- Install: `pip install -r requirements.txt`
- Run: `python run.py` (or `flask --app run.py run`)
- Test: `pytest -q`
- Init/migrate DB: `flask --app run.py init-db`
- Demo content: `flask --app run.py seed-demo` (explicit only)
- Reset admin password: `flask --app run.py reset-admin-password`

## Testing
- pytest tests/ must pass before declaring done.
- Cover admin login, unauthorized access, CRUD, uploads, public pages, likes, interest, search/filter, settings, visitor identity, activity.

## Phases
No separate phased project spec is currently present. Document any future phase plan before claiming phase compliance. Keep AGENTS.md updated if permanent rules change.
