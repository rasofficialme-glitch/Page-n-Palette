"""
app.py — Page & Palette Flask application.
Completely rewritten to drop SQLAlchemy and use the Supabase Python SDK exclusively.
Maintains all original Flask routes, decorators, error handlers, and JSON payload shapes.
"""

import os
import json
import random
from datetime import datetime, timezone
from functools import wraps
from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, send_from_directory, Response)
from dotenv import load_dotenv
from supabase import create_client, Client, AuthApiError
from validators import (validate_signup, validate_login, validate_profile,
                        validate_book, validate_art_supply, validate_category,
                        validate_feedback, EMAIL_RE)

# ---------------------------------------------------------------------------
# Load environment & initialize Supabase client
# ---------------------------------------------------------------------------
load_dotenv()
_local_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_local_env):
    load_dotenv(_local_env)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_auth_client() -> Client:
    """
    Short-lived client used ONLY for sign-up / sign-in / OTP calls.

    supabase-py swaps a client's Authorization header to the signed-in user's JWT
    after sign_in_with_password(). Doing that on the shared `supabase` data client
    would make every later database call (for every visitor) run as the last person
    who logged in, so auth always gets its own throw-away client instead.
    """
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or SUPABASE_KEY
    return create_client(SUPABASE_URL, key)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app():
    app = Flask(__name__)

    # SECRET_KEY for Flask session cookie encryption
    # No hard-coded fallback: a publicly known key would let anyone forge an admin
    # session cookie. Without FLASK_SECRET_KEY a random per-process key is used
    # (sessions simply reset on restart).
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32).hex()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # =========================================================================
    # Auth decorators
    # =========================================================================

    def login_required(f):
        """Redirect unauthenticated visitors to the auth page (GET routes only)."""
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated

    def admin_required(f):
        """
        Guard for admin routes.
        - Path is exactly /admin (GET page request):
            not logged in  → redirect to /
            customer       → render 403 page
        - Any other /admin/* route (fetch/API call):
            not logged in  → JSON 401
            customer       → JSON 403
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            is_api = (request.path != "/admin")

            if "user_id" not in session:
                if is_api:
                    return jsonify({"response": "Fail",
                                    "message": "Authentication required."}), 401
                return redirect(url_for("index"))

            if session.get("role") != "admin":
                if is_api:
                    return jsonify({"response": "Fail",
                                    "message": "Admin access required."}), 403
                return render_template("403.html"), 403

            return f(*args, **kwargs)
        return decorated

    # =========================================================================
    # Custom error handlers
    # =========================================================================

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.method != "GET":
            return jsonify({"response": "Fail",
                            "message": "Something went wrong on the server. Please try again."}), 500
        return "Internal server error", 500

    # =========================================================================
    # AUTH ROUTES
    # =========================================================================

    @app.route("/")
    def index():
        """Render Sign In / Sign Up page. Redirect if already logged in."""
        if "user_id" in session:
            if session.get("role") == "admin":
                return redirect(url_for("admin_page"))
            return redirect(url_for("home"))
        return render_template("auth.html")

    @app.route("/signup", methods=["POST"])
    def signup():
        """
        Create a new customer account via Supabase Auth and store profile row.
        Expects JSON: {name, email, password, confirm_password, phone?, address?}
        Returns JSON: {"response":"OK"} or {"response":"Fail","errors":{...}}
        """
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail",
                            "message": "Invalid request body."}), 400

        # Field-level validation
        errors = validate_signup(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        email = data["email"].strip().lower()
        password = data["password"]
        name = data["name"].strip()
        phone = (data.get("phone") or "").strip() or None
        address = (data.get("address") or "").strip() or None

        # Sign up using Supabase Auth
        try:
            auth_resp = get_auth_client().auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "role": "customer"
                    }
                }
            })
        except AuthApiError as e:
            err_msg = str(e)
            if "already registered" in err_msg.lower() or "already exists" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"email": "This email address is already registered."}
                }), 409
            return jsonify({"response": "Fail", "message": err_msg}), 400
        except Exception as e:
            err_msg = str(e)
            if "already registered" in err_msg.lower() or "already exists" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"email": "This email address is already registered."}
                }), 409
            return jsonify({"response": "Fail", "message": "An error occurred during sign up."}), 400

        user = getattr(auth_resp, "user", None)
        if not user:
            return jsonify({"response": "Fail", "message": "Sign up failed to create user."}), 400

        # Check identities list when email confirmation is enabled and email is registered
        identities = getattr(user, "identities", None)
        if identities is not None and len(identities) == 0:
            return jsonify({
                "response": "Fail",
                "errors": {"email": "This email address is already registered."}
            }), 409

        user_id = str(user.id)

        # Insert or upsert into profiles table
        try:
            profile_data = {
                "user_id": user_id,
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "role": "customer",
                "approval_status": "approved",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            supabase.table("profiles").upsert(profile_data).execute()
        except Exception as e:
            err_msg = str(e)
            if "duplicate key" in err_msg.lower() or "profiles_email_key" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"email": "This email address is already registered."}
                }), 409
            return jsonify({"response": "Fail", "message": "Failed to create user profile."}), 500

        return jsonify({
            "response": "OK",
            "verification_required": True,
            "email": email,
            "message": "Account created! Check your email to verify your address."
        }), 201

    @app.route("/verify-email", methods=["POST"])
    def verify_email():
        """
        Verification endpoint. Supabase handles email verification automatically via links.
        If an OTP token is submitted, attempt verification; otherwise direct the user to check their email.
        """
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        email = str(data.get("email") or "").strip().lower()
        otp = str(data.get("otp") or "").strip()

        if not EMAIL_RE.match(email):
            return jsonify({"response": "Fail", "errors": {"otp": "Please enter a valid email address."}}), 400

        if otp and supabase:
            try:
                res = get_auth_client().auth.verify_otp({"email": email, "token": otp, "type": "signup"})
                if res and res.user:
                    return jsonify({"response": "OK", "message": "Email verified! You can now sign in."}), 200
            except Exception:
                pass

        return jsonify({
            "response": "OK",
            "message": "Please check your email and click the confirmation link to verify your account."
        }), 200

    @app.route("/resend-verification", methods=["POST"])
    def resend_verification():
        """
        Resend confirmation email via Supabase Auth.
        """
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        email = str(data.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            return jsonify({"response": "Fail", "errors": {"email": "Please enter a valid email address."}}), 400

        try:
            if supabase:
                get_auth_client().auth.resend({"type": "signup", "email": email})
        except Exception:
            pass

        return jsonify({
            "response": "OK",
            "cooldown": 60,
            "message": "If that account is awaiting verification, a new code is on its way."
        }), 200

    @app.route("/login", methods=["POST"])
    def login():
        """
        Authenticate a user via Supabase Auth and create a Flask session.
        Returns generic error on failure, or redirect URL on success.
        """
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_login(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        email = data["email"].strip().lower()
        password = data["password"]

        try:
            auth_resp = get_auth_client().auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        except AuthApiError as e:
            err_msg = str(e)
            if "email not confirmed" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "verification_required": True,
                    "email": email,
                    "message": "Please verify your email address before signing in. Check your email for the confirmation link."
                }), 403
            return jsonify({
                "response": "Fail",
                "errors": {"email": "Invalid email or password."}
            }), 401
        except Exception as e:
            err_msg = str(e)
            if "email not confirmed" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "verification_required": True,
                    "email": email,
                    "message": "Please verify your email address before signing in. Check your email for the confirmation link."
                }), 403
            return jsonify({
                "response": "Fail",
                "errors": {"email": "Invalid email or password."}
            }), 401

        user = getattr(auth_resp, "user", None)
        if not user:
            return jsonify({
                "response": "Fail",
                "errors": {"email": "Invalid email or password."}
            }), 401

        user_id = str(user.id)

        # Look up user profile in profiles table
        profile = None
        try:
            p_res = supabase.table("profiles").select("*").eq("user_id", user_id).maybe_single().execute()
            profile = p_res.data if p_res else None
        except Exception:
            profile = None

        if not profile:
            # Fallback to metadata if profile row does not exist yet
            user_meta = getattr(user, "user_metadata", {}) or {}
            # user_metadata is editable by the user themselves, so it must never decide the role
            role = "customer"
            name = user_meta.get("name") or email.split("@")[0]
            profile = {
                "user_id": user_id,
                "name": name,
                "email": email,
                "phone": None,
                "address": None,
                "role": role,
                "approval_status": "approved",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            try:
                supabase.table("profiles").upsert(profile).execute()
            except Exception:
                pass

        # Set Flask session
        session.clear()
        session["user_id"] = user_id
        session["role"] = profile.get("role", "customer")
        session["name"] = profile.get("name", "")

        redirect_url = url_for("admin_page") if session["role"] == "admin" else url_for("home")
        return jsonify({"response": "OK", "redirect": redirect_url}), 200

    @app.route("/logout", methods=["POST"])
    def logout():
        """Clear the session and confirm logout."""
        session.clear()
        return jsonify({"response": "OK"}), 200

    @app.route("/home")
    def home():
        """Landing target after sign-in: redirect to storefront."""
        return redirect("/shop/")

    # =========================================================================
    # STOREFRONT — static pages in ./storefront with dynamic common.js injection
    # =========================================================================
    STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storefront")

    THUMBS = ["thumb-maroon", "thumb-dark", "thumb-sage",
              "thumb-tan", "thumb-mustard", "thumb-terracotta"]

    def _num(x):
        """Numeric(8,2) -> int when whole (499), float otherwise (499.5)."""
        if x is None:
            return 0
        x = float(x)
        return int(x) if x == int(x) else x

    def store_payload():
        """
        Everything the storefront needs, read live from Supabase tables.
        - Items with stock 0 are hidden.
        - Product ids are 'b-<book_id>' / 'a-<art_id>'.
        - Bundles only show while BOTH book and art supply are in stock.
        """
        products = []
        in_stock_books, in_stock_arts = {}, {}

        # Fetch in-stock books with category name
        try:
            b_res = (supabase.table("books")
                     .select("*, book_categories(name)")
                     .gt("stock_qty", 0)
                     .order("book_id")
                     .execute())
            books = b_res.data or []
        except Exception:
            books = []

        for b in books:
            bid = b["book_id"]
            pid = f"b-{bid}"
            in_stock_books[bid] = b
            cat_name = ""
            cat_obj = b.get("book_categories")
            if isinstance(cat_obj, dict):
                cat_name = cat_obj.get("name", "")
            elif isinstance(cat_obj, list) and cat_obj:
                cat_name = cat_obj[0].get("name", "")

            products.append({
                "id": pid,
                "domain": "books",
                "name": b["title"],
                "category": cat_name,
                "price": _num(b["price"]),
                "thumb": THUMBS[bid % len(THUMBS)],
                "blurb": b.get("description") or f"by {b['author']}",
                "author": b["author"],
                "image": b.get("cover_image_url") or None,
                "stock": b["stock_qty"],
                "rank": b.get("rank_order"),
                "bestseller": b.get("rank_order") is not None,
            })

        # Fetch in-stock art supplies with category name
        try:
            a_res = (supabase.table("art_supplies")
                     .select("*, art_categories(name)")
                     .gt("stock_qty", 0)
                     .order("art_id")
                     .execute())
            arts = a_res.data or []
        except Exception:
            arts = []

        for a in arts:
            aid = a["art_id"]
            pid = f"a-{aid}"
            in_stock_arts[aid] = a
            cat_name = ""
            cat_obj = a.get("art_categories")
            if isinstance(cat_obj, dict):
                cat_name = cat_obj.get("name", "")
            elif isinstance(cat_obj, list) and cat_obj:
                cat_name = cat_obj[0].get("name", "")

            products.append({
                "id": pid,
                "domain": "art",
                "name": a["name"],
                "category": cat_name,
                "price": _num(a["price"]),
                "thumb": THUMBS[aid % len(THUMBS)],
                "blurb": a.get("description") or f"by {a['brand']}",
                "brand": a["brand"],
                "image": a.get("image_url") or None,
                "stock": a["stock_qty"],
                "rank": a.get("rank_order"),
                "bestseller": a.get("rank_order") is not None,
            })

        # Fetch bundles (curated pairs)
        try:
            bd_res = supabase.table("bundles").select("*").order("bundle_id").execute()
            bundles = bd_res.data or []
        except Exception:
            bundles = []

        pairs = []
        for bd in bundles:
            book = in_stock_books.get(bd["book_id"])
            art = in_stock_arts.get(bd["art_id"])
            if not book or not art:
                continue
            price = _num(bd["bundle_price"])
            original = max(_num(book["price"]) + _num(art["price"]), price)
            pairs.append({
                "id": f"pair-{bd['bundle_id']}",
                "title": f"{book['title']} + {art['name']}",
                "bookId": f"b-{book['book_id']}",
                "artId": f"a-{art['art_id']}",
                "price": price,
                "originalPrice": original,
                "tag": "Curated Pair",
                "blurb": bd.get("description") or "",
            })

        # Fetch categories
        try:
            bc_res = supabase.table("book_categories").select("name").order("name").execute()
            book_categories = [c["name"] for c in (bc_res.data or []) if "name" in c]
        except Exception:
            book_categories = []

        try:
            ac_res = supabase.table("art_categories").select("name").order("name").execute()
            art_categories = [c["name"] for c in (ac_res.data or []) if "name" in c]
        except Exception:
            art_categories = []

        return {
            "products": products,
            "pairs": pairs,
            "book_categories": book_categories,
            "art_categories": art_categories,
        }

    @app.route("/shop/")
    @app.route("/shop/<path:filename>")
    def storefront(filename="index.html"):
        """Serve storefront files. common.js is built per request to inject window.__ME__ and window.__STORE__."""
        if filename == "common.js":
            me = {"logged_in": False}
            if "user_id" in session:
                try:
                    p_res = supabase.table("profiles").select("*").eq("user_id", session["user_id"]).maybe_single().execute()
                    u = p_res.data if p_res else None
                    if u:
                        me = {
                            "logged_in": True,
                            "name": u.get("name", ""),
                            "email": u.get("email", ""),
                            "phone": u.get("phone") or "",
                            "address": u.get("address") or "",
                            "role": u.get("role", "customer"),
                        }
                except Exception:
                    pass

            with open(os.path.join(STORE_DIR, "auth-bridge.js"), encoding="utf-8") as f:
                bridge = f.read()
            with open(os.path.join(STORE_DIR, "common.js"), encoding="utf-8") as f:
                common = f.read()

            me_js = json.dumps(me).replace("</", "<\\/")
            store_js = json.dumps(store_payload()).replace("</", "<\\/")
            body = (f"window.__ME__ = {me_js};\n"
                    f"window.__STORE__ = {store_js};\n{bridge}\n{common}")
            resp = Response(body, mimetype="application/javascript")
            resp.headers["Cache-Control"] = "no-store"
            return resp

        return send_from_directory(STORE_DIR, filename)

    # =========================================================================
    # CUSTOMER FEEDBACK & STATISTICS
    # =========================================================================

    def _auth_json():
        """JSON 401 for storefront fetch calls when user is unauthenticated."""
        return jsonify({"response": "Fail",
                        "message": "Please sign in to continue."}), 401

    @app.route("/my/feedback", methods=["GET"])
    def my_feedback_list():
        """Customer's past feedback and their order history."""
        if "user_id" not in session:
            return _auth_json()
        uid = session["user_id"]

        try:
            fb_res = (supabase.table("customer_feedback")
                      .select("*, books(title), art_supplies(name), orders(order_ref)")
                      .eq("user_id", uid)
                      .order("created_at", desc=True)
                      .execute())
            items = fb_res.data or []
        except Exception:
            items = []

        out = []
        for f in items:
            if f.get("book_id"):
                b_info = f.get("books")
                target = b_info.get("title") if isinstance(b_info, dict) else "Book"
            elif f.get("art_id"):
                a_info = f.get("art_supplies")
                target = a_info.get("name") if isinstance(a_info, dict) else "Art supply"
            else:
                o_info = f.get("orders")
                target = f"Order {o_info.get('order_ref')}" if (isinstance(o_info, dict) and o_info.get("order_ref")) else "Order"

            out.append({
                "feedback_id": f["feedback_id"],
                "target": target,
                "rating": f["rating"],
                "comment": f["comment"],
                "admin_response": f.get("admin_response"),
                "created_at": f.get("created_at"),
            })

        try:
            o_res = (supabase.table("orders")
                     .select("order_id, order_ref")
                     .eq("user_id", uid)
                     .order("order_date", desc=True)
                     .execute())
            orders = o_res.data or []
        except Exception:
            orders = []

        return jsonify({
            "response": "OK",
            "feedback": out,
            "orders": [{"order_id": o["order_id"], "order_ref": o["order_ref"]} for o in orders]
        }), 200

    @app.route("/my/feedback", methods=["POST"])
    def my_feedback_create():
        """Save customer feedback."""
        if "user_id" not in session:
            return _auth_json()
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_feedback(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        uid = session["user_id"]
        book_id = art_id = order_id = None

        pid = str(data.get("product_id") or "").strip()
        if pid:
            kind, _, num = pid.partition("-")
            if not num.isdigit() or kind not in ("b", "a"):
                return jsonify({"response": "Fail", "errors": {"target": "That item could not be found."}}), 400
            if kind == "b":
                b_chk = supabase.table("books").select("book_id").eq("book_id", int(num)).maybe_single().execute()
                if not (b_chk and b_chk.data):
                    return jsonify({"response": "Fail", "errors": {"target": "That item could not be found."}}), 400
                book_id = int(num)
            elif kind == "a":
                a_chk = supabase.table("art_supplies").select("art_id").eq("art_id", int(num)).maybe_single().execute()
                if not (a_chk and a_chk.data):
                    return jsonify({"response": "Fail", "errors": {"target": "That item could not be found."}}), 400
                art_id = int(num)

        if data.get("order_id"):
            try:
                oid = int(data["order_id"])
            except (TypeError, ValueError):
                oid = None
            if not oid:
                return jsonify({"response": "Fail", "errors": {"target": "That order could not be found."}}), 400
            ord_chk = supabase.table("orders").select("order_id, user_id").eq("order_id", oid).maybe_single().execute()
            if not (ord_chk and ord_chk.data and str(ord_chk.data["user_id"]) == str(uid)):
                return jsonify({"response": "Fail", "errors": {"target": "That order could not be found."}}), 400
            order_id = oid

        fb_record = {
            "user_id": uid,
            "book_id": book_id,
            "art_id": art_id,
            "order_id": order_id,
            "rating": data["rating"],
            "comment": str(data["comment"]).strip(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            supabase.table("customer_feedback").insert(fb_record).execute()
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to submit feedback."}), 500

        return jsonify({"response": "OK", "message": "Thank you! Your feedback has been submitted."}), 201

    @app.route("/my/statistics", methods=["GET"])
    def my_statistics():
        """Purchase statistics for the signed-in customer (paid orders only)."""
        if "user_id" not in session:
            return _auth_json()
        uid = session["user_id"]

        try:
            o_res = (supabase.table("orders")
                     .select("*")
                     .eq("user_id", uid)
                     .eq("payment_status", "paid")
                     .order("order_date", desc=True)
                     .execute())
            orders = o_res.data or []
        except Exception:
            orders = []

        total_spent = 0.0
        items_total = books_qty = art_qty = 0
        cat = {}
        months = {}

        order_ids = [o["order_id"] for o in orders]
        items_by_order = {}
        if order_ids:
            try:
                it_res = (supabase.table("order_items")
                          .select("*, books(book_id, book_categories(name)), art_supplies(art_id, art_categories(name))")
                          .in_("order_id", order_ids)
                          .execute())
                for item in (it_res.data or []):
                    items_by_order.setdefault(item["order_id"], []).append(item)
            except Exception:
                pass

        for o in orders:
            amt = float(o["total_amount"])
            total_spent += amt
            odate_str = str(o.get("order_date") or "")
            key = odate_str[:7] if len(odate_str) >= 7 else None
            if key:
                m = months.setdefault(key, {"spent": 0.0, "orders": 0})
                m["spent"] += amt
                m["orders"] += 1

            for it in items_by_order.get(o["order_id"], []):
                qty = it["quantity"]
                items_total += qty
                price_purchase = float(it["price_at_purchase"])

                if it.get("book_id"):
                    books_qty += qty
                    cat_name = "Books"
                    b_info = it.get("books")
                    if isinstance(b_info, dict) and b_info.get("book_categories"):
                        bc = b_info["book_categories"]
                        cat_name = bc.get("name") if isinstance(bc, dict) else (bc[0].get("name") if isinstance(bc, list) and bc else "Books")
                else:
                    art_qty += qty
                    cat_name = "Art supplies"
                    a_info = it.get("art_supplies")
                    if isinstance(a_info, dict) and a_info.get("art_categories"):
                        ac = a_info["art_categories"]
                        cat_name = ac.get("name") if isinstance(ac, dict) else (ac[0].get("name") if isinstance(ac, list) and ac else "Art supplies")

                c = cat.setdefault(cat_name, {"qty": 0, "spent": 0.0})
                c["qty"] += qty
                c["spent"] += price_purchase * qty

        # Last 6 calendar months
        today = datetime.now(timezone.utc)
        y, mth = today.year, today.month
        monthly = []
        for _ in range(6):
            k = f"{y:04d}-{mth:02d}"
            monthly.append({
                "label": datetime(y, mth, 1).strftime("%b %Y"),
                "spent": round(months.get(k, {}).get("spent", 0.0), 2),
                "orders": months.get(k, {}).get("orders", 0)
            })
            mth -= 1
            if mth == 0:
                y, mth = y - 1, 12
        monthly.reverse()

        top_cats = sorted(({"name": n, **v} for n, v in cat.items()),
                          key=lambda c: (-c["qty"], c["name"]))
        for c in top_cats:
            c["spent"] = round(c["spent"], 2)

        fb_count = 0
        try:
            fb_c_res = supabase.table("customer_feedback").select("feedback_id", count="exact").eq("user_id", uid).execute()
            fb_count = fb_c_res.count if hasattr(fb_c_res, "count") and fb_c_res.count is not None else len(fb_c_res.data or [])
        except Exception:
            pass

        recent_orders = []
        for o in orders[:5]:
            d_str = ""
            odate = o.get("order_date")
            if odate:
                try:
                    dt = datetime.fromisoformat(str(odate).replace("Z", "+00:00"))
                    d_str = dt.strftime("%d %b %Y")
                except Exception:
                    d_str = str(odate)[:10]

            ord_items = items_by_order.get(o["order_id"], [])
            recent_orders.append({
                "order_ref": o["order_ref"],
                "date": d_str,
                "total": float(o["total_amount"]),
                "items": sum(i["quantity"] for i in ord_items),
                "status": o.get("delivery_status", "pending"),
            })

        return jsonify({
            "response": "OK",
            "total_orders": len(orders),
            "total_spent": round(total_spent, 2),
            "items_purchased": items_total,
            "average_order": round(total_spent / len(orders), 2) if orders else 0,
            "books_qty": books_qty,
            "art_qty": art_qty,
            "favourite_category": top_cats[0]["name"] if top_cats else None,
            "categories": top_cats[:6],
            "monthly": monthly,
            "feedback_given": fb_count,
            "recent_orders": recent_orders,
        }), 200

    # =========================================================================
    # ADMIN PAGE
    # =========================================================================

    @app.route("/admin")
    @admin_required
    def admin_page():
        """Render the back-office panel. Pre-loads category lists for dropdowns."""
        try:
            bc_res = supabase.table("book_categories").select("*").order("name").execute()
            book_cats = [{"category_id": c["category_id"], "name": c["name"]} for c in (bc_res.data or [])]
        except Exception:
            book_cats = []

        try:
            ac_res = supabase.table("art_categories").select("*").order("name").execute()
            art_cats = [{"category_id": c["category_id"], "name": c["name"]} for c in (ac_res.data or [])]
        except Exception:
            art_cats = []

        return render_template("admin.html",
                               book_cats=book_cats,
                               art_cats=art_cats,
                               admin_name=session.get("name", "Admin"))

    # =========================================================================
    # ADMIN API — BOOKS
    # =========================================================================

    @app.route("/admin/books", methods=["GET"])
    @admin_required
    def list_books():
        """Return the full book catalogue as JSON."""
        try:
            res = supabase.table("books").select("*, book_categories(name)").order("book_id").execute()
            books = res.data or []
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to load books."}), 500

        out = []
        for b in books:
            cat_name = None
            cat_obj = b.get("book_categories")
            if isinstance(cat_obj, dict):
                cat_name = cat_obj.get("name")
            elif isinstance(cat_obj, list) and cat_obj:
                cat_name = cat_obj[0].get("name")

            out.append({
                "book_id": b["book_id"],
                "title": b["title"],
                "author": b["author"],
                "category_id": b["category_id"],
                "category_name": cat_name,
                "price": float(b["price"]),
                "description": b.get("description"),
                "cover_image_url": b.get("cover_image_url"),
                "stock_qty": b["stock_qty"],
                "units_sold": b.get("units_sold", 0),
                "rank_order": b.get("rank_order"),
            })
        return jsonify({"response": "OK", "data": out}), 200

    @app.route("/admin/books", methods=["POST"])
    @admin_required
    def create_book():
        """Create a new book."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_book(data)
        if not errors:
            try:
                cat_res = supabase.table("book_categories").select("category_id, name").eq("category_id", int(data["category_id"])).maybe_single().execute()
                if not (cat_res and cat_res.data):
                    errors["category_id"] = "The selected category does not exist."
            except Exception:
                errors["category_id"] = "The selected category does not exist."

        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        title = data["title"].strip()
        author = data["author"].strip()

        # Duplicate check (title + author)
        try:
            dup = supabase.table("books").select("book_id").eq("title", title).eq("author", author).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"title": "A book with this title and author already exists."}
                }), 409
        except Exception:
            pass

        new_book = {
            "title": title,
            "author": author,
            "category_id": int(data["category_id"]),
            "price": float(data["price"]),
            "description": (data.get("description") or "").strip() or None,
            "cover_image_url": (data.get("cover_image_url") or "").strip() or None,
            "stock_qty": int(data["stock_qty"]),
            "units_sold": 0,
            "rank_order": int(data["rank_order"]) if data.get("rank_order") else None,
        }

        try:
            ins = supabase.table("books").insert(new_book).execute()
            b = ins.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"title": "A book with this title and author already exists."}
                }), 409
            return jsonify({"response": "Fail", "message": "Database error creating book."}), 500

        cat_name = None
        try:
            c_res = supabase.table("book_categories").select("name").eq("category_id", b["category_id"]).maybe_single().execute()
            if c_res and c_res.data:
                cat_name = c_res.data.get("name")
        except Exception:
            pass

        book_dict = {
            "book_id": b["book_id"],
            "title": b["title"],
            "author": b["author"],
            "category_id": b["category_id"],
            "category_name": cat_name,
            "price": float(b["price"]),
            "description": b.get("description"),
            "cover_image_url": b.get("cover_image_url"),
            "stock_qty": b["stock_qty"],
            "units_sold": b.get("units_sold", 0),
            "rank_order": b.get("rank_order"),
        }
        return jsonify({"response": "OK", "data": book_dict}), 201

    @app.route("/admin/books/<int:book_id>", methods=["PUT"])
    @admin_required
    def update_book(book_id):
        """Update an existing book by ID."""
        try:
            b_chk = supabase.table("books").select("*").eq("book_id", book_id).maybe_single().execute()
            if not (b_chk and b_chk.data):
                return jsonify({"response": "Fail", "message": "Book not found."}), 404
            book = b_chk.data
        except Exception:
            return jsonify({"response": "Fail", "message": "Book not found."}), 404

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_book(data)
        if not errors:
            try:
                cat_res = supabase.table("book_categories").select("category_id").eq("category_id", int(data["category_id"])).maybe_single().execute()
                if not (cat_res and cat_res.data):
                    errors["category_id"] = "The selected category does not exist."
            except Exception:
                errors["category_id"] = "The selected category does not exist."

        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        title = data["title"].strip()
        author = data["author"].strip()

        # Duplicate check excluding current book
        try:
            dup = supabase.table("books").select("book_id").eq("title", title).eq("author", author).neq("book_id", book_id).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"title": "Another book with this title and author already exists."}
                }), 409
        except Exception:
            pass

        update_vals = {
            "title": title,
            "author": author,
            "category_id": int(data["category_id"]),
            "price": float(data["price"]),
            "description": (data.get("description") or "").strip() or None,
            "cover_image_url": (data.get("cover_image_url") or "").strip() or None,
            "stock_qty": int(data["stock_qty"]),
            "rank_order": int(data["rank_order"]) if data.get("rank_order") else None,
        }

        try:
            up = supabase.table("books").update(update_vals).eq("book_id", book_id).execute()
            b = up.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"title": "Duplicate title + author combination."}
                }), 409
            return jsonify({"response": "Fail", "message": "Database error updating book."}), 500

        cat_name = None
        try:
            c_res = supabase.table("book_categories").select("name").eq("category_id", b["category_id"]).maybe_single().execute()
            if c_res and c_res.data:
                cat_name = c_res.data.get("name")
        except Exception:
            pass

        book_dict = {
            "book_id": b["book_id"],
            "title": b["title"],
            "author": b["author"],
            "category_id": b["category_id"],
            "category_name": cat_name,
            "price": float(b["price"]),
            "description": b.get("description"),
            "cover_image_url": b.get("cover_image_url"),
            "stock_qty": b["stock_qty"],
            "units_sold": b.get("units_sold", 0),
            "rank_order": b.get("rank_order"),
        }
        return jsonify({"response": "OK", "data": book_dict}), 200

    @app.route("/admin/books/<int:book_id>", methods=["DELETE"])
    @admin_required
    def delete_book(book_id):
        """Delete a book — blocked if referenced in order history or bundles."""
        try:
            b_chk = supabase.table("books").select("*").eq("book_id", book_id).maybe_single().execute()
            if not (b_chk and b_chk.data):
                return jsonify({"response": "Fail", "message": "Book not found."}), 404
            book = b_chk.data
        except Exception:
            return jsonify({"response": "Fail", "message": "Book not found."}), 404

        # Block deletion if present in order history
        try:
            oi = supabase.table("order_items").select("order_item_id").eq("book_id", book_id).limit(1).execute()
            if oi and oi.data:
                return jsonify({
                    "response": "Fail",
                    "message": (
                        f'Cannot delete "{book["title"]}" — it appears in one or more '
                        f"customer orders. Set stock to 0 to hide it instead."
                    )
                }), 409
        except Exception:
            pass

        # Block deletion if part of a bundle
        try:
            bd = supabase.table("bundles").select("bundle_id").eq("book_id", book_id).limit(1).execute()
            if bd and bd.data:
                return jsonify({
                    "response": "Fail",
                    "message": f'Cannot delete "{book["title"]}" — it is part of a bundle. Remove the bundle first.'
                }), 409
        except Exception:
            pass

        try:
            try:
                supabase.table("cart_items").delete().eq("book_id", book_id).execute()
                supabase.table("wishlist").delete().eq("book_id", book_id).execute()
                supabase.table("customer_feedback").delete().eq("book_id", book_id).execute()
            except Exception:
                pass
            supabase.table("books").delete().eq("book_id", book_id).execute()
        except Exception:
            return jsonify({
                "response": "Fail",
                "message": "Cannot delete — this book is referenced by other records."
            }), 409

        return jsonify({"response": "OK", "message": f'"{book["title"]}" has been deleted.'}), 200

    # =========================================================================
    # ADMIN API — ART SUPPLIES
    # =========================================================================

    @app.route("/admin/art-supplies", methods=["GET"])
    @admin_required
    def list_art_supplies():
        """Return the full art supply catalogue as JSON."""
        try:
            res = supabase.table("art_supplies").select("*, art_categories(name)").order("art_id").execute()
            arts = res.data or []
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to load art supplies."}), 500

        out = []
        for a in arts:
            cat_name = None
            cat_obj = a.get("art_categories")
            if isinstance(cat_obj, dict):
                cat_name = cat_obj.get("name")
            elif isinstance(cat_obj, list) and cat_obj:
                cat_name = cat_obj[0].get("name")

            out.append({
                "art_id": a["art_id"],
                "name": a["name"],
                "brand": a["brand"],
                "category_id": a["category_id"],
                "category_name": cat_name,
                "price": float(a["price"]),
                "description": a.get("description"),
                "image_url": a.get("image_url"),
                "stock_qty": a["stock_qty"],
                "units_sold": a.get("units_sold", 0),
                "rank_order": a.get("rank_order"),
            })
        return jsonify({"response": "OK", "data": out}), 200

    @app.route("/admin/art-supplies", methods=["POST"])
    @admin_required
    def create_art_supply():
        """Create a new art supply."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_art_supply(data)
        if not errors:
            try:
                cat_res = supabase.table("art_categories").select("category_id").eq("category_id", int(data["category_id"])).maybe_single().execute()
                if not (cat_res and cat_res.data):
                    errors["category_id"] = "The selected category does not exist."
            except Exception:
                errors["category_id"] = "The selected category does not exist."

        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        name = data["name"].strip()
        brand = data["brand"].strip()

        try:
            dup = supabase.table("art_supplies").select("art_id").eq("name", name).eq("brand", brand).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "An art supply with this name and brand already exists."}
                }), 409
        except Exception:
            pass

        new_art = {
            "name": name,
            "brand": brand,
            "category_id": int(data["category_id"]),
            "price": float(data["price"]),
            "description": (data.get("description") or "").strip() or None,
            "image_url": (data.get("image_url") or "").strip() or None,
            "stock_qty": int(data["stock_qty"]),
            "units_sold": 0,
            "rank_order": int(data["rank_order"]) if data.get("rank_order") else None,
        }

        try:
            ins = supabase.table("art_supplies").insert(new_art).execute()
            a = ins.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "An art supply with this name and brand already exists."}
                }), 409
            return jsonify({"response": "Fail", "message": "Database error creating art supply."}), 500

        cat_name = None
        try:
            c_res = supabase.table("art_categories").select("name").eq("category_id", a["category_id"]).maybe_single().execute()
            if c_res and c_res.data:
                cat_name = c_res.data.get("name")
        except Exception:
            pass

        art_dict = {
            "art_id": a["art_id"],
            "name": a["name"],
            "brand": a["brand"],
            "category_id": a["category_id"],
            "category_name": cat_name,
            "price": float(a["price"]),
            "description": a.get("description"),
            "image_url": a.get("image_url"),
            "stock_qty": a["stock_qty"],
            "units_sold": a.get("units_sold", 0),
            "rank_order": a.get("rank_order"),
        }
        return jsonify({"response": "OK", "data": art_dict}), 201

    @app.route("/admin/art-supplies/<int:art_id>", methods=["PUT"])
    @admin_required
    def update_art_supply(art_id):
        """Update an existing art supply by ID."""
        try:
            a_chk = supabase.table("art_supplies").select("*").eq("art_id", art_id).maybe_single().execute()
            if not (a_chk and a_chk.data):
                return jsonify({"response": "Fail", "message": "Art supply not found."}), 404
            art = a_chk.data
        except Exception:
            return jsonify({"response": "Fail", "message": "Art supply not found."}), 404

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_art_supply(data)
        if not errors:
            try:
                cat_res = supabase.table("art_categories").select("category_id").eq("category_id", int(data["category_id"])).maybe_single().execute()
                if not (cat_res and cat_res.data):
                    errors["category_id"] = "The selected category does not exist."
            except Exception:
                errors["category_id"] = "The selected category does not exist."

        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        name = data["name"].strip()
        brand = data["brand"].strip()

        try:
            dup = supabase.table("art_supplies").select("art_id").eq("name", name).eq("brand", brand).neq("art_id", art_id).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "Another art supply with this name and brand already exists."}
                }), 409
        except Exception:
            pass

        update_vals = {
            "name": name,
            "brand": brand,
            "category_id": int(data["category_id"]),
            "price": float(data["price"]),
            "description": (data.get("description") or "").strip() or None,
            "image_url": (data.get("image_url") or "").strip() or None,
            "stock_qty": int(data["stock_qty"]),
            "rank_order": int(data["rank_order"]) if data.get("rank_order") else None,
        }

        try:
            up = supabase.table("art_supplies").update(update_vals).eq("art_id", art_id).execute()
            a = up.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "Duplicate name + brand combination."}
                }), 409
            return jsonify({"response": "Fail", "message": "Database error updating art supply."}), 500

        cat_name = None
        try:
            c_res = supabase.table("art_categories").select("name").eq("category_id", a["category_id"]).maybe_single().execute()
            if c_res and c_res.data:
                cat_name = c_res.data.get("name")
        except Exception:
            pass

        art_dict = {
            "art_id": a["art_id"],
            "name": a["name"],
            "brand": a["brand"],
            "category_id": a["category_id"],
            "category_name": cat_name,
            "price": float(a["price"]),
            "description": a.get("description"),
            "image_url": a.get("image_url"),
            "stock_qty": a["stock_qty"],
            "units_sold": a.get("units_sold", 0),
            "rank_order": a.get("rank_order"),
        }
        return jsonify({"response": "OK", "data": art_dict}), 200

    @app.route("/admin/art-supplies/<int:art_id>", methods=["DELETE"])
    @admin_required
    def delete_art_supply(art_id):
        """Delete an art supply — blocked if referenced in order history or bundles."""
        try:
            a_chk = supabase.table("art_supplies").select("*").eq("art_id", art_id).maybe_single().execute()
            if not (a_chk and a_chk.data):
                return jsonify({"response": "Fail", "message": "Art supply not found."}), 404
            art = a_chk.data
        except Exception:
            return jsonify({"response": "Fail", "message": "Art supply not found."}), 404

        try:
            oi = supabase.table("order_items").select("order_item_id").eq("art_id", art_id).limit(1).execute()
            if oi and oi.data:
                return jsonify({
                    "response": "Fail",
                    "message": (
                        f'Cannot delete "{art["name"]}" — it appears in one or more '
                        f"customer orders. Set stock to 0 to hide it instead."
                    )
                }), 409
        except Exception:
            pass

        try:
            bd = supabase.table("bundles").select("bundle_id").eq("art_id", art_id).limit(1).execute()
            if bd and bd.data:
                return jsonify({
                    "response": "Fail",
                    "message": f'Cannot delete "{art["name"]}" — it is part of a bundle. Remove the bundle first.'
                }), 409
        except Exception:
            pass

        try:
            try:
                supabase.table("cart_items").delete().eq("art_id", art_id).execute()
                supabase.table("wishlist").delete().eq("art_id", art_id).execute()
                supabase.table("customer_feedback").delete().eq("art_id", art_id).execute()
            except Exception:
                pass
            supabase.table("art_supplies").delete().eq("art_id", art_id).execute()
        except Exception:
            return jsonify({
                "response": "Fail",
                "message": "Cannot delete — this art supply is referenced by other records."
            }), 409

        return jsonify({"response": "OK", "message": f'"{art["name"]}" has been deleted.'}), 200

    # =========================================================================
    # ADMIN API — CATEGORIES
    # =========================================================================

    @app.route("/admin/book-categories", methods=["POST"])
    @admin_required
    def create_book_category():
        """Create a new book category."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400
        errors = validate_category(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        name = data["name"].strip()
        try:
            dup = supabase.table("book_categories").select("category_id").eq("name", name).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "This book category already exists."}
                }), 409
        except Exception:
            pass

        try:
            ins = supabase.table("book_categories").insert({"name": name}).execute()
            cat = ins.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "This book category already exists."}
                }), 409
            return jsonify({"response": "Fail", "message": "Failed to create category."}), 500

        return jsonify({"response": "OK", "data": {"category_id": cat["category_id"], "name": cat["name"]}}), 201

    @app.route("/admin/art-categories", methods=["POST"])
    @admin_required
    def create_art_category():
        """Create a new art category."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400
        errors = validate_category(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        name = data["name"].strip()
        try:
            dup = supabase.table("art_categories").select("category_id").eq("name", name).maybe_single().execute()
            if dup and dup.data:
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "This art category already exists."}
                }), 409
        except Exception:
            pass

        try:
            ins = supabase.table("art_categories").insert({"name": name}).execute()
            cat = ins.data[0]
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "unique" in err_msg.lower():
                return jsonify({
                    "response": "Fail",
                    "errors": {"name": "This art category already exists."}
                }), 409
            return jsonify({"response": "Fail", "message": "Failed to create category."}), 500

        return jsonify({"response": "OK", "data": {"category_id": cat["category_id"], "name": cat["name"]}}), 201

    # =========================================================================
    # ORDERS API
    # =========================================================================

    @app.route("/orders", methods=["POST"])
    def create_order():
        """
        Create a new order from cart.
        Requires JSON: {"items":[{"id":"b-3","qty":2},...], "payment_method":"UPI"}
        """
        if "user_id" not in session:
            return jsonify({"response": "Fail", "message": "Please sign in to place an order."}), 401

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        items = data.get("items", [])
        if not items or not isinstance(items, list):
            return jsonify({"response": "Fail", "message": "Cart is empty or invalid."}), 400

        valid_payment_methods = ["UPI", "Net Banking", "Credit Card", "Debit Card"]
        payment_method = data.get("payment_method")
        if payment_method not in valid_payment_methods:
            return jsonify({"response": "Fail", "message": "Invalid payment method."}), 400

        # ---- 1. Validate the cart and merge repeated lines of the same product ----
        wanted = {}  # ("b" | "a", product_id) -> total qty (insertion ordered)
        for item in items:
            if not isinstance(item, dict):
                return jsonify({"response": "Fail", "message": "Invalid cart item."}), 400
            item_id = str(item.get("id", "")).strip()
            try:
                qty = int(item.get("qty", 0))
            except (ValueError, TypeError):
                return jsonify({"response": "Fail", "message": "Invalid quantity."}), 400
            if not (1 <= qty <= 20):
                return jsonify({"response": "Fail", "message": "Quantity must be between 1 and 20."}), 400

            kind, _, num = item_id.partition("-")
            if kind not in ("b", "a") or not (num.isascii() and num.isdigit()):
                return jsonify({"response": "Fail", "message": f"Invalid item id {item_id}."}), 400
            key = (kind, int(num))
            wanted[key] = wanted.get(key, 0) + qty
            if wanted[key] > 20:
                return jsonify({"response": "Fail", "message": "Quantity must be between 1 and 20."}), 400

        class _OrderFailed(Exception):
            def __init__(self, message, status):
                super().__init__(message)
                self.message, self.status = message, status

        created_order_id = None
        applied_stock = []  # (table, pk_col, pk, previous_stock, previous_sold) for rollback

        def _rollback():
            """Best-effort undo so a failed checkout never leaves a half-made order."""
            for tbl, pk_col, pk, prev_stock, prev_sold in reversed(applied_stock):
                try:
                    supabase.table(tbl).update(
                        {"stock_qty": prev_stock, "units_sold": prev_sold}
                    ).eq(pk_col, pk).execute()
                except Exception:
                    pass
            if created_order_id is not None:
                for tbl in ("stock_transactions", "order_items", "order_delivery_addresses", "payments"):
                    try:
                        supabase.table(tbl).delete().eq("order_id", created_order_id).execute()
                    except Exception:
                        pass
                try:
                    supabase.table("orders").delete().eq("order_id", created_order_id).execute()
                except Exception:
                    pass

        total_amount = 0.0
        order_items = []

        try:
            # ---- 2. Look every product up and check stock against the MERGED quantity ----
            for (kind, pid), qty in wanted.items():
                if kind == "b":
                    res = supabase.table("books").select("*").eq("book_id", pid).maybe_single().execute()
                    product = res.data if res else None
                    if not product:
                        raise _OrderFailed(f"Book with id {pid} not found.", 404)
                    label = product["title"]
                else:
                    res = supabase.table("art_supplies").select("*").eq("art_id", pid).maybe_single().execute()
                    product = res.data if res else None
                    if not product:
                        raise _OrderFailed(f"Art supply with id {pid} not found.", 404)
                    label = product["name"]
                if product["stock_qty"] < qty:
                    raise _OrderFailed(f"Not enough stock for {label}.", 400)

                price = float(product["price"])
                total_amount += price * qty
                order_items.append({"type": "book" if kind == "b" else "art",
                                    "product": product, "qty": qty, "price": price})

            # Generate unique order_ref
            while True:
                order_ref = "PP-" + "".join([str(random.randint(0, 9)) for _ in range(6)])
                chk = supabase.table("orders").select("order_id").eq("order_ref", order_ref).maybe_single().execute()
                if not (chk and chk.data):
                    break

            uid = session["user_id"]
            order_date_iso = datetime.now(timezone.utc).isoformat()

            # Find default or first saved address for the customer
            user_addr = None
            try:
                addr_res = supabase.table("customer_addresses").select("*").eq("user_id", uid).eq("is_default", True).maybe_single().execute()
                if addr_res and addr_res.data:
                    user_addr = addr_res.data
                else:
                    addr_res2 = supabase.table("customer_addresses").select("*").eq("user_id", uid).limit(1).execute()
                    if addr_res2 and addr_res2.data:
                        user_addr = addr_res2.data[0]
            except Exception:
                user_addr = None

            new_order_data = {
                "user_id": uid,
                "order_ref": order_ref,
                "total_amount": round(total_amount, 2),
                "payment_method": payment_method,
                "payment_status": "paid",
                "order_date": order_date_iso,
                "delivery_status": "processing" if user_addr else "pending",
            }

            if user_addr:
                new_order_data["delivery_address_id"] = user_addr["address_id"]
                new_order_data["shipping_address"] = f"{user_addr['recipient_name']}, {user_addr['address_line1']}, {user_addr['city']}, {user_addr['state']} - {user_addr['postal_code']}"
                new_order_data["delivery_recipient_name"] = user_addr["recipient_name"]
                new_order_data["delivery_phone"] = user_addr["phone"]

            ord_ins = supabase.table("orders").insert(new_order_data).execute()
            order_id = ord_ins.data[0]["order_id"]
            created_order_id = order_id

            # Record payment
            payment_data = {
                "order_id": order_id,
                "user_id": uid,
                "payment_ref": f"PAY-{order_ref}",
                "payment_method": payment_method,
                "amount": round(total_amount, 2),
                "currency": "INR",
                "payment_status": "successful",
                "payment_date": order_date_iso,
                "transaction_details": f"Payment for Order #{order_ref} via {payment_method}"
            }
            supabase.table("payments").insert(payment_data).execute()

            # Record order delivery address snapshot
            if user_addr:
                oda_data = {
                    "order_id": order_id,
                    "address_id": user_addr["address_id"],
                    "recipient_name": user_addr["recipient_name"],
                    "phone": user_addr["phone"],
                    "address_line1": user_addr["address_line1"],
                    "address_line2": user_addr.get("address_line2"),
                    "city": user_addr["city"],
                    "state": user_addr["state"],
                    "postal_code": user_addr["postal_code"],
                    "country": user_addr.get("country", "India"),
                    "delivery_status": "processing",
                    "created_at": order_date_iso
                }
                try:
                    supabase.table("order_delivery_addresses").insert(oda_data).execute()
                except Exception:
                    pass

            # Insert order items, update inventory, and log stock transactions
            for o_item in order_items:
                product = o_item["product"]
                qty = o_item["qty"]
                is_book = (o_item["type"] == "book")
                bid = product["book_id"] if is_book else None
                aid = product["art_id"] if not is_book else None

                supabase.table("order_items").insert({
                    "order_id": order_id,
                    "book_id": bid,
                    "art_id": aid,
                    "quantity": qty,
                    "price_at_purchase": o_item["price"]
                }).execute()

                prev_stock = product["stock_qty"]
                prev_sold = product.get("units_sold") or 0
                new_stock = prev_stock - qty
                tbl, pk_col, pk = ("books", "book_id", bid) if is_book else ("art_supplies", "art_id", aid)

                # Optimistic lock: only succeeds if nobody else changed the stock since we read it,
                # so two simultaneous checkouts can never both take the last copy.
                upd = (supabase.table(tbl)
                       .update({"stock_qty": new_stock, "units_sold": prev_sold + qty})
                       .eq(pk_col, pk)
                       .eq("stock_qty", prev_stock)
                       .execute())
                if not (upd and upd.data):
                    raise _OrderFailed("Stock just changed for an item in your cart. Please review your cart and try again.", 409)
                applied_stock.append((tbl, pk_col, pk, prev_stock, prev_sold))

                stock_tx = {
                    "book_id": bid,
                    "art_id": aid,
                    "transaction_type": "sale",
                    "quantity_change": -qty,
                    "previous_stock": prev_stock,
                    "new_stock": new_stock,
                    "reference_id": order_ref,
                    "order_id": order_id,
                    "created_by_id": uid,
                    "notes": f"Order {order_ref} checkout",
                    "created_at": order_date_iso
                }
                try:
                    supabase.table("stock_transactions").insert(stock_tx).execute()
                except Exception:
                    pass

            return jsonify({
                "response": "OK",
                "order_ref": order_ref,
                "total": round(total_amount, 2),
                "payment_method": payment_method
            }), 201

        except _OrderFailed as e:
            _rollback()
            return jsonify({"response": "Fail", "message": e.message}), e.status
        except Exception:
            _rollback()
            return jsonify({"response": "Fail", "message": "An error occurred while processing your order."}), 500

    # =========================================================================
    # USER ACCOUNT API
    # =========================================================================

    @app.route("/account", methods=["PUT"])
    def update_account():
        """Update profile details for the signed-in user."""
        if "user_id" not in session:
            return jsonify({"response": "Fail", "message": "Please sign in to update your profile."}), 401

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        errors = validate_profile(data)
        if errors:
            return jsonify({"response": "Fail", "errors": errors}), 400

        uid = session["user_id"]
        try:
            p_res = supabase.table("profiles").select("*").eq("user_id", uid).maybe_single().execute()
            if not (p_res and p_res.data):
                return jsonify({"response": "Fail", "message": "User not found."}), 404
            user = p_res.data
        except Exception:
            return jsonify({"response": "Fail", "message": "User not found."}), 404

        name = data["name"].strip()
        phone = (data.get("phone") or "").strip() or None
        address = (data.get("address") or "").strip() or None

        update_vals = {
            "name": name,
            "phone": phone,
            "address": address
        }

        try:
            up = supabase.table("profiles").update(update_vals).eq("user_id", uid).execute()
            updated = up.data[0] if (up and up.data) else {**user, **update_vals}
        except Exception:
            return jsonify({"response": "Fail", "message": "Database error."}), 500

        session["name"] = updated["name"]

        user_dict = {
            "user_id": updated["user_id"],
            "name": updated["name"],
            "email": updated["email"],
            "phone": updated.get("phone"),
            "address": updated.get("address"),
            "role": updated.get("role", "customer"),
            "approval_status": updated.get("approval_status", "approved"),
            "approved_at": updated.get("approved_at"),
            "approved_by_id": updated.get("approved_by_id"),
            "created_dt": updated.get("created_at"),
        }
        return jsonify({"response": "OK", "data": user_dict}), 200

    # =========================================================================
    # CART & WISHLIST API (server-side persistence, tables: cart_items / wishlist)
    # =========================================================================

    def _parse_pid(raw):
        """'b-3' -> ('b', 3), 'a-7' -> ('a', 7); anything else -> None."""
        kind, _, num = str(raw or "").strip().partition("-")
        if kind in ("b", "a") and num.isascii() and num.isdigit():
            return kind, int(num)
        return None

    def _find_product(kind, pid):
        """Return {'label': ..., 'price': ...} for an existing product, else None."""
        if kind == "b":
            r = supabase.table("books").select("book_id, title, price").eq("book_id", pid).maybe_single().execute()
            d = r.data if r else None
            return {"label": d["title"], "price": d["price"]} if d else None
        r = supabase.table("art_supplies").select("art_id, name, price").eq("art_id", pid).maybe_single().execute()
        d = r.data if r else None
        return {"label": d["name"], "price": d["price"]} if d else None

    def _row_to_product(row):
        """Flatten a cart/wishlist row with embedded books / art_supplies."""
        if row.get("book_id") and isinstance(row.get("books"), dict):
            b = row["books"]
            return {"id": f"b-{row['book_id']}", "name": b.get("title"),
                    "price": _num(b.get("price")), "stock": b.get("stock_qty")}
        if row.get("art_id") and isinstance(row.get("art_supplies"), dict):
            a = row["art_supplies"]
            return {"id": f"a-{row['art_id']}", "name": a.get("name"),
                    "price": _num(a.get("price")), "stock": a.get("stock_qty")}
        return None

    @app.route("/my/cart", methods=["GET"])
    def get_cart():
        """The signed-in customer's saved cart."""
        if "user_id" not in session:
            return _auth_json()
        try:
            res = (supabase.table("cart_items")
                   .select("*, books(title, price, stock_qty), art_supplies(name, price, stock_qty)")
                   .eq("user_id", session["user_id"]).order("cart_item_id").execute())
            rows = res.data or []
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to load cart."}), 500

        items = []
        for r in rows:
            prod = _row_to_product(r)
            if prod:
                prod["qty"] = r["quantity"]
                items.append(prod)
        return jsonify({"response": "OK", "items": items}), 200

    @app.route("/my/cart", methods=["PUT"])
    def replace_cart():
        """Replace the saved cart. Body: {"items": [{"id": "b-1", "qty": 2}, ...]} (empty list clears it)."""
        if "user_id" not in session:
            return _auth_json()
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400

        wanted = {}
        for item in data["items"]:
            if not isinstance(item, dict):
                return jsonify({"response": "Fail", "message": "Invalid cart item."}), 400
            parsed = _parse_pid(item.get("id"))
            if not parsed:
                return jsonify({"response": "Fail", "message": f"Invalid item id {item.get('id')}."}), 400
            try:
                qty = int(item.get("qty", 0))
            except (ValueError, TypeError):
                return jsonify({"response": "Fail", "message": "Invalid quantity."}), 400
            wanted[parsed] = wanted.get(parsed, 0) + qty
            if not (1 <= wanted[parsed] <= 20):
                return jsonify({"response": "Fail", "message": "Quantity must be between 1 and 20."}), 400

        uid = session["user_id"]
        new_rows = []
        try:
            for (kind, pid), qty in wanted.items():
                prod = _find_product(kind, pid)
                if not prod:
                    return jsonify({"response": "Fail", "message": f"Item { 'b' if kind == 'b' else 'a' }-{pid} not found."}), 404
                row = {"user_id": uid, "quantity": qty,
                       "updated_at": datetime.now(timezone.utc).isoformat()}
                if kind == "b":
                    row.update({"book_id": pid, "title": prod["label"]})
                else:
                    row.update({"art_id": pid, "name": prod["label"]})
                new_rows.append(row)

            old = supabase.table("cart_items").select("*").eq("user_id", uid).execute().data or []
            supabase.table("cart_items").delete().eq("user_id", uid).execute()
            try:
                for row in new_rows:
                    supabase.table("cart_items").insert(row).execute()
            except Exception:
                # restore the previous cart so a failed save never loses it
                supabase.table("cart_items").delete().eq("user_id", uid).execute()
                for row in old:
                    supabase.table("cart_items").insert({k: v for k, v in row.items() if k != "cart_item_id"}).execute()
                raise
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to save cart."}), 500
        return jsonify({"response": "OK", "count": len(new_rows)}), 200

    @app.route("/my/cart", methods=["DELETE"])
    def clear_cart():
        """Empty the saved cart."""
        if "user_id" not in session:
            return _auth_json()
        try:
            supabase.table("cart_items").delete().eq("user_id", session["user_id"]).execute()
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to clear cart."}), 500
        return jsonify({"response": "OK"}), 200

    @app.route("/my/wishlist", methods=["GET"])
    def get_wishlist():
        """The signed-in customer's wishlist."""
        if "user_id" not in session:
            return _auth_json()
        try:
            res = (supabase.table("wishlist")
                   .select("*, books(title, price, stock_qty), art_supplies(name, price, stock_qty)")
                   .eq("user_id", session["user_id"]).order("wishlist_id").execute())
            rows = res.data or []
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to load wishlist."}), 500
        items = []
        for r in rows:
            prod = _row_to_product(r)
            if prod:
                prod["added_at"] = r.get("added_at")
                items.append(prod)
        return jsonify({"response": "OK", "items": items}), 200

    @app.route("/my/wishlist", methods=["POST"])
    def add_wishlist():
        """Add a product to the wishlist. Body: {"id": "b-1"}. Adding twice is harmless."""
        if "user_id" not in session:
            return _auth_json()
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"response": "Fail", "message": "Invalid request body."}), 400
        parsed = _parse_pid(data.get("id"))
        if not parsed:
            return jsonify({"response": "Fail", "message": "Invalid item id."}), 400
        kind, pid = parsed
        uid = session["user_id"]
        col = "book_id" if kind == "b" else "art_id"
        try:
            prod = _find_product(kind, pid)
            if not prod:
                return jsonify({"response": "Fail", "message": "That item could not be found."}), 404
            dup = supabase.table("wishlist").select("wishlist_id").eq("user_id", uid).eq(col, pid).maybe_single().execute()
            if dup and dup.data:
                return jsonify({"response": "OK", "message": "Already in your wishlist."}), 200
            row = {"user_id": uid, col: pid,
                   "added_at": datetime.now(timezone.utc).isoformat()}
            row["title" if kind == "b" else "name"] = prod["label"]
            supabase.table("wishlist").insert(row).execute()
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to update wishlist."}), 500
        return jsonify({"response": "OK", "message": "Added to your wishlist."}), 201

    @app.route("/my/wishlist/<pid>", methods=["DELETE"])
    def remove_wishlist(pid):
        """Remove one product (e.g. /my/wishlist/b-1) from the wishlist."""
        if "user_id" not in session:
            return _auth_json()
        parsed = _parse_pid(pid)
        if not parsed:
            return jsonify({"response": "Fail", "message": "Invalid item id."}), 400
        kind, num = parsed
        try:
            (supabase.table("wishlist").delete()
             .eq("user_id", session["user_id"])
             .eq("book_id" if kind == "b" else "art_id", num).execute())
        except Exception:
            return jsonify({"response": "Fail", "message": "Failed to update wishlist."}), 500
        return jsonify({"response": "OK"}), 200

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
