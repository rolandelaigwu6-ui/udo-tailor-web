# Udo Tailor

A Flask catalogue for browsing tailoring designs, liking designs, voluntarily expressing interest, and contacting the tailor. Only the admin signs in. There are no customer accounts, cart, checkout, or payment processing. The admin overview supports catalogue management and activity reporting.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env`: set `SECRET_KEY` to the generated value and choose `ADMIN_USERNAME` and a unique `ADMIN_PASSWORD` of at least 12 characters. Keep `.env` private; it is ignored by Git. Then initialize the database:

```bash
flask --app run.py init-db
python run.py
```

Sign in at `/admin/login`. No default credentials are installed. Tests use separate, explicitly non-production credentials and temporary upload directories.

## Configuration

| Variable | Behavior |
| --- | --- |
| `SECRET_KEY` | Required random signing key, at least 32 characters. |
| `ADMIN_USERNAME` | Required initial admin username, at most 80 characters. |
| `ADMIN_PASSWORD` | Required strong initial password, at least 12 characters. |
| `DATABASE_URL` | Defaults to SQLite at `instance/tailor.db`. |
| `STORAGE_BACKEND` | `local` for development; `supabase` for free cloud hosting. |
| `SUPABASE_URL` | HTTPS project URL for cloud image storage. |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only image storage credential; never exposed publicly. |
| `SUPABASE_STORAGE_BUCKET` | Dedicated public catalogue-image bucket, defaults to `tailor-images`. |
| `REQUIRE_EXTERNAL_STORAGE` | Free Render deployment sets `1` to prohibit ephemeral SQLite/local images. |
| `UPLOAD_FOLDER` | Defaults to `app/static/uploads`; may be outside the project. |
| `MAX_CONTENT_LENGTH` | Maximum entire request size; defaults to 16 MiB. |
| `TRUST_PROXY_HEADERS` | Defaults to `0`; enable only behind one trusted proxy setting client IP and scheme. |
| `SESSION_COOKIE_SECURE` | Defaults to `1`; set `0` only for local HTTP. |
| `RATELIMIT_STORAGE_URI` | Defaults to `memory://`; use shared storage for multiple workers. |
| `FLASK_DEBUG` | Defaults to `0`; local development only. |
| `PORT` | Defaults to `5000` for `python run.py`. |

Uploads are served through `/uploads/<filename>` from the configured folder. PNG, JPEG, GIF, and WebP files must match their extensions and contain no more than 25 million pixels. Every file in a multiple-image upload is validated. Replaced/deleted generated images are removed after successful database commits, provided nothing else references them. Bundled static assets and remote images are preserved.

## Database migrations and existing installations

Back up the database and upload folder before upgrading an existing installation. Stop application workers, install the requirements, configure strong secrets, then run:

```bash
flask --app run.py init-db
```

This command applies versioned Alembic migrations, adopts the original unversioned schema while preserving existing rows, and creates the admin/settings only when absent. Restart all workers afterward. Startup does not silently alter the schema. An uninitialized/outdated database returns HTTP 503 until initialized or migrated.

Migration files live in `migrations/versions`. Add a new revision with its `down_revision` pointing to the preceding revision for future schema changes; `init-db` applies all pending revisions. The initial migration is intentionally not destructively reversible: restore a backup to undo it.

The PostgreSQL driver is included. Use `DATABASE_URL=postgresql+psycopg://user:password@host/database`. Provision a fresh database with `init-db`. Moving existing SQLite rows to PostgreSQL requires a separate data transfer and verification; migrations create/upgrade schemas, not cross-database data transfers.

Demo catalogue entries are created only when explicitly requested:

```bash
flask --app run.py seed-demo
```

An empty catalogue stays empty after a restart.

## Admin password recovery and secret rotation

Changing `ADMIN_PASSWORD` in the environment does not overwrite an existing admin password. Use:

```bash
flask --app run.py reset-admin-password
```

Enter and confirm a strong password at the hidden prompt. `ADMIN_USERNAME` must identify the existing admin. If you changed the environment username after the account was created, use the old username explicitly and rename it during recovery:

```bash
flask --app run.py reset-admin-password --username OLD_USERNAME --rename-to-configured
```

This updates the existing account to `ADMIN_USERNAME` while setting the new password. For installations previously using the fallback signing key or password, reset the admin password, generate a fresh `SECRET_KEY`, and restart every worker. Rotating the signing key invalidates existing sessions.

