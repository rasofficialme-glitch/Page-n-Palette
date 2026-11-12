# Page & Palette

Online bookstore + art-supplies shop. **Group 10 — Web Frameworks.**

Flask backend, **Supabase** (Auth + PostgreSQL) for users and data, plain HTML/CSS/JS storefront.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your Supabase values
```

1. In the Supabase dashboard, open **SQL Editor** and run `schema.sql` (creates all 16 tables).
2. Seed the catalogue and the admin user:
   ```bash
   python seed.py
   ```
3. Start the server:
   ```bash
   python app.py            # http://127.0.0.1:5000
   ```

Demo admin (created by `seed.py`, local testing only): `admin@pagepalette.com` / `Admin@1234` — change it before any real deployment.

## Tests

The suite runs **offline** against an in-memory fake of Supabase, so it never touches your real database.

```bash
pip install -r requirements-dev.txt
python -m pytest test_backend.py -v
```

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Signs session cookies. If unset, a random key is generated per run (sessions reset on restart) |
| `FLASK_DEBUG` | `1` enables debug mode. **Off by default** |
| `SESSION_COOKIE_SECURE` | `1` when served over HTTPS |
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | Project URL and public key (used for sign-up / sign-in) |
| `SUPABASE_SECRET_KEY` | Server-side key for database access. Keep private |

## Project structure

```
app.py            Flask app: all routes
validators.py     Server-side input validation
seed.py           Seeds categories, books, art supplies, bundles, admin user (Supabase SDK)
schema.sql        PostgreSQL schema (source of truth for the data model)
test_backend.py   Offline backend test suite
templates/        Sign-in/up page, admin panel, 403/404
static/           Auth + admin CSS/JS
storefront/       Customer-facing store (served at /shop/)
```

## API

### Auth & account
| Method | Route | Description |
|---|---|---|
| POST | `/signup` | Create customer account |
| POST | `/login` | Sign in, start session |
| POST | `/logout` | Sign out |
| POST | `/verify-email`, `/resend-verification` | Email confirmation helpers |
| PUT | `/account` | Update own profile |

### Customer (sign-in required)
| Method | Route | Description |
|---|---|---|
| POST | `/orders` | Place an order `{items:[{id:"b-1",qty:2}], payment_method}` |
| GET / POST | `/my/feedback` | List / submit feedback |
| GET | `/my/statistics` | Purchase statistics |
| GET / PUT / DELETE | `/my/cart` | Read, replace (`{items:[{id,qty}]}`), clear saved cart |
| GET / POST | `/my/wishlist` | List / add (`{id:"b-1"}`) |
| DELETE | `/my/wishlist/<id>` | Remove an item |

Product ids: `b-<book_id>` for books, `a-<art_id>` for art supplies.

### Admin (admin role required)
`GET /admin`, plus JSON CRUD at `/admin/books`, `/admin/art-supplies` (GET, POST, PUT/DELETE `/<id>`) and `POST /admin/book-categories`, `/admin/art-categories`.

## Security notes

- Never commit `.env`. If a key ever leaks, rotate it in Supabase.
- Enable **Row Level Security** on the tables in Supabase if the publishable key is exposed to browsers; the Flask server uses the secret key.
- The role (`customer` / `admin`) comes only from the `profiles` table, never from user-editable metadata.
