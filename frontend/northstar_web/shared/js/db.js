/*
 * NorthstarDB — a thin fetch() client for backend/northstar_web_api/ (FastAPI +
 * Postgres). Replaces the earlier localStorage-backed version; every
 * function keeps the same name/shape it had before (all, find, query,
 * insert, update) so page logic barely changed — they're just async now.
 */
const NorthstarDB = (() => {
  const API_BASE = "/api";

  // ------------------------------------------
  // REQUEST — shared fetch wrapper: cookies for the session, JSON in/out
  // ------------------------------------------
  async function request(path, options = {}) {
    const res = await fetch(API_BASE + path, {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (res.status === 401) {
      window.location.href = "login.html";
      throw new Error("Not logged in.");
    }
    if (res.status === 404) return null;
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  // ------------------------------------------
  // CRUD HELPERS — used by every page instead of touching fetch() directly
  // ------------------------------------------
  async function all(name) {
    return (await request(`/${name}`)) || [];
  }

  async function find(name, id) {
    return request(`/${name}/${id}`);
  }

  async function query(name, predicate) {
    const rows = await all(name);
    return rows.filter(predicate);
  }

  async function insert(name, row) {
    return request(`/${name}`, { method: "POST", body: JSON.stringify(row) });
  }

  async function update(name, id, patch) {
    return request(`/${name}/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  }

  return { all, find, query, insert, update };
})();
