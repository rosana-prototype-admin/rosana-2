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
- `DELETE /api/groups/<id>/` archives a Group and its subgroups; it no longer permanently deletes them.
- `POST /api/groups/<id>/restore/` restores an archived Group tree for platform administrators.
- `POST /api/groups/<id>/set-admin/` transfers administration to an active, email-verified group member. The outgoing administrator remains a regular member, and the transfer is recorded in the audit log.
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

Platform administration details:

- `GET /api/auth/admin/users/` lists users for platform staff, with optional `q`, `is_active`, `email_verified`, and `subscription_type` filters.
- `GET/PATCH /api/auth/admin/users/<id>/` reads or updates account profile and lifecycle fields for platform staff.
- `POST /api/auth/admin/users/<id>/resend-verification/` resends verification mail for an unverified account.
- `POST /api/auth/admin/users/<id>/send-password-reset/` sends a password-reset email for an active, verified account.
- `GET /api/auth/admin/groups/` lists company groups with members and subscription summaries.
- `GET/PATCH /api/auth/admin/groups/<group-id>/subscription/` reads or updates the company's dated subscription and seat limit.
- `GET/POST /api/auth/admin/groups/<group-id>/contracts/` lists or creates company contract records.
- `GET/PATCH /api/auth/admin/groups/<group-id>/contracts/<contract-id>/` reads or updates one company contract.
- `GET/POST /api/auth/admin/groups/<group-id>/seats/` lists or assigns seats to company members.
- `DELETE /api/auth/admin/groups/<group-id>/seats/<seat-id>/` releases a seat without deleting its history.
- These endpoints require a Django `is_staff` user. The `subscription_type` value does not grant administrative access.
- Company subscriptions are owned by Groups; the legacy per-user `subscription_type` field is retained only for compatibility and is not assigned from account management.
- Administrative requests also require the staff user to be active, and the last active platform administrator cannot be disabled or demoted.
