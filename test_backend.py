"""
test_backend.py — Offline backend tests for Page & Palette (Flask + Supabase SDK).

Run with:   python -m pytest test_backend.py -v

No network and no real Supabase project is needed: an in-memory fake of the
Supabase client (auth + PostgREST-style table API) is swapped into app.py, so
these tests can never touch your live database.
"""
import itertools
import os
import re
import uuid

import pytest

# Make sure importing app.py can never create a real client from a local .env
for _k in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY"):
    os.environ.pop(_k, None)

import app as app_module  # noqa: E402
from supabase import AuthApiError  # noqa: E402


# =============================================================================
# Fake Supabase
# =============================================================================
PKS = {
    "profiles": "user_id", "book_categories": "category_id", "art_categories": "category_id",
    "books": "book_id", "art_supplies": "art_id", "bundles": "bundle_id",
    "customer_addresses": "address_id", "orders": "order_id", "order_items": "order_item_id",
    "order_delivery_addresses": "order_address_id", "customer_feedback": "feedback_id",
    "payments": "payment_id", "stock_transactions": "transaction_id",
    "cart_items": "cart_item_id", "wishlist": "wishlist_id",
}
UNIQUE = {
    "profiles": [("email",)], "book_categories": [("name",)], "art_categories": [("name",)],
    "books": [("title", "author")], "art_supplies": [("name", "brand")],
    "orders": [("order_ref",)], "payments": [("payment_ref",)],
}
# embedded relation name -> (fk column on the current row, pk column on target)
EMBED = {
    "book_categories": ("category_id", "category_id", "book_categories"),
    "art_categories": ("category_id", "category_id", "art_categories"),
    "books": ("book_id", "book_id", "books"),
    "art_supplies": ("art_id", "art_id", "art_supplies"),
    "orders": ("order_id", "order_id", "orders"),
}
CHECKS = {
    "books": lambda r: r["stock_qty"] >= 0 and float(r["price"]) > 0,
    "art_supplies": lambda r: r["stock_qty"] >= 0 and float(r["price"]) > 0,
}


class Resp:
    def __init__(self, data, count=None):
        self.data, self.count = data, count


