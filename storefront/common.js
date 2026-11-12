function escapeXml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

function escapeHtml(str) {
  return String(str == null ? '' : str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

const COLOR_PALETTES = {
  "thumb-maroon": { bg: "#7A3B2E", accent: "#4A1E14" },
  "thumb-dark": { bg: "#3D2B1F", accent: "#1F140D" },
  "thumb-sage": { bg: "#5A6B4A", accent: "#3B4730" },
  "thumb-tan": { bg: "#9E7B56", accent: "#6B5034" },
  "thumb-mustard": { bg: "#D48F28", accent: "#945F12" },
  "thumb-terracotta": { bg: "#B54D20", accent: "#732C0D" }
};

function generateBookCoverDataUri(title, category, thumbClass) {
  const palette = COLOR_PALETTES[thumbClass] || COLOR_PALETTES["thumb-maroon"];
  const words = title.split(' ');
  let line1 = title, line2 = '';
  if (words.length > 2) {
    const mid = Math.ceil(words.length / 2);
    line1 = words.slice(0, mid).join(' ');
    line2 = words.slice(mid).join(' ');
  }

  const titleSvg = line2
    ? `<text x="200" y="300" text-anchor="middle" fill="#FFF3E4" font-family="'Fraunces', Georgia, serif" font-size="28" font-weight="bold">${escapeXml(line1)}</text>
       <text x="200" y="338" text-anchor="middle" fill="#FFF3E4" font-family="'Fraunces', Georgia, serif" font-size="28" font-weight="bold">${escapeXml(line2)}</text>`
    : `<text x="200" y="320" text-anchor="middle" fill="#FFF3E4" font-family="'Fraunces', Georgia, serif" font-size="30" font-weight="bold">${escapeXml(line1)}</text>`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 560" width="100%" height="100%">
    <defs>
      <linearGradient id="bgGrad_${thumbClass}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${palette.bg}"/>
        <stop offset="100%" stop-color="${palette.accent}"/>
      </linearGradient>
      <linearGradient id="spineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="rgba(0,0,0,0.5)"/>
        <stop offset="70%" stop-color="rgba(0,0,0,0.1)"/>
        <stop offset="100%" stop-color="rgba(255,255,255,0.2)"/>
      </linearGradient>
    </defs>
    <rect width="400" height="560" rx="14" fill="url(#bgGrad_${thumbClass})"/>
    <rect x="0" y="0" width="28" height="560" rx="6" fill="url(#spineGrad)"/>
    <rect x="34" y="32" width="332" height="496" rx="8" fill="none" stroke="rgba(255,243,228,0.35)" stroke-width="2"/>
    <rect x="44" y="42" width="312" height="476" rx="6" fill="none" stroke="rgba(255,243,228,0.2)" stroke-dasharray="6,4" stroke-width="1.5"/>
    <circle cx="200" cy="175" r="60" fill="rgba(255,243,228,0.12)"/>
    <polygon points="200,125 215,160 250,160 220,182 232,217 200,195 168,217 180,182 150,160 185,160" fill="rgba(255,243,228,0.85)"/>
    ${titleSvg}
    <text x="200" y="405" text-anchor="middle" fill="#E8A33D" font-family="sans-serif" font-size="13" font-weight="bold" letter-spacing="3" text-transform="uppercase">${escapeXml(category)}</text>
    <line x1="140" y1="425" x2="260" y2="425" stroke="rgba(255,243,228,0.4)" stroke-width="1.5"/>
    <text x="200" y="458" text-anchor="middle" fill="rgba(255,243,228,0.8)" font-family="Georgia, serif" font-size="13" font-style="italic">Page &amp; Palette Original</text>
  </svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

function generateArtSupplyDataUri(name, category, thumbClass) {
  const palette = COLOR_PALETTES[thumbClass] || COLOR_PALETTES["thumb-mustard"];
  const words = name.split(' ');
  let line1 = name, line2 = '';
  if (words.length > 2) {
    const mid = Math.ceil(words.length / 2);
    line1 = words.slice(0, mid).join(' ');
    line2 = words.slice(mid).join(' ');
  }

  const titleSvg = line2
    ? `<text x="200" y="385" text-anchor="middle" fill="#3D2B1F" font-family="sans-serif" font-size="22" font-weight="bold">${escapeXml(line1)}</text>
       <text x="200" y="415" text-anchor="middle" fill="#3D2B1F" font-family="sans-serif" font-size="22" font-weight="bold">${escapeXml(line2)}</text>`
    : `<text x="200" y="398" text-anchor="middle" fill="#3D2B1F" font-family="sans-serif" font-size="24" font-weight="bold">${escapeXml(line1)}</text>`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 560" width="100%" height="100%">
    <defs>
      <linearGradient id="artBgGrad_${thumbClass}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${palette.bg}"/>
        <stop offset="100%" stop-color="${palette.accent}"/>
      </linearGradient>
    </defs>
    <rect width="400" height="560" rx="14" fill="url(#artBgGrad_${thumbClass})"/>
    <circle cx="200" cy="190" r="100" fill="rgba(255,253,245,0.85)"/>
    <path d="M160 160 C180 120, 220 120, 240 160 C260 200, 240 240, 200 240 C160 240, 140 200, 160 160 Z" fill="#C1592B" opacity="0.8"/>
    <rect x="180" y="140" width="40" height="90" rx="6" fill="#7A3B2E"/>
    <polygon points="200,100 215,140 185,140" fill="#E8A33D"/>
    <rect x="35" y="335" width="330" height="175" rx="12" fill="#FFF3E4" stroke="#EED7BC" stroke-width="2"/>
    <text x="200" y="362" text-anchor="middle" fill="#C1592B" font-family="sans-serif" font-size="12" font-weight="bold" letter-spacing="2" text-transform="uppercase">${escapeXml(category)}</text>
    ${titleSvg}
    <text x="200" y="462" text-anchor="middle" fill="#94714B" font-family="sans-serif" font-size="12" font-weight="600">Artist Quality Supply</text>
    <line x1="160" y1="482" x2="240" y2="482" stroke="#E8A33D" stroke-width="3" stroke-linecap="round"/>
  </svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

// ---- Catalogue: read live from the database ----
// Flask injects window.__STORE__ when it serves this file (see app.py store_payload()).
// Products with stock 0 are already excluded; bundles only appear while both items are in stock.
const STORE = window.__STORE__ || { products: [], pairs: [], book_categories: [], art_categories: [] };
const CATALOG = STORE.products.map((p) => Object.assign({}, p));
const PAIRS = STORE.pairs.slice();

// Use the admin's image URL when given, otherwise fall back to the generated cover
CATALOG.forEach((p) => {
  if (!p.image) {
    p.image = p.domain === "books"
      ? generateBookCoverDataUri(p.name, p.category, p.thumb)
      : generateArtSupplyDataUri(p.name, p.category, p.thumb);
  }
});

function findProduct(id) {
  return CATALOG.find((p) => p.id === id);
}

// Drop cart / wishlist entries whose product no longer exists (deleted, out of stock,
// or saved under the old built-in ids) and cap quantities to current stock.
(function pruneStaleStorage() {
  try {
    const cart = getCart();
    const cleanCart = cart
      .filter((e) => findProduct(e.id))
      .map((e) => Object.assign({}, e, { qty: Math.max(1, Math.min(e.qty || 1, findProduct(e.id).stock || 1)) }));
    if (JSON.stringify(cart) !== JSON.stringify(cleanCart)) saveCart(cleanCart);
    const wl = getWishlist();
    const cleanWl = wl.filter((id) => findProduct(id));
    if (cleanWl.length !== wl.length) saveWishlist(cleanWl);
  } catch (e) { /* storage blocked: ignore */ }
})();

// ---- Customer navigation bar (all storefront pages) ----
// "Hello, <name>", Books / Art Supplies dropdowns built from the DATABASE categories
// (STORE.book_categories / STORE.art_categories), plus Combos, Feedback, Wishlist,
// Cart, Statistics and Logout. Pages just contain <header id="customerNav">.
function buildCustomerNav() {
  const nav = document.getElementById("customerNav");
  if (!nav) return;

  const me = window.__ME__ || { logged_in: false };
  const params = new URLSearchParams(window.location.search);
  const page = (window.location.pathname.split("/").pop() || "index.html").toLowerCase();
  const curCategory = params.get("category");
  const curDomain = params.get("domain");
  const onHome = page === "index.html";
  const isBooksPage = onHome && (curDomain === "books" ||
    (curCategory && STORE.book_categories.indexOf(curCategory) > -1));
  const isArtPage = onHome && (curDomain === "art" ||
    (curCategory && STORE.art_categories.indexOf(curCategory) > -1));

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function link(href, label, active) {
    const a = el("a", "cnav-link" + (active ? " active" : ""), label);
    a.href = href;
    return a;
  }
  function iconLink(href, label, iconName, badgeId, active) {
    const a = el("a", "cnav-link" + (active ? " active" : ""));
    a.href = href;
    const i = el("i", "icon"); i.dataset.icon = iconName;
    a.appendChild(i);
    a.appendChild(document.createTextNode(" " + label));
    if (badgeId) {
      const b = el("span", "cnav-badge", "0"); b.id = badgeId;
      a.appendChild(b);
    }
    return a;
  }
  function dropdown(label, allHref, allLabel, categories, active) {
    const wrap = el("div", "cnav-dd");
    const btn = el("button", "cnav-link cnav-dd-btn" + (active ? " active" : ""));
    btn.type = "button";
    btn.setAttribute("aria-haspopup", "true");
    btn.setAttribute("aria-expanded", "false");
    btn.appendChild(document.createTextNode(label + " "));
    const chev = el("i", "icon cnav-chev"); chev.dataset.icon = "chevron";
    btn.appendChild(chev);

    const menu = el("div", "cnav-menu");
    const all = el("a", "cnav-menu-item cnav-menu-all", allLabel);
    all.href = allHref;
    if (onHome && curDomain === (label === "Books" ? "books" : "art")) all.classList.add("active");
    menu.appendChild(all);
    if (!categories.length) {
      menu.appendChild(el("span", "cnav-menu-empty", "No categories yet"));
    }
    categories.forEach((name) => {
      const a = el("a", "cnav-menu-item", name);
      a.href = "index.html?category=" + encodeURIComponent(name);
      a.dataset.category = name;
      if (onHome && curCategory === name) a.classList.add("active");
      menu.appendChild(a);
    });

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = !wrap.classList.contains("open");
      closeAllMenus();
      wrap.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    wrap.appendChild(btn);
    wrap.appendChild(menu);
    return wrap;
  }
  function closeAllMenus() {
    nav.querySelectorAll(".cnav-dd.open").forEach((d) => {
      d.classList.remove("open");
      d.querySelector(".cnav-dd-btn").setAttribute("aria-expanded", "false");
    });
  }

  nav.innerHTML = "";
  const inner = el("div", "cnav-inner");

  // Brand
  const logo = el("a", "cnav-logo");
  logo.href = "index.html";
  logo.innerHTML = '<svg width="26" height="26" viewBox="0 0 30 30" aria-hidden="true">' +
    '<path d="M6 24 L6 7 Q6 5 8 5 L15 5 L15 24 Q11 22 6 24 Z" fill="#FFF3E4"></path>' +
    '<path d="M24 24 L24 7 Q24 5 22 5 L15 5 L15 24 Q19 22 24 24 Z" fill="#E8A33D"></path>' +
    '<path d="M15 5 L20 1 L21.5 2.5 L16.5 6.2 Z" fill="#F2C6A0"></path></svg>';
  logo.appendChild(el("span", null, "Page & Palette"));
  inner.appendChild(logo);

  // Greeting — name comes from the signed-in account (database)
  const hello = el("p", "cnav-hello");
  hello.appendChild(document.createTextNode("Hello, "));
  const nameEl = el("span", "cnav-hello-name", me.logged_in ? me.name : "Guest");
  nameEl.id = "greetingName";
  hello.appendChild(nameEl);
  inner.appendChild(hello);

  // Links
  const links = el("nav", "cnav-links");
  links.setAttribute("aria-label", "Customer navigation");
  links.appendChild(dropdown("Books", "index.html?domain=books", "All books",
    STORE.book_categories, isBooksPage));
  links.appendChild(dropdown("Art Supplies", "index.html?domain=art", "All art supplies",
    STORE.art_categories, isArtPage));
  links.appendChild(link("index.html?view=combos", "Combos", onHome && params.get("view") === "combos"));
  links.appendChild(link("feedback.html", "Feedback", page === "feedback.html"));
  links.appendChild(iconLink("wishlist.html", "Wishlist", "heart", "wishlistCount", page === "wishlist.html"));
  links.appendChild(iconLink("cart.html", "Cart", "bag", "cartCount",
    page === "cart.html" || page === "checkout.html"));
  links.appendChild(link("statistics.html", "Statistics", page === "statistics.html"));

  if (me.logged_in) {
    const out = el("button", "cnav-link cnav-logout", "Logout");
    out.type = "button";
    out.addEventListener("click", () => {
      out.disabled = true;
      fetch("/logout", { method: "POST" }).finally(() => { window.location.href = "/"; });
    });
    links.appendChild(out);
  } else {
    const inn = link("/", "Sign in", false);
    inn.classList.add("cnav-logout");
    links.appendChild(inn);
  }
  inner.appendChild(links);
  nav.appendChild(inner);

  document.addEventListener("click", closeAllMenus);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAllMenus(); });
}

// ---- Icons (inline SVG, replaces emoji glyphs) ----
const ICONS = {
  heart: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-6.7-4.35-9.3-8.2C1 10.1 1.4 6.6 4.2 5.1c2.3-1.25 4.9-.5 6.3 1.4.4.5.7 1 1 1.4l.5.7.5-.7c.3-.4.6-.9 1-1.4 1.4-1.9 4-2.65 6.3-1.4 2.8 1.5 3.2 5 1.5 7.7C18.7 16.65 12 21 12 21z"/></svg>',
  bag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8h12l-1 12.5a1.5 1.5 0 0 1-1.5 1.5h-7a1.5 1.5 0 0 1-1.5-1.5L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>',
  headset: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="3" y="13" width="4.5" height="6" rx="1.5"/><rect x="16.5" y="13" width="4.5" height="6" rx="1.5"/><path d="M20.5 19v.5A3.5 3.5 0 0 1 17 23h-2.5"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>',
  flame: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c1 3-2.5 4.2-2.5 7.3 0 1.5 1 2.6 2.5 2.6s2.5-1.1 2.5-2.6C14.5 8 13.5 6.7 13.5 5c2.5 1.5 5 4.7 5 8.3C18.5 17.6 15.6 21 12 21s-6.5-3.4-6.5-7.7C5.5 8.7 9 5 12 2z"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.7 14.9A8.6 8.6 0 0 1 9.1 3.3a.7.7 0 0 0-.9-.9A10 10 0 1 0 21.6 15.8a.7.7 0 0 0-.9-.9z"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 5l14 14M19 5 5 19"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 12h14"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 .8 12.1A2 2 0 0 0 8.8 21h6.4a2 2 0 0 0 2-1.9L18 7"/></svg>',
  arrowRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>',
  card: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>',
  upi: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v16H4z"/><path d="M12 7v10M8 10l4-3 4 3"/></svg>',
  bank: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M3 10h18M5 10v11M9 10v11M15 10v11M19 10v11M12 3l9 7H3l9-7z"/></svg>'
};

function renderIcons(root) {
  (root || document).querySelectorAll(".icon[data-icon]").forEach((el) => {
    const name = el.dataset.icon;
    if (ICONS[name] && el.innerHTML.trim() === "") el.innerHTML = ICONS[name];
  });
}

// ---- Theme (light / dark) ----
function getTheme() {
  return localStorage.getItem("pp_theme") || (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelectorAll(".theme-toggle .icon").forEach((el) => {
    el.dataset.icon = theme === "dark" ? "sun" : "moon";
    el.innerHTML = "";
  });
  renderIcons();
}
function toggleTheme() {
  const next = getTheme() === "dark" ? "light" : "dark";
  localStorage.setItem("pp_theme", next);
  applyTheme(next);
}

// ---- Profile ----
function getProfile() {
  return JSON.parse(localStorage.getItem("pp_profile") || "null");
}
function saveProfile(profile) {
  localStorage.setItem("pp_profile", JSON.stringify(profile));
}
function initials(name) {
  if (!name || !name.trim()) return "JS";
  return name.trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

// ---- Wishlist ----
function getWishlist() {
  try {
    const data = JSON.parse(localStorage.getItem("pp_wishlist") || "[]");
    return Array.isArray(data) ? data.filter((id) => typeof id === "string" && id.trim() !== "") : [];
  } catch (e) {
    return [];
  }
}
function saveWishlist(list) {
  localStorage.setItem("pp_wishlist", JSON.stringify(list));
}
function toggleWishlist(id) {
  const list = getWishlist();
  const idx = list.indexOf(id);
  if (idx > -1) list.splice(idx, 1);
  else list.push(id);
  saveWishlist(list);
  return list;
}

// ---- Cart (quantity-aware) ----
function getCart() {
  try {
    const data = JSON.parse(localStorage.getItem("pp_cart") || "[]");
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
}
function saveCart(cart) {
  localStorage.setItem("pp_cart", JSON.stringify(cart));
}
function clearCart() {
  saveCart([]);
  applyHeaderState();
}
function getCartItemCount() {
  return getCart().reduce((sum, e) => sum + (e.qty || 1), 0);
}
function addToCart(id, qty, note) {
  qty = qty || 1;
  const cart = getCart();
  const existing = cart.find((e) => e.id === id);
  if (existing) {
    existing.qty += qty;
  } else {
    cart.push({ id, qty, note: note || null });
  }
  saveCart(cart);
  return cart;
}
function setCartQty(id, qty) {
  let cart = getCart();
  if (qty <= 0) {
    cart = cart.filter((e) => e.id !== id);
  } else {
    const entry = cart.find((e) => e.id === id);
    if (entry) entry.qty = qty;
  }
  saveCart(cart);
  return cart;
}
function removeFromCart(id) {
  const cart = getCart().filter((e) => e.id !== id);
  saveCart(cart);
  return cart;
}

// ---- Toast feedback ----
function showToast(message) {
  let toast = document.getElementById("ppToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "ppToast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.remove("show");
  // force reflow so repeated toasts re-trigger the animation
  void toast.offsetWidth;
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), 2400);
}

// ---- Quick-view modal (shared across pages) ----
function ensureQuickViewModal() {
  let modal = document.getElementById("quickView");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "quickView";
  modal.className = "qv-backdrop";
  modal.innerHTML = `
    <div class="qv-card" role="dialog" aria-modal="true" aria-labelledby="qvName">
      <button class="qv-close" type="button" aria-label="Close quick view">
        <i class="icon" data-icon="x"></i>
      </button>
      <div class="qv-media">
        <span class="thumb qv-thumb" id="qvThumb"></span>
      </div>
      <div class="qv-body">
        <p class="qv-category" id="qvCategory"></p>
        <h2 id="qvName"></h2>
        <p class="qv-price" id="qvPrice"></p>
        <p class="qv-blurb" id="qvBlurb"></p>
        <div class="qv-actions">
          <div class="qty-stepper" id="qvQtyStepper">
            <button type="button" class="qty-btn" data-step="-1" aria-label="Decrease quantity"><i class="icon" data-icon="minus"></i></button>
            <span id="qvQty">1</span>
            <button type="button" class="qty-btn" data-step="1" aria-label="Increase quantity"><i class="icon" data-icon="plus"></i></button>
          </div>
          <button class="btn-primary" type="button" id="qvAddBtn">Add to cart</button>
          <button class="wish-toggle qv-wish" type="button" id="qvWishBtn" aria-label="Toggle wishlist">
            <i class="icon" data-icon="heart"></i>
          </button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(modal);

  let qty = 1;
  let currentId = null;

  function close() {
    modal.classList.remove("open");
    document.body.classList.remove("qv-locked");
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) close();
  });
  modal.querySelector(".qv-close").addEventListener("click", close);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("open")) close();
  });

  modal.querySelector("#qvQtyStepper").addEventListener("click", (e) => {
    const btn = e.target.closest(".qty-btn");
    if (!btn) return;
    qty = Math.max(1, qty + Number(btn.dataset.step));
    modal.querySelector("#qvQty").textContent = qty;
  });

  modal.querySelector("#qvAddBtn").addEventListener("click", () => {
    if (!currentId) return;
    const p = findProduct(currentId);
    addToCart(currentId, qty);
    applyHeaderState();
    showToast(`Added ${qty > 1 ? qty + " × " : ""}"${p.name}" to cart`);
    close();
  });

  modal.querySelector("#qvWishBtn").addEventListener("click", () => {
    if (!currentId) return;
    const list = toggleWishlist(currentId);
    modal.querySelector("#qvWishBtn").classList.toggle("active", list.includes(currentId));
    applyHeaderState();
    document.dispatchEvent(new CustomEvent("pp:wishlist-changed"));
  });

  modal._open = (id) => {
    const p = findProduct(id);
    if (!p) return;
    currentId = id;
    qty = 1;
    const thumbEl = modal.querySelector("#qvThumb");
    thumbEl.className = `thumb qv-thumb ${p.thumb}`;
    thumbEl.innerHTML = p.image ? `<img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" class="product-img" onerror="this.style.display='none'" />` : "";
    modal.querySelector("#qvCategory").textContent = p.category;
    modal.querySelector("#qvName").textContent = p.name;
    modal.querySelector("#qvPrice").textContent = `₹${p.price}`;
    modal.querySelector("#qvBlurb").textContent = p.blurb || "";
    modal.querySelector("#qvQty").textContent = "1";
    modal.querySelector("#qvWishBtn").classList.toggle("active", getWishlist().includes(id));
    renderIcons(modal);
    modal.classList.add("open");
    document.body.classList.add("qv-locked");
  };

  return modal;
}
function openQuickView(id) {
  ensureQuickViewModal()._open(id);
}

// ---- Pair quick-view modal ----
function ensurePairQuickViewModal() {
  let modal = document.getElementById("pairQuickView");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "pairQuickView";
  modal.className = "qv-backdrop";
  modal.innerHTML = `
    <div class="qv-card qv-pair-card" role="dialog" aria-modal="true" aria-labelledby="pqvTitle">
      <button class="qv-close" type="button" aria-label="Close quick view">
        <i class="icon" data-icon="x"></i>
      </button>
      <div class="qv-pair-media">
        <div class="qv-pair-img-box">
          <p class="qv-pair-img-label">Book</p>
          <span class="thumb qv-thumb" id="pqvBookThumb"></span>
          <p class="qv-pair-item-name" id="pqvBookName"></p>
        </div>
        <div class="qv-pair-img-box">
          <p class="qv-pair-img-label">Art Supply</p>
          <span class="thumb qv-thumb" id="pqvArtThumb"></span>
          <p class="qv-pair-item-name" id="pqvArtName"></p>
        </div>
      </div>
      <div class="qv-body">
        <span class="pair-tag" id="pqvTag">Curated Pairing</span>
        <h2 id="pqvTitle"></h2>
        <p class="qv-price" id="pqvPrice"></p>
        <p class="qv-blurb" id="pqvBlurb"></p>
        <div class="qv-actions">
          <button class="btn-primary" type="button" id="pqvAddBtn">Add Pair to Cart</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(modal);

  let currentPairId = null;

  function close() {
    modal.classList.remove("open");
    document.body.classList.remove("qv-locked");
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) close();
  });
  modal.querySelector(".qv-close").addEventListener("click", close);

  modal.querySelector("#pqvAddBtn").addEventListener("click", () => {
    if (!currentPairId) return;
    const pair = PAIRS.find((p) => p.id === currentPairId);
    if (!pair) return;
    addToCart(pair.bookId, 1, pair.title);
    addToCart(pair.artId, 1, pair.title);
    applyHeaderState();
    showToast(`Added "${pair.title}" to cart`);
    close();
  });

  modal._open = (pairId) => {
    const pair = PAIRS.find((p) => p.id === pairId);
    if (!pair) return;
    const book = findProduct(pair.bookId);
    const art = findProduct(pair.artId);
    if (!book || !art) return;

    currentPairId = pairId;
    modal.querySelector("#pqvTag").textContent = pair.tag || "Curated Pairing";
    modal.querySelector("#pqvTitle").textContent = pair.title;
    modal.querySelector("#pqvPrice").textContent = `₹${pair.price} (Save ₹${pair.originalPrice - pair.price})`;
    modal.querySelector("#pqvBlurb").textContent = pair.blurb;

    const bThumb = modal.querySelector("#pqvBookThumb");
    bThumb.className = `thumb qv-thumb ${book.thumb}`;
    bThumb.innerHTML = `<img src="${escapeHtml(book.image)}" alt="${escapeHtml(book.name)}" class="product-img" />`;
    modal.querySelector("#pqvBookName").textContent = book.name;

    const aThumb = modal.querySelector("#pqvArtThumb");
    aThumb.className = `thumb qv-thumb ${art.thumb}`;
    aThumb.innerHTML = `<img src="${escapeHtml(art.image)}" alt="${escapeHtml(art.name)}" class="product-img" />`;
    modal.querySelector("#pqvArtName").textContent = art.name;

    renderIcons(modal);
    modal.classList.add("open");
    document.body.classList.add("qv-locked");
  };

  return modal;
}

function openPairQuickView(pairId) {
  ensurePairQuickViewModal()._open(pairId);
}

// ---- Shared header state (badges + avatar initials + theme) on every page ----
function applyHeaderState() {
  const profile = getProfile();

  document.querySelectorAll(".avatar").forEach((el) => {
    el.textContent = initials(profile && profile.name);
  });

  const wishBadge = document.getElementById("wishlistCount");
  if (wishBadge) wishBadge.textContent = getWishlist().length;

  const cartBadge = document.getElementById("cartCount");
  if (cartBadge) cartBadge.textContent = getCartItemCount();

  const greeting = document.getElementById("greetingName");
  if (greeting) greeting.textContent = (profile && profile.name) || ((window.__ME__ || {}).name) || "Guest";
}

document.addEventListener("DOMContentLoaded", () => {
  applyTheme(getTheme());
  buildCustomerNav();
  applyHeaderState();
  renderIcons();

  const themeBtn = document.querySelector(".theme-toggle");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);
});
