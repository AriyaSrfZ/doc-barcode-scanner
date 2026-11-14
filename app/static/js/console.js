/*
Document & Picture Barcode Scanner & Generator Client Script.
Interacts with /api/v1/scan and /api/v1/generate.
*/

// --- Tab Management ---
function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    
    const target = document.getElementById(tabId);
    if (target) target.style.display = "block";
    
    const btn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.getAttribute("onclick")?.includes(tabId));
    if (btn) btn.classList.add("active");

    if (tabId === "tab-analytics" && getToken()) {
        initAnalytics();
    }
}

// --- Drag and Drop File Upload ---
const dropZone = document.getElementById("drop-zone");
if (dropZone) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) handleFileSelected(files[0]);
    }, false);
}

// --- Scanner Logic ---
let currentScanImage = null;

async function handleFileSelected(file) {
    if (!file) return;
    const loading = document.getElementById("scan-loading");
    const resultsBox = document.getElementById("scan-results-box");
    const list = document.getElementById("barcode-list");
    const countEl = document.getElementById("results-count");
    
    loading.style.display = "block";
    resultsBox.style.display = "none";
    list.innerHTML = "";

    // Load image preview into memory if image
    if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
            currentScanImage = new Image();
            currentScanImage.onload = () => {};
            currentScanImage.src = e.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        currentScanImage = null;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/v1/scan", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Scanning failed.");
        }

        const data = await res.json();
        loading.style.display = "none";
        resultsBox.style.display = "block";
        countEl.textContent = data.total_detected;

        if (data.barcodes.length === 0) {
            list.innerHTML = `<p class="muted" style="padding:12px; background:#fff; border-radius:6px;">No barcodes or QR codes were detected in this file.</p>`;
        } else {
            data.barcodes.forEach((b, idx) => {
                const item = document.createElement("div");
                item.className = "barcode-item";
                item.innerHTML = `
                    <div>
                        <span class="badge">${b.symbology}</span>
                        ${b.page > 1 ? `<span class="badge" style="background:#f1f5f9; color:#475569;">Page ${b.page}</span>` : ""}
                        <div class="barcode-data" id="barcode-val-${idx}">${escapeHtml(b.data)}</div>
                        <div class="muted" style="font-size:0.75rem; margin-top:2px;">Location: x=${b.rect.x}, y=${b.rect.y} (${b.rect.width}x${b.rect.height}px)</div>
                    </div>
                    <div>
                        <button class="copy-btn" onclick="copyToClipboard('${escapeAttr(b.data)}')">Copy</button>
                    </div>
                `;
                list.appendChild(item);
            });
        }

        // Draw image and bounding boxes onto canvas
        if (currentScanImage) {
            renderScanCanvas(currentScanImage, data.barcodes);
        } else {
            document.getElementById("canvas-container").style.display = "none";
        }
    } catch (err) {
        loading.style.display = "none";
        alert("Error scanning file: " + err.message);
    }
}

function renderScanCanvas(img, barcodes) {
    const container = document.getElementById("canvas-container");
    container.style.display = "inline-block";
    const canvas = document.getElementById("preview-canvas");
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");

    // Draw base image
    ctx.drawImage(img, 0, 0);

    // Draw green bounding boxes around barcodes
    ctx.lineWidth = Math.max(3, Math.round(canvas.width / 300));
    ctx.strokeStyle = "#10b981"; // emerald green
    ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
    ctx.font = `bold ${Math.max(14, Math.round(canvas.width / 40))}px sans-serif`;

    barcodes.forEach(b => {
        const { x, y, width, height } = b.rect;
        ctx.fillRect(x, y, width, height);
        ctx.strokeRect(x, y, width, height);

        // Label tag
        const tag = `${b.symbology}: ${b.data.slice(0, 16)}`;
        ctx.fillStyle = "#10b981";
        ctx.fillRect(x, Math.max(0, y - 26), ctx.measureText(tag).width + 12, 24);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(tag, x + 6, Math.max(16, y - 8));
        ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
    });
}

// --- Generator Logic ---
const SAMPLE_PAYLOADS = {
    qr: "https://example.com",
    code128: "INV-2026-9812",
    code39: "CODE39-TEST",
    ean13: "5901234123457",
    ean8: "96385074",
    upca: "012345678905",
    isbn13: "9780306406157"
};

function updateGeneratorFields() {
    const sym = document.getElementById("gen-symbology").value;
    const dataInput = document.getElementById("gen-data");
    if (dataInput) {
        const currentVal = dataInput.value.trim();
        if (!currentVal || Object.values(SAMPLE_PAYLOADS).includes(currentVal)) {
            dataInput.value = SAMPLE_PAYLOADS[sym] || "SAMPLE";
        }
        dataInput.placeholder = SAMPLE_PAYLOADS[sym] || "Payload";
    }
    previewGeneratedBarcode();
}

