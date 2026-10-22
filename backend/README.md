# Backend setup

From this directory, create/activate a virtual environment and install `-r requirements.txt`.

```bash
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
pytest -q
```

`DATABASE_URL` defaults to SQLite for local development. Set it to a PostgreSQL URL for deployment and run Alembic migrations before starting the application. Tables are not automatically created on application startup.

Email verification codes are returned only when `APP_ENV=development` or `APP_ENV=test`; this is a development convenience, not email delivery. Production registration currently returns HTTP 503 until a real email provider adapter is implemented. Do not set production to development mode.


## Password reset

The API supports `POST /api/v1/auth/password-reset/request`, `/verify`, and `/complete`. In development/test mode the request endpoint returns a `development_reset_code` for repeatable local testing; it never sends a real email. Codes expire after 10 minutes, are limited to five verification attempts, and requests have a 60-second cooldown. Successful password changes invalidate all existing sessions. Configure a real email provider before production deployment.
