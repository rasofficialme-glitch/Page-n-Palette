/**
 * admin.js — Back-office JavaScript for Page & Palette.
 * Uses plain fetch + async/await (no Vue, no framework).
 * All admin API calls use the correct HTTP method for each action:
 *   GET  list, POST  create, PUT  update, DELETE  delete.
 */

"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentTab     = "books";  // "books" | "art"
let currentBookId  = null;     // null = create mode, number = edit mode
let currentArtId   = null;

// Local copies of categories (repopulated after adding a new one)
let bookCats = window.BOOK_CATS || [];
let artCats  = window.ART_CATS  || [];

// ---------------------------------------------------------------------------
// Initialisation — load both tables on page load
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadBooks();
  loadArtSupplies();
});

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function switchAdminTab(tab) {
  currentTab = tab;

  document.getElementById("panel-books").hidden = (tab !== "books");
  document.getElementById("panel-art").hidden   = (tab !== "art");

  document.getElementById("nav-books").classList.toggle("active", tab === "books");
  document.getElementById("nav-art").classList.toggle("active", tab === "art");
}

// ---------------------------------------------------------------------------
// Banner helpers
// ---------------------------------------------------------------------------
function showBanner(message, type = "error") {
  const el = document.getElementById("adminBanner");
  el.textContent = message;
  el.className   = "global-banner " + type;
  el.hidden      = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (type === "success") setTimeout(() => { el.hidden = true; }, 4000);
}

// ---------------------------------------------------------------------------
// Field error helpers (generic — used by both books and art forms)
// ---------------------------------------------------------------------------
function clearFormErrors(fields) {
  fields.forEach((f) => {
    const err = document.getElementById(`${f}-err`);
    const inp = document.getElementById(f);
    if (err) err.textContent = "";
    if (inp) inp.classList.remove("error");
  });
}

function showFormErrors(errors, fields) {
  Object.entries(errors).forEach(([field, msg]) => {
    // Map validator field names to DOM IDs
    const idMap = {
      title: "b-title", author: "b-author", category_id: "b-category",
      price: "b-price", stock_qty: "b-stock", rank_order: "b-rank",
      description: "b-desc", cover_image_url: "b-cover",
      name: currentTab === "books" ? "b-title" : "a-name",
      brand: "a-brand",
      image_url: "a-image",
    };
    const domId  = idMap[field] || field;
    const errEl  = document.getElementById(`${domId}-err`);
    const inpEl  = document.getElementById(domId);
    if (errEl) { errEl.textContent = msg; }
    if (inpEl) { inpEl.classList.add("error"); }
  });
}

// ---------------------------------------------------------------------------
// Client-side (Layer 1) validation — called before every fetch
// ---------------------------------------------------------------------------
const URL_RE_ADMIN = /^https?:\/\/\S+$/i;

function validateBookClient() {
  const errors = {};
  const title  = document.getElementById("b-title").value.trim();
  const author = document.getElementById("b-author").value.trim();
  const cat    = document.getElementById("b-category").value;
  const price  = parseFloat(document.getElementById("b-price").value);
  const stock  = parseInt(document.getElementById("b-stock").value, 10);
  const rank   = document.getElementById("b-rank").value.trim();
  const cover  = document.getElementById("b-cover").value.trim();

  if (!title)               errors["b-title"] = "Title is required.";
  if (!author)              errors["b-author"] = "Author is required.";
  if (!cat)                 errors["b-category"] = "Please select a category.";
  if (!price || price <= 0) errors["b-price"] = "Price must be greater than 0.";
  else if (!/^\d+(\.\d{1,2})?$/.test(document.getElementById("b-price").value))
                            errors["b-price"] = "Price may have at most 2 decimal places.";
  if (isNaN(stock) || stock < 0) errors["b-stock"] = "Stock must be 0 or more.";
  if (rank && (isNaN(parseInt(rank, 10)) || parseInt(rank, 10) < 1))
                            errors["b-rank"] = "Rank order must be a positive integer.";
  if (cover && !URL_RE_ADMIN.test(cover))
                            errors["b-cover"] = "Cover URL must start with http:// or https://.";
  return errors;
}

