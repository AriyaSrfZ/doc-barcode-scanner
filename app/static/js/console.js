/*
Talks directly to this service's own JSON API (documented in docs/API.md)
using the bearer token entered on this page. No separate backend logic -
this page is just another API consumer, same as an external app would be.
*/

const PALETTE = { primary: "#5b5ff0", primaryLight: "rgba(91,95,240,0.15)", categories: ["#5b5ff0", "#22c3a6", "#f5a623", "#ef476f", "#118ab2"] };

function getToken() { return localStorage.getItem("qr_access_token"); }
function saveToken() {
  const token = document.getElementById("token-input").value.trim();
  if (!token) return;
  localStorage.setItem("qr_access_token", token);
  init();
}
function logout() {
  localStorage.removeItem("qr_access_token");
  location.reload();
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" },
  });
  if (res.status === 401) {
    document.getElementById("token-error").textContent = "That token was rejected (expired or invalid). Get a fresh one and try again.";
    document.getElementById("token-error").style.display = "block";
    localStorage.removeItem("qr_access_token");
    document.getElementById("token-gate").style.display = "block";
    document.getElementById("app-view").style.display = "none";
    throw new Error("unauthorized");
  }
  return res;
}

function updateFields() {
  const type = document.getElementById("new-type").value;
  document.querySelectorAll(".qr-fields").forEach((el) => (el.style.display = "none"));
  document.getElementById("field-" + type).style.display = "block";
}

async function createCode(event) {
  event.preventDefault();
  const type = document.getElementById("new-type").value;
  const body = { type };
  if (type === "url") body.url = document.getElementById("f-url").value;
  if (type === "text") body.text = document.getElementById("f-text").value;
  if (type === "wifi") {
    body.wifi_ssid = document.getElementById("f-wifi-ssid").value;
    body.wifi_password = document.getElementById("f-wifi-password").value;
  }
  if (type === "vcard") {
    body.vcard_name = document.getElementById("f-vcard-name").value;
    body.vcard_phone = document.getElementById("f-vcard-phone").value;
  }

  const errEl = document.getElementById("create-error");
  errEl.style.display = "none";
  try {
    const res = await api("/codes", { method: "POST", body: JSON.stringify(body) });
    if (!res.ok) {
      const err = await res.json();
      errEl.textContent = err.detail || "Something went wrong.";
      errEl.style.display = "block";
      return;
    }
    loadCodes();
    loadStats();
  } catch (e) {
    /* 401 already handled in api() */
  }
}

async function loadStats() {
  try {
    const res = await api("/stats");
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById("stat-total").textContent = stats.summary.total;
    document.getElementById("stat-last24").textContent = stats.summary.last_24h;

    new Chart(document.getElementById("chart-daily"), {
      type: "line",
      data: { labels: stats.daily.map((d) => d.day.slice(5)), datasets: [{ data: stats.daily.map((d) => d.count), borderColor: PALETTE.primary, backgroundColor: PALETTE.primaryLight, fill: true, tension: 0.35 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });

    if (stats.devices.length) {
      new Chart(document.getElementById("chart-devices"), {
        type: "doughnut",
        data: { labels: stats.devices.map((d) => d.device_type), datasets: [{ data: stats.devices.map((d) => d.count), backgroundColor: PALETTE.categories, borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, cutout: "60%" },
      });
    }
  } catch (e) {}
}

async function loadCodes() {
  try {
    const res = await api("/codes");
    if (!res.ok) return;
    const codes = await res.json();
    document.getElementById("stat-count").textContent = codes.length;

    const grid = document.getElementById("codes-grid");
    grid.innerHTML = "";
    for (const c of codes) {
      const card = document.createElement("div");
      card.className = "card qr-card";
      card.innerHTML = `
        <img width="160" height="160" alt="QR code">
        <p class="muted">${c.type}${c.type === "url" ? " &middot; trackable" : ""}</p>
        <p class="muted" style="font-size:0.75rem;">${new Date(c.created_at).toLocaleDateString()}</p>`;
      grid.appendChild(card);

      // <img src> can't carry an Authorization header, and putting a JWT
      // in a query string would leak it into browser history and server
      // logs - so fetch the image properly and hand the img a blob URL.
      api(c.image_url)
        .then((r) => r.blob())
        .then((blob) => {
          card.querySelector("img").src = URL.createObjectURL(blob);
        })
        .catch(() => {});
    }
  } catch (e) {}
}

function init() {
  const token = getToken();
  if (!token) {
    document.getElementById("token-gate").style.display = "block";
    document.getElementById("app-view").style.display = "none";
    return;
  }
  document.getElementById("token-gate").style.display = "none";
  document.getElementById("app-view").style.display = "block";
  document.getElementById("logout-link").style.display = "inline";
  loadStats();
  loadCodes();
}

document.addEventListener("DOMContentLoaded", init);
