/* auth-bridge.js — links the storefront to the Flask login session.
   Flask prepends `window.__ME__` (who is signed in) when it serves common.js,
   so this runs synchronously, before the page header is drawn (no flicker). */
(function () {
  var me = window.__ME__ || { logged_in: false };
  var KEYS = ["pp_cart", "pp_wishlist", "pp_profile", "pp_user"];
  try {
    var prev = localStorage.getItem("pp_user") || "";
    if (me.logged_in) {
      // A different person used this browser before -> don't leak their cart/wishlist
      if (prev && prev !== me.email) {
        localStorage.removeItem("pp_cart");
        localStorage.removeItem("pp_wishlist");
      }
      // First visit for this account: copy identity into the storefront profile
      if (prev !== me.email) {
        localStorage.setItem("pp_profile", JSON.stringify({
          name: me.name, email: me.email, phone: me.phone || "", address: me.address || ""
        }));
      }
      localStorage.setItem("pp_user", me.email);
    } else if (prev) {
      // Someone signed out earlier: browse as a clean guest
      KEYS.forEach(function (k) { localStorage.removeItem(k); });
    }
  } catch (e) { /* storage blocked: storefront still works */ }

  // Sign in / Sign out (and Back office for admins) next to the avatar
  document.addEventListener("DOMContentLoaded", function () {
    var avatar = document.querySelector(".avatar");
    if (!avatar) return;
    function pill(tag, text) {
      var el = document.createElement(tag);
      el.textContent = text;
      el.style.cssText = "font:600 .85rem/1 inherit;padding:.55rem .9rem;border-radius:999px;" +
        "border:1.5px solid var(--card-border,#EED7BC);background:var(--surface,#fff);" +
        "color:var(--maroon,#7A3B2E);text-decoration:none;cursor:pointer;white-space:nowrap;";
      return el;
    }
    var anchor = avatar;
    // Pages with the customer nav bar already have Logout / Sign in there
    var hasNav = !!document.getElementById("customerNav");
    if (me.logged_in) {
      if (me.role === "admin") {
        var bo = pill("a", "Back office"); bo.href = "/admin";
        anchor.insertAdjacentElement("afterend", bo); anchor = bo;
      }
      if (hasNav) return;
      var out = pill("button", "Sign out"); out.type = "button";
      out.addEventListener("click", function () {
        fetch("/logout", { method: "POST" }).finally(function () { window.location.href = "/"; });
      });
      anchor.insertAdjacentElement("afterend", out);
    } else if (!hasNav) {
      var inn = pill("a", "Sign in"); inn.href = "/";
      anchor.insertAdjacentElement("afterend", inn);
    }
  });
})();
