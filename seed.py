"""
seed.py — Populates the Supabase PostgreSQL database with:
  • 4 book categories and 3 art categories
  • 24 books
  • 30 art supplies
  • 4 bundles
  • 1 admin user: admin@pagepalette.com / Admin@1234

Uses the Supabase Python SDK directly — no SQLAlchemy.
Idempotent: safe to run multiple times (skips existing records).

Run with:
    python seed.py
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Load environment and initialise Supabase client
# ---------------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SECRET_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Admin credentials
# ---------------------------------------------------------------------------
ADMIN_EMAIL    = "admin@pagepalette.com"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_NAME     = "Page & Palette Admin"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
BOOK_CATEGORIES = ["Fiction", "Mystery & Thriller", "Self-Help", "Poetry"]

ART_CATEGORIES  = ["Drawing & Sketchbooks", "Painting & Brushes", "Art Accessories"]

BOOKS = [
    # --- Fiction (6) ---
    {"title": "The Quiet Hour",            "author": "Clara Whitfield", "category": "Fiction",           "price": 499,  "blurb": "A slow-burn novel about a lighthouse keeper's last summer on the coast.",         "stock": 25, "rank": 1},
    {"title": "Whispers of the Old Oak",   "author": "James Harrow",    "category": "Fiction",           "price": 599,  "blurb": "A gripping tale of family secrets hidden in a rural village.",                     "stock": 18, "rank": None},
    {"title": "The Starling's Journey",    "author": "Priya Menon",     "category": "Fiction",           "price": 449,  "blurb": "An uplifting story of friendship across continents.",                              "stock": 22, "rank": None},
    {"title": "Echoes in the Mist",        "author": "Oliver Strand",   "category": "Fiction",           "price": 549,  "blurb": "Atmospheric novel following a musician's quest for lost melodies.",                "stock": 15, "rank": None},
    {"title": "Shadows of Autumn",         "author": "Nadia Serrano",   "category": "Fiction",           "price": 399,  "blurb": "Poignant storytelling of love, loss, and new beginnings.",                        "stock": 30, "rank": None},
    {"title": "Midnight at the Bookstore", "author": "Tom Ellery",      "category": "Fiction",           "price": 649,  "blurb": "A charming story about a midnight book club and unexpected magic.",                "stock": 20, "rank": None},
    # --- Mystery & Thriller (6) ---
    {"title": "Cold Case, Warm Coffee",    "author": "Ruth Callahan",   "category": "Mystery & Thriller","price": 429,  "blurb": "A small-town detective reopens a decade-old disappearance, one cup at a time.",   "stock": 35, "rank": 2},
    {"title": "The Silent Witness",        "author": "Marcus Dern",     "category": "Mystery & Thriller","price": 549,  "blurb": "A high-stakes courtroom thriller filled with unexpected twists.",                  "stock": 28, "rank": None},
    {"title": "Clockwork Alibi",           "author": "Evelyn Cross",    "category": "Mystery & Thriller","price": 499,  "blurb": "An intricate murder mystery set in Victorian London.",                            "stock": 22, "rank": None},
    {"title": "Vanishing Point",           "author": "Sam Archer",      "category": "Mystery & Thriller","price": 599,  "blurb": "A psychological thriller about a missing wildlife photographer.",                 "stock": 17, "rank": None},
    {"title": "Cipher of the Serpent",     "author": "Laila Nazari",    "category": "Mystery & Thriller","price": 649,  "blurb": "An archeological thriller tracking ancient codebreakers.",                        "stock": 14, "rank": None},
    {"title": "The Glass Labyrinth",       "author": "Peter Vane",      "category": "Mystery & Thriller","price": 529,  "blurb": "A tension-filled puzzle room murder mystery.",                                    "stock": 19, "rank": None},
    # --- Self-Help (6) ---
    {"title": "Small Good Things",         "author": "Anna Lim",        "category": "Self-Help",         "price": 399,  "blurb": "Bite-sized habits for a calmer, kinder daily routine.",                          "stock": 40, "rank": 3},
    {"title": "Mindful Mornings",          "author": "Rohan Kapoor",    "category": "Self-Help",         "price": 499,  "blurb": "Practical guides to starting your day with clarity and focus.",                   "stock": 33, "rank": None},
    {"title": "The Art of Deep Rest",      "author": "Celia Marsh",     "category": "Self-Help",         "price": 449,  "blurb": "Unlocking the secrets of true recovery and stress relief.",                      "stock": 27, "rank": None},
    {"title": "Digital Detox & Focus",     "author": "Ben Holloway",    "category": "Self-Help",         "price": 529,  "blurb": "Reclaiming your attention in a hyper-connected world.",                          "stock": 31, "rank": None},
    {"title": "Courage to Begin",          "author": "Maya Patel",      "category": "Self-Help",         "price": 379,  "blurb": "Overcoming self-doubt and building lasting momentum.",                           "stock": 45, "rank": None},
    {"title": "Habit Crafting 101",        "author": "Leo Grant",       "category": "Self-Help",         "price": 459,  "blurb": "A step-by-step blueprint for building personal routines.",                       "stock": 38, "rank": None},
    # --- Poetry (6) ---
    {"title": "Quiet Static",              "author": "Iris Bloom",      "category": "Poetry",            "price": 349,  "blurb": "Short, plainspoken poems about noise, silence, and everything between.",         "stock": 20, "rank": None},
    {"title": "Constellations Within",     "author": "Dev Sharma",      "category": "Poetry",            "price": 399,  "blurb": "Verses exploring intimacy, grief, and emotional healing.",                       "stock": 16, "rank": None},
    {"title": "Paper Lanterns",            "author": "Yuki Tanaka",     "category": "Poetry",            "price": 299,  "blurb": "Haiku and short poems celebrating nature's subtle transitions.",                 "stock": 24, "rank": None},
    {"title": "River of Solitude",         "author": "Fiona Walsh",     "category": "Poetry",            "price": 429,  "blurb": "Reflective modern poetry on memory, time, and belonging.",                       "stock": 18, "rank": None},
    {"title": "Threads of Sunlight",       "author": "Carlos Vega",     "category": "Poetry",            "price": 379,  "blurb": "Lyrical prose poems celebrating small daily wonders.",                           "stock": 21, "rank": None},
    {"title": "Echoes of Rain",            "author": "Nina Frost",      "category": "Poetry",            "price": 319,  "blurb": "Evocative stanzas written during quiet rainy seasons.",                          "stock": 26, "rank": None},
]

ART_SUPPLIES = [
    # --- Drawing & Sketchbooks (12) ---
    {"name": "Willow Charcoal Tin",             "brand": "Winsor & Newton", "category": "Drawing & Sketchbooks", "price": 299,  "blurb": "Soft, mid, and hard willow sticks for fast tonal studies.",                                           "stock": 40, "rank": 4},
    {"name": "Graphite Sketching Pencil Set",   "brand": "Staedtler",       "category": "Drawing & Sketchbooks", "price": 399,  "blurb": "12 graded pencils from 9B to 9H in a durable metal case.",                                           "stock": 35, "rank": None},
    {"name": "Compressed Charcoal Blocks",      "brand": "Daler-Rowney",    "category": "Drawing & Sketchbooks", "price": 249,  "blurb": "Rich black charcoal blocks for dramatic shading and gestures.",                                       "stock": 50, "rank": None},
    {"name": "Architectural Fineliner Pens",    "brand": "Rotring",         "category": "Drawing & Sketchbooks", "price": 499,  "blurb": "Waterproof pigment liners in sizes 0.05 to 0.8mm for technical line art.",                            "stock": 28, "rank": None},
    {"name": "Kneaded Eraser & Stump Pack",     "brand": "Faber-Castell",   "category": "Drawing & Sketchbooks", "price": 199,  "blurb": "Malleable erasers and paper blending stumps for soft smudging.",                                      "stock": 60, "rank": None},
    {"name": "Colored Pencil Set of 24",        "brand": "Prismacolor",     "category": "Drawing & Sketchbooks", "price": 699,  "blurb": "Soft-core artist pencils with vibrant color payoff and smooth layering.",                             "stock": 22, "rank": None},
    {"name": "Hardbound Sketchbook",            "brand": "Moleskine",       "category": "Drawing & Sketchbooks", "price": 349,  "blurb": "160gsm toothy paper, 96 pages, lies flat at every spread.",                                          "stock": 45, "rank": 3},
    {"name": "Cold-Press Watercolor Block",     "brand": "Arches",          "category": "Drawing & Sketchbooks", "price": 699,  "blurb": "300gsm 100% cotton paper, 20 sheets bound on 4 sides for zero buckling.",                             "stock": 18, "rank": None},
    {"name": "Tone-Tan Mixed Media Journal",    "brand": "Strathmore",      "category": "Drawing & Sketchbooks", "price": 449,  "blurb": "Heavyweight tan paper ideal for working with both dark and white highlights.",                         "stock": 30, "rank": None},
    {"name": "Black Paper Sketch Pad",          "brand": "Canson",          "category": "Drawing & Sketchbooks", "price": 399,  "blurb": "High-contrast black sheets perfect for gel pens, metallic inks, and gouache.",                        "stock": 25, "rank": None},
    {"name": "Spiral Bound Mixed Media Pad",    "brand": "Daler-Rowney",    "category": "Drawing & Sketchbooks", "price": 499,  "blurb": "200gsm multi-technique paper with micro-perforated pages.",                                          "stock": 32, "rank": None},
    {"name": "Vintage Handmade Deckle Journal", "brand": "Paperblanks",     "category": "Drawing & Sketchbooks", "price": 799,  "blurb": "Recycled cotton paper with torn deckled edges and genuine leather wrap.",                             "stock": 12, "rank": None},
    # --- Painting & Brushes (12) ---
    {"name": "12-Shade Gouache Set",            "brand": "Winsor & Newton", "category": "Painting & Brushes",   "price": 799,  "blurb": "Highly pigmented, reactivatable gouache in a travel-friendly tin.",                                    "stock": 30, "rank": 1},
    {"name": "Professional Artist Oil Paints",  "brand": "Gamblin",         "category": "Painting & Brushes",   "price": 1299, "blurb": "Set of 10 essential 40ml oil paint tubes with high lightfastness.",                                    "stock": 15, "rank": None},
    {"name": "Heavy-Body Acrylic Set",          "brand": "Golden",          "category": "Painting & Brushes",   "price": 899,  "blurb": "Vibrant, thick-consistency acrylic paints for rich impasto textures.",                                "stock": 20, "rank": None},
    {"name": "Botanical Watercolor Pans",       "brand": "Schmincke",       "category": "Painting & Brushes",   "price": 999,  "blurb": "18 artist-grade half pans with folding palette lid for field painting.",                              "stock": 18, "rank": None},
    {"name": "Metallic Palette Gouache",        "brand": "Holbein",         "category": "Painting & Brushes",   "price": 599,  "blurb": "Shimmering gold, bronze, and silver accent colors for special details.",                              "stock": 25, "rank": None},
    {"name": "Fabric & Textile Paint Set",      "brand": "Jacquard",        "category": "Painting & Brushes",   "price": 649,  "blurb": "Permanent, washable paints for custom canvas bags, jackets, and textiles.",                           "stock": 22, "rank": None},
    {"name": "Round Brush Trio",                "brand": "Princeton",       "category": "Painting & Brushes",   "price": 549,  "blurb": "Three synthetic rounds in sizes 2, 6, and 10 for detail through wash work.",                          "stock": 35, "rank": 2},
    {"name": "Flat Wash Brush Set",             "brand": "Da Vinci",        "category": "Painting & Brushes",   "price": 649,  "blurb": "Wide synthetic flats ideal for smooth background washes and acrylic grounds.",                        "stock": 28, "rank": None},
    {"name": "Hake Goat-Hair Mop Brush",        "brand": "Yasutomo",        "category": "Painting & Brushes",   "price": 399,  "blurb": "Soft natural hair brush for delicate wet-on-wet watercolor washes.",                                  "stock": 40, "rank": None},
    {"name": "Detail Micro Brush Set",          "brand": "Raphael",         "category": "Painting & Brushes",   "price": 429,  "blurb": "Precision miniature brushes (sizes 0000 to 1) for fine linework.",                                    "stock": 32, "rank": None},
    {"name": "Filbert Bristle Brushes",         "brand": "Escoda",          "category": "Painting & Brushes",   "price": 599,  "blurb": "Curved-edge hog bristle brushes for oil and acrylic paint blending.",                                 "stock": 26, "rank": None},
    {"name": "Bamboo Sumi-e Brush",             "brand": "Yasutomo",        "category": "Painting & Brushes",   "price": 349,  "blurb": "Traditional Asian calligraphy and expressive ink wash brush.",                                        "stock": 20, "rank": None},
    # --- Art Accessories (6) ---
    {"name": "Washi Tape Set",                  "brand": "MT Masking Tape", "category": "Art Accessories",      "price": 249,  "blurb": "Six rolls of low-tack patterned tape for masking borders and journals.",                               "stock": 50, "rank": None},
    {"name": "Wooden Artist Manikin",           "brand": "Jack Richeson",   "category": "Art Accessories",      "price": 399,  "blurb": "12-inch posable wooden figure for figure drawing and proportion reference.",                           "stock": 30, "rank": None},
    {"name": "Stainless Steel Palette Knives",  "brand": "Liquitex",        "category": "Art Accessories",      "price": 499,  "blurb": "Set of 5 flexible stainless steel palette knives for impasto and paint mixing.",                       "stock": 25, "rank": None},
    {"name": "Wooden Table Easel",              "brand": "Mabef",           "category": "Art Accessories",      "price": 899,  "blurb": "Adjustable H-frame desktop easel crafted from solid seasoned beechwood.",                             "stock": 15, "rank": None},
    {"name": "Ceramic Brush Rest & Dish",       "brand": "Speedball",       "category": "Art Accessories",      "price": 299,  "blurb": "Hand-glazed pottery dish with grooved rests for rinsing and drying brushes.",                         "stock": 40, "rank": None},
    {"name": "Airtight Paint Saver Palette",    "brand": "Masterson",       "category": "Art Accessories",      "price": 599,  "blurb": "Leak-proof palette box with silicone seal to keep paint fresh for weeks.",                            "stock": 20, "rank": None},
]

BUNDLES = [
    {
        "book_title":  "The Quiet Hour",
        "art_name":    "Willow Charcoal Tin",
        "price":       749,
        "description": "Pair the haunting coastal story of 'The Quiet Hour' with soft willow charcoal for moody tonal sketches.",
    },
    {
        "book_title":  "Cold Case, Warm Coffee",
        "art_name":    "12-Shade Gouache Set",
        "price":       1149,
        "description": "Unravel detective mysteries in 'Cold Case, Warm Coffee' while painting rich opaque scenes in gouache.",
    },
    {
        "book_title":  "Quiet Static",
        "art_name":    "Round Brush Trio",
        "price":       849,
        "description": "Read minimalist poetry verses alongside a trio of synthetic round brushes for delicate ink wash studies.",
    },
    {
        "book_title":  "Whispers of the Old Oak",
        "art_name":    "Hardbound Sketchbook",
        "price":       899,
        "description": "Immerse yourself in village secrets and immediately sketch your ideas in a 160gsm lay-flat sketchbook.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def upsert_category(table: str, name: str) -> int:
    """Insert a category if it doesn't exist; return its ID either way."""
    res = supabase.table(table).select("category_id").eq("name", name).execute()
    if res.data:
        print(f"[seed] {table} '{name}' already exists — skipped.")
        return res.data[0]["category_id"]
    ins = supabase.table(table).insert({"name": name}).execute()
    cid = ins.data[0]["category_id"]
    print(f"[seed] Created {table} '{name}' (id={cid}).")
    return cid


