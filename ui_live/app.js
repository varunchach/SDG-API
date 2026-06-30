const API = "";

let currentInitiate = null;
let currentScenario = "clean-approval";
const PRODUCER_ORDER = [
  "mbCibil", "mbEquifax", "mbHighMark", "mbMbEot", "perfios", "posidex", "hunter", "summary",
];

let selectedProducer = null;
let producerHighlightsMap = {};
let pollTimer = null;
let activeOrcId = null;

const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  return res.json();
}

function setError(msg) {
  const el = $("#error-banner");
  if (msg) {
    el.textContent = msg;
    el.classList.add("show");
  } else {
    el.classList.remove("show");
  }
}

function showStep2(show) {
  $("#step2-header").classList.toggle("hidden", !show);
  $("#step2-body").classList.toggle("hidden", !show);
  $("#btn-submit").disabled = !show || !currentInitiate;
  $("#btn-download-json").classList.toggle("hidden", !show || !currentInitiate);
}

function downloadBlob(filename, content, mime = "application/octet-stream") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function downloadInitiateJson() {
  if (!currentInitiate) return;
  const pan = currentInitiate.applicant?.customerDemog?.ids?.panNo || "initiate";
  downloadBlob(
    `initiate-request-${pan}.json`,
    JSON.stringify(currentInitiate, null, 2),
    "application/json"
  );
}

async function downloadCsv() {
  const res = await fetch(`${API}/api/export/csv`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "CSV not available");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "eligibility-records.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function downloadJourneyJson(orcId) {
  const data = await api(`/api/journey/${orcId}/export`);
  downloadBlob(
    `journey-${orcId}.json`,
    JSON.stringify(data, null, 2),
    "application/json"
  );
}

function renderDownloadActions(orcId, csvSaved) {
  const existing = document.getElementById("download-actions");
  if (existing) existing.remove();
  const bar = document.createElement("div");
  bar.id = "download-actions";
  bar.className = "actions";
  bar.style.marginTop = "0.75rem";
  bar.innerHTML = `
    <button type="button" id="btn-dl-journey" class="btn-secondary">Download Journey JSON</button>
    ${csvSaved ? `<button type="button" id="btn-dl-csv" class="btn-secondary">Download CSV</button>` : ""}
  `;
  $("#response-panel .panel-body").appendChild(bar);
  document.getElementById("btn-dl-journey")?.addEventListener("click", () =>
    downloadJourneyJson(orcId).catch((e) => setError(e.message))
  );
  document.getElementById("btn-dl-csv")?.addEventListener("click", () =>
    downloadCsv().catch((e) => setError(e.message))
  );
}

function renderGeneratedSummary(details) {
  const a = details.applicant;
  const co = details.coApplicant;
  const j = details.journey;
  const addr = a.address;

  $("#generated-summary").innerHTML = `
    <div class="summary-section">
      <h3>Applicant (your input + synthetic fields)</h3>
      <div class="detail-grid">
        <div><span class="lbl">Name</span><span class="val">${a.name.fName} ${a.name.mName || ""} ${a.name.lName}</span></div>
        <div><span class="lbl">DOB / Age</span><span class="val">${a.dob} (${a.age} yrs, ${a.gender})</span></div>
        <div><span class="lbl">PAN</span><span class="val">${a.panNo}</span></div>
        <div><span class="lbl">Mobile</span><span class="val">${a.mobile}</span></div>
        <div><span class="lbl">Email</span><span class="val">${a.emailId1}</span></div>
        <div><span class="lbl">Employer</span><span class="val">${a.employerName}</span></div>
        <div><span class="lbl">Loan</span><span class="val">₹${Number(a.loanAmount).toLocaleString("en-IN")}</span></div>
        <div class="full"><span class="lbl">Address</span><span class="val">${addr.address1}, ${addr.address2}${addr.address3 ? ", " + addr.address3 : ""}, ${addr.city} ${addr.state} ${addr.pinCode}</span></div>
      </div>
    </div>
    <div class="summary-section">
      <h3>Co-applicant (fully synthetic)</h3>
      <div class="detail-grid">
        <div><span class="lbl">Name</span><span class="val">${co.name.fName} ${co.name.lName}</span></div>
        <div><span class="lbl">PAN</span><span class="val">${co.panNo}</span></div>
        <div class="full"><span class="lbl">Address</span><span class="val">${co.address.address1}, ${co.address.city} ${co.address.state}</span></div>
      </div>
    </div>
    <div class="summary-section">
      <h3>Journey IDs (synthetic)</h3>
      <div class="detail-grid">
        <div><span class="lbl">partnerJourneyID</span><span class="val">${j.partnerJourneyID}</span></div>
        <div><span class="lbl">bankJourneyID</span><span class="val">${j.bankJourneyID}</span></div>
      </div>
    </div>
  `;
}

async function loadScenarios() {
  const data = await api("/api/scenarios");
  $("#scenario").innerHTML = data.scenarios.map((s) => `<option value="${s}">${s}</option>`).join("");
}

