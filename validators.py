"""
validators.py — All server-side validation functions for Page & Palette.
Called by every route handler BEFORE touching the database (Layer 2).
Returns a dict of {field_name: error_message}; an empty dict means valid.
"""

import re
from decimal import Decimal, InvalidOperation


# ---------------------------------------------------------------------------
# Compiled regex patterns (compiled once at import time for performance)
# ---------------------------------------------------------------------------
# Strict email format: dot-separated local part (no leading/trailing/double dots),
# domain of valid labels, and an alphabetic TLD of 2+ letters (rejects "a@b.c", "a@b..com").
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9_%+\-]+(?:\.[A-Za-z0-9_%+\-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)
# Indian mobile: 10 digits starting with 6-9, optional +91 prefix
PHONE_RE = re.compile(r"^(\+91)?[6-9]\d{9}$")
# Basic URL sanity check — must start with http:// or https://
URL_RE   = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _t(value):
    """Strip whitespace; return empty string for None/falsy."""
    return str(value or "").strip()


# ---------------------------------------------------------------------------
# Sign-up validation
# ---------------------------------------------------------------------------
def validate_signup(data):
    """Validate all fields submitted via POST /signup."""
    errors = {}

    name     = _t(data.get("name"))
    email    = _t(data.get("email"))
    password = str(data.get("password") or "")
    confirm  = str(data.get("confirm_password") or "")
    phone    = _t(data.get("phone"))
    address  = _t(data.get("address"))

    # Full name
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) > 200:
        errors["name"] = "Name must be 200 characters or fewer."

    # Email
    if not email:
        errors["email"] = "Email address is required."
    elif len(email) > 254 or len(email.split("@")[0]) > 64:
        errors["email"] = "Email address is too long."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."

    # Password (min 8 chars, at least 1 letter and 1 digit)
    pwd_err = _validate_password_strength(password)
    if pwd_err:
        errors["password"] = pwd_err

    # Confirm password (only check if password itself is valid)
    if "password" not in errors:
        if not confirm:
            errors["confirm_password"] = "Please confirm your password."
        elif password != confirm:
            errors["confirm_password"] = "Passwords do not match."

    # Phone (optional, but must be valid Indian mobile if provided)
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid 10-digit Indian mobile number (e.g. 9876543210 or +919876543210)."

    # Address (optional, max 500 chars)
    if address and len(address) > 500:
        errors["address"] = "Address must be 500 characters or fewer."

    return errors


def validate_profile(data):
    """Validate fields submitted via PUT /account (name, phone, address)."""
    errors = {}

    name     = _t(data.get("name"))
    phone    = _t(data.get("phone"))
    address  = _t(data.get("address"))

    # Full name
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) > 200:
        errors["name"] = "Name must be 200 characters or fewer."

    # Phone (optional, but must be valid Indian mobile if provided)
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid 10-digit Indian mobile number (e.g. 9876543210 or +919876543210)."

    # Address (optional, max 500 chars)
    if address and len(address) > 500:
        errors["address"] = "Address must be 500 characters or fewer."

    return errors


def _validate_password_strength(password):
    """Return an error string, or None if the password is acceptable."""
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[a-zA-Z]", password):
        return "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one digit."
    return None


# ---------------------------------------------------------------------------
# Login validation — only checks presence; credential verification is in app.py
# ---------------------------------------------------------------------------
def validate_login(data):
    """Ensure email and password fields are present before DB lookup."""
    errors = {}
    if not _t(data.get("email")):
        errors["email"] = "Email address is required."
    if not str(data.get("password") or ""):
        errors["password"] = "Password is required."
    return errors


# ---------------------------------------------------------------------------
# Customer feedback validation
# ---------------------------------------------------------------------------
def validate_feedback(data):
    """Validate POST /my/feedback: rating 1-5, comment, and what is being reviewed."""
    errors = {}

    rating = data.get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        errors["rating"] = "Please choose a rating from 1 to 5 stars."

    comment = _t(data.get("comment"))
    if not comment:
        errors["comment"] = "Please write a short comment."
    elif len(comment) > 1000:
        errors["comment"] = "Comment must be 1000 characters or fewer."

    if not _t(data.get("product_id")) and not data.get("order_id"):
        errors["target"] = "Choose the book, art supply or order you are reviewing."

    return errors