def seed_books(book_cat_map: dict):
    for b in BOOKS:
        cat_id = book_cat_map.get(b["category"])
        if cat_id is None:
            print(f"[seed] WARNING: category '{b['category']}' not found — book '{b['title']}' skipped.")
            continue
        # Idempotency check
        exists = supabase.table("books").select("book_id")\
            .eq("title", b["title"]).eq("author", b["author"])\
            .execute()
        if exists.data:
            print(f"[seed] Book '{b['title']}' already exists — skipped.")
            continue
        supabase.table("books").insert({
            "title":       b["title"],
            "author":      b["author"],
            "category_id": cat_id,
            "price":       b["price"],
            "description": b["blurb"],
            "stock_qty":   b["stock"],
            "units_sold":  0,
            "rank_order":  b.get("rank"),
        }).execute()
        print(f"[seed] Created Book '{b['title']}'.")


def seed_art_supplies(art_cat_map: dict):
    for a in ART_SUPPLIES:
        cat_id = art_cat_map.get(a["category"])
        if cat_id is None:
            print(f"[seed] WARNING: category '{a['category']}' not found — art supply '{a['name']}' skipped.")
            continue
        exists = supabase.table("art_supplies").select("art_id")\
            .eq("name", a["name"]).eq("brand", a["brand"])\
            .execute()
        if exists.data:
            print(f"[seed] ArtSupply '{a['name']}' already exists — skipped.")
            continue
        supabase.table("art_supplies").insert({
            "name":        a["name"],
            "brand":       a["brand"],
            "category_id": cat_id,
            "price":       a["price"],
            "description": a["blurb"],
            "stock_qty":   a["stock"],
            "units_sold":  0,
            "rank_order":  a.get("rank"),
        }).execute()
        print(f"[seed] Created ArtSupply '{a['name']}'.")