def _split_top(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


class Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.op, self.payload, self.cols, self.count = "select", None, "*", None
        self.filters, self.order_by, self._limit, self.single = [], None, None, False

    # builders
    def select(self, cols="*", count=None):
        self.op, self.cols, self.count = "select", cols, count
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def upsert(self, row):
        self.op, self.payload = "upsert", row
        return self

    def update(self, vals):
        self.op, self.payload = "update", vals
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, c, v):
        self.filters.append((c, "eq", v)); return self

    def neq(self, c, v):
        self.filters.append((c, "neq", v)); return self

    def gt(self, c, v):
        self.filters.append((c, "gt", v)); return self

    def in_(self, c, v):
        self.filters.append((c, "in", list(v))); return self

    def order(self, c, desc=False):
        self.order_by = (c, desc); return self

    def limit(self, n):
        self._limit = n; return self

    def maybe_single(self):
        self.single = True; return self

    # execution
    def _match(self, row):
        for c, op, v in self.filters:
            x = row.get(c)
            if op == "eq" and not (x == v or str(x) == str(v)):
                return False
            if op == "neq" and (x == v or str(x) == str(v)):
                return False
            if op == "gt" and not (x is not None and x > v):
                return False
            if op == "in" and x not in v:
                return False
        return True

    def _embed(self, row, cols):
        out = dict(row)
        for part in _split_top(cols):
            m = re.match(r"^(\w+)\((.*)\)$", part)
            if not m:
                continue
            rel, inner = m.groups()
            fk, tpk, table = EMBED[rel]
            target = next((r for r in self.db.tables[table] if r.get(tpk) == row.get(fk)), None)
            if target is None:
                out[rel] = None
            else:
                out[rel] = self._project(target, inner)
        return out

    def _project(self, row, cols):
        parts = _split_top(cols)
        base = {} if "*" not in parts else dict(row)
        for p in parts:
            if p == "*" or "(" in p:
                continue
            base[p] = row.get(p)
        emb = [p for p in parts if "(" in p]
        if emb:
            base.update({k: v for k, v in self._embed(row, ",".join(emb)).items()
                         if k in {re.match(r"^(\w+)", e).group(1) for e in emb}})
        return base

    def execute(self):
        db, rows = self.db, self.db.tables[self.name]
        if self.op == "select":
            sel = [r for r in rows if self._match(r)]
            if self.order_by:
                c, desc = self.order_by
                sel.sort(key=lambda r: (r.get(c) is None, r.get(c)), reverse=desc)
            if self._limit is not None:
                sel = sel[: self._limit]
            count = len(sel) if self.count else None
            out = [self._project(r, self.cols) for r in sel]
            if self.single:
                if not out:
                    return None
                if len(out) > 1:
                    raise Exception("Cannot coerce the result to a single JSON object")
                return Resp(out[0], count)
            return Resp(out, count)

        if self.op in ("insert", "upsert"):
            row = dict(self.payload)
            pk = PKS[self.name]
            if self.op == "upsert" and any(r.get(pk) == row.get(pk) for r in rows):
                target = next(r for r in rows if r.get(pk) == row.get(pk))
                target.update(row)
                return Resp([dict(target)])
            if pk not in row or row[pk] is None:
                if self.name != "profiles":
                    row[pk] = next(db.seq[self.name])
            for uq in UNIQUE.get(self.name, []):
                if any(all(r.get(c) == row.get(c) for c in uq) for r in rows):
                    raise Exception(f'duplicate key value violates unique constraint "{self.name}_{uq[0]}_key"')
            if self.name in CHECKS and not CHECKS[self.name](row):
                raise Exception("violates check constraint")
            rows.append(row)
            return Resp([dict(row)])

        if self.op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                trial = {**r, **self.payload}
                if self.name in CHECKS and not CHECKS[self.name](trial):
                    raise Exception("violates check constraint")
                for uq in UNIQUE.get(self.name, []):
                    if any(o is not r and all(o.get(c) == trial.get(c) for c in uq) for o in rows):
                        raise Exception("duplicate key value violates unique constraint")
            for r in hit:
                r.update(self.payload)
            return Resp([dict(r) for r in hit])

        if self.op == "delete":
            hit = [r for r in rows if self._match(r)]
            # RESTRICT-style FK checks for the tables the admin routes delete from
            if self.name == "books":
                for r in hit:
                    if any(i.get("book_id") == r["book_id"] for i in db.tables["order_items"]) or \
                       any(b["book_id"] == r["book_id"] for b in db.tables["bundles"]):
                        raise Exception("violates foreign key constraint")
            if self.name == "art_supplies":
                for r in hit:
                    if any(i.get("art_id") == r["art_id"] for i in db.tables["order_items"]) or \
                       any(b["art_id"] == r["art_id"] for b in db.tables["bundles"]):
                        raise Exception("violates foreign key constraint")
            db.tables[self.name] = [r for r in rows if r not in hit]
            return Resp([dict(r) for r in hit])
        raise AssertionError(self.op)


class FakeUser:
    def __init__(self, uid, email, meta, identities=True):
        self.id, self.email, self.user_metadata = uid, email, meta
        self.identities = [object()] if identities else []


class FakeAuthResp:
    def __init__(self, user):
        self.user = user


class FakeAuth:
    def __init__(self, db):
        self.db = db

    def sign_up(self, creds):
        email = creds["email"]
        if email in self.db.auth_users:
            raise AuthApiError("User already registered", 422, "user_already_exists")
        u = FakeUser(str(uuid.uuid4()), email, (creds.get("options") or {}).get("data", {}))
        self.db.auth_users[email] = {"user": u, "password": creds["password"], "confirmed": self.db.autoconfirm}
        return FakeAuthResp(u)

    def sign_in_with_password(self, creds):
        rec = self.db.auth_users.get(creds["email"])
        if not rec or rec["password"] != creds["password"]:
            raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")
        if not rec["confirmed"]:
            raise AuthApiError("Email not confirmed", 400, "email_not_confirmed")
        return FakeAuthResp(rec["user"])

    def verify_otp(self, params):
        rec = self.db.auth_users.get(params["email"])
        if rec and params["token"] == "123456":
            rec["confirmed"] = True
            return FakeAuthResp(rec["user"])
        raise AuthApiError("Token has expired or is invalid", 403, "otp_expired")

    def resend(self, params):
        return None

    def sign_out(self):
        return None


class FakeSupabase:
    def __init__(self):
        self.tables = {t: [] for t in PKS}
        self.seq = {t: itertools.count(1) for t in PKS}
        self.auth_users = {}
        self.autoconfirm = True
        self.auth = FakeAuth(self)

    def table(self, name):
        return Query(self, name)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture()
