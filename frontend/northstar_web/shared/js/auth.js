/*
 * NorthstarAuth — real, server-side authentication against
 * backend/northstar_web_api/. Login sets an HttpOnly session cookie the
 * browser handles automatically; there is no client-readable session
 * token and no password ever touches localStorage/sessionStorage.
 */
const NorthstarAuth = (() => {
  const API_BASE = "http://localhost:8020/api/auth";

  // ------------------------------------------
  // LOGIN — POST credentials, server sets the session cookie on success
  // ------------------------------------------
  async function login(portal, email, password) {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portal, email, password }),
    });
    if (!res.ok) return null;
    return res.json();
  }

  async function logout() {
    await fetch(`${API_BASE}/logout`, { method: "POST", credentials: "include" });
    window.location.href = "login.html";
  }

  // ------------------------------------------
  // CURRENT USER — ask the server who the session cookie belongs to
  // ------------------------------------------
  async function currentUser() {
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    if (!res.ok) return null;
    return res.json();
  }

  // ------------------------------------------
  // REQUIRE AUTH — call at the top of every protected page
  // ------------------------------------------
  async function requireAuth(portal) {
    const user = await currentUser();
    if (!user || user.portal.toLowerCase() !== portal) {
      window.location.href = "login.html";
      return null;
    }
    return user;
  }

  return { login, logout, currentUser, requireAuth };
})();