function validateArtClient() {
  const errors = {};
  const name   = document.getElementById("a-name").value.trim();
  const brand  = document.getElementById("a-brand").value.trim();
  const cat    = document.getElementById("a-category").value;
  const price  = parseFloat(document.getElementById("a-price").value);
  const stock  = parseInt(document.getElementById("a-stock").value, 10);
  const rank   = document.getElementById("a-rank").value.trim();
  const image  = document.getElementById("a-image").value.trim();

  if (!name)                errors["a-name"]  = "Name is required.";
  if (!brand)               errors["a-brand"] = "Brand is required.";
  if (!cat)                 errors["a-category"] = "Please select a category.";
  if (!price || price <= 0) errors["a-price"] = "Price must be greater than 0.";
  else if (!/^\d+(\.\d{1,2})?$/.test(document.getElementById("a-price").value))
                            errors["a-price"] = "Price may have at most 2 decimal places.";
  if (isNaN(stock) || stock < 0) errors["a-stock"] = "Stock must be 0 or more.";
  if (rank && (isNaN(parseInt(rank, 10)) || parseInt(rank, 10) < 1))
                            errors["a-rank"] = "Rank order must be a positive integer.";
  if (image && !URL_RE_ADMIN.test(image))
                            errors["a-image"] = "Image URL must start with http:// or https://.";
  return errors;
}

// ---------------------------------------------------------------------------
// BOOKS — load and render table
// ---------------------------------------------------------------------------
async function loadBooks() {
  try {
    const res  = await fetch("/admin/books");
    const data = await res.json();
    if (data.response === "OK") {
      renderBooksTable(data.data);
    } else {
      document.getElementById("booksTableBody").innerHTML =
        `<tr><td colspan="8" class="table-empty">Failed to load books.</td></tr>`;
    }
  } catch (err) {
    console.error("loadBooks error:", err);
  }
}

function renderBooksTable(books) {
  const tbody = document.getElementById("booksTableBody");
  if (!books.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty">No books yet — add one above.</td></tr>`;
    return;
  }
  tbody.innerHTML = books.map((b) => `
    <tr>
      <td>${b.book_id}</td>
      <td><strong>${esc(b.title)}</strong></td>
      <td>${esc(b.author)}</td>
      <td>${esc(b.category_name || "—")}</td>
      <td>₹${b.price.toFixed(2)}</td>
      <td>${b.stock_qty}</td>
      <td>${b.rank_order ?? "—"}</td>
      <td>
        <div class="table-actions">
          <button class="btn-edit" onclick="editBook(${b.book_id})" aria-label="Edit ${esc(b.title)}">${ICON_PENCIL} Edit</button>
          <button class="btn-danger" data-name="${esc(b.title)}" onclick="deleteBook(${b.book_id}, this.dataset.name)" aria-label="Delete ${esc(b.title)}">${ICON_TRASH} Delete</button>
        </div>
      </td>
    </tr>
  `).join("");
}

// ---- Book form open/close ----
function openBookForm(book) {
  currentBookId = book ? book.book_id : null;
  document.getElementById("bookFormTitle").textContent = book ? "Edit Book" : "Add New Book";
  document.getElementById("bookEditId").value = book ? book.book_id : "";

  // Pre-fill or reset fields
  document.getElementById("b-title").value  = book ? book.title       : "";
  document.getElementById("b-author").value = book ? book.author      : "";
  document.getElementById("b-price").value  = book ? book.price       : "";
  document.getElementById("b-stock").value  = book ? book.stock_qty   : "";
  document.getElementById("b-rank").value   = book ? (book.rank_order ?? "") : "";
  document.getElementById("b-cover").value  = book ? (book.cover_image_url ?? "") : "";
  document.getElementById("b-desc").value   = book ? (book.description ?? "") : "";

  // Set category dropdown
  if (book) {
    document.getElementById("b-category").value = book.category_id;
  } else {
    document.getElementById("b-category").value = "";
  }

  clearFormErrors(["b-title","b-author","b-category","b-price","b-stock","b-rank","b-cover","b-desc"]);
  document.getElementById("bookFormCard").hidden = false;
  document.getElementById("b-title").focus();
  document.getElementById("bookFormCard").scrollIntoView({ behavior: "smooth" });
}

