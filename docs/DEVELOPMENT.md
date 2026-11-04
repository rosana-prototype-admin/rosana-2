# Development and validation

## Local setup

1. Copy `backend/.env.example` to `backend/.env` and fill in PostgreSQL values.
2. Install backend dependencies from `backend/requirements.txt`.
3. Install frontend dependencies with `npm ci` in `frontend/`.
4. Start Django and Vite in separate terminals.

The frontend uses `VITE_API_BASE_URL` from `frontend/.env`; the default is
`http://localhost:8000/api`.

Email uses Django's console backend locally, so verification and reset emails
appear in the backend terminal. Production should use the Hostinger SMTP
settings in `backend/.env.production.example`, with the mailbox password
provided only through the VPS environment.

## Validation commands

From `frontend/`:

```text
npm run lint
npm run build
```

From `backend/`:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
```

If a local test database already exists and should be reused, run:

```text
python manage.py test --keepdb --noinput
```

For production configuration validation, populate the required environment
variables from `backend/.env.production.example` and run:

```text
python manage.py check --deploy
```

## Operational checks

- `GET /health/` checks process liveness.
- `GET /health/ready/` checks process and PostgreSQL readiness.