def fake(monkeypatch):
    db = FakeSupabase()
    monkeypatch.setattr(app_module, "supabase", db)
    # auth calls use a dedicated client in the fixed app; keep both patchable
    if hasattr(app_module, "get_auth_client"):
        monkeypatch.setattr(app_module, "get_auth_client", lambda: db)
    return db


@pytest.fixture()
def seeded(fake):
    fake.table("book_categories").insert({"name": "Fiction"}).execute()
    fake.table("art_categories").insert({"name": "Paints"}).execute()
    fake.table("books").insert({"title": "Dune", "author": "Herbert", "category_id": 1, "price": 499.0,
                                "stock_qty": 5, "units_sold": 0, "rank_order": 1}).execute()
    fake.table("books").insert({"title": "Emma", "author": "Austen", "category_id": 1, "price": 250.5,
                                "stock_qty": 0, "units_sold": 0}).execute()
    fake.table("art_supplies").insert({"name": "Acrylic Set", "brand": "Camlin", "category_id": 1, "price": 300.0,
                                       "stock_qty": 4, "units_sold": 0}).execute()
    fake.table("bundles").insert({"book_id": 1, "art_id": 1, "bundle_price": 700.0, "description": "combo"}).execute()
    return fake


@pytest.fixture()
def client(fake):
    return app_module.create_app().test_client()


def _mk_user(fake, email, role="customer", password="Passw0rd1", name="Test User"):
    uid = str(uuid.uuid4())
    u = FakeUser(uid, email, {"name": name, "role": role})
    fake.auth_users[email] = {"user": u, "password": password, "confirmed": True}
    fake.table("profiles").insert({"user_id": uid, "name": name, "email": email, "role": role,
                                   "approval_status": "approved"}).execute()
    return uid


def login(client, email, password="Passw0rd1"):
    return client.post("/login", json={"email": email, "password": password})


@pytest.fixture()
def customer(client, fake):
    _mk_user(fake, "cust@example.com")
    assert login(client, "cust@example.com").status_code == 200
    return client


@pytest.fixture()
def admin(client, fake):
    _mk_user(fake, "admin@example.com", role="admin", name="Admin")
    assert login(client, "admin@example.com").status_code == 200
    return client


SIGNUP = {"name": "Ann Lee", "email": "ann@example.com", "password": "Passw0rd1",
          "confirm_password": "Passw0rd1", "phone": "9876543210"}


