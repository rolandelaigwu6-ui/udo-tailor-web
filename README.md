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

For PostgreSQL, install a suitable driver, such as `psycopg[binary]`, and use `DATABASE_URL=postgresql+psycopg://user:password@host/database`. Provision a fresh database with `init-db`. Moving existing SQLite rows to PostgreSQL requires a separate data transfer and verification; migrations create/upgrade schemas, not cross-database data transfers.

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

## Render deployment

The included `render.yaml` defines a **paid single-instance web service with a 1 GB persistent disk**. Creating the Blueprint incurs Render hosting/storage charges; review Render's displayed price before creating it. No Render resources are created by committing this file.

1. In Render, choose **New → Blueprint**, connect this GitHub repository, and select `main`.
2. Enter an admin username and a unique password of at least 12 characters when prompted. Render generates its own signing key. Do not paste or upload your local `.env` file.
3. Review the paid service/disk configuration and create the Blueprint.
4. Check the deploy logs and `/healthz`, then sign in at `/admin/login` using the credentials entered in Render.

The build command installs requirements. `scripts/start-render.sh` runs migrations **at runtime**, when the persistent disk is mounted, and then starts Gunicorn on Render's `PORT`. The SQLite database is `/var/data/tailor.db`; images are `/var/data/uploads`. Both persist across deploys. `.python-version` selects Python 3.13 with the latest available patch. Auto-deploys are disabled initially; trigger a manual deploy when ready to release a pushed commit.

One Gunicorn process serves multiple threads and maintains one in-memory limiter for this instance. Rate limits reset on restarts. `TRUST_PROXY_HEADERS=1` trusts one final proxy's client IP and scheme headers while leaving forwarded host headers untrusted. Use this only behind the Render proxy; verify client-IP behavior when deploying through any additional CDN/proxy.

The cloud database begins empty. Local database contents, uploads, and private environment files are excluded from Git and are **not transferred by a push**. To preserve local catalogue data, arrange a separate backup and transfer before publishing the cloud catalogue. Do not overwrite a running cloud database.

A free Render web service cannot preserve this app's SQLite database and local uploads across restarts/redeploys. A free-service architecture would require separately persistent database and image storage, which the included Blueprint does not configure. See [Render persistent disks](https://render.com/docs/disks), [Flask deployment](https://render.com/docs/deploy-flask), and [Python version selection](https://render.com/docs/python-version).

## Tests

```bash
pytest -q
```

The suite covers login, protected management routes, catalogue CRUD, image handling and rollback, public pages, search/filter/pagination, likes/interest/activity, settings, visitor identity/privacy, CSRF, rate limiting, and migration adoption. PostgreSQL deployment requires integration testing against the target PostgreSQL server.

## Project requirements

`AGENTS.md` contains permanent development rules. No separate phased project specification is included in this repository. Existing scope is maintained; a future phase plan must be documented before claiming conformance to it.
