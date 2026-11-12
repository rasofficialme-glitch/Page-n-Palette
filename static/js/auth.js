/**
 * auth.js — Client-side logic for the Sign In / Sign Up page.
 * Uses plain fetch + async/await (no Vue, no framework).
 * Pattern matches the project's Sync-Async.py sample style.
 */

"use strict";

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function switchTab(tab) {
  const tabs   = { signin: "panel-signin", signup: "panel-signup" };
  const tabBtns = { signin: "tab-signin",   signup: "tab-signup"   };

  // Show the selected panel, hide the other
  Object.keys(tabs).forEach((key) => {
    const panel = document.getElementById(tabs[key]);
    const btn   = document.getElementById(tabBtns[key]);
    if (key === tab) {
      panel.classList.remove("hidden");
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
    } else {
      panel.classList.add("hidden");
      btn.classList.remove("active");
      btn.setAttribute("aria-selected", "false");
    }
  });

  const verifyPanel = document.getElementById("panel-verify");
  if (verifyPanel) verifyPanel.classList.add("hidden");

  clearAllErrors();
  hideBanner();
}

// ---------------------------------------------------------------------------
// Banner helpers
// ---------------------------------------------------------------------------
function showBanner(message, type = "error") {
  const el = document.getElementById("globalBanner");
  el.textContent = message;
  el.className   = "global-banner " + type;
  el.hidden      = false;
  // Auto-dismiss success banners after 4 s
  if (type === "success") {
    setTimeout(() => { el.hidden = true; }, 4000);
  }
}

// Parse a fetch response as JSON; flag failures so we can tell "server error" from "no connection"
async function readJSON(res) {
  try { return await res.json(); }
  catch (e) { const err = new Error("bad-response"); err.isServer = true; throw err; }
}

function netErrorMessage(err) {
  return err && err.isServer
    ? "Something went wrong on the server. Please try again."
    : "Cannot reach the server — make sure the app is running.";
}

function hideBanner() {
  const el = document.getElementById("globalBanner");
  if (el) el.hidden = true;
}

// ---------------------------------------------------------------------------
// Field-level error helpers
// ---------------------------------------------------------------------------
function showFieldErrors(errors, prefix) {
  Object.entries(errors).forEach(([field, msg]) => {
    const errEl = document.getElementById(`${prefix}-${field}-err`);
    const inpEl = document.getElementById(`${prefix}-${field}`);
    if (errEl) errEl.textContent = msg;
    if (inpEl) inpEl.classList.add("error");
  });
}

function clearErrors(prefix, fields) {
  fields.forEach((f) => {
    const errEl = document.getElementById(`${prefix}-${f}-err`);
    const inpEl = document.getElementById(`${prefix}-${f}`);
    if (errEl) errEl.textContent = "";
    if (inpEl) inpEl.classList.remove("error");
  });
}

function clearAllErrors() {
  document.querySelectorAll(".field-error").forEach((el) => { el.textContent = ""; });
  document.querySelectorAll(".field-input").forEach((el) => { el.classList.remove("error"); });
}

// ---------------------------------------------------------------------------
// Client-side (Layer 1) validation helpers
// ---------------------------------------------------------------------------
const EMAIL_RE = /^[A-Za-z0-9_%+\-]+(?:\.[A-Za-z0-9_%+\-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$/;
const PHONE_RE = /^(\+91)?[6-9]\d{9}$/;
const URL_RE   = /^https?:\/\/\S+$/i;

function validateSignupClient() {
  const errors = {};
  const name    = document.getElementById("su-name").value.trim();
  const email   = document.getElementById("su-email").value.trim();
  const pwd     = document.getElementById("su-password").value;
  const confirm = document.getElementById("su-confirm").value;
  const phone   = document.getElementById("su-phone").value.trim();
  const address = document.getElementById("su-address").value.trim();

  if (!name)               errors.name = "Full name is required.";
  else if (name.length > 200) errors.name = "Name must be 200 characters or fewer.";

  if (!email)              errors.email = "Email address is required.";
  else if (!EMAIL_RE.test(email)) errors.email = "Please enter a valid email address.";

  if (!pwd)                errors.password = "Password is required.";
  else if (pwd.length < 8) errors.password = "Password must be at least 8 characters.";
  else if (!/[a-zA-Z]/.test(pwd)) errors.password = "Password must contain at least one letter.";
  else if (!/\d/.test(pwd))       errors.password = "Password must contain at least one digit.";

  if (!errors.password) {
    if (!confirm)          errors.confirm_password = "Please confirm your password.";
    else if (pwd !== confirm) errors.confirm_password = "Passwords do not match.";
  }

  if (phone && !PHONE_RE.test(phone)) {
    errors.phone = "Enter a valid 10-digit Indian mobile number.";
  }
  if (address.length > 500) errors.address = "Address must be 500 characters or fewer.";

  return errors;
}

function validateLoginClient() {
  const errors = {};
  const email = document.getElementById("si-email").value.trim();
  const pwd   = document.getElementById("si-password").value;
  if (!email) errors.email    = "Email address is required.";
  if (!pwd)   errors.password = "Password is required.";
  return errors;
}

// ---------------------------------------------------------------------------
// SIGN IN — form submit handler
// ---------------------------------------------------------------------------
document.getElementById("signinForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAllErrors();
  hideBanner();

  // Layer 1 client check
  const clientErrors = validateLoginClient();
  if (Object.keys(clientErrors).length) {
    showFieldErrors(clientErrors, "si");
    return;
  }

  const btn = document.getElementById("signinBtn");
  btn.disabled = true;
  btn.textContent = "Signing in…";

  try {
    // POST JSON to /login — exactly the pattern from Sync-Async.py sample
    const res  = await fetch("/login", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({
        email:    document.getElementById("si-email").value.trim().toLowerCase(),
        password: document.getElementById("si-password").value,
      }),
    });
    const data = await readJSON(res);

    if (data.response === "OK") {
      // Redirect to the URL the server decided (admin → /admin, customer → /home)
      window.location.href = data.redirect;
    } else if (data.verification_required) {
      // Correct password but email not verified yet → ask for the OTP
      showVerifyPanel(data.email, data.message, "error");
    } else {
      // Show field-level errors from the server (Layer 2 / Layer 3)
      if (data.errors) showFieldErrors(data.errors, "si");
      else showBanner(data.message || "Sign in failed. Please try again.", "error");
    }
  } catch (err) {
    showBanner(netErrorMessage(err), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign In";
  }
});

// ---------------------------------------------------------------------------
// SIGN UP — form submit handler
// ---------------------------------------------------------------------------
document.getElementById("signupForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAllErrors();
  hideBanner();

  // Layer 1 client check
  const clientErrors = validateSignupClient();
  if (Object.keys(clientErrors).length) {
    showFieldErrors(clientErrors, "su");
    return;
  }

  const btn = document.getElementById("signupBtn");
  btn.disabled = true;
  btn.textContent = "Creating account…";

  try {
    const res  = await fetch("/signup", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({
        name:             document.getElementById("su-name").value.trim(),
        email:            document.getElementById("su-email").value.trim().toLowerCase(),
        password:         document.getElementById("su-password").value,
        confirm_password: document.getElementById("su-confirm").value,
        phone:            document.getElementById("su-phone").value.trim() || null,
        address:          document.getElementById("su-address").value.trim() || null,
      }),
    });
    const data = await readJSON(res);

    if (data.response === "OK") {
      // Account created → ask the user to verify their email with the OTP
      document.getElementById("signupForm").reset();
      showVerifyPanel(data.email, data.message, "success");
    } else {
      if (data.errors) showFieldErrors(data.errors, "su");
      else showBanner(data.message || "Sign up failed. Please try again.", "error");
    }
  } catch (err) {
    showBanner(netErrorMessage(err), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Account";
  }
});

