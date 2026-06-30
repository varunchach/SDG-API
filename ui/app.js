const API = "";

let currentInitiate = null;
let pollTimer = null;
let activeOrcId = null;
let expectedCallbacks = [];

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

function syncFormToInitiate() {
  if (!currentInitiate) return;
  const g = (id, path, transform = (v) => v) => {
    const el = document.getElementById(id);
    if (!el) return;
    const val = transform(el.value);
    setNested(currentInitiate, path, val);
  };
  g("partnerJourneyID", "contextParameter.partnerJourneyID");
  g("bankJourneyID", "contextParameter.bankJourneyID");
  g("fName", "applicant.customerDemog.name[0].fName", (v) => v.toUpperCase());
  g("mName", "applicant.customerDemog.name[0].mName", (v) => v.toUpperCase());
  g("lName", "applicant.customerDemog.name[0].lName", (v) => v.toUpperCase());
  g("dob", "applicant.customerDemog.dob");
  g("gender", "applicant.customerDemog.gender");
  g("panNo", "applicant.customerDemog.ids.panNo", (v) => v.toUpperCase());
  g("emailId1", "applicant.customerDemog.emailId1");
  g("address1", "applicant.customerDemog.address[0].address1");
  g("city", "applicant.customerDemog.address[0].city", (v) => v.toUpperCase());
  g("state", "applicant.customerDemog.address[0].state", (v) => v.toUpperCase());
  g("pinCode", "applicant.customerDemog.address[0].pinCode");
  g("loanAmount", "applicant.bankingDetails.loanDetails.loanAmount");
  $("#json-editor").value = JSON.stringify(currentInitiate, null, 2);
}

function syncInitiateToForm() {
  if (!currentInitiate) return;
  const get = (path) => getNested(currentInitiate, path) ?? "";
  $("#partnerJourneyID").value = get("contextParameter.partnerJourneyID");
  $("#bankJourneyID").value = get("contextParameter.bankJourneyID");
  $("#fName").value = get("applicant.customerDemog.name[0].fName");
  $("#mName").value = get("applicant.customerDemog.name[0].mName");
  $("#lName").value = get("applicant.customerDemog.name[0].lName");
  $("#dob").value = get("applicant.customerDemog.dob");
  $("#gender").value = get("applicant.customerDemog.gender") || "M";
  $("#panNo").value = get("applicant.customerDemog.ids.panNo");
  $("#emailId1").value = get("applicant.customerDemog.emailId1");
  $("#address1").value = get("applicant.customerDemog.address[0].address1");
  $("#city").value = get("applicant.customerDemog.address[0].city");
  $("#state").value = get("applicant.customerDemog.address[0].state");
  $("#pinCode").value = get("applicant.customerDemog.address[0].pinCode");
  $("#loanAmount").value = get("applicant.bankingDetails.loanDetails.loanAmount");
  $("#json-editor").value = JSON.stringify(currentInitiate, null, 2);
}

function setNested(obj, path, value) {
  const parts = path.replace(/\[(\d+)\]/g, ".$1").split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    cur = cur[parts[i]];
  }
  cur[parts[parts.length - 1]] = value;
}

function getNested(obj, path) {
  const parts = path.replace(/\[(\d+)\]/g, ".$1").split(".");
  let cur = obj;
  for (const p of parts) {
    if (cur == null) return undefined;
    cur = cur[p];
  }
  return cur;
}

async function loadScenarios() {
  const data = await api("/api/scenarios");
  const sel = $("#scenario");
  sel.innerHTML = data.scenarios
    .map((s) => `<option value="${s}">${s}</option>`)
    .join("");
}

async function loadRecords() {
  const data = await api("/api/records");
  const sel = $("#record-select");
  if (!data.records.length) {
    sel.innerHTML = '<option value="">No records — run generate_customers.py</option>';
    return;
  }
  sel.innerHTML =
    '<option value="">— pick a generated record —</option>' +
    data.records
      .map(
        (r) =>
          `<option value="${r.recordId}">${r.recordId} · ${r.fullName} · ${r.scenario}</option>`
      )
      .join("");
}

async function onRecordSelect() {
  const id = $("#record-select").value;
  if (!id) return;
  setError(null);
  const rec = await api(`/api/records/${id}`);
  currentInitiate = JSON.parse(JSON.stringify(rec.initiateRequest));
  $("#scenario").value = rec.scenario;
  syncInitiateToForm();
}