function cancelBookForm() {
  currentBookId = null;
  document.getElementById("bookFormCard").hidden = true;
}

function editBook(bookId) {
  // Fetch from the already-loaded table data by re-querying
  fetch("/admin/books")
    .then((r) => r.json())
    .then((data) => {
      const book = data.data.find((b) => b.book_id === bookId);
      if (book) openBookForm(book);
    });
}

// ---- Book form submit (POST create / PUT update) ----
async function submitBookForm() {
  // Layer 1: client-side check
  const clientErrors = validateBookClient();
  if (Object.keys(clientErrors).length) {
    Object.entries(clientErrors).forEach(([id, msg]) => {
      const errEl = document.getElementById(`${id}-err`);
      const inpEl = document.getElementById(id);
      if (errEl) errEl.textContent = msg;
      if (inpEl) inpEl.classList.add("error");
    });
    return;
  }

  const body = {
    title:           document.getElementById("b-title").value.trim(),
    author:          document.getElementById("b-author").value.trim(),
    category_id:     parseInt(document.getElementById("b-category").value, 10),
    price:           document.getElementById("b-price").value,
    stock_qty:       document.getElementById("b-stock").value,
    rank_order:      document.getElementById("b-rank").value.trim() || null,
    cover_image_url: document.getElementById("b-cover").value.trim() || null,
    description:     document.getElementById("b-desc").value.trim()  || null,
  };

  const isEdit = currentBookId !== null;
  const url    = isEdit ? `/admin/books/${currentBookId}` : "/admin/books";
  const method = isEdit ? "PUT" : "POST";

  try {
    const res  = await fetch(url, {
      method,
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(isEdit ? "Book updated successfully." : "Book added successfully.", "success");
      cancelBookForm();
      await loadBooks();
    } else {
      if (data.errors) showFormErrors(data.errors, []);
      else showBanner(data.message || "Failed to save book.", "error");
    }
  } catch (err) {
    showBanner("Network error — please try again.", "error");
  }
}

// ---- Book delete ----
async function deleteBook(bookId, title) {
  if (!confirm(`Delete "${title}"?\nThis cannot be undone. The action will be blocked if this book has been ordered.`)) return;

  try {
    const res  = await fetch(`/admin/books/${bookId}`, { method: "DELETE" });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(data.message, "success");
      await loadBooks();
    } else {
      showBanner(data.message || "Could not delete book.", "error");
    }
  } catch (err) {
    showBanner("Network error — please try again.", "error");
  }
}

// ---------------------------------------------------------------------------
// ART SUPPLIES — load and render table
// ---------------------------------------------------------------------------
async function loadArtSupplies() {
  try {
    const res  = await fetch("/admin/art-supplies");
    const data = await res.json();
    if (data.response === "OK") {
      renderArtTable(data.data);
    } else {
      document.getElementById("artTableBody").innerHTML =
        `<tr><td colspan="8" class="table-empty">Failed to load art supplies.</td></tr>`;
    }
  } catch (err) {
    console.error("loadArtSupplies error:", err);
  }
}

