// ===== Page & Palette — script.js (homepage only) =====
// Relies on CATALOG / PAIRS / helper functions defined in common.js

function productCardHTML(product, index) {
  const wished = getWishlist().includes(product.id);
  const rankBadge = product.rank ? `<span class="rank">#${product.rank}</span>` : "";
  const imgTag = product.image ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}" class="product-img" loading="lazy" onerror="this.style.display='none'" />` : "";
  return `
    <article class="product-card" data-id="${product.id}" style="--i:${index || 0}">
      ${rankBadge}
      <div class="thumb-wrap">
        <span class="thumb ${product.thumb}">${imgTag}</span>
        <span class="quick-peek"><i class="icon" data-icon="eye"></i> Quick view</span>
      </div>
      <p class="product-name">${escapeHtml(product.name)}</p>
      <p class="product-meta">${escapeHtml(product.category)} — ₹${product.price}</p>
      <button class="wish-toggle ${wished ? "active" : ""}" type="button"
        aria-label="Toggle wishlist for ${escapeHtml(product.name)}">
        <i class="icon" data-icon="heart"></i>
      </button>
    </article>`;
}

function renderPairingRectangle() {
  const container = document.getElementById("pairsRectangle");
  if (!container) return;

  container.innerHTML = PAIRS.map((pair) => {
    const book = findProduct(pair.bookId);
    const art = findProduct(pair.artId);
    if (!book || !art) return "";

    return `
      <article class="pair-card-item" data-pair-id="${pair.id}">
        <span class="pair-tag">${escapeHtml(pair.tag)}</span>
        <div class="pair-images">
          <div class="pair-img-wrap">
            <img src="${escapeHtml(book.image)}" alt="${escapeHtml(book.name)}" />
          </div>
          <div class="pair-img-wrap">
            <img src="${escapeHtml(art.image)}" alt="${escapeHtml(art.name)}" />
          </div>
        </div>
        <p class="pair-card-title">${escapeHtml(pair.title)}</p>
        <p class="pair-card-sub">${escapeHtml(pair.blurb)}</p>
        <div class="pair-card-footer">
          <span class="pair-price">₹${pair.price} <s class="pair-orig-price">₹${pair.originalPrice}</s></span>
          <span class="pair-preview-btn"><i class="icon" data-icon="eye"></i> Preview</span>
        </div>
      </article>`;
  }).join("");

  renderIcons(container);
}

function renderShelves() {
  renderPairingRectangle();

  const books = CATALOG.filter((p) => p.domain === "books" && p.bestseller).sort((a, b) => a.rank - b.rank);
  const art = CATALOG.filter((p) => p.domain === "art" && p.bestseller).sort((a, b) => a.rank - b.rank);

  document.getElementById("booksShelf").innerHTML = books.map(productCardHTML).join("");
  document.getElementById("artShelf").innerHTML = art.map(productCardHTML).join("");
  renderIcons();
}

function renderResults(products, title) {
  document.getElementById("homeDefault").hidden = true;
  document.getElementById("resultsView").hidden = false;
  document.getElementById("resultsTitle").textContent = title;
  document.getElementById("resultsCount").textContent = `${products.length} item${products.length === 1 ? "" : "s"}`;

  const grid = document.getElementById("resultsGrid");
  const noResults = document.getElementById("noResults");
  grid.innerHTML = products.map(productCardHTML).join("");
  noResults.hidden = products.length > 0;
  renderIcons();
}

function applyUrlFilters() {
  const params = new URLSearchParams(window.location.search);
  const category = params.get("category");
  const query = params.get("q");

  if (query) {
    document.getElementById("siteSearch").value = query;
    const q = query.trim().toLowerCase();
    const matches = CATALOG.filter(
      (p) => p.name.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)
    );
    renderResults(matches, `Results for “${query}”`);
    return;
  }

  if (category) {
    const matches = CATALOG.filter((p) => p.category === category);
    renderResults(matches, category);
    return;
  }

  // "All books" / "All art supplies" from the navigation dropdowns
  const domain = params.get("domain");
  if (domain === "books" || domain === "art") {
    const matches = CATALOG.filter((p) => p.domain === domain);
    renderResults(matches, domain === "books" ? "All books" : "All art supplies");
    return;
  }

  // "Combos" from the navigation bar: only the Book & Art Supply bundles
  if (params.get("view") === "combos") {
    renderShelves();
    document.getElementById("shelfBooks").hidden = true;
    document.getElementById("shelfArt").hidden = true;
    const sub = document.querySelector(".pairs-sub");
    if (sub && !PAIRS.length) sub.textContent = "No combos are available right now — check back soon!";
    return;
  }

  // Default view
  renderShelves();
}

function syncWishHearts() {
  const ids = getWishlist();
  document.querySelectorAll(".product-card").forEach((card) => {
    const btn = card.querySelector(".wish-toggle");
    if (btn) btn.classList.toggle("active", ids.includes(card.dataset.id));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyUrlFilters();
  document.addEventListener("pp:wishlist-changed", syncWishHearts);

  // --- Wishlist heart toggling ---
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".wish-toggle");
    if (!btn) return;
    e.stopPropagation();

    const card = btn.closest(".product-card");
    const id = card.dataset.id;
    const product = findProduct(id);

    const list = toggleWishlist(id);
    btn.classList.toggle("active", list.includes(id));
    btn.classList.add("pulse");
    setTimeout(() => btn.classList.remove("pulse"), 300);

    const wishBadge = document.getElementById("wishlistCount");
    if (wishBadge) wishBadge.textContent = list.length;

    showToast(list.includes(id) ? `Added "${product.name}" to wishlist` : `Removed "${product.name}" from wishlist`);
  });

  // --- Product card click opens quick view ---
  document.addEventListener("click", (e) => {
    const card = e.target.closest(".product-card");
    if (!card || e.target.closest(".wish-toggle")) return;
    openQuickView(card.dataset.id);
  });

  // --- Pairing card click opens pair preview modal ---
  document.addEventListener("click", (e) => {
    const pairCard = e.target.closest(".pair-card-item");
    if (!pairCard) return;
    openPairQuickView(pairCard.dataset.pairId);
  });
});