# =============================================================================
# Auth
# =============================================================================
class TestAuth:
    def test_signup_ok_creates_profile(self, client, fake):
        r = client.post("/signup", json=SIGNUP)
        assert r.status_code == 201 and r.json["response"] == "OK"
        prof = fake.tables["profiles"][0]
        assert prof["email"] == "ann@example.com" and prof["role"] == "customer"

    def test_signup_cannot_self_assign_admin(self, client, fake):
        client.post("/signup", json={**SIGNUP, "role": "admin"})
        assert fake.tables["profiles"][0]["role"] == "customer"

    @pytest.mark.parametrize("patch,field", [
        ({"email": "not-an-email"}, "email"),
        ({"password": "short", "confirm_password": "short"}, "password"),
        ({"confirm_password": "Different1"}, "confirm_password"),
        ({"phone": "123"}, "phone"),
        ({"name": ""}, "name"),
    ])
    def test_signup_validation(self, client, patch, field):
        r = client.post("/signup", json={**SIGNUP, **patch})
        assert r.status_code == 400 and field in r.json["errors"]

    def test_signup_duplicate_email(self, client):
        assert client.post("/signup", json=SIGNUP).status_code == 201
        r = client.post("/signup", json=SIGNUP)
        assert r.status_code == 409 and "email" in r.json["errors"]

    def test_signup_bad_body(self, client):
        assert client.post("/signup", data="nope", content_type="text/plain").status_code == 400
        assert client.post("/signup", json=[1, 2]).status_code == 400

    def test_login_customer_redirects_home(self, client, fake):
        _mk_user(fake, "c@example.com")
        r = login(client, "c@example.com")
        assert r.status_code == 200 and r.json["redirect"] == "/home"

    def test_login_admin_redirects_admin(self, client, fake):
        _mk_user(fake, "a@example.com", role="admin")
        assert login(client, "a@example.com").json["redirect"] == "/admin"

    def test_login_wrong_password_generic_401(self, client, fake):
        _mk_user(fake, "c@example.com")
        r = login(client, "c@example.com", "WrongPass1")
        assert r.status_code == 401 and "Invalid email or password" in r.json["errors"]["email"]

    def test_login_unknown_user_same_message(self, client):
        r = login(client, "ghost@example.com")
        assert r.status_code == 401 and "Invalid email or password" in r.json["errors"]["email"]

    def test_login_unverified_email(self, client, fake):
        _mk_user(fake, "u@example.com")
        fake.auth_users["u@example.com"]["confirmed"] = False
        r = login(client, "u@example.com")
        assert r.status_code == 403 and r.json["verification_required"] is True

    def test_login_missing_profile_never_trusts_metadata_role(self, client, fake):
        """A user can edit their own Supabase user_metadata -> role there must not grant admin."""
        u = FakeUser(str(uuid.uuid4()), "sneaky@example.com", {"name": "S", "role": "admin"})
        fake.auth_users["sneaky@example.com"] = {"user": u, "password": "Passw0rd1", "confirmed": True}
        r = login(client, "sneaky@example.com")
        assert r.status_code == 200 and r.json["redirect"] == "/home"
        assert client.get("/admin").status_code == 403

    def test_logout_clears_session(self, customer):
        assert customer.post("/logout").status_code == 200
        assert customer.get("/my/statistics").status_code == 401

    def test_verify_email_otp(self, client, fake):
        client.post("/signup", json=SIGNUP)
        r = client.post("/verify-email", json={"email": "ann@example.com", "otp": "123456"})
        assert r.status_code == 200 and "verified" in r.json["message"].lower()

    def test_verify_email_bad_email(self, client):
        assert client.post("/verify-email", json={"email": "x"}).status_code == 400

    def test_resend_verification(self, client):
        r = client.post("/resend-verification", json={"email": "ann@example.com"})
        assert r.status_code == 200 and r.json["cooldown"] == 60


# =============================================================================
# Access control
# =============================================================================
class TestAccessControl:
    ADMIN_API = [("get", "/admin/books"), ("post", "/admin/books"), ("put", "/admin/books/1"),
                 ("delete", "/admin/books/1"), ("get", "/admin/art-supplies"),
                 ("post", "/admin/art-supplies"), ("put", "/admin/art-supplies/1"),
                 ("delete", "/admin/art-supplies/1"), ("post", "/admin/book-categories"),
                 ("post", "/admin/art-categories")]

    @pytest.mark.parametrize("method,path", ADMIN_API)
    def test_admin_api_401_for_guest(self, client, method, path):
        assert getattr(client, method)(path, json={}).status_code == 401

    @pytest.mark.parametrize("method,path", ADMIN_API)
    def test_admin_api_403_for_customer(self, customer, method, path):
        assert getattr(customer, method)(path, json={}).status_code == 403

    def test_admin_page_guest_redirect_customer_403(self, client, customer):
        c2 = app_module.create_app().test_client()
        assert c2.get("/admin").status_code == 302
        assert customer.get("/admin").status_code == 403

    @pytest.mark.parametrize("method,path", [("get", "/my/feedback"), ("post", "/my/feedback"),
                                             ("get", "/my/statistics"), ("post", "/orders"),
                                             ("put", "/account")])
    def test_customer_api_401_for_guest(self, client, method, path):
        assert getattr(client, method)(path, json={}).status_code == 401

    def test_unknown_route_404_page(self, client):
        assert client.get("/nope").status_code == 404


# =============================================================================
# Storefront
# =============================================================================
class TestStorefront:
    def test_root_and_home(self, client, customer):
        assert client.get("/home").headers["Location"].endswith("/shop/")

    def test_common_js_injects_store_hides_zero_stock(self, seeded, client):
        body = client.get("/shop/common.js").get_data(as_text=True)
        assert "window.__STORE__" in body and "Dune" in body and "Acrylic Set" in body
        assert "Emma" not in body  # stock 0 -> hidden

    def test_pair_visible_only_when_both_in_stock(self, seeded, client):
        assert "pair-1" in client.get("/shop/common.js").get_data(as_text=True)
        seeded.table("art_supplies").update({"stock_qty": 0}).eq("art_id", 1).execute()
        assert "pair-1" not in client.get("/shop/common.js").get_data(as_text=True)

    def test_common_js_logged_in_me(self, seeded, customer):
        body = customer.get("/shop/common.js").get_data(as_text=True)
        assert '"logged_in": true' in body

    def test_static_pages_served(self, client):
        for p in ("index.html", "cart.html", "checkout.html", "feedback.html"):
            assert client.get(f"/shop/{p}").status_code == 200

    def test_path_traversal_blocked(self, client):
        assert client.get("/shop/../app.py").status_code in (301, 308, 404)
        assert client.get("/shop/%2e%2e/app.py").status_code == 404


