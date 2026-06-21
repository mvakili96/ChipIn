"use strict";

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

const state = {
  initData: tg ? tg.initData : "",
  requestedGroupId: new URLSearchParams(window.location.search).get("group_id") || "",
  user: null,
  groups: [],
  settlements: { aggregate: [], groups: [] },
  selectedGroupId: "",
  detail: null,
};

const els = {
  status: document.querySelector("#status"),
  dashboard: document.querySelector("#dashboard"),
  userPill: document.querySelector("#user-pill"),
  groupsCount: document.querySelector("#groups-count"),
  netBalance: document.querySelector("#net-balance"),
  balancesList: document.querySelector("#balances-list"),
  groupsList: document.querySelector("#groups-list"),
  groupDetail: document.querySelector("#group-detail"),
  toast: document.querySelector("#toast"),
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function setStatus(stateName, text) {
  els.status.dataset.state = stateName;
  els.status.textContent = text;
  els.status.hidden = false;
}

let toastTimer;
function showToast(message, kind = "info") {
  window.clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.dataset.kind = kind;
  els.toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => {
    els.toast.classList.remove("is-visible");
  }, 2800);
}

function haptic(kind) {
  if (!tg || !tg.HapticFeedback) {
    return;
  }

  if (kind === "success" || kind === "error") {
    tg.HapticFeedback.notificationOccurred(kind);
  } else {
    tg.HapticFeedback.selectionChanged();
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": state.initData,
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null
        ? payload.error || payload.warning || JSON.stringify(payload)
        : payload || "Request failed";
    throw new Error(message);
  }

  return payload;
}

async function authenticate() {
  if (!state.initData) {
    throw new Error("Open ChipIn from Telegram to continue.");
  }

  return api("/telegram/auth/", {
    method: "POST",
    body: JSON.stringify({ init_data: state.initData }),
  });
}

async function refreshGroups() {
  const [groupsPayload, settlementsPayload] = await Promise.all([
    api("/telegram/api/groups/"),
    api("/telegram/api/settlements/"),
  ]);

  state.groups = groupsPayload.groups || [];
  state.settlements = settlementsPayload || { aggregate: [], groups: [] };

  if (
    state.selectedGroupId &&
    !state.groups.some((group) => group.id === state.selectedGroupId)
  ) {
    state.selectedGroupId = "";
    state.detail = null;
  }
}

async function loadGroup(groupId) {
  if (!groupId) {
    state.detail = null;
    render();
    return;
  }

  const detail = await api(`/telegram/api/groups/${encodeURIComponent(groupId)}/`);
  state.selectedGroupId = groupId;
  state.detail = detail;
  render();
}

function render() {
  els.dashboard.hidden = false;
  els.status.hidden = true;
  renderHeader();
  renderMetrics();
  renderBalances();
  renderGroups();
  renderGroupDetail();
}

function renderHeader() {
  els.userPill.textContent = state.user ? state.user.name : "";
}

function renderMetrics() {
  const net = (state.settlements.aggregate || []).reduce((sum, row) => {
    const amount = Number(row.amount) || 0;
    return sum + (row.direction === "owes_you" ? amount : -amount);
  }, 0);

  els.groupsCount.textContent = String(state.groups.length);
  els.netBalance.textContent = money.format(net);
}

function renderBalances() {
  const balances = state.settlements.aggregate || [];
  if (!balances.length) {
    els.balancesList.innerHTML = `<div class="empty">No open balances</div>`;
    return;
  }

  els.balancesList.innerHTML = balances
    .map((row) => {
      const isPositive = row.direction === "owes_you";
      const label = isPositive ? "owes you" : "you owe";
      return `
        <div class="row">
          <div class="row-main">
            <span class="row-title">${escapeHtml(row.name)}</span>
            <span class="row-value ${isPositive ? "good" : "bad"}">
              ${money.format(Number(row.amount) || 0)}
            </span>
          </div>
          <div class="row-meta">${escapeHtml(label)}</div>
        </div>
      `;
    })
    .join("");
}

function renderGroups() {
  if (!state.groups.length) {
    els.groupsList.innerHTML = `<div class="empty">No groups yet</div>`;
    return;
  }

  els.groupsList.innerHTML = state.groups
    .map(
      (group) => `
        <button class="group-item" data-group-id="${escapeHtml(group.id)}"
          aria-current="${group.id === state.selectedGroupId ? "true" : "false"}">
          <span class="row-main">
            <span class="row-title">${escapeHtml(group.name)}</span>
            <span class="row-value">${Number(group.expenses_count) || 0}</span>
          </span>
          <span class="row-meta">
            <span>ID ${escapeHtml(group.id)}</span>
            <span>${(group.users || []).length} users</span>
            <span>${escapeHtml(group.source || "manual")}</span>
          </span>
        </button>
      `,
    )
    .join("");
}