function renderArtTable(arts) {
  const tbody = document.getElementById("artTableBody");
  if (!arts.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty">No art supplies yet — add one above.</td></tr>`;
    return;
  }
  tbody.innerHTML = arts.map((a) => `
    <tr>
      <td>${a.art_id}</td>
      <td><strong>${esc(a.name)}</strong></td>
      <td>${esc(a.brand)}</td>
      <td>${esc(a.category_name || "—")}</td>
      <td>₹${a.price.toFixed(2)}</td>
      <td>${a.stock_qty}</td>
      <td>${a.rank_order ?? "—"}</td>
      <td>
        <div class="table-actions">
          <button class="btn-edit" onclick="editArt(${a.art_id})" aria-label="Edit ${esc(a.name)}">${ICON_PENCIL} Edit</button>
          <button class="btn-danger" data-name="${esc(a.name)}" onclick="deleteArt(${a.art_id}, this.dataset.name)" aria-label="Delete ${esc(a.name)}">${ICON_TRASH} Delete</button>
        </div>
      </td>
    </tr>
  `).join("");
}

// ---- Art form open/close ----
function openArtForm(art) {
  currentArtId = art ? art.art_id : null;
  document.getElementById("artFormTitle").textContent = art ? "Edit Art Supply" : "Add New Art Supply";
  document.getElementById("artEditId").value = art ? art.art_id : "";

  document.getElementById("a-name").value  = art ? art.name        : "";
  document.getElementById("a-brand").value = art ? art.brand       : "";
  document.getElementById("a-price").value = art ? art.price       : "";
  document.getElementById("a-stock").value = art ? art.stock_qty   : "";
  document.getElementById("a-rank").value  = art ? (art.rank_order ?? "") : "";
  document.getElementById("a-image").value = art ? (art.image_url  ?? "") : "";
  document.getElementById("a-desc").value  = art ? (art.description ?? "") : "";

  if (art) {
    document.getElementById("a-category").value = art.category_id;
  } else {
    document.getElementById("a-category").value = "";
  }

  clearFormErrors(["a-name","a-brand","a-category","a-price","a-stock","a-rank","a-image","a-desc"]);
  document.getElementById("artFormCard").hidden = false;
  document.getElementById("a-name").focus();
  document.getElementById("artFormCard").scrollIntoView({ behavior: "smooth" });
}

function cancelArtForm() {
  currentArtId = null;
  document.getElementById("artFormCard").hidden = true;
}

function editArt(artId) {
  fetch("/admin/art-supplies")
    .then((r) => r.json())
    .then((data) => {
      const art = data.data.find((a) => a.art_id === artId);
      if (art) openArtForm(art);
    });
}

// ---- Art supply form submit ----
async function submitArtForm() {
  const clientErrors = validateArtClient();
  if (Object.keys(clientErrors).length) {
    Object.entries(clientErrors).forEach(([id, msg]) => {
      const errEl = document.getElementById(`${id}-err`);
      const inpEl = document.getElementById(id);
      if (errEl) errEl.textContent = msg;
      if (inpEl) inpEl.classList.add("error");
    });
    return;
  }

  const body = {
    name:        document.getElementById("a-name").value.trim(),
    brand:       document.getElementById("a-brand").value.trim(),
    category_id: parseInt(document.getElementById("a-category").value, 10),
    price:       document.getElementById("a-price").value,
    stock_qty:   document.getElementById("a-stock").value,
    rank_order:  document.getElementById("a-rank").value.trim()  || null,
    image_url:   document.getElementById("a-image").value.trim() || null,
    description: document.getElementById("a-desc").value.trim()  || null,
  };

  const isEdit = currentArtId !== null;
  const url    = isEdit ? `/admin/art-supplies/${currentArtId}` : "/admin/art-supplies";
  const method = isEdit ? "PUT" : "POST";

  try {
    const res  = await fetch(url, {
      method,
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(isEdit ? "Art supply updated." : "Art supply added.", "success");
      cancelArtForm();
      await loadArtSupplies();
    } else {
      if (data.errors) {
        // Remap server field names to DOM IDs for art form
        const artIdMap = { name: "a-name", brand: "a-brand", category_id: "a-category",
                           price: "a-price", stock_qty: "a-stock", rank_order: "a-rank",
                           image_url: "a-image", description: "a-desc" };
        Object.entries(data.errors).forEach(([field, msg]) => {
          const domId = artIdMap[field] || field;
          const errEl = document.getElementById(`${domId}-err`);
          const inpEl = document.getElementById(domId);
          if (errEl) errEl.textContent = msg;
          if (inpEl) inpEl.classList.add("error");
        });
      } else {
        showBanner(data.message || "Failed to save art supply.", "error");
      }
    }
  } catch (err) {
    showBanner("Network error — please try again.", "error");
  }
}

// ---- Art supply delete ----
async function deleteArt(artId, name) {
  if (!confirm(`Delete "${name}"?\nBlocked if this art supply has been ordered.`)) return;

  try {
    const res  = await fetch(`/admin/art-supplies/${artId}`, { method: "DELETE" });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(data.message, "success");
      await loadArtSupplies();
    } else {
      showBanner(data.message || "Could not delete art supply.", "error");
    }
  } catch (err) {
    showBanner("Network error — please try again.", "error");
  }
}