# =============================================================================
# Admin: books / art / categories
# =============================================================================
BOOK = {"title": "Neuromancer", "author": "Gibson", "category_id": 1, "price": 399, "stock_qty": 10}
ART = {"name": "Brush Set", "brand": "Faber", "category_id": 1, "price": 150, "stock_qty": 7}


class TestAdminCatalogue:
    def test_book_crud(self, seeded, admin):
        r = admin.post("/admin/books", json=BOOK)
        assert r.status_code == 201 and r.json["data"]["category_name"] == "Fiction"
        bid = r.json["data"]["book_id"]
        assert any(b["book_id"] == bid for b in admin.get("/admin/books").json["data"])
        r = admin.put(f"/admin/books/{bid}", json={**BOOK, "price": 450})
        assert r.status_code == 200 and r.json["data"]["price"] == 450
        assert admin.delete(f"/admin/books/{bid}").status_code == 200

    def test_book_duplicate_409(self, seeded, admin):
        assert admin.post("/admin/books", json=BOOK).status_code == 201
        assert admin.post("/admin/books", json=BOOK).status_code == 409

    def test_book_update_duplicate_409(self, seeded, admin):
        bid = admin.post("/admin/books", json=BOOK).json["data"]["book_id"]
        assert admin.put(f"/admin/books/{bid}", json={**BOOK, "title": "Dune", "author": "Herbert"}).status_code == 409

    @pytest.mark.parametrize("patch", [{"price": -5}, {"price": 0}, {"stock_qty": -1}, {"title": ""},
                                       {"category_id": 999}, {"price": "abc"}])
    def test_book_validation(self, seeded, admin, patch):
        assert admin.post("/admin/books", json={**BOOK, **patch}).status_code == 400

    def test_book_missing_404(self, seeded, admin):
        assert admin.put("/admin/books/999", json=BOOK).status_code == 404
        assert admin.delete("/admin/books/999").status_code == 404

    def test_delete_book_blocked_by_bundle(self, seeded, admin):
        assert admin.delete("/admin/books/1").status_code == 409

    def test_delete_book_blocked_by_order_history(self, seeded, admin):
        seeded.table("bundles").delete().eq("book_id", 1).execute()
        seeded.table("order_items").insert({"order_id": 1, "book_id": 1, "quantity": 1, "price_at_purchase": 1}).execute()
        assert admin.delete("/admin/books/1").status_code == 409

    def test_art_crud(self, seeded, admin):
        r = admin.post("/admin/art-supplies", json=ART)
        assert r.status_code == 201
        aid = r.json["data"]["art_id"]
        assert admin.put(f"/admin/art-supplies/{aid}", json={**ART, "price": 200}).status_code == 200
        assert admin.delete(f"/admin/art-supplies/{aid}").status_code == 200

    def test_art_duplicate_409(self, seeded, admin):
        assert admin.post("/admin/art-supplies", json=ART).status_code == 201
        assert admin.post("/admin/art-supplies", json=ART).status_code == 409

    def test_art_validation(self, seeded, admin):
        assert admin.post("/admin/art-supplies", json={**ART, "price": -1}).status_code == 400
        assert admin.post("/admin/art-supplies", json={**ART, "name": ""}).status_code == 400

    @pytest.mark.parametrize("url", ["/admin/book-categories", "/admin/art-categories"])
    def test_categories(self, seeded, admin, url):
        r = admin.post(url, json={"name": "Poetry"})
        assert r.status_code == 201 and r.json["data"]["name"] == "Poetry"
        assert admin.post(url, json={"name": "Poetry"}).status_code == 409
        assert admin.post(url, json={"name": ""}).status_code == 400

    def test_invalid_json_body(self, seeded, admin):
        assert admin.post("/admin/books", data="{bad", content_type="application/json").status_code == 400