async function loadStorageInfo() {
  const h = await api("/api/health");
  const s = h.csvStorage;
  $("#storage-info").textContent =
    s.backend === "s3"
      ? `CSV export → S3/MinIO: ${s.bucket}/${s.objectKey}`
      : `CSV export → ${s.path}`;
  $("#delay-hint").textContent = `Callbacks fire every ${h.callbackDelaySeconds}s each`;
}

function validateIdentityInput() {
  const name = $("#fullName").value.trim();
  const dob = $("#dob").value;
  const pan = $("#panNo").value.trim().toUpperCase();
  if (!name) throw new Error("Name is required");
  if (!dob) throw new Error("DOB is required");
  if (!pan) throw new Error("PAN is required");
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan)) throw new Error("PAN must match format AAAAA9999A");
  return { name, dob, panNo: pan };
}

async function buildEeRequest() {
  setError(null);
  let identity;
  try {
    identity = validateIdentityInput();
  } catch (e) {
    setError(e.message);
    return;
  }

  $("#btn-build").disabled = true;
  $("#btn-build").textContent = "Building…";

  try {
    const scenario = $("#scenario").value;
    const data = await api("/api/initiate-request/build", {
      method: "POST",
      body: JSON.stringify({ ...identity, scenario }),
    });

    currentInitiate = data.initiateRequest;
    currentScenario = data.scenario;
    $("#json-editor").value = JSON.stringify(currentInitiate, null, 2);
    renderGeneratedSummary(data.generatedDetails);
    showStep2(true);
    setError(null);
  } catch (e) {
    setError(String(e.message || e));
    showStep2(false);
  } finally {
    $("#btn-build").disabled = false;
    $("#btn-build").textContent = "Build EE Request";
  }
}

function renderTimeline(callbackOrder, received, status) {
  const ul = $("#callback-timeline");
  ul.innerHTML = callbackOrder
    .map((rt) => {
      const has = received.includes(rt);
      const isSummary = rt === "summary";
      let dotClass = has ? (isSummary ? "summary-done" : "done") : "pending";
      if (!has && status === "IN_PROGRESS" && received.length < callbackOrder.length) {
        if (callbackOrder[received.length] === rt) dotClass = "active";
      }
      const payload = window._callbacks?.[rt];
      return `<li>
        <div class="status-dot ${dotClass}">${has ? "✓" : "·"}</div>
        <div>
          <div class="callback-title">${rt}</div>
          <div class="callback-meta">${has ? "Received" : "Pending"}</div>
          ${has ? `<button type="button" class="toggle-json" data-rt="${rt}">Show JSON</button>
            <div class="callback-json" id="json-${rt}"><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></div>` : ""}
        </div>
      </li>`;
    })
    .join("");
  ul.querySelectorAll(".toggle-json").forEach((btn) => {
    btn.addEventListener("click", () => {
      const box = document.getElementById(`json-${btn.dataset.rt}`);
      const open = box.classList.toggle("open");
      btn.textContent = open ? "Hide JSON" : "Show JSON";
    });
  });
  if (received.includes("summary") && window._callbacks?.summary) {
    renderSummary(window._callbacks.summary);
  }
  updateProducerInvestigation(received);
}

function updateProducerInvestigation(received) {
  const wrap = document.getElementById("producer-investigation");
  const select = document.getElementById("producer-select");
  if (!wrap || !select) return;

  const available = PRODUCER_ORDER.filter((rt) => received.includes(rt) && producerHighlightsMap[rt]);
  if (!available.length) {
    wrap.classList.add("hidden");
    return;
  }

  wrap.classList.remove("hidden");
  const prev = select.value;
  select.innerHTML = available
    .map((rt) => {
      const title = producerHighlightsMap[rt]?.title || rt;
      return `<option value="${rt}">${title}</option>`;
    })
    .join("");

  if (prev && available.includes(prev)) {
    select.value = prev;
  } else if (selectedProducer && available.includes(selectedProducer)) {
    select.value = selectedProducer;
  } else {
    select.value = available[0];
  }
  selectedProducer = select.value;
  renderProducerHighlights(producerHighlightsMap[selectedProducer]);
}