# ---------------------------------------------------------------------------
# Book validation
# ---------------------------------------------------------------------------
def validate_book(data, db=None, BookCategory=None):
    """
    Validate book form data (create or update).
    Pass db and BookCategory to enable category-existence check (Layer 2 DB read).
    """
    errors = {}

    title       = _t(data.get("title"))
    author      = _t(data.get("author"))
    category_id = data.get("category_id")
    price       = data.get("price")
    description = _t(data.get("description"))
    cover_url   = _t(data.get("cover_image_url"))
    stock_qty   = data.get("stock_qty")
    rank_order  = data.get("rank_order")

    # Title
    if not title:
        errors["title"] = "Title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."

    # Author
    if not author:
        errors["author"] = "Author name is required."
    elif len(author) > 100:
        errors["author"] = "Author name must be 100 characters or fewer."

    # Category (must be a valid integer and exist in the DB)
    cat_err = _validate_fk_int(category_id, "Category")
    if cat_err:
        errors["category_id"] = cat_err
    elif db is not None and BookCategory is not None:
        if not db.session.get(BookCategory, int(category_id)):
            errors["category_id"] = "The selected category does not exist."

    # Price
    price_err = _validate_price(price)
    if price_err:
        errors["price"] = price_err

    # Description (optional)
    if description and len(description) > 2000:
        errors["description"] = "Description must be 2000 characters or fewer."

    # Cover image URL (optional but must be a valid URL if provided)
    if cover_url and not URL_RE.match(cover_url):
        errors["cover_image_url"] = "Cover image URL must begin with http:// or https://."

    # Stock quantity (required, integer >= 0)
    stock_err = _validate_non_neg_int(stock_qty, "Stock quantity")
    if stock_err:
        errors["stock_qty"] = stock_err

    # Rank order (optional, positive integer)
    if rank_order not in (None, "", 0, "0"):
        ro_err = _validate_positive_int(rank_order, "Rank order")
        if ro_err:
            errors["rank_order"] = ro_err

    return errors


# ---------------------------------------------------------------------------
# Art supply validation
# ---------------------------------------------------------------------------
def validate_art_supply(data, db=None, ArtCategory=None):
    """
    Validate art supply form data (create or update).
    Pass db and ArtCategory to enable category-existence check.
    """
    errors = {}

    name        = _t(data.get("name"))
    brand       = _t(data.get("brand"))
    category_id = data.get("category_id")
    price       = data.get("price")
    description = _t(data.get("description"))
    image_url   = _t(data.get("image_url"))
    stock_qty   = data.get("stock_qty")
    rank_order  = data.get("rank_order")

    # Name
    if not name:
        errors["name"] = "Product name is required."
    elif len(name) > 200:
        errors["name"] = "Name must be 200 characters or fewer."

    # Brand
    if not brand:
        errors["brand"] = "Brand is required."
    elif len(brand) > 100:
        errors["brand"] = "Brand must be 100 characters or fewer."

    # Category
    cat_err = _validate_fk_int(category_id, "Category")
    if cat_err:
        errors["category_id"] = cat_err
    elif db is not None and ArtCategory is not None:
        if not db.session.get(ArtCategory, int(category_id)):
            errors["category_id"] = "The selected category does not exist."

    # Price
    price_err = _validate_price(price)
    if price_err:
        errors["price"] = price_err

    # Description (optional)
    if description and len(description) > 2000:
        errors["description"] = "Description must be 2000 characters or fewer."

    # Image URL (optional)
    if image_url and not URL_RE.match(image_url):
        errors["image_url"] = "Image URL must begin with http:// or https://."

    # Stock quantity
    stock_err = _validate_non_neg_int(stock_qty, "Stock quantity")
    if stock_err:
        errors["stock_qty"] = stock_err

    # Rank order (optional)
    if rank_order not in (None, "", 0, "0"):
        ro_err = _validate_positive_int(rank_order, "Rank order")
        if ro_err:
            errors["rank_order"] = ro_err

    return errors


# ---------------------------------------------------------------------------
# Category validation (shared for book and art categories)
# ---------------------------------------------------------------------------
def validate_category(data):
    """Validate a category name for both book and art category endpoints."""
    errors = {}
    name = _t(data.get("name"))
    if not name:
        errors["name"] = "Category name is required."
    elif len(name) > 100:
        errors["name"] = "Category name must be 100 characters or fewer."
    return errors


# ---------------------------------------------------------------------------
# Private helper validators
# ---------------------------------------------------------------------------

def _validate_price(value):
    """Return an error string or None. Price must be > 0, max 2 decimal places."""
    if value is None or str(value).strip() == "":
        return "Price is required."
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return "Price must be a valid number (e.g. 499 or 499.99)."
    if d <= 0:
        return "Price must be greater than ₹0."
    if d > Decimal("99999.99"):
        return "Price must be less than ₹1,00,000."
    # Reject more than 2 decimal places
    if d.as_tuple().exponent < -2:
        return "Price may have at most 2 decimal places."
    return None


def _validate_non_neg_int(value, label="Value"):
    """Return an error string or None. Must be a whole number >= 0."""
    if value is None or str(value).strip() == "":
        return f"{label} is required."
    try:
        v = int(value)
    except (ValueError, TypeError):
        return f"{label} must be a whole number."
    if v < 0:
        return f"{label} cannot be negative."
    return None


def _validate_positive_int(value, label="Value"):
    """Return an error string or None. Must be a whole number >= 1 (or absent)."""
    if value is None or str(value).strip() == "":
        return None   # field is optional
    try:
        v = int(value)
    except (ValueError, TypeError):
        return f"{label} must be a positive whole number."
    if v < 1:
        return f"{label} must be at least 1."
    return None


def _validate_fk_int(value, label="Field"):
    """Return an error string or None. FK selectors must be non-empty integers."""
    if value is None or str(value).strip() == "":
        return f"{label} selection is required."
    try:
        int(value)
    except (ValueError, TypeError):
        return f"{label} must be a valid selection."
    return None
