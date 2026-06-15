"use strict";

const state = {
  users: [],
  groups: [],
  expenses: [],
  settlements: {},
  selectedGroupId: "",
  selectedSettlementGroupId: "",
};

const els = {
  apiStatus: document.querySelector("#api-status"),
  refreshButton: document.querySelector("#refresh-button"),
  toast: document.querySelector("#toast"),
  userForm: document.querySelector("#user-form"),
  userName: document.querySelector("#user-name"),
  userEmail: document.querySelector("#user-email"),
  groupForm: document.querySelector("#group-form"),
  groupName: document.querySelector("#group-name"),
  groupUsers: document.querySelector("#group-users"),
  expenseForm: document.querySelector("#expense-form"),
  expenseName: document.querySelector("#expense-name"),
  expenseAmount: document.querySelector("#expense-amount"),
  expenseGroup: document.querySelector("#expense-group"),
  expensePayer: document.querySelector("#expense-payer"),
  expenseSharers: document.querySelector("#expense-sharers"),
  settlementGroup: document.querySelector("#settlement-group"),
  usersCount: document.querySelector("#users-count"),
  groupsCount: document.querySelector("#groups-count"),
  expensesCount: document.querySelector("#expenses-count"),
  averageExpensesGroup: document.querySelector("#average-expenses-group"),
  averageExpensesUser: document.querySelector("#average-expenses-user"),
  usersTable: document.querySelector("#users-table"),
  usersManageTable: document.querySelector("#users-manage-table"),
  groupsList: document.querySelector("#groups-list"),
  groupDetail: document.querySelector("#group-detail"),
  expensesTable: document.querySelector("#expenses-table"),
  settlementsList: document.querySelector("#settlements-list"),
  overviewSettlements: document.querySelector("#overview-settlements"),
  overviewUserBalances: document.querySelector("#overview-user-balances"),
};

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function iconTrash() {
  return `
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M3 6h18"></path>
      <path d="M8 6V4h8v2"></path>
      <path d="M19 6l-1 14H6L5 6"></path>
      <path d="M10 11v5"></path>
      <path d="M14 11v5"></path>
    </svg>
  `;
}

function formatMoney(value) {
  const amount = Number(value) || 0;
  return currency.format(amount);
}

function formatAverageCount(value) {
  const amount = Number(value) || 0;
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
  }).format(amount);
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function groupSettlementKey(groupId) {
  return `settlement-group:${groupId}`;
}

function groupById(groupId) {
  return state.groups.find((group) => group.id === groupId);
}

function groupByName(name) {
  return state.groups.find((group) => group.name === name);
}

function expensesForGroup(group) {
  if (!group) {
    return [];
  }

  return state.expenses.filter((expense) => expense.group === group.name);
}

function settlementsForGroup(groupId) {
  if (!groupId) {
    return [];
  }

  return state.settlements[groupSettlementKey(groupId)] || [];
}

function totalForExpenses(expenses) {
  return expenses.reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
}

function setApiStatus(kind, text) {
  els.apiStatus.dataset.state = kind;
  els.apiStatus.textContent = text;
}

