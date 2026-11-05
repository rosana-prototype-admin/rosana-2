# Rosana API

The backend exposes a Django REST Framework API under `/api/`. Except where
noted, endpoints require a JWT access token:

```text
Authorization: Bearer <access-token>
```

## Operational endpoints

These endpoints do not require authentication:

- `GET /health/` — process liveness.
- `GET /health/ready/` — application and PostgreSQL readiness.

## Authentication

- `POST /api/auth/register/` — create a user account.
- `POST /api/auth/token/` — obtain access and refresh tokens.
- `POST /api/auth/token/refresh/` — rotate a refresh token.
- `POST /api/auth/token/blacklist/` — blacklist a refresh token.
- `GET/PATCH /api/auth/me/` — read or update the authenticated user's profile and preferences.
- `GET /api/auth/users/` — authenticated directory search for invitations.

## Core application resources

- `GET/POST /api/opportunities/`
- `GET/PATCH/DELETE /api/opportunities/<id>/`
- `POST /api/opportunities/<id>/clone/`
- `GET/POST /api/opportunities/<id>/members/`
- `PATCH/DELETE /api/opportunities/<id>/members/<user-id>/`
- `GET/POST /api/opportunities/<id>/projects/`
- `GET/PATCH/DELETE /api/projects/<id>/`
- `GET/POST /api/projects/<id>/sites/`
- `GET/PATCH/DELETE /api/sites/<id>/`
- `GET /api/sites/<id>/strategies/` — list/provision strategies for a site.
- `GET/PATCH/DELETE /api/strategies/<id>/` — read or update a strategy.

## Supporting resources

- Groups and memberships: `/api/groups/`
- Notifications: `/api/notifications/`
- Comments and votes: `/api/projects/<id>/comments/` and `/api/comments/`
- Focus areas and intervention types: `/api/focus-areas/` and `/api/intervention-types/`
- Jurisdictions: `/api/jcodes/` and `/api/country-codes/`
- CMFs: `/api/cmfs/`
- Crash/casualty conversion tables: `/api/crash-conversion-tables/`

## Error handling

Validation errors are returned with HTTP 400 and field names where possible.
Unauthenticated requests return 401, forbidden actions return 403, and an
object outside the caller's visibility is generally returned as 404 to avoid
revealing its existence.

The existing endpoint shapes remain unchanged during the foundation milestone.
New API areas may use `/api/v1/` when a versioned contract is needed.

Account onboarding details:

- `POST /api/auth/register/` creates an inactive account and sends a verification email.
- `POST /api/auth/verify-email/` accepts the `uid` and `token` from that email and activates the account.
- `POST /api/auth/password-reset/` requests a password reset email without revealing whether an account exists.
- `POST /api/auth/password-reset/confirm/` accepts the reset `uid`, `token`, and `new_password`.
