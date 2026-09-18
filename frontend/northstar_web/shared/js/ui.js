/*
 * Small reusable UI helpers shared by every page: toasts, formatting, status
 * pills, and one generic confirm/note modal (used for Approve/Reject/Hold
 * actions everywhere instead of a separate modal per page).
 */

// ------------------------------------------
// TOASTS — a small stack in the corner, auto-dismissing
// ------------------------------------------
function toast(message, kind = "ok") {
  let stack = document.getElementById("toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.id = "toast-stack";
    document.body.appendChild(stack);
  }
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

// ------------------------------------------
// FORMATTING — currency, date, datetime
// ------------------------------------------
function formatCurrency(amount) {
  return "$" + Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

// ------------------------------------------
// STATUS PILLS — one lookup table, reused across every list/detail page
// ------------------------------------------
const STATUS_PILL_KIND = {
  PENDING_REVIEW: "warn", APPROVED: "ok", REJECTED: "bad",
  SCHEDULED: "info", ENROUTE: "info", AT_DOCK: "warn", DELIVERED: "ok",
  PENDING_APPROVAL: "warn", ON_HOLD: "bad",
  Satisfactory: "ok", Conditional: "warn",
};
function pillHtml(statusText, labelOverride) {
  const kind = STATUS_PILL_KIND[statusText] || "muted";
  const label = labelOverride || statusText.replace(/_/g, " ");
  return `<span class="pill pill-${kind}">${label}</span>`;
}

// ------------------------------------------
// FILTER PILLS — a small "All / Status / Status..." row that filters a list
// client-side. `options` is [{value, label}]; onChange(value) re-renders.
// ------------------------------------------
function renderFilterPills(containerId, options, activeValue, onChange) {
  const el = document.getElementById(containerId);
  el.innerHTML = options.map((o) =>
    `<button type="button" class="filter-pill ${o.value === activeValue ? "active" : ""}" data-value="${o.value}">${o.label}</button>`
  ).join("");
  el.querySelectorAll(".filter-pill").forEach((btn) => {
    btn.addEventListener("click", () => onChange(btn.dataset.value));
  });
}

// ------------------------------------------
// AUTO-CAPTURED DOCK EVENTS — simulates a live telematics/geofence feed
// logging a shipment's real arrival/departure the moment it's marked
// delivered. Deliberately NOT a form any employee (or carrier) can type
// into — that would let the same person checking an invoice also write
// the "ground truth" it's checked against.
// ------------------------------------------
function toNaiveIso(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
async function autoLogDockEvents(shipment) {
  const arrival = new Date(shipment.deliveryAppt);
  arrival.setMinutes(arrival.getMinutes() + Math.round((Math.random() - 0.5) * 40)); // +/-20 min of the appointment
  const dwellHours = Math.random() < 0.7
    ? 0.5 + Math.random() * 1.5   // usually near/under the free-time allowance
    : 2.5 + Math.random() * 2.5;  // sometimes a real detention case
  const departure = new Date(arrival.getTime() + dwellHours * 3600 * 1000);
  await NorthstarDB.insert("dockEvents", { shipmentId: shipment.id, type: "ARRIVAL", timestamp: toNaiveIso(arrival) });
  await NorthstarDB.insert("dockEvents", { shipmentId: shipment.id, type: "DEPARTURE", timestamp: toNaiveIso(departure) });
}

// ------------------------------------------
// EMPLOYEE SIDEBAR BADGES — pending-count bubbles shown on every employee page
// ------------------------------------------
async function renderEmployeeBadges() {
  const pendingBookings = (await NorthstarDB.query("shipmentRequests", (r) => r.status === "PENDING_REVIEW")).length;
  const pendingInvoices = (await NorthstarDB.query("invoices", (i) => i.status === "PENDING_APPROVAL")).length;
  const bookingBadge = document.getElementById("badge-bookings");
  const invoiceBadge = document.getElementById("badge-invoices");
  if (bookingBadge) { bookingBadge.textContent = pendingBookings; bookingBadge.style.display = pendingBookings ? "inline-block" : "none"; }
  if (invoiceBadge) { invoiceBadge.textContent = pendingInvoices; invoiceBadge.style.display = pendingInvoices ? "inline-block" : "none"; }
}

// ------------------------------------------
// CARRIER SIDEBAR BADGE — disputed-invoice count shown on every carrier page
// ------------------------------------------
async function renderCarrierBadges(carrierId) {
  const disputed = (await NorthstarDB.query("invoices", (i) => i.carrierId === carrierId && i.status === "ON_HOLD")).length;
  const badge = document.getElementById("badge-disputes");
  if (badge) { badge.textContent = disputed; badge.style.display = disputed ? "inline-block" : "none"; }
}

// ------------------------------------------
// ACTION MODAL — one generic confirm-with-optional-note dialog, built on
// demand so no page has to hand-write modal markup for every action.
// ------------------------------------------
const ActionModal = (() => {
  let onConfirmCallback = null;

  function ensureDom() {
    if (document.getElementById("action-modal-backdrop")) return;
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <div class="modal-backdrop" id="action-modal-backdrop" hidden>
        <div class="modal">
          <h3 id="action-modal-title"></h3>
          <p class="desc" id="action-modal-desc"></p>
          <div class="field" id="action-modal-note-field">
            <label id="action-modal-note-label"></label>
            <textarea id="action-modal-note" placeholder="Explain what needs to change..."></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" id="action-modal-cancel">Cancel</button>
            <button class="btn" id="action-modal-confirm"></button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(wrap.firstElementChild);
    document.getElementById("action-modal-cancel").addEventListener("click", close);
  }

  function open({ title, desc, noteRequired = false, noteLabel = "Note", confirmLabel = "Confirm", confirmClass = "btn-primary", onConfirm }) {
    ensureDom();
    document.getElementById("action-modal-title").textContent = title;
    document.getElementById("action-modal-desc").textContent = desc || "";
    const noteField = document.getElementById("action-modal-note-field");
    const noteInput = document.getElementById("action-modal-note");
    noteInput.value = "";
    noteField.style.display = noteRequired || noteLabel ? "block" : "none";
    document.getElementById("action-modal-note-label").textContent = noteLabel + (noteRequired ? " (required)" : " (optional)");

    const confirmBtn = document.getElementById("action-modal-confirm");
    confirmBtn.textContent = confirmLabel;
    confirmBtn.className = "btn " + confirmClass;
    onConfirmCallback = onConfirm;
    confirmBtn.onclick = () => {
      const note = noteInput.value.trim();
      if (noteRequired && !note) {
        noteInput.focus();
        toast("A note is required for this action.", "bad");
        return;
      }
      close();
      if (onConfirmCallback) onConfirmCallback(note);
    };
    document.getElementById("action-modal-backdrop").hidden = false;
  }

  function close() {
    const backdrop = document.getElementById("action-modal-backdrop");
    if (backdrop) backdrop.hidden = true;
  }

  return { open, close };
})();