let toastTimer;
function showToast(message, kind = "info") {
  clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.dataset.kind = kind;
  els.toast.classList.add("is-visible");
  toastTimer = window.setTimeout(() => {
    els.toast.classList.remove("is-visible");
  }, 3200);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
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

async function refreshData({ quiet = false } = {}) {
  if (!quiet) {
    setApiStatus("loading", "Refreshing");
  }

  try {
    const [users, groups, expenses, settlements] = await Promise.all([
      request("/users/"),
      request("/groups/"),
      request("/expenses/"),
      request("/settlements/group/").catch(() => ({})),
    ]);

    state.users = users;
    state.groups = groups;
    state.expenses = expenses;
    state.settlements = settlements || {};

    if (
      state.selectedSettlementGroupId &&
      !state.groups.some((group) => group.id === state.selectedSettlementGroupId)
    ) {
      state.selectedSettlementGroupId = "";
    }

    if (
      state.selectedGroupId &&
      !state.groups.some((group) => group.id === state.selectedGroupId)
    ) {
      state.selectedGroupId = "";
    }

    if (!state.selectedGroupId && state.groups[0]) {
      state.selectedGroupId = state.groups[0].id;
    }

    if (!state.selectedSettlementGroupId && state.groups[0]) {
      state.selectedSettlementGroupId = state.groups[0].id;
    }

    render();
    setApiStatus("ok", "API online");
  } catch (error) {
    setApiStatus("error", "API offline");
    showToast(error.message, "error");
  }
}

function render() {
  renderSummary();
  renderUserOptions();
  renderExpenseGroupOptions();
  renderSettlementGroupOptions();
  renderUsersTable();
  renderUsersManageTable();
  renderGroups();
  renderGroupDetail();
  renderExpenses();
  renderSettlements();
}

function renderSummary() {
  const averageGroup = state.groups.length
    ? state.expenses.length / state.groups.length
    : 0;
  const averageUser = state.users.length
    ? state.expenses.length / state.users.length
    : 0;

  els.usersCount.textContent = String(state.users.length);
  els.groupsCount.textContent = String(state.groups.length);
  els.expensesCount.textContent = String(state.expenses.length);
  els.averageExpensesGroup.textContent = formatAverageCount(averageGroup);
  els.averageExpensesUser.textContent = `${formatAverageCount(averageUser)} / user`;
}

function renderUserOptions() {
  els.groupUsers.innerHTML = state.users
    .map(
      (user) => `
        <label class="check-item">
          <input type="checkbox" name="members" value="${escapeHtml(user.name)}">
          <span>${escapeHtml(user.name)}</span>
        </label>
      `,
    )
    .join("");
}

function renderExpenseGroupOptions() {
  els.expenseGroup.innerHTML = state.groups.length
    ? state.groups
        .map(
          (group) =>
            `<option value="${escapeHtml(group.name)}">${escapeHtml(group.name)}</option>`,
        )
        .join("")
    : `<option value="">No groups</option>`;

  els.expenseGroup.disabled = state.groups.length === 0;
  updateExpenseUsers();
}

function updateExpenseUsers() {
  const group = groupByName(els.expenseGroup.value);
  const members = group ? group.users || [] : [];

  els.expensePayer.innerHTML = members.length
    ? members
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join("")
    : `<option value="">No members</option>`;
  els.expensePayer.disabled = members.length === 0;

  els.expenseSharers.innerHTML = members
    .map(
      (name) => `
        <label class="check-item">
          <input type="checkbox" name="sharers" value="${escapeHtml(name)}" checked>
          <span>${escapeHtml(name)}</span>
        </label>
      `,
    )
    .join("");
}

function renderSettlementGroupOptions() {
  els.settlementGroup.innerHTML = state.groups.length
    ? state.groups
        .map(
          (group) => `
            <option value="${escapeHtml(group.id)}" ${
              group.id === state.selectedSettlementGroupId ? "selected" : ""
            }>
              ${escapeHtml(group.name)}
            </option>
          `,
        )
        .join("")
    : `<option value="">No groups</option>`;

  els.settlementGroup.disabled = state.groups.length === 0;
}

function renderUsersTable() {
  if (!state.users.length) {
    els.usersTable.innerHTML = `
      <tr>
        <td colspan="2"><div class="empty-state">No users</div></td>
      </tr>
    `;
    return;
  }

  els.usersTable.innerHTML = state.users
    .map(
      (user) => `
        <tr>
          <td><strong>${escapeHtml(user.name)}</strong></td>
          <td class="muted">${escapeHtml(user.email)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderUsersManageTable() {
  if (!state.users.length) {
    els.usersManageTable.innerHTML = `
      <tr>
        <td colspan="4"><div class="empty-state">No users</div></td>
      </tr>
    `;
    return;
  }

  els.usersManageTable.innerHTML = state.users
    .map(
      (user) => `
        <tr data-user-row="${escapeHtml(user.id)}">
          <td><strong>${escapeHtml(user.name)}</strong></td>
          <td class="muted">${escapeHtml(user.email)}</td>
          <td><small class="muted">${escapeHtml(user.id)}</small></td>
        </tr>
      `,
    )
    .join("");
}

function renderGroups() {
  if (!state.groups.length) {
    els.groupsList.innerHTML = `<div class="empty-state">No groups</div>`;
    return;
  }

  els.groupsList.innerHTML = state.groups
    .map((group) => {
      const isSelected = group.id === state.selectedGroupId;
      const members = (group.users || [])
        .map((name) => `<span class="chip">${escapeHtml(name)}</span>`)
        .join("");

      return `
        <article class="record-card group-card ${isSelected ? "is-selected" : ""}">
          <button
            class="group-card-button"
            type="button"
            data-select-group="${escapeHtml(group.id)}"
            aria-pressed="${isSelected ? "true" : "false"}"
            aria-label="Open ${escapeHtml(group.name)}"
          >
            <span class="group-card-main">
              <strong class="group-card-name">${escapeHtml(group.name)}</strong>
              <small>${escapeHtml(group.id)}</small>
            </span>
            <span class="chip-row">${members}</span>
          </button>
          <div class="record-actions">
            <button class="danger-button" type="button" data-delete-group="${escapeHtml(
              group.id,
            )}" title="Delete group" aria-label="Delete ${escapeHtml(group.name)}">
              ${iconTrash()}
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderGroupDetail() {
  if (!state.groups.length) {
    els.groupDetail.innerHTML = `<div class="empty-state">No group selected</div>`;
    return;
  }

  const group = groupById(state.selectedGroupId) || state.groups[0];
  const members = group.users || [];
  const expenses = expensesForGroup(group);
  const settlements = settlementsForGroup(group.id);
  const total = totalForExpenses(expenses);
  const memberChips = members
    .map((name) => `<span class="chip">${escapeHtml(name)}</span>`)
    .join("");

  els.groupDetail.innerHTML = `
    <section class="group-detail-card">
      <header class="group-detail-header">
        <div>
          <h3>${escapeHtml(group.name)}</h3>
          <small>${escapeHtml(group.id)}</small>
        </div>
        <div class="group-detail-metrics">
          <span><strong>${members.length}</strong> Members</span>
          <span><strong>${expenses.length}</strong> Expenses</span>
          <span><strong>${formatMoney(total)}</strong> Total</span>
        </div>
      </header>

      <div class="group-detail-section">
        <h4>Members</h4>
        <div class="chip-row">${memberChips || `<span class="muted">No members</span>`}</div>
      </div>

      <div class="group-detail-section">
        <h4>Expenses</h4>
        ${groupExpensesMarkup(expenses)}
      </div>

      <div class="group-detail-section">
        <h4>Balances</h4>
        <div class="settlement-list">
          ${
            settlements.length
              ? settlements
                  .map(([debtor, creditor, amount]) =>
                    settlementMarkup({ debtor, creditor, amount }),
                  )
                  .join("")
              : `<div class="empty-state">No balances</div>`
          }
        </div>
      </div>
    </section>
  `;
}

function groupExpensesMarkup(expenses) {
  if (!expenses.length) {
    return `<div class="empty-state">No expenses</div>`;
  }

  return `
    <div class="table-wrap">
      <table class="compact-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Paid by</th>
            <th>Split</th>
            <th class="numeric">Amount</th>
          </tr>
        </thead>
        <tbody>
          ${expenses
            .map(
              (expense) => `
                <tr>
                  <td><strong>${escapeHtml(expense.name)}</strong></td>
                  <td>${escapeHtml(expense.payer)}</td>
                  <td>${escapeHtml((expense.sharers || []).join(", "))}</td>
                  <td class="numeric"><strong>${formatMoney(expense.amount)}</strong></td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderExpenses() {
  if (!state.expenses.length) {
    els.expensesTable.innerHTML = `
      <tr>
        <td colspan="6"><div class="empty-state">No expenses</div></td>
      </tr>
    `;
    return;
  }

  els.expensesTable.innerHTML = state.expenses
    .map(
      (expense) => `
        <tr>
          <td><strong>${escapeHtml(expense.name)}</strong></td>
          <td>${escapeHtml(expense.group)}</td>
          <td>${escapeHtml(expense.payer)}</td>
          <td>${escapeHtml((expense.sharers || []).join(", "))}</td>
          <td class="numeric"><strong>${formatMoney(expense.amount)}</strong></td>
          <td class="action-cell">
            <button class="danger-button" type="button" data-delete-expense="${escapeHtml(
              expense.id,
            )}" title="Delete expense" aria-label="Delete ${escapeHtml(expense.name)}">
              ${iconTrash()}
            </button>
          </td>
        </tr>
      `,
    )
    .join("");
}

function allNamedSettlements() {
  return Object.entries(state.settlements).reduce((items, [key, settlements]) => {
    const groupId = key.replace("settlement-group:", "");
    const group = groupById(groupId);
    const groupName = group ? group.name : groupId;

    (settlements || []).forEach(([debtor, creditor, amount]) => {
      items.push({
        groupName,
        debtor,
        creditor,
        amount,
      });
    });

    return items;
  }, []);
}

function aggregatedUserBalances() {
  const balances = new Map();

  state.users.forEach((user) => {
    balances.set(user.name, 0);
  });

  allNamedSettlements().forEach(({ debtor, creditor, amount }) => {
    const value = Number(amount) || 0;
    balances.set(debtor, (balances.get(debtor) || 0) - value);
    balances.set(creditor, (balances.get(creditor) || 0) + value);
  });

  return Array.from(balances.entries())
    .map(([name, balance]) => ({ name, balance }))
    .sort((a, b) => Math.abs(b.balance) - Math.abs(a.balance) || a.name.localeCompare(b.name));
}

function renderSettlements() {
  const group = groupById(state.selectedSettlementGroupId);
  const selectedKey = state.selectedSettlementGroupId
    ? groupSettlementKey(state.selectedSettlementGroupId)
    : "";
  const settlements = state.settlements[selectedKey] || [];
  const allSettlements = allNamedSettlements();
  const userBalances = aggregatedUserBalances();

  els.settlementsList.innerHTML = settlements.length
    ? settlements
        .map(([debtor, creditor, amount]) =>
          settlementMarkup({
            debtor,
            creditor,
            amount,
            groupName: group ? group.name : "",
          }),
        )
        .join("")
    : `<div class="empty-state">No balances</div>`;

  els.overviewSettlements.innerHTML = allSettlements.length
    ? allSettlements.slice(0, 6).map(settlementMarkup).join("")
    : `<div class="empty-state">No balances</div>`;

  els.overviewUserBalances.innerHTML = userBalances.length
    ? userBalances.map(userBalanceMarkup).join("")
    : `<div class="empty-state">No users</div>`;
}

function settlementMarkup({ debtor, creditor, amount, groupName }) {
  return `
    <article class="settlement-item">
      <span>
        <strong>${escapeHtml(debtor)}</strong>
        pays
        <strong>${escapeHtml(creditor)}</strong>
        ${groupName ? `<span class="muted">in ${escapeHtml(groupName)}</span>` : ""}
      </span>
      <b>${formatMoney(amount)}</b>
    </article>
  `;
}

function userBalanceMarkup({ name, balance }) {
  const isSettled = Math.abs(balance) < 0.005;
  const kind = isSettled ? "settled" : balance > 0 ? "owed" : "owes";
  const label = isSettled ? "settled" : balance > 0 ? "gets back" : "owes";

  return `
    <article class="user-balance-item" data-kind="${kind}">
      <span><strong>${escapeHtml(name)}</strong> ${label}</span>
      <b>${isSettled ? formatMoney(0) : formatMoney(Math.abs(balance))}</b>
    </article>
  `;
}

function setSubmitting(form, isSubmitting) {
  const button = form.querySelector("button[type='submit']");
  if (button) {
    button.disabled = isSubmitting;
  }
}

async function createUser(event) {
  event.preventDefault();
  setSubmitting(els.userForm, true);

  try {
    await request("/users/", {
      method: "POST",
      body: JSON.stringify({
        name: els.userName.value.trim(),
        email: els.userEmail.value.trim(),
      }),
    });
    els.userForm.reset();
    await refreshData({ quiet: true });
    showToast("User added");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setSubmitting(els.userForm, false);
  }
}

async function createGroup(event) {
  event.preventDefault();
  const members = Array.from(
    els.groupUsers.querySelectorAll("input[name='members']:checked"),
  ).map((input) => input.value);

  if (!members.length) {
    showToast("Choose at least one member", "error");
    return;
  }

  setSubmitting(els.groupForm, true);

  try {
    const savedGroup = await request("/groups/", {
      method: "POST",
      body: JSON.stringify({
        name: els.groupName.value.trim(),
        users: members,
      }),
    });
    state.selectedGroupId = savedGroup.id;
    state.selectedSettlementGroupId = savedGroup.id;
    els.groupForm.reset();
    await refreshData({ quiet: true });
    showToast("Group created");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setSubmitting(els.groupForm, false);
  }
}

async function createExpense(event) {
  event.preventDefault();
  const sharers = Array.from(
    els.expenseSharers.querySelectorAll("input[name='sharers']:checked"),
  ).map((input) => input.value);

  if (!sharers.length) {
    showToast("Choose at least one sharer", "error");
    return;
  }

  setSubmitting(els.expenseForm, true);

  try {
    await request("/expenses/", {
      method: "POST",
      body: JSON.stringify({
        name: els.expenseName.value.trim(),
        group: els.expenseGroup.value,
        amount: Number(els.expenseAmount.value),
        payer: els.expensePayer.value,
        sharers,
      }),
    });
    els.expenseForm.reset();
    await refreshData({ quiet: true });
    showToast("Expense added");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setSubmitting(els.expenseForm, false);
  }
}

async function deleteGroup(groupId) {
  try {
    await request(`/groups/${encodeURIComponent(groupId)}/`, { method: "DELETE" });
    await refreshData({ quiet: true });
    showToast("Group deleted");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteExpense(expenseId) {
  try {
    await request(`/expenses/${encodeURIComponent(expenseId)}/`, {
      method: "DELETE",
    });
    await refreshData({ quiet: true });
    showToast("Expense deleted");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function selectGroup(groupId) {
  state.selectedGroupId = groupId;
  state.selectedSettlementGroupId = groupId;
  renderGroups();
  renderGroupDetail();
  renderSettlementGroupOptions();
  renderSettlements();
}

function setupTabs() {
  const tabs = Array.from(document.querySelectorAll("[role='tab']"));
  const panels = Array.from(document.querySelectorAll("[role='tabpanel']"));

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => {
        item.classList.toggle("is-active", item === tab);
        item.setAttribute("aria-selected", item === tab ? "true" : "false");
      });

      panels.forEach((panel) => {
        const isActive = panel.id === tab.getAttribute("aria-controls");
        panel.classList.toggle("is-active", isActive);
        panel.hidden = !isActive;
      });
    });
  });
}

function setupEvents() {
  setupTabs();
  els.refreshButton.addEventListener("click", () => refreshData());
  els.userForm.addEventListener("submit", createUser);
  els.groupForm.addEventListener("submit", createGroup);
  els.expenseForm.addEventListener("submit", createExpense);
  els.expenseGroup.addEventListener("change", updateExpenseUsers);
  els.settlementGroup.addEventListener("change", (event) => {
    state.selectedSettlementGroupId = event.target.value;
    renderSettlements();
  });

  document.addEventListener("click", (event) => {
    const selectButton = event.target.closest("[data-select-group]");
    if (selectButton) {
      selectGroup(selectButton.dataset.selectGroup);
      return;
    }

    const groupButton = event.target.closest("[data-delete-group]");
    if (groupButton) {
      deleteGroup(groupButton.dataset.deleteGroup);
      return;
    }

    const expenseButton = event.target.closest("[data-delete-expense]");
    if (expenseButton) {
      deleteExpense(expenseButton.dataset.deleteExpense);
    }
  });
}

setupEvents();
refreshData();