## Interactions and privacy

Identity is voluntary; visitors can browse and interact without supplying an email. Visitor emails appear only on protected admin activity pages. Likes count once per browser session per design. Interest records the first yes/no answer per browser session per design; repeat submissions do not increase counts or change the first answer. Clearing cookies starts a new session. These are lightweight engagement counts, not verified unique-person statistics.

Design detail visits increment views. Contact-click endpoints record WhatsApp/phone events only. Counter changes and their activity records commit together. No browser fingerprinting is used. Newsletter signup records voluntary subscriptions; this application does not send newsletter emails.

## Production

Gunicorn is included for production WSGI serving behind HTTPS; `python run.py` is the development runner. Set `SESSION_COOKIE_SECURE=1`, keep debug disabled, and configure shared rate-limit storage for multiple workers. For Redis storage, install `redis` and set `RATELIMIT_STORAGE_URI=redis://...`. Preserve the database and upload folder across deployments and back them up together. Configure a reverse proxy to forward client addresses only through a trusted deployment configuration; do not blindly trust client-provided forwarding headers.

## Free Render deployment

`render.yaml` uses **Render Free** with **Supabase Free** for durable PostgreSQL data and public catalogue images. It provisions no paid disk or paid database. Stay within both providers' free limits; do not enable paid add-ons. Provider quotas and account-verification rules can change.

1. Create a Supabase project in a **Free** organization. Keep the database password private.
2. In Supabase's **Connect** dialog, choose **Session pooler** (IPv4, port 5432). Copy its PostgreSQL URI and replace the password placeholder with your database password, percent-encoding reserved characters. Render cannot use Supabase's IPv6-only direct endpoint without a paid IPv4 add-on; the free session pooler avoids that add-on.
3. In Supabase, copy the project URL and the **legacy service-role key** from API settings. Keep the service-role key server-only. Never place it in browser code, Git, or chat messages.
4. Close any old paid Blueprint/payment dialog in Render. Create a **new Blueprint** from the updated `main` branch. Confirm the web service is **Free** and there is **no disk**.
5. Enter `ADMIN_USERNAME`, a unique `ADMIN_PASSWORD` of at least 12 characters, the session-pooler URI as `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. Render generates its own signing key. Do not upload your local `.env` file.
6. Deploy, check `/healthz`, then sign in at `/admin/login`. The runtime startup command applies migrations and creates the dedicated public `tailor-images` bucket if absent. An existing private bucket is never made public automatically.

The image bucket is for public catalogue photos only. Upload/delete requests use the service-role key on the Flask server, while browsers receive public image URLs without credentials. Database migrations enable row-level security on application tables so Supabase's anonymous Data API cannot reveal visitor emails or admin password hashes. The app connects through the database owner's server-only connection.

The build installs requirements and a patched pip. `scripts/start-render.sh` initializes the database/storage before starting Gunicorn on Render's `PORT`. `.python-version` selects Python 3.13. One Gunicorn process uses multiple threads and one in-memory limiter; rate limits reset on restarts. Proxy headers are trusted only for the final proxy's client IP and scheme. Auto-deploys are initially disabled; trigger a manual deploy when ready to release a pushed commit.

Free Render services sleep after 15 idle minutes and may take about a minute to wake. Supabase Free includes database/image-storage quotas and may pause inactive projects. This setup avoids Render's 30-day-expiring free PostgreSQL offering. See [Render free limits](https://render.com/docs/free), [Supabase free quotas](https://supabase.com/docs/guides/platform/billing-on-supabase), and [database connection methods](https://supabase.com/docs/guides/database/connecting-to-postgres).

The cloud database starts empty. Git pushes do not transfer the local database or images. Arrange a separate reviewed transfer to preserve existing catalogue data. Keep local SQLite/uploads for development; free Render deployment refuses local-only storage to prevent data loss after a restart. A custom domain purchase is optional and not included in free hosting.

## Tests

```bash
pytest -q
```

The suite covers login, protected management routes, catalogue CRUD, image handling and rollback, public pages, search/filter/pagination, likes/interest/activity, settings, visitor identity/privacy, CSRF, rate limiting, and migration adoption. PostgreSQL deployment requires integration testing against the target PostgreSQL server.

## Project requirements

`AGENTS.md` contains permanent development rules. No separate phased project specification is included in this repository. Existing scope is maintained; a future phase plan must be documented before claiming conformance to it.