// ---------------------------------------------------------------------------
// EMAIL VERIFICATION (OTP)
// ---------------------------------------------------------------------------
let pendingVerifyEmail = "";
let resendTimer = null;

function showVerifyPanel(email, message, bannerType) {
  pendingVerifyEmail = email;
  ["panel-signin", "panel-signup"].forEach((id) =>
    document.getElementById(id).classList.add("hidden"));
  ["tab-signin", "tab-signup"].forEach((id) => {
    const b = document.getElementById(id);
    b.classList.remove("active");
    b.setAttribute("aria-selected", "false");
  });
  document.getElementById("panel-verify").classList.remove("hidden");
  document.getElementById("vf-email-label").textContent = email;
  document.getElementById("vf-otp").value = "";
  clearErrors("vf", ["otp"]);
  if (message) showBanner(message, bannerType || "success");
  startResendCooldown(60);
  document.getElementById("vf-otp").focus();
}

function startResendCooldown(seconds) {
  const btn = document.getElementById("resendBtn");
  clearInterval(resendTimer);
  let left = seconds;
  btn.disabled = true;
  btn.textContent = `Resend code (${left}s)`;
  resendTimer = setInterval(() => {
    left -= 1;
    if (left <= 0) {
      clearInterval(resendTimer);
      btn.disabled = false;
      btn.textContent = "Resend code";
    } else {
      btn.textContent = `Resend code (${left}s)`;
    }
  }, 1000);
}

document.getElementById("verifyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearErrors("vf", ["otp"]);
  hideBanner();

  const otp = document.getElementById("vf-otp").value.trim();
  if (!/^\d{6}$/.test(otp)) {
    showFieldErrors({ otp: "Enter the 6-digit code from your email." }, "vf");
    return;
  }

  const btn = document.getElementById("verifyBtn");
  btn.disabled = true;
  btn.textContent = "Verifying…";

  try {
    const res  = await fetch("/verify-email", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({ email: pendingVerifyEmail, otp }),
    });
    const data = await readJSON(res);

    if (data.response === "OK") {
      switchTab("signin");
      document.getElementById("si-email").value = pendingVerifyEmail;
      showBanner(data.message || "Email verified! You can now sign in.", "success");
    } else if (data.errors) {
      showFieldErrors(data.errors, "vf");
    } else {
      showBanner(data.message || "Verification failed. Please try again.", "error");
    }
  } catch (err) {
    showBanner(netErrorMessage(err), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Verify Email";
  }
});

document.getElementById("resendBtn").addEventListener("click", async () => {
  hideBanner();
  try {
    const res  = await fetch("/resend-verification", {
      method:  "POST",
      headers: { "Content-Type": "application/JSON" },
      body:    JSON.stringify({ email: pendingVerifyEmail }),
    });
    const data = await readJSON(res);
    showBanner(data.message || "Please try again.", data.response === "OK" ? "success" : "error");
    if (data.response === "OK") startResendCooldown(data.cooldown || 60);
  } catch (err) {
    showBanner(netErrorMessage(err), "error");
  }
});

// ---------------------------------------------------------------------------
// Password eye-toggle
// ---------------------------------------------------------------------------
function toggleEye(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "🙈";
  } else {
    input.type = "password";
    btn.textContent = "👁";
  }
}