async function previewGeneratedBarcode() {
    const symbology = document.getElementById("gen-symbology").value;
    const data = document.getElementById("gen-data").value.trim() || "SAMPLE";
    const fg = document.getElementById("gen-fg").value;
    const bg = document.getElementById("gen-bg").value;
    const imgEl = document.getElementById("gen-preview-img");

    try {
        const res = await fetch("/api/v1/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbology,
                data,
                output_format: "png",
                fg_color: fg,
                bg_color: bg,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Generation failed.");
        }

        const blob = await res.blob();
        imgEl.src = URL.createObjectURL(blob);
    } catch (e) {
        console.error("Preview error:", e);
    }
}

async function downloadGenerated(format) {
    const symbology = document.getElementById("gen-symbology").value;
    const data = document.getElementById("gen-data").value.trim() || "SAMPLE";
    const fg = document.getElementById("gen-fg").value;
    const bg = document.getElementById("gen-bg").value;

    try {
        const res = await fetch("/api/v1/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                symbology,
                data,
                output_format: format,
                fg_color: fg,
                bg_color: bg,
            }),
        });

        if (!res.ok) throw new Error("Download failed");

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `barcode-${symbology}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert("Failed to download: " + err.message);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied payload to clipboard!");
    }).catch(() => {
        prompt("Copy payload:", text);
    });
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// --- Analytics & Auth (Preserved for JWT compatibility) ---
const PALETTE = { primary: "#5b5ff0", primaryLight: "rgba(91,95,240,0.15)", categories: ["#5b5ff0", "#22c3a6", "#f5a623", "#ef476f", "#118ab2"] };
let chartDailyInstance = null;
let chartDevicesInstance = null;

function getToken() { return localStorage.getItem("qr_access_token"); }
function saveToken() {
    const token = document.getElementById("token-input").value.trim();
    if (!token) return;
    localStorage.setItem("qr_access_token", token);
    initAnalytics();
}

async function initAnalytics() {
    const token = getToken();
    if (!token) {
        document.getElementById("token-gate").style.display = "block";
        document.getElementById("app-view").style.display = "none";
        return;
    }
    document.getElementById("token-gate").style.display = "none";
    document.getElementById("app-view").style.display = "block";

    try {
        const res = await fetch("/stats", {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            document.getElementById("stat-total").textContent = data.summary?.total ?? 0;
            document.getElementById("stat-last24").textContent = data.summary?.last_24h ?? 0;

            if (data.daily && document.getElementById("chart-daily") && typeof Chart !== "undefined") {
                if (chartDailyInstance) chartDailyInstance.destroy();
                chartDailyInstance = new Chart(document.getElementById("chart-daily"), {
                    type: "line",
                    data: {
                        labels: data.daily.map(d => d.day.slice(5)),
                        datasets: [{
                            data: data.daily.map(d => d.count),
                            borderColor: PALETTE.primary,
                            backgroundColor: PALETTE.primaryLight,
                            fill: true,
                            tension: 0.35,
                        }],
                    },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
                });
            }

            if (data.devices && data.devices.length && document.getElementById("chart-devices") && typeof Chart !== "undefined") {
                if (chartDevicesInstance) chartDevicesInstance.destroy();
                chartDevicesInstance = new Chart(document.getElementById("chart-devices"), {
                    type: "doughnut",
                    data: {
                        labels: data.devices.map(d => d.device_type),
                        datasets: [{
                            data: data.devices.map(d => d.count),
                            backgroundColor: PALETTE.categories,
                            borderWidth: 0,
                        }],
                    },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, cutout: "60%" },
                });
            }
        }

        const codesRes = await fetch("/codes", {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (codesRes.ok) {
            const codes = await codesRes.json();
            const countEl = document.getElementById("stat-count");
            if (countEl) countEl.textContent = codes.length;

            const codeList = document.getElementById("code-list");
            if (codeList) {
                codeList.innerHTML = "";
                if (codes.length === 0) {
                    codeList.innerHTML = `<p class="muted">No saved QR codes for this tenant yet.</p>`;
                } else {
                    for (const c of codes) {
                        const item = document.createElement("div");
                        item.className = "barcode-item";
                        item.innerHTML = `
                            <div>
                                <span class="badge">${c.type}</span>
                                <div class="barcode-data">ID #${c.id} &middot; Created ${new Date(c.created_at).toLocaleDateString()}</div>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <a class="copy-btn" href="${c.image_url}" target="_blank" style="text-decoration:none;">PNG</a>
                                <a class="copy-btn" href="${c.svg_url}" target="_blank" style="text-decoration:none;">SVG</a>
                            </div>
                        `;
                        codeList.appendChild(item);
                    }
                }
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
    previewGeneratedBarcode();
});