function onJsonBlur() {
  try {
    currentInitiate = JSON.parse($("#json-editor").value);
    syncInitiateToForm();
    setError(null);
  } catch (e) {
    setError("Invalid JSON in editor: " + e.message);
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
        const next = callbackOrder[received.length];
        if (next === rt) dotClass = "active";
      }
      const payload = window._callbacks?.[rt];
      return `<li>
        <div class="status-dot ${dotClass}">${has ? "✓" : "·"}</div>
        <div>
          <div class="callback-title">${rt}</div>
          <div class="callback-meta">${has ? "Received" : "Pending"} · reportType: ${rt}</div>
          ${
            has
              ? `<button type="button" class="toggle-json" data-rt="${rt}">Show JSON</button>
                 <div class="callback-json" id="json-${rt}"><pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre></div>`
              : ""
          }
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
}

function renderSummary(summaryCb) {
  const s = summaryCb.applicant?.summary || {};
  const grid = Object.entries(s)
    .map(
      ([k, v]) =>
        `<div class="summary-item"><span class="key">${k}</span><span class="val ${v === "Failed" ? "failed" : "success"}">${v}</span></div>`
    )
    .join("");
  $("#summary-card").innerHTML = `<div class="summary-card"><strong>Eligibility Summary</strong><div class="summary-grid">${grid}</div></div>`;
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function pollJourney(orcId) {
  try {
    const data = await api(`/api/journey/${orcId}`);
    window._callbacks = data.callbacks;
    $("#journey-status").textContent = data.status;
    $("#callbacks-received").textContent = `${data.callbacksReceived.length} / ${data.callbackOrder.length}`;
    renderTimeline(data.callbackOrder, data.callbacksReceived, data.status);
    if (data.status === "COMPLETED") {
      clearInterval(pollTimer);
      pollTimer = null;
      $("#submit-btn").disabled = false;
    }
  } catch (e) {
    console.error(e);
  }
}

async function submitInitiate() {
  setError(null);
  syncFormToInitiate();
  let initiateRequest;
  try {
    initiateRequest = JSON.parse($("#json-editor").value);
  } catch (e) {
    setError("Invalid initiate JSON: " + e.message);
    return;
  }

  $("#submit-btn").disabled = true;
  $("#response-panel .panel-body").innerHTML = `<p>Sending initiate request…</p>`;

  try {
    const scenario = $("#scenario").value;
    const result = await api("/api/journey/initiate", {
      method: "POST",
      body: JSON.stringify({ initiateRequest, scenario }),
    });

    activeOrcId = result.orcJourneyID;
    expectedCallbacks = result.callbackOrder;

    $("#response-panel .panel-body").innerHTML = `
      <div class="meta-bar">
        <span><strong>orcJourneyID:</strong> <code>${result.orcJourneyID}</code></span>
        <span><strong>Scenario:</strong> ${result.scenario}</span>
        <span><strong>Callback delay:</strong> ${result.callbackDelaySeconds}s each</span>
        <span><strong>Status:</strong> <span id="journey-status">INITIATED</span></span>
        <span><strong>Callbacks:</strong> <span id="callbacks-received">0 / ${result.callbackOrder.length}</span></span>
      </div>
      <div class="ack-box">
        <h3>Sync ACK Response</h3>
        <pre>${escapeHtml(JSON.stringify(result.ackResponse, null, 2))}</pre>
      </div>
      <h3 style="font-size:0.9rem;margin:0 0 0.5rem">Async Producer Callbacks</h3>
      <ul class="timeline" id="callback-timeline"></ul>
      <div id="summary-card"></div>
    `;

    window._callbacks = {};
    renderTimeline(result.callbackOrder, [], "INITIATED");
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => pollJourney(activeOrcId), 1500);
    pollJourney(activeOrcId);
  } catch (e) {
    setError(String(e.message || e));
    $("#submit-btn").disabled = false;
  }
}

function wireForm() {
  [
    "partnerJourneyID",
    "bankJourneyID",
    "fName",
    "mName",
    "lName",
    "dob",
    "gender",
    "panNo",
    "emailId1",
    "address1",
    "city",
    "state",
    "pinCode",
    "loanAmount",
  ].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", syncFormToInitiate);
  });
  $("#json-editor").addEventListener("blur", onJsonBlur);
  $("#record-select").addEventListener("change", onRecordSelect);
  $("#submit-btn").addEventListener("click", submitInitiate);
  $("#quick-submit").addEventListener("click", async () => {
    const id = $("#record-select").value;
    if (!id) {
      setError("Select a generated record first");
      return;
    }
    await onRecordSelect();
    await submitInitiate();
  });
}

async function init() {
  wireForm();
  await Promise.all([loadScenarios(), loadRecords()]);
  const health = await api("/api/health");
  $("#delay-hint").textContent = `Callbacks fire every ${health.callbackDelaySeconds}s (set CALLBACK_DELAY_SECONDS=120 for spec 2min)`;
}

init();
