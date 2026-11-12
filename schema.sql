-- =============================================================================
-- Page & Palette — Supabase PostgreSQL Schema
-- Paste and run this script in the Supabase SQL Editor.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. profiles
-- Links to Supabase auth.users by UUID user_id; stores customer/admin details.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'admin')),
    approval_status TEXT NOT NULL DEFAULT 'approved' CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_at TIMESTAMPTZ,
    approved_by_id UUID REFERENCES profiles(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS ix_profiles_role ON profiles(role);
CREATE INDEX IF NOT EXISTS ix_profiles_approval_status ON profiles(approval_status);

-- -----------------------------------------------------------------------------
-- 2. book_categories
-- Reference table for book genres.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS book_categories (
    category_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. art_categories
-- Reference table for art supply categories.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS art_categories (
    category_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. books
-- Titles sold in the bookstore.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS books (
    book_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category_id INT NOT NULL REFERENCES book_categories(category_id) ON DELETE RESTRICT,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    description TEXT,
    cover_image_url TEXT,
    stock_qty INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    units_sold INT NOT NULL DEFAULT 0 CHECK (units_sold >= 0),
    rank_order INT,
    CONSTRAINT uq_books_title_author UNIQUE (title, author)
);

CREATE INDEX IF NOT EXISTS ix_books_category_id ON books(category_id);
CREATE INDEX IF NOT EXISTS ix_books_title ON books(title);

-- -----------------------------------------------------------------------------
-- 5. art_supplies
-- Art materials sold in the store.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS art_supplies (
    art_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    category_id INT NOT NULL REFERENCES art_categories(category_id) ON DELETE RESTRICT,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    description TEXT,
    image_url TEXT,
    stock_qty INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    units_sold INT NOT NULL DEFAULT 0 CHECK (units_sold >= 0),
    rank_order INT,
    CONSTRAINT uq_art_name_brand UNIQUE (name, brand)
);

CREATE INDEX IF NOT EXISTS ix_art_supplies_category_id ON art_supplies(category_id);
CREATE INDEX IF NOT EXISTS ix_art_supplies_name ON art_supplies(name);

-- -----------------------------------------------------------------------------
-- 6. bundles
-- Curated book + art supply pairing with combo discount.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bundles (
    bundle_id SERIAL PRIMARY KEY,
    book_id INT NOT NULL REFERENCES books(book_id) ON DELETE RESTRICT,
    art_id INT NOT NULL REFERENCES art_supplies(art_id) ON DELETE RESTRICT,
    bundle_price NUMERIC(10, 2) NOT NULL CHECK (bundle_price > 0),
    description TEXT
);

CREATE INDEX IF NOT EXISTS ix_bundles_book_id ON bundles(book_id);
CREATE INDEX IF NOT EXISTS ix_bundles_art_id ON bundles(art_id);

-- -----------------------------------------------------------------------------
-- 7. customer_addresses
-- Saved shipping/delivery addresses for users.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    recipient_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_customer_addresses_user_id ON customer_addresses(user_id);

-- -----------------------------------------------------------------------------
-- 8. orders
-- Placed customer orders.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE RESTRICT,
    order_ref TEXT UNIQUE NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    payment_method TEXT,
    payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed')),
    order_date TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    delivery_address_id INT REFERENCES customer_addresses(address_id) ON DELETE SET NULL,
    shipping_address TEXT,
    delivery_recipient_name TEXT,
    delivery_phone TEXT,
    delivery_status TEXT NOT NULL DEFAULT 'pending' CHECK (delivery_status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    estimated_delivery TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS ix_orders_order_ref ON orders(order_ref);
CREATE INDEX IF NOT EXISTS ix_orders_delivery_address_id ON orders(delivery_address_id);

-- -----------------------------------------------------------------------------
-- 9. order_items
-- Individual line items in an order (price snapshot).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    book_id INT REFERENCES books(book_id) ON DELETE RESTRICT,
    art_id INT REFERENCES art_supplies(art_id) ON DELETE RESTRICT,
    bundle_id INT REFERENCES bundles(bundle_id) ON DELETE SET NULL,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    price_at_purchase NUMERIC(10, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_book_id ON order_items(book_id);
CREATE INDEX IF NOT EXISTS ix_order_items_art_id ON order_items(art_id);
CREATE INDEX IF NOT EXISTS ix_order_items_bundle_id ON order_items(bundle_id);

-- -----------------------------------------------------------------------------
-- 10. order_delivery_addresses
-- Snapshot and fulfillment tracking of delivery address for an order.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_delivery_addresses (
    order_address_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    address_id INT REFERENCES customer_addresses(address_id) ON DELETE SET NULL,
    recipient_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    delivery_status TEXT NOT NULL DEFAULT 'pending' CHECK (delivery_status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    estimated_delivery TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_order_delivery_addresses_order_id ON order_delivery_addresses(order_id);

-- -----------------------------------------------------------------------------
-- 11. customer_feedback
-- Customer reviews and star ratings for books, art supplies, or orders.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    book_id INT REFERENCES books(book_id) ON DELETE CASCADE,
    art_id INT REFERENCES art_supplies(art_id) ON DELETE CASCADE,
    order_id INT REFERENCES orders(order_id) ON DELETE CASCADE,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT NOT NULL,
    admin_response TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT ck_feedback_target CHECK (book_id IS NOT NULL OR art_id IS NOT NULL OR order_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_customer_feedback_user_id ON customer_feedback(user_id);
CREATE INDEX IF NOT EXISTS ix_customer_feedback_book_id ON customer_feedback(book_id);
CREATE INDEX IF NOT EXISTS ix_customer_feedback_art_id ON customer_feedback(art_id);
CREATE INDEX IF NOT EXISTS ix_customer_feedback_order_id ON customer_feedback(order_id);

-- -----------------------------------------------------------------------------
-- 12. payments
-- Payment transaction receipts.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE RESTRICT,
    payment_ref TEXT UNIQUE NOT NULL,
    payment_method TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    payment_status TEXT NOT NULL DEFAULT 'successful' CHECK (payment_status IN ('pending', 'successful', 'paid', 'failed', 'refunded')),
    payment_date TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    transaction_details TEXT
);

CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS ix_payments_ref ON payments(payment_ref);

-- -----------------------------------------------------------------------------
-- 13. combo_purchases
-- Dedicated tracking for bundle / combo purchases.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS combo_purchases (
    combo_purchase_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    bundle_id INT NOT NULL REFERENCES bundles(bundle_id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE RESTRICT,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    price_at_purchase NUMERIC(10, 2) NOT NULL CHECK (price_at_purchase >= 0),
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_combo_purchases_order_id ON combo_purchases(order_id);
CREATE INDEX IF NOT EXISTS ix_combo_purchases_bundle_id ON combo_purchases(bundle_id);
CREATE INDEX IF NOT EXISTS ix_combo_purchases_user_id ON combo_purchases(user_id);

-- -----------------------------------------------------------------------------
-- 14. stock_transactions
-- Audit log of stock movements (sales, replenishments, returns).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_transactions (
    transaction_id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(book_id) ON DELETE SET NULL,
    art_id INT REFERENCES art_supplies(art_id) ON DELETE SET NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('sale', 'replenishment', 'restock', 'return', 'adjustment', 'initial')),
    quantity_change INT NOT NULL,
    previous_stock INT NOT NULL CHECK (previous_stock >= 0),
    new_stock INT NOT NULL CHECK (new_stock >= 0),
    reference_id TEXT,
    order_id INT REFERENCES orders(order_id) ON DELETE SET NULL,
    created_by_id UUID REFERENCES profiles(user_id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_stock_transactions_book_id ON stock_transactions(book_id);
CREATE INDEX IF NOT EXISTS ix_stock_transactions_art_id ON stock_transactions(art_id);
CREATE INDEX IF NOT EXISTS ix_stock_transactions_order_id ON stock_transactions(order_id);
CREATE INDEX IF NOT EXISTS ix_stock_transactions_created_at ON stock_transactions(created_at);

-- -----------------------------------------------------------------------------
-- 15. cart_items (Storefront Cart Persistence)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    book_id INT REFERENCES books(book_id) ON DELETE CASCADE,
    art_id INT REFERENCES art_supplies(art_id) ON DELETE CASCADE,
    bundle_id INT REFERENCES bundles(bundle_id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    title TEXT,
    name TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS ix_cart_items_user_id ON cart_items(user_id);

-- -----------------------------------------------------------------------------
-- 16. wishlist (Storefront Wishlist Persistence)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    book_id INT REFERENCES books(book_id) ON DELETE CASCADE,
    art_id INT REFERENCES art_supplies(art_id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    title TEXT,
    name TEXT,
    CONSTRAINT uq_wishlist_user_book UNIQUE (user_id, book_id),
    CONSTRAINT uq_wishlist_user_art UNIQUE (user_id, art_id)
);

CREATE INDEX IF NOT EXISTS ix_wishlist_user_id ON wishlist(user_id);
