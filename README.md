# Threadly — Backend

A Reddit-style community platform API, built with Django REST Framework. Users can create communities, post within them, leave nested (infinitely-deep) comments, and upvote/downvote posts and comments.

**Live API:** https://threadly-backend.up.railway.app
**Frontend repo:** https://github.com/ArlanSul/threadly-frontend

## Features

- JWT authentication (register, login, token refresh)
- Communities — create, join, leave, search
- Posts — CRUD, filterable by community/author, sortable by newest or top score
- **Self-referencing comment model** supporting infinite nested replies
- Upvote/downvote system with toggle-to-remove logic, shared between posts and comments
- Author-only edit/delete permissions
- N+1-safe queries via `select_related` / `prefetch_related` / `annotate`
- Environment-based secrets (no credentials committed to source)

## Tech Stack

- Django 6 / Django REST Framework
- `djangorestframework-simplejwt` for JWT auth
- PostgreSQL (production) / SQLite (local dev)
- Gunicorn + WhiteNoise (production serving)
- Deployed on Railway

## Setup (local development)

```bash
git clone https://github.com/your-username/threadly-backend.git
cd threadly-backend

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set a real SECRET_KEY:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin
python manage.py runserver
```

API will be live at `http://127.0.0.1:8000/api/`. Django admin at `http://127.0.0.1:8000/admin/`.

## Environment Variables

| Variable | Description | Local default |
|---|---|---|
| `SECRET_KEY` | Django cryptographic signing key | — (required) |
| `DEBUG` | Enable debug mode | `True` |
| `DATABASE_URL` | Postgres connection string (production only) | falls back to SQLite |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |

## API Reference

All authenticated requests require header: `Authorization: Bearer <access_token>`

### Auth
| Method | Endpoint | Body | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | `{username, email, password}` | Create account |
| POST | `/api/auth/login/` | `{username, password}` | Returns `{access, refresh}` |
| POST | `/api/auth/refresh/` | `{refresh}` | Returns new `{access}` |

### Communities
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/communities/` | List (supports `?search=`) |
| POST | `/api/communities/` | Create (auth required) |
| GET | `/api/communities/<name>/` | Detail |
| PATCH / DELETE | `/api/communities/<name>/` | Author only |
| POST | `/api/communities/<name>/join/` | Join |
| POST | `/api/communities/<name>/leave/` | Leave |

### Posts
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/posts/` | List — supports `?community=<name>`, `?author=<username>`, `?search=`, `?ordering=-score_agg` or `?ordering=-created_at` |
| POST | `/api/posts/` | Create `{community, title, body, image?}` |
| GET | `/api/posts/<id>/` | Detail — includes full nested comment tree |
| PATCH / DELETE | `/api/posts/<id>/` | Author only |

### Comments
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/comments/?post=<id>` | List comments for a post |
| POST | `/api/comments/` | Create `{post, body, parent?}` — omit `parent` for a top-level comment |
| PATCH / DELETE | `/api/comments/<id>/` | Author only |

### Votes
| Method | Endpoint | Body | Description |
|---|---|---|---|
| POST | `/api/votes/` | `{post: id, value: 1\|-1}` or `{comment: id, value: 1\|-1}` | Voting the same value again removes the vote |

## Data Model

```
User ──< Membership >── Community ──< Post >── Comment (self-referencing: parent → replies)
              │                          │           │
              └──────────< Vote >────────┴───────────┘
```

`Comment.parent` is a foreign key to `Comment` itself, which is what allows unlimited reply depth from a single table — no separate "Reply" or "ReplyToReply" model needed.

## Notable Engineering Decisions

- **N+1 query fix:** early versions of the post list triggered a separate query per post to compute `score` and `comment_count`. Fixed with `select_related`/`prefetch_related` plus database-level `annotate()` aggregation — query count now stays constant regardless of result size, rather than scaling linearly.
- **Vote toggling:** a single `Vote` model with nullable `post`/`comment` foreign keys (exactly one set, enforced by a serializer-level validator plus database unique constraints) supports voting on either posts or comments without duplicating the model.
- **Two Post serializers** (list vs. detail) — list responses skip the full comment tree to avoid over-fetching; only the detail view resolves nested comments.

## What I'd Improve With More Time

- Move from `SimpleJWT` access tokens to httpOnly refresh cookies for stronger XSS resistance
- Add rate limiting on auth endpoints
- Swap `ImageField` local storage for S3-compatible object storage in production
- Add automated tests (currently manually verified via curl + the connected frontend)

## License

MIT
