// shared.js — Xpediture common utilities

(function() {
  const saved = localStorage.getItem("xp_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("xp_theme", next);
}

// ── AUTH GUARD ────────────────────────────────────────────
function requireAuth() {
  const user = JSON.parse(localStorage.getItem("xp_logged"));
  if (!user) { window.location.href = "index.html"; return null; }
  return user;
}

function logout() {
  localStorage.removeItem("xp_logged");
  window.location.href = "index.html";
}

// ── DATA HELPERS ──────────────────────────────────────────
function getData() {
  return JSON.parse(localStorage.getItem("xp_data")) || {};
}

function saveData(data) {
  localStorage.setItem("xp_data", JSON.stringify(data));
}

function getUserStore(user) {
  const data = getData();
  if (!data[user.u]) data[user.u] = { trips: {}, currentTrip: "" };
  return { data, store: data[user.u] };
}

// ── RATES ─────────────────────────────────────────────────
const FALLBACK_NAMES = { USD: "US Dollar", EUR: "Euro", GBP: "British Pound", JPY: "Japanese Yen", AUD: "Australian Dollar", CAD: "Canadian Dollar", CHF: "Swiss Franc", INR: "Indian Rupee", SGD: "Singapore Dollar", AED: "UAE Dirham", THB: "Thai Baht", MXN: "Mexican Peso", HKD: "Hong Kong Dollar", KRW: "South Korean Won", NZD: "New Zealand Dollar" };
let _rates = JSON.parse(localStorage.getItem("xp_rates")) || { USD: 1, EUR: 0.85, GBP: 0.74, JPY: 156.8, AUD: 1.38, CAD: 1.37, CHF: 0.78, INR: 94.6, SGD: 1.27, AED: 3.67, THB: 32.2, MXN: 17.2, HKD: 7.83, KRW: 1463, NZD: 1.68 };
let _currencyNames = JSON.parse(localStorage.getItem("xp_cnames")) || { ...FALLBACK_NAMES };

async function loadRates() {
  try {
    const res = await fetch("https://open.er-api.com/v6/latest/USD").then(x => x.json());
    if (res.result === "success") {
      _rates = res.rates;
      // Merge API keys into fallback names
      const merged = { ...FALLBACK_NAMES };
      Object.keys(_rates).forEach(c => { if (!merged[c]) merged[c] = c; });
      _currencyNames = merged;
      localStorage.setItem("xp_rates", JSON.stringify(_rates));
      localStorage.setItem("xp_cnames", JSON.stringify(_currencyNames));
    }
  } catch (e) {
    console.warn("Using cached rates");
  }
  return { rates: _rates, currencyNames: _currencyNames };
}

function convert(amount, from, to) {
  if (!_rates[from] || !_rates[to]) return amount;
  return (amount / _rates[from]) * _rates[to];
}

// ── POPULATE CURRENCY SELECT ──────────────────────────────
function populateCurrencySelect(el, selectedVal) {
  const codes = Object.keys(_currencyNames).sort();
  el.innerHTML = codes.map(c => `<option value="${c}">${c} — ${_currencyNames[c]}</option>`).join('');
  if (selectedVal) el.value = selectedVal;
}

// ── STATUS LABEL ──────────────────────────────────────────
function statusLabel(s) {
  return s === 'planned' ? '📅 Planned' : s === 'ongoing' ? '🟢 Ongoing' : '✅ Completed';
}

// ── TOAST ─────────────────────────────────────────────────
function notify(msg, type = "success") {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.style.background = type === "success" ? "#4ade80" : type === "warn" ? "#fbbf24" : "#f87171";
  t.style.color = "#0a0a0f";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

// ── RENDER SIDEBAR USER ───────────────────────────────────
function renderSidebarUser(user) {
  const el = document.getElementById("sidebarUser");
  if (el) el.innerHTML = `<strong>${user.u}</strong>${user.base}`;
  const cur = document.getElementById("sidebarCurrency");
  if (cur) {
    populateCurrencySelect(cur, user.base);
    cur.onchange = () => {
      user.base = cur.value;
      localStorage.setItem("xp_logged", JSON.stringify(user));
      const users = JSON.parse(localStorage.getItem("xp_users")) || [];
      const idx = users.findIndex(x => x.u === user.u);
      if (idx >= 0) { users[idx].base = user.base; localStorage.setItem("xp_users", JSON.stringify(users)); }
      notify(`Home currency: ${user.base}`);
      if (typeof onCurrencyChange === 'function') onCurrencyChange();
    };
  }
}

// ── BUDGET BAR HTML ───────────────────────────────────────
function budgetBarHtml(cur, total, budget) {
  if (!budget) return '';
  const pct = Math.min(100, (total / budget) * 100);
  const cls = pct > 100 ? 'over' : pct > 80 ? 'warn' : '';
  return `<div style="margin-top:10px;">
    <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
      <span>Budget</span>
      <span>${cur} ${total.toFixed(0)} / ${budget} (${pct.toFixed(0)}%)</span>
    </div>
    <div class="progress-wrap"><div class="progress-bar ${cls}" style="width:${pct.toFixed(1)}%"></div></div>
  </div>`;
}

// ── SPENDING STREAK ───────────────────────────────────────
function spendingStreak(expenses) {
  const expDays = [...new Set(expenses.map(e => e.date).filter(Boolean))].sort();
  let maxStreak = 0, cur = 0;
  for (let i = 0; i < expDays.length; i++) {
    cur = (i === 0 || (new Date(expDays[i]) - new Date(expDays[i - 1])) / 86400000 !== 1) ? 1 : cur + 1;
    if (cur > maxStreak) maxStreak = cur;
  }
  return maxStreak;
}

// ── MOST EXPENSIVE DAY ────────────────────────────────────
function mostExpensiveDay(expenses) {
  const byDay = {};
  expenses.forEach(e => { if (e.date) byDay[e.date] = (byDay[e.date] || 0) + e.amount; });
  const maxDay = Object.keys(byDay).sort((a, b) => byDay[b] - byDay[a])[0];
  return maxDay ? { date: maxDay, amount: byDay[maxDay] } : null;
}