# =============================================================================
# Orders
# =============================================================================
class TestOrders:
    def _order(self, c, items, method="UPI"):
        return c.post("/orders", json={"items": items, "payment_method": method})

    def test_happy_path_updates_everything(self, seeded, customer):
        r = self._order(customer, [{"id": "b-1", "qty": 2}, {"id": "a-1", "qty": 1}])
        assert r.status_code == 201, r.json
        assert r.json["total"] == 2 * 499 + 300 and re.match(r"^PP-\d{6}$", r.json["order_ref"])
        t = seeded.tables
        assert t["books"][0]["stock_qty"] == 3 and t["books"][0]["units_sold"] == 2
        assert t["art_supplies"][0]["stock_qty"] == 3
        assert len(t["orders"]) == 1 and len(t["order_items"]) == 2 and len(t["payments"]) == 1
        assert [s["new_stock"] for s in t["stock_transactions"]] == [3, 3]

    def test_price_comes_from_db_not_client(self, seeded, customer):
        r = customer.post("/orders", json={"items": [{"id": "b-1", "qty": 1, "price": 1}], "payment_method": "UPI"})
        assert r.json["total"] == 499

    def test_duplicate_line_items_do_not_oversell(self, seeded, customer):
        """Same product twice in one cart: stock must drop by the SUM, not just the last line."""
        r = self._order(customer, [{"id": "b-1", "qty": 2}, {"id": "b-1", "qty": 3}])
        assert r.status_code == 201, r.json
        assert seeded.tables["books"][0]["stock_qty"] == 0
        assert seeded.tables["books"][0]["units_sold"] == 5

    def test_duplicate_lines_exceeding_stock_rejected(self, seeded, customer):
        r = self._order(customer, [{"id": "b-1", "qty": 3}, {"id": "b-1", "qty": 3}])  # 6 > stock 5
        assert r.status_code == 400
        assert seeded.tables["books"][0]["stock_qty"] == 5 and not seeded.tables["orders"]

    def test_insufficient_stock(self, seeded, customer):
        assert self._order(customer, [{"id": "b-1", "qty": 6}]).status_code == 400
        assert not seeded.tables["orders"]

    @pytest.mark.parametrize("items", [[], "x", None, [{"id": "b-1", "qty": 0}], [{"id": "b-1", "qty": 21}],
                                       [{"id": "b-1", "qty": "x"}], [{"id": "z-1", "qty": 1}]])
    def test_bad_cart_400(self, seeded, customer, items):
        assert self._order(customer, items).status_code == 400

    @pytest.mark.parametrize("items", [[{"id": "b-abc", "qty": 1}], ["b-1"], [None], [{"id": "b-", "qty": 1}]])
    def test_malformed_items_are_400_not_500(self, seeded, customer, items):
        assert self._order(customer, items).status_code == 400

    def test_unknown_product_404(self, seeded, customer):
        assert self._order(customer, [{"id": "b-999", "qty": 1}]).status_code == 404

    def test_invalid_payment_method(self, seeded, customer):
        assert self._order(customer, [{"id": "b-1", "qty": 1}], "Bitcoin").status_code == 400

    def test_uses_default_address(self, seeded, customer):
        uid = seeded.tables["profiles"][0]["user_id"]
        seeded.table("customer_addresses").insert({
            "user_id": uid, "recipient_name": "Ann", "phone": "9876543210", "address_line1": "1 Road",
            "city": "Vijayapura", "state": "KA", "postal_code": "586101", "is_default": True}).execute()
        r = self._order(customer, [{"id": "b-1", "qty": 1}])
        assert r.status_code == 201
        assert seeded.tables["orders"][0]["delivery_status"] == "processing"
        assert len(seeded.tables["order_delivery_addresses"]) == 1

    def test_failure_midway_rolls_back(self, seeded, customer, monkeypatch):
        """If writing an order line fails, no half-made order / stock change may remain."""
        real_table = seeded.table

        def flaky(name):
            q = real_table(name)
            if name == "order_items":
                def boom():
                    raise Exception("db down")
                q.execute = boom
            return q
        monkeypatch.setattr(seeded, "table", flaky)
        r = self._order(customer, [{"id": "b-1", "qty": 2}])
        assert r.status_code == 500
        assert seeded.tables["books"][0]["stock_qty"] == 5
        assert seeded.tables["orders"] == []