// ---------------------------------------------------------------------------
// CATEGORIES — add book / art category
// ---------------------------------------------------------------------------
async function addBookCategory() {
  const nameEl  = document.getElementById("bookCatName");
  const errEl   = document.getElementById("bookCatName-err");
  const name    = nameEl.value.trim();
  errEl.textContent = "";
  nameEl.classList.remove("error");

  if (!name) { errEl.textContent = "Category name is required."; nameEl.classList.add("error"); return; }
  if (name.length > 100) { errEl.textContent = "Max 100 characters."; nameEl.classList.add("error"); return; }

  try {
    const res  = await fetch("/admin/book-categories", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({ name }),
    });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(`Book category "${name}" added.`, "success");
      nameEl.value = "";
      // Append to dropdown immediately so admin can use it without a page refresh
      const opt = document.createElement("option");
      opt.value = data.data.category_id;
      opt.textContent = data.data.name;
      document.getElementById("b-category").appendChild(opt);
    } else {
      errEl.textContent = (data.errors && data.errors.name) || data.message || "Failed.";
      nameEl.classList.add("error");
    }
  } catch (err) {
    showBanner("Network error.", "error");
  }
}

async function addArtCategory() {
  const nameEl = document.getElementById("artCatName");
  const errEl  = document.getElementById("artCatName-err");
  const name   = nameEl.value.trim();
  errEl.textContent = "";
  nameEl.classList.remove("error");

  if (!name) { errEl.textContent = "Category name is required."; nameEl.classList.add("error"); return; }
  if (name.length > 100) { errEl.textContent = "Max 100 characters."; nameEl.classList.add("error"); return; }

  try {
    const res  = await fetch("/admin/art-categories", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({ name }),
    });
    const data = await res.json();

    if (data.response === "OK") {
      showBanner(`Art category "${name}" added.`, "success");
      nameEl.value = "";
      const opt = document.createElement("option");
      opt.value = data.data.category_id;
      opt.textContent = data.data.name;
      document.getElementById("a-category").appendChild(opt);
    } else {
      errEl.textContent = (data.errors && data.errors.name) || data.message || "Failed.";
      nameEl.classList.add("error");
    }
  } catch (err) {
    showBanner("Network error.", "error");
  }
}

// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------
async function doLogout() {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/";
}

// ---------------------------------------------------------------------------
// XSS-safe escaping for table cell innerHTML
// ---------------------------------------------------------------------------
// Outline icons (brown, same stroke style as the storefront icons)
const ICON_PENCIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>';
const ICON_TRASH  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 .8 12.1A2 2 0 0 0 8.8 21h6.4a2 2 0 0 0 1.9-1.9L18 7"/></svg>';

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