function renderProducerHighlights(highlights) {
  const el = document.getElementById("producer-highlights-body");
  if (!el || !highlights) return;
  const rows = highlights.fields
    .map((f) => {
      const matchCell =
        f.match === true
          ? '<span class="match-yes">✓ Match</span>'
          : f.match === false
            ? '<span class="match-no">✗ Mismatch</span>'
            : '<span class="match-na">—</span>';
      return `<tr>
        <td>${escapeHtml(f.label)}</td>
        <td>${escapeHtml(String(f.initiate))}</td>
        <td>${escapeHtml(String(f.output))}</td>
        <td>${matchCell}</td>
      </tr>`;
    })
    .join("");
  el.innerHTML = `
    <p class="producer-meta">${highlights.matchedCount} / ${highlights.comparableCount} comparable fields match initiate input</p>
    <table class="producer-table">
      <thead><tr><th>Field</th><th>Initiate (input)</th><th>Producer (output)</th><th>Check</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderSummary(summaryCb) {
  const s = summaryCb.applicant?.summary || {};
  const grid = Object.entries(s)
    .map(([k, v]) => `<div class="summary-item"><span class="key">${k}</span><span class="val ${v === "Failed" ? "failed" : "success"}">${v}</span></div>`)
    .join("");
  $("#summary-card").innerHTML = `<div class="summary-card"><strong>Eligibility Summary</strong><div class="summary-grid">${grid}</div></div>`;
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function pollJourney(orcId) {
  const data = await api(`/api/journey/${orcId}`);
  window._callbacks = data.callbacks;
  $("#journey-status").textContent = data.status;
  $("#callbacks-received").textContent = `${data.callbacksReceived.length} / ${data.callbackOrder.length}`;
  renderTimeline(data.callbackOrder, data.callbacksReceived, data.status);
  if (data.producerHighlights) {
    producerHighlightsMap = data.producerHighlights;
    updateProducerInvestigation(data.callbacksReceived);
  }
  if (data.csvSaved) {
    $("#csv-status").innerHTML = `Saved to CSV. <a href="#" id="csv-dl-link">Download CSV</a>`;
    $("#csv-status").classList.add("show");
    document.getElementById("csv-dl-link")?.addEventListener("click", (e) => {
      e.preventDefault();
      downloadCsv().catch((err) => setError(err.message));
    });
  }
  if (data.status === "COMPLETED") {
    clearInterval(pollTimer);
    $("#btn-submit").disabled = false;
    renderDownloadActions(orcId, data.csvSaved);
  }
}

async function submitInitiate() {
  if (!currentInitiate) {
    setError("Build EE Request first");
    return;
  }
  setError(null);

  $("#btn-submit").disabled = true;
  $("#response-panel .panel-body").innerHTML = `<p>Sending initiate request…</p>`;

  try {
    const result = await api("/api/journey/initiate", {
      method: "POST",
      body: JSON.stringify({ initiateRequest: currentInitiate, scenario: currentScenario }),
    });

    activeOrcId = result.orcJourneyID;
    $("#response-panel .panel-body").innerHTML = `
      <div class="meta-bar">
        <span><strong>recordId:</strong> ${result.recordId}</span>
        <span><strong>orcJourneyID:</strong> <code>${result.orcJourneyID}</code></span>
        <span><strong>Scenario:</strong> ${result.scenario}</span>
        <span><strong>Status:</strong> <span id="journey-status">INITIATED</span></span>
        <span><strong>Callbacks:</strong> <span id="callbacks-received">0 / ${result.callbackOrder.length}</span></span>
      </div>
      <div id="csv-status" class="csv-status"></div>
      <div class="ack-box">
        <h3>Sync ACK Response</h3>
        <pre>${escapeHtml(JSON.stringify(result.ackResponse, null, 2))}</pre>
      </div>
      <h3 style="font-size:0.9rem;margin:0 0 0.5rem">Async Producer Callbacks</h3>
      <ul class="timeline" id="callback-timeline"></ul>
      <div id="producer-investigation" class="producer-investigation hidden">
        <div class="producer-investigation-header">
          <h3>Producer Field Investigation</h3>
          <label class="producer-select-label">
            Producer system
            <select id="producer-select"></select>
          </label>
        </div>
        <div id="producer-highlights-body"></div>
      </div>
      <div id="summary-card"></div>
    `;
    window._callbacks = {};
    producerHighlightsMap = {};
    selectedProducer = null;
    renderTimeline(result.callbackOrder, [], "INITIATED");
    document.getElementById("producer-select")?.addEventListener("change", (e) => {
      selectedProducer = e.target.value;
      renderProducerHighlights(producerHighlightsMap[selectedProducer]);
    });
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => pollJourney(activeOrcId), 1500);
    pollJourney(activeOrcId);
  } catch (e) {
    setError(String(e.message || e));
    $("#btn-submit").disabled = false;
  }
}

function wireForm() {
  $("#btn-build").addEventListener("click", () => buildEeRequest().catch((e) => setError(e.message)));
  $("#btn-submit").addEventListener("click", submitInitiate);
  $("#btn-download-json").addEventListener("click", downloadInitiateJson);
  $("#btn-rebuild").addEventListener("click", () => {
    showStep2(false);
    currentInitiate = null;
    setError(null);
  });
  $("#panNo").addEventListener("input", (e) => {
    e.target.value = e.target.value.toUpperCase();
  });
  ["fullName", "dob", "panNo"].forEach((id) => {
    document.getElementById(id)?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") buildEeRequest().catch((err) => setError(err.message));
    });
  });
}

wireForm();
loadScenarios().then(loadStorageInfo).catch((e) => setError(e.message));