# =============================================================================
# Feedback / statistics / account
# =============================================================================
class TestCustomerFeatures:
    def test_feedback_for_book(self, seeded, customer):
        r = customer.post("/my/feedback", json={"product_id": "b-1", "rating": 5, "comment": "Great read"})
        assert r.status_code == 201
        listing = customer.get("/my/feedback").json
        assert listing["feedback"][0]["target"] == "Dune" and listing["feedback"][0]["rating"] == 5

    @pytest.mark.parametrize("payload", [{"rating": 0, "comment": "x"}, {"rating": 6, "comment": "x"},
                                         {"rating": 5, "comment": ""}, {"rating": "five", "comment": "x"}])
    def test_feedback_validation(self, seeded, customer, payload):
        assert customer.post("/my/feedback", json={"product_id": "b-1", **payload}).status_code == 400

    def test_feedback_unknown_product(self, seeded, customer):
        assert customer.post("/my/feedback", json={"product_id": "b-999", "rating": 4, "comment": "x"}).status_code == 400
        assert customer.post("/my/feedback", json={"product_id": "q-1", "rating": 4, "comment": "x"}).status_code == 400

    def test_feedback_other_users_order_rejected(self, seeded, customer):
        other = _mk_user(seeded, "other@example.com")
        seeded.table("orders").insert({"user_id": other, "order_ref": "PP-000001", "total_amount": 1,
                                       "payment_status": "paid"}).execute()
        r = customer.post("/my/feedback", json={"order_id": 1, "rating": 4, "comment": "mine?"})
        assert r.status_code == 400

    def test_feedback_only_lists_own(self, seeded, customer):
        other = _mk_user(seeded, "other@example.com")
        seeded.table("customer_feedback").insert({"user_id": other, "book_id": 1, "rating": 1, "comment": "meh"}).execute()
        assert customer.get("/my/feedback").json["feedback"] == []

    def test_statistics_empty(self, seeded, customer):
        r = customer.get("/my/statistics")
        assert r.status_code == 200 and r.json["total_orders"] == 0 and len(r.json["monthly"]) == 6

    def test_statistics_after_order(self, seeded, customer):
        customer.post("/orders", json={"items": [{"id": "b-1", "qty": 2}, {"id": "a-1", "qty": 1}], "payment_method": "UPI"})
        s = customer.get("/my/statistics").json
        assert s["total_orders"] == 1 and s["total_spent"] == 1298 and s["items_purchased"] == 3
        assert s["books_qty"] == 2 and s["art_qty"] == 1 and s["favourite_category"] == "Fiction"

    def test_account_update(self, customer):
        r = customer.put("/account", json={"name": "New Name", "phone": "9876543210", "address": "12 Street"})
        assert r.status_code == 200 and r.json["data"]["name"] == "New Name"

    def test_account_cannot_change_role(self, customer, fake):
        customer.put("/account", json={"name": "N", "role": "admin", "email": "x@y.com"})
        p = fake.tables["profiles"][0]
        assert p["role"] == "customer" and p["email"] == "cust@example.com"

    def test_account_validation(self, customer):
        assert customer.put("/account", json={"name": "", "phone": "12"}).status_code == 400


