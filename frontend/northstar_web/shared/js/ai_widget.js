/* ------------------------------------------
   AI WIDGET — a floating "ask the AI copilot" bubble, additive to the
   employee portal. Fully self-contained (injects its own <style>, reuses
   this page's own existing CSS variables for visual consistency) so
   including it is exactly one new <script> tag, nothing else. The AI's own
   routes are mounted under /api/ai/... on this same app (see
   backend/northstar_web_api/main.py, which also serves this very file) —
   one process, one port, and one login: there is no separate AI session
   or login of any kind. The AI reads the same portal session cookie every
   other page already relies on (see backend/copilot_api/auth.py).
   ------------------------------------------ */
const AI_API_BASE = "/api/ai";

async function aiApiRequest(method, path, body) {
  const res = await fetch(AI_API_BASE + path, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

function aiEscapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
  ));
}

/* Same fixed-shape markdown rendering the AI console itself uses
   (### headings, **bold**, pipe tables, "- " bullets), so a reply looks
   identical here and in the full console. */
function aiRenderMarkdown(raw) {
  const lines = aiEscapeHtml(raw).split("\n");
  const parts = [];
  let listBuffer = [];
  function flushList() {
    if (listBuffer.length) {
      parts.push(`<ul>${listBuffer.map((item) => `<li>${item}</li>`).join("")}</ul>`);
      listBuffer = [];
    }
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*\|.*\|\s*$/.test(line) && lines[i + 1] && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      flushList();
      const headerCells = line.split("|").map((c) => c.trim()).filter(Boolean);
      const rows = [];
      let j = i + 2;
      while (j < lines.length && /^\s*\|.*\|\s*$/.test(lines[j])) {
        rows.push(lines[j].split("|").map((c) => c.trim()).filter(Boolean));
        j++;
      }
      parts.push(`<table class="ai-widget-table"><thead><tr>${headerCells.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      i = j - 1;
      continue;
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading && heading[1].length <= 100) {
      flushList();
      parts.push(`<h4>${heading[1].replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</h4>`);
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      listBuffer.push(bullet[1].replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"));
      continue;
    }
    flushList();
    if (line.trim() !== "") parts.push(`<p>${line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</p>`);
  }
  flushList();
  return parts.join("");
}

/* ------------------------------------------
   INJECT STYLES — widget-specific layout rules only; colors reference
   this page's own existing CSS custom properties (--accent, --ink-900,
   --surface, and friends, from shared/css/tokens.css) so the widget
   matches whichever portal it's on.
   ------------------------------------------ */
function injectAiWidgetStyles() {
  const style = document.createElement("style");
  style.textContent = `
    .ai-widget-btn { position: fixed; bottom: 24px; right: 24px; z-index: 200; width: 52px; height: 52px; border-radius: 50%; border: none; background: var(--accent); color: #fff; font-size: 22px; box-shadow: var(--shadow-md); cursor: pointer; display: flex; align-items: center; justify-content: center; }
    .ai-widget-btn:hover { transform: scale(1.06); }
    .ai-widget-panel { position: fixed; bottom: 88px; right: 24px; z-index: 200; width: 360px; height: 480px; max-height: calc(100vh - 120px); background: var(--surface); border: 1px solid var(--ink-200); border-radius: var(--radius-md); box-shadow: var(--shadow-md); display: flex; flex-direction: column; overflow: hidden; font-family: inherit; }
    .ai-widget-panel[hidden] { display: none; }
    .ai-widget-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--ink-900); color: #fff; font-weight: 700; font-size: 13px; }
    .ai-widget-head a { color: #fff; opacity: 0.8; font-weight: 500; font-size: 11.5px; text-decoration: none; }
    .ai-widget-head a:hover { opacity: 1; text-decoration: underline; }
    .ai-widget-close { background: none; border: none; color: #fff; font-size: 18px; cursor: pointer; line-height: 1; }
    .ai-widget-messages { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
    .ai-widget-msg { max-width: 88%; padding: 10px 12px; border-radius: 10px; font-size: 12.5px; white-space: pre-wrap; }
    .ai-widget-msg.user { align-self: flex-end; background: var(--accent); color: #fff; }
    .ai-widget-msg.assistant { align-self: flex-start; background: var(--ink-100); color: var(--ink-900); }
    .ai-widget-msg.pending { align-self: flex-start; background: var(--ink-100); color: var(--ink-500); font-style: italic; }
    .ai-widget-msg.assistant h4 { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.03em; margin: 10px 0 4px; }
    .ai-widget-msg.assistant h4:first-child { margin-top: 0; }
    .ai-widget-msg.assistant p { margin: 4px 0; }
    .ai-widget-msg.assistant ul { margin: 4px 0; padding-left: 16px; }
    .ai-widget-table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 11.5px; }
    .ai-widget-table th, .ai-widget-table td { padding: 4px 8px; border: 1px solid var(--ink-200); text-align: left; }
    .ai-widget-table th { background: var(--ink-100); }
    .ai-widget-input-row { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--ink-200); }
    .ai-widget-input-row input { flex: 1; padding: 8px 12px; border: 1px solid var(--ink-300); border-radius: 999px; font-size: 12.5px; font-family: inherit; }
    .ai-widget-login { padding: 20px; display: flex; flex-direction: column; gap: 10px; flex: 1; }
    .ai-widget-login .ai-widget-error { color: #b91c1c; font-size: 12px; }
  `;
  document.head.appendChild(style);
}

/* ------------------------------------------
   SHIPMENT -> INVOICE LOOKUP — the AI's own data (flags, audit entries) is
   keyed by shipment_id, but invoice-detail.html links by the invoices
   table's own id. Shared by every native AI page that links back to an
   invoice (ai-approvals.html).
   ------------------------------------------ */
async function aiShipmentToInvoiceId() {
  const invoices = await NorthstarDB.all("invoices");
  return Object.fromEntries(invoices.map((i) => [i.shipmentId, i.id]));
}

/* ------------------------------------------
   REQUIRE AI SESSION — shared by the widget and every native AI page
   (ai-approvals.html, ai-audit.html). There's no separate AI login to
   prompt for: by the time any employee page reaches this point,
   NorthstarAuth.requireAuth("employee") has already confirmed the one,
   single portal login, and the AI's /me reads that exact same session
   cookie server-side. A failure here means something genuinely went
   wrong (the server is unreachable, or this role has no AI access at
   all) — shown as a plain message, not a second login box.
   ------------------------------------------ */
async function requireAiSession(containerEl, onReady) {
  try {
    await aiApiRequest("GET", "/me");
    onReady();
  } catch (e) {
    containerEl.innerHTML = `<div class="ai-widget-login"><p class="ai-widget-error">${aiEscapeHtml(e.message)}</p></div>`;
  }
}

/* ------------------------------------------
   RENDER WIDGET — the floating button + panel, appended to every employee
   page that includes this script. Checks for an existing AI-console
   session first; shows an inline login prompt (reusing the same portal
   credentials) if none exists yet, before switching to chat.
   ------------------------------------------ */
function renderAiWidget() {
  injectAiWidgetStyles();

  const wrap = document.createElement("div");
  wrap.innerHTML = `
    <button type="button" class="ai-widget-btn" id="ai-widget-btn" aria-label="Ask the AI copilot">&#129302;</button>
    <div class="ai-widget-panel" id="ai-widget-panel" hidden>
      <div class="ai-widget-head">
        <span>Ask Northstar Copilot</span>
        <button type="button" class="ai-widget-close" id="ai-widget-close" aria-label="Close">&times;</button>
      </div>
      <div id="ai-widget-body"></div>
    </div>`;
  document.body.appendChild(wrap);

  const btn = document.getElementById("ai-widget-btn");
  const panel = document.getElementById("ai-widget-panel");
  const body = document.getElementById("ai-widget-body");
  let opened = false;

  btn.addEventListener("click", async () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden && !opened) {
      opened = true;
      await loadWidgetBody();
    }
  });
  document.getElementById("ai-widget-close").addEventListener("click", () => { panel.hidden = true; });

  async function loadWidgetBody() {
    requireAiSession(body, renderChatBody);
  }

  /* ------------------------------------------
     CHAT BODY — same shape as the standalone console's own chat widget.
     ------------------------------------------ */
  function renderChatBody() {
    body.innerHTML = `
      <div class="ai-widget-messages" id="ai-widget-messages">
        <div style="color:var(--ink-500); font-size:12.5px;">e.g. &ldquo;Is the detention charge on shipment 98 legitimate?&rdquo;</div>
      </div>
      <form class="ai-widget-input-row" id="ai-widget-form">
        <input type="text" id="ai-widget-input" placeholder="Ask about a shipment, carrier, or policy..." autocomplete="off" required>
        <button type="submit" class="ai-widget-btn" style="position:static; width:36px; height:36px; font-size:16px;">&#8594;</button>
      </form>`;

    const messagesEl = document.getElementById("ai-widget-messages");
    const formEl = document.getElementById("ai-widget-form");
    const inputEl = document.getElementById("ai-widget-input");

    function addMessage(role, text) {
      if (messagesEl.children.length === 1 && messagesEl.children[0].tagName === "DIV" && !messagesEl.children[0].classList.contains("ai-widget-msg")) {
        messagesEl.innerHTML = "";
      }
      const el = document.createElement("div");
      el.className = `ai-widget-msg ${role}`;
      if (role === "assistant") {
        el.innerHTML = aiRenderMarkdown(text);
      } else {
        el.textContent = text;
      }
      messagesEl.appendChild(el);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return el;
    }

    formEl.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = inputEl.value.trim();
      if (!message) return;
      inputEl.value = "";
      addMessage("user", message);
      const pending = addMessage("pending", "Checking reconciliation, policy, and history...");
      try {
        const { response } = await aiApiRequest("POST", "/chat", { message });
        pending.remove();
        addMessage("assistant", response);
      } catch (err) {
        pending.remove();
        addMessage("assistant", `Error: ${err.message}`);
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", renderAiWidget);