def seed_bundles():
    for bun in BUNDLES:
        book = supabase.table("books").select("book_id")\
            .eq("title", bun["book_title"]).execute()
        art  = supabase.table("art_supplies").select("art_id")\
            .eq("name", bun["art_name"]).execute()

        if not book.data:
            print(f"[seed] WARNING: book '{bun['book_title']}' not found — bundle skipped.")
            continue
        if not art.data:
            print(f"[seed] WARNING: art supply '{bun['art_name']}' not found — bundle skipped.")
            continue

        book_id = book.data[0]["book_id"]
        art_id  = art.data[0]["art_id"]

        exists = supabase.table("bundles").select("bundle_id")\
            .eq("book_id", book_id).eq("art_id", art_id)\
            .execute()
        if exists.data:
            print(f"[seed] Bundle ({bun['book_title']} + {bun['art_name']}) already exists — skipped.")
            continue

        supabase.table("bundles").insert({
            "book_id":      book_id,
            "art_id":       art_id,
            "bundle_price": bun["price"],
            "description":  bun["description"],
        }).execute()
        print(f"[seed] Created Bundle: {bun['book_title']} + {bun['art_name']}.")


def seed_admin():
    """Create the admin user via Supabase Auth and insert their profile row."""
    # Check if profile already exists (idempotent)
    existing = supabase.table("profiles").select("user_id")\
        .eq("email", ADMIN_EMAIL).maybe_single().execute()
    if existing.data:
        print(f"[seed] Admin user '{ADMIN_EMAIL}' already exists — skipped.")
        return

    # Create admin account in Supabase Auth
    try:
        res = supabase.auth.sign_up({
            "email":    ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "options":  {
                "data": {
                    "name": ADMIN_NAME,
                    "role": "admin",
                }
            }
        })
        user_id = res.user.id
    except Exception as e:
        err_msg = str(e)
        # If the auth account already exists but profile row is missing, fetch the UID
        if "already registered" in err_msg or "User already registered" in err_msg:
            print(f"[seed] Auth account for {ADMIN_EMAIL} already exists — inserting profile only.")
            # Sign in to get the UID
            try:
                login = supabase.auth.sign_in_with_password({
                    "email":    ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                })
                user_id = login.user.id
            except Exception as login_err:
                print(f"[seed] ERROR: Could not retrieve admin UID: {login_err}")
                return
        else:
            print(f"[seed] ERROR creating admin auth account: {e}")
            return

    # Insert profile row
    supabase.table("profiles").insert({
        "user_id":         str(user_id),
        "name":            ADMIN_NAME,
        "email":           ADMIN_EMAIL,
        "role":            "admin",
        "approval_status": "approved",
    }).execute()
    print(f"[seed] Created admin user: {ADMIN_EMAIL} (UUID: {user_id})")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary():
    book_cats  = supabase.table("book_categories").select("category_id", count="exact").execute()
    art_cats   = supabase.table("art_categories").select("category_id",  count="exact").execute()
    books      = supabase.table("books").select("book_id",               count="exact").execute()
    arts       = supabase.table("art_supplies").select("art_id",         count="exact").execute()
    bundles    = supabase.table("bundles").select("bundle_id",           count="exact").execute()
    profiles   = supabase.table("profiles").select("user_id",            count="exact").execute()

    print("\n" + "=" * 55)
    print(" Page & Palette — database seeded successfully!")
    print("=" * 55)
    print(f"  Book Categories : {book_cats.count}")
    print(f"  Art Categories  : {art_cats.count}")
    print(f"  Books           : {books.count}")
    print(f"  Art Supplies    : {arts.count}")
    print(f"  Bundles         : {bundles.count}")
    print(f"  Profiles (users): {profiles.count}")
    print("=" * 55)
    print(f"  Admin login  ->  {ADMIN_EMAIL}")
    print(f"  Password     ->  {ADMIN_PASSWORD}")
    print("=" * 55 + "\n")
    print("NOTE: The admin email needs to be verified before first login.")
    print("      Go to your Supabase Dashboard > Authentication > Users,")
    print(f"      find {ADMIN_EMAIL}, click the 3-dot menu → Confirm email.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def seed():
    print("[seed] Connecting to Supabase...")

    # Categories
    print("\n[seed] Seeding book categories...")
    book_cat_map = {name: upsert_category("book_categories", name) for name in BOOK_CATEGORIES}

    print("\n[seed] Seeding art categories...")
    art_cat_map  = {name: upsert_category("art_categories",  name) for name in ART_CATEGORIES}

    # Products
    print("\n[seed] Seeding books...")
    seed_books(book_cat_map)

    print("\n[seed] Seeding art supplies...")
    seed_art_supplies(art_cat_map)

    print("\n[seed] Seeding bundles...")
    seed_bundles()

    # Admin user
    print("\n[seed] Seeding admin user...")
    seed_admin()

    # Summary
    print_summary()


if __name__ == "__main__":
    seed()