# =============================================================================
# Configuration safety
# =============================================================================
class TestConfig:
    def test_no_hardcoded_default_secret(self, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        assert app_module.create_app().config["SECRET_KEY"] != "dev-secret-change-in-prod"

    def test_secret_key_from_env(self, monkeypatch):
        monkeypatch.setenv("FLASK_SECRET_KEY", "abc123")
        assert app_module.create_app().config["SECRET_KEY"] == "abc123"

    def test_session_cookie_flags(self):
        cfg = app_module.create_app().config
        assert cfg["SESSION_COOKIE_HTTPONLY"] is True and cfg["SESSION_COOKIE_SAMESITE"] == "Lax"

    def test_debug_is_opt_in(self):
        src = open(os.path.join(os.path.dirname(__file__), "app.py"), encoding="utf-8").read()
        assert 'get("FLASK_DEBUG", "1")' not in src

    def test_data_client_never_used_for_user_sign_in(self):
        """Signing a user in on the shared service client swaps its Authorization header to that
        user's JWT, so every later DB call would run as them. Auth must use its own client."""
        src = open(os.path.join(os.path.dirname(__file__), "app.py"), encoding="utf-8").read()
        assert "supabase.auth.sign_in_with_password" not in src
        assert "supabase.auth.sign_up" not in src


# =============================================================================
# Cart & wishlist
# =============================================================================
class TestCartWishlist:
    @pytest.mark.parametrize("method,path", [("get", "/my/cart"), ("put", "/my/cart"), ("delete", "/my/cart"),
                                             ("get", "/my/wishlist"), ("post", "/my/wishlist"),
                                             ("delete", "/my/wishlist/b-1")])
    def test_guest_401(self, client, method, path):
        assert getattr(client, method)(path, json={}).status_code == 401

    def test_cart_roundtrip_and_replace(self, seeded, customer):
        assert customer.get("/my/cart").json["items"] == []
        r = customer.put("/my/cart", json={"items": [{"id": "b-1", "qty": 2}, {"id": "a-1", "qty": 1}]})
        assert r.status_code == 200 and r.json["count"] == 2
        items = customer.get("/my/cart").json["items"]
        assert {(i["id"], i["qty"]) for i in items} == {("b-1", 2), ("a-1", 1)}
        assert items[0]["name"] == "Dune" and items[0]["price"] == 499
        customer.put("/my/cart", json={"items": [{"id": "a-1", "qty": 3}]})
        assert [(i["id"], i["qty"]) for i in customer.get("/my/cart").json["items"]] == [("a-1", 3)]

    def test_cart_merges_duplicates(self, seeded, customer):
        customer.put("/my/cart", json={"items": [{"id": "b-1", "qty": 2}, {"id": "b-1", "qty": 3}]})
        assert [(i["id"], i["qty"]) for i in customer.get("/my/cart").json["items"]] == [("b-1", 5)]

    @pytest.mark.parametrize("items", [[{"id": "b-1", "qty": 0}], [{"id": "b-1", "qty": 21}],
                                       [{"id": "b-1", "qty": "x"}], [{"id": "z-1", "qty": 1}],
                                       [{"id": "b-abc", "qty": 1}], ["b-1"], [None]])
    def test_cart_validation(self, seeded, customer, items):
        assert customer.put("/my/cart", json={"items": items}).status_code == 400

    def test_cart_unknown_product_404_and_keeps_old_cart(self, seeded, customer):
        customer.put("/my/cart", json={"items": [{"id": "b-1", "qty": 1}]})
        assert customer.put("/my/cart", json={"items": [{"id": "b-999", "qty": 1}]}).status_code == 404
        assert len(customer.get("/my/cart").json["items"]) == 1

    def test_cart_is_per_user(self, seeded, customer):
        customer.put("/my/cart", json={"items": [{"id": "b-1", "qty": 1}]})
        _mk_user(seeded, "two@example.com")
        c2 = app_module.create_app().test_client()
        login(c2, "two@example.com")
        assert c2.get("/my/cart").json["items"] == []

    def test_cart_clear(self, seeded, customer):
        customer.put("/my/cart", json={"items": [{"id": "b-1", "qty": 1}]})
        assert customer.delete("/my/cart").status_code == 200
        assert customer.get("/my/cart").json["items"] == []

    def test_wishlist_add_list_remove(self, seeded, customer):
        assert customer.post("/my/wishlist", json={"id": "b-1"}).status_code == 201
        assert customer.post("/my/wishlist", json={"id": "a-1"}).status_code == 201
        assert customer.post("/my/wishlist", json={"id": "b-1"}).status_code == 200  # idempotent
        items = customer.get("/my/wishlist").json["items"]
        assert {i["id"] for i in items} == {"b-1", "a-1"}
        assert customer.delete("/my/wishlist/b-1").status_code == 200
        assert [i["id"] for i in customer.get("/my/wishlist").json["items"]] == ["a-1"]

    def test_wishlist_validation(self, seeded, customer):
        assert customer.post("/my/wishlist", json={"id": "q-1"}).status_code == 400
        assert customer.post("/my/wishlist", json={"id": "b-999"}).status_code == 404
        assert customer.delete("/my/wishlist/zzz").status_code == 400

    def test_wishlist_is_per_user(self, seeded, customer):
        customer.post("/my/wishlist", json={"id": "b-1"})
        _mk_user(seeded, "two@example.com")
        c2 = app_module.create_app().test_client()
        login(c2, "two@example.com")
        assert c2.get("/my/wishlist").json["items"] == []
        c2.delete("/my/wishlist/b-1")  # must not remove the other user's entry
        assert len(customer.get("/my/wishlist").json["items"]) == 1