function renderGroupDetail() {
  const detail = state.detail;
  if (!detail || !detail.group) {
    els.groupDetail.hidden = true;
    els.groupDetail.innerHTML = "";
    return;
  }

  const group = detail.group;
  const users = group.users || [];

  els.groupDetail.hidden = false;
  els.groupDetail.innerHTML = `
    <div class="section-title">
      <h2>${escapeHtml(group.name)}</h2>
    </div>
    <div class="detail-body">
      <div class="subsection">
        <h3>Members</h3>
        <div class="chips">
          ${users.map((name) => `<span class="chip">${escapeHtml(name)}</span>`).join("")}
        </div>
      </div>

      <form id="expense-form" class="expense-form">
        <div class="field">
          <label for="expense-name">Expense</label>
          <input id="expense-name" name="name" type="text" required autocomplete="off">
        </div>
        <div class="field">
          <label for="expense-amount">Amount</label>
          <input id="expense-amount" name="amount" type="number" min="0.01" step="0.01" required>
        </div>
        <fieldset class="check-list">
          <legend>Sharers</legend>
          <div class="check-options">
            ${users
              .map(
                (name) => `
                  <label class="check-item">
                    <input type="checkbox" name="sharers" value="${escapeHtml(name)}" checked>
                    <span>${escapeHtml(name)}</span>
                  </label>
                `,
              )
              .join("")}
          </div>
        </fieldset>
        <button class="primary-button" type="submit">Add Expense</button>
      </form>

      <div class="subsection">
        <h3>Settlements</h3>
        <div class="list">${renderSettlements(detail.settlements || [])}</div>
      </div>

      <div class="subsection">
        <h3>Expenses</h3>
        <div class="list">${renderExpenses(detail.expenses || [])}</div>
      </div>
    </div>
  `;
}

function renderSettlements(settlements) {
  if (!settlements.length) {
    return `<div class="empty">No settlements</div>`;
  }

  return settlements
    .map(
      ([debtor, creditor, amount]) => `
        <div class="row">
          <div class="row-main">
            <span class="row-title">${escapeHtml(debtor)} to ${escapeHtml(creditor)}</span>
            <span class="row-value">${money.format(Number(amount) || 0)}</span>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderExpenses(expenses) {
  if (!expenses.length) {
    return `<div class="empty">No expenses</div>`;
  }

  return expenses
    .map(
      (expense) => `
        <div class="row">
          <div class="row-main">
            <span class="row-title">${escapeHtml(expense.name)}</span>
            <span class="row-value">${money.format(Number(expense.amount) || 0)}</span>
          </div>
          <div class="row-meta">
            <span>${escapeHtml(expense.payer)}</span>
            <span>${(expense.sharers || []).length} sharers</span>
          </div>
        </div>
      `,
    )
    .join("");
}

els.groupsList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-group-id]");
  if (!button) {
    return;
  }

  try {
    haptic("select");
    await loadGroup(button.dataset.groupId);
  } catch (error) {
    haptic("error");
    showToast(error.message, "error");
  }
});

els.groupDetail.addEventListener("submit", async (event) => {
  const form = event.target.closest("#expense-form");
  if (!form) {
    return;
  }

  event.preventDefault();

  const formData = new FormData(form);
  const sharers = formData.getAll("sharers");

  try {
    await api("/telegram/api/expenses/", {
      method: "POST",
      body: JSON.stringify({
        group_id: state.selectedGroupId,
        name: formData.get("name"),
        amount: formData.get("amount"),
        sharers,
      }),
    });

    form.reset();
    await refreshGroups();
    await loadGroup(state.selectedGroupId);
    haptic("success");
    showToast("Expense added");
  } catch (error) {
    haptic("error");
    showToast(error.message, "error");
  }
});

async function start() {
  if (tg) {
    tg.ready();
    tg.expand();
  }

  try {
    setStatus("loading", "Loading");
    const payload = await authenticate();
    state.user = payload.user;
    state.groups = payload.groups || [];
    state.settlements = payload.settlements || { aggregate: [], groups: [] };
    state.selectedGroupId = selectInitialGroup(payload);

    render();
    if (state.selectedGroupId) {
      await loadGroup(state.selectedGroupId);
    }
  } catch (error) {
    els.dashboard.hidden = true;
    setStatus("error", error.message);
  }
}

start();

function selectInitialGroup(payload) {
  if (
    state.requestedGroupId &&
    state.groups.some((group) => group.id === state.requestedGroupId)
  ) {
    return state.requestedGroupId;
  }

  if (payload.launch_group) {
    return payload.launch_group.id;
  }

  return state.groups[0] ? state.groups[0].id : "";
}
