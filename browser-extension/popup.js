import { getServerConfig, loadCredentials, loadEntries } from "./api.js";
import { isRestrictedTabUrl, storageSyncSet, tabs } from "./browser.js";

const statusEl = document.getElementById("status");
const statusDot = document.getElementById("status-dot");
const entriesEl = document.getElementById("entries");
const portEl = document.getElementById("port");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status err" : "status";
  statusDot.className = `status-dot${isError ? " err" : text ? " ok" : ""}`;
}

function renderEntries(entries) {
  entriesEl.replaceChildren();
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No entries in cotp-web.";
    entriesEl.append(empty);
    return;
  }

  const table = document.createElement("table");
  table.className = "entries-table";

  const colgroup = document.createElement("colgroup");
  for (const name of ["col-account", "col-user", "col-otp"]) {
    const col = document.createElement("col");
    col.className = name;
    colgroup.append(col);
  }
  table.append(colgroup);

  const tbody = document.createElement("tbody");
  for (const entry of entries) {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.dataset.entryId = entry.id;
    row.dataset.hasOtp = entry.has_otp ? "1" : "0";

    const keyCell = document.createElement("td");
    keyCell.className = "col-account";
    const keyText = entry.key || entry.id.split(".")[0] || "";
    const keySpan = document.createElement("span");
    keySpan.className = "entry-key";
    keySpan.textContent = keyText;
    keySpan.title = keyText;
    keyCell.append(keySpan);

    const userCell = document.createElement("td");
    userCell.className = "col-user";
    const userText = entry.username || entry.id.split(".").slice(1).join(".") || entry.id;
    const userSpan = document.createElement("span");
    userSpan.className = "entry-user";
    userSpan.textContent = userText;
    userSpan.title = userText;
    userCell.append(userSpan);

    const otpCell = document.createElement("td");
    if (entry.has_otp) {
      const otpSpan = document.createElement("span");
      otpSpan.className = "entry-otp";
      otpSpan.textContent = "OTP";
      otpCell.append(otpSpan);
    }

    if (entry.error) {
      row.title = entry.error;
      row.style.opacity = "0.55";
    } else {
      row.addEventListener("click", () => fillEntry(row, entry));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          fillEntry(row, entry);
        }
      });
    }

    row.append(keyCell, userCell, otpCell);
    tbody.append(row);
  }
  table.append(tbody);
  entriesEl.append(table);
}

async function fillEntry(row, entry) {
  row.classList.add("is-busy");
  setStatus(`Filling ${entry.username || entry.id}…`);
  try {
    const [tab] = await tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) {
      throw new Error("No active tab.");
    }
    if (isRestrictedTabUrl(tab.url)) {
      throw new Error("Open a login page first.");
    }

    const credentials = await loadCredentials(entry.id, Boolean(entry.has_otp));
    const response = await tabs.sendMessage(tab.id, {
      type: "COTP_FILL",
      credentials,
    });

    if (!response?.ok) {
      throw new Error(response?.error || "Fill failed on page.");
    }

    const parts = [];
    if (response.result.username) parts.push("user");
    if (response.result.password) parts.push("pwd");
    if (response.result.otp) parts.push("otp");
    if (response.result.submitted) parts.push("submit");
    setStatus(parts.length ? `Done: ${parts.join(", ")}` : "No matching fields on page.");
    window.close();
  } catch (error) {
    const message = String(error?.message || error);
    if (message.includes("Could not establish connection")) {
      setStatus("Reload the login page, then try again.", true);
    } else {
      setStatus(message, true);
    }
  } finally {
    row.classList.remove("is-busy");
  }
}

async function refresh() {
  setStatus("Connecting…");
  statusDot.className = "status-dot";
  try {
    const entries = await loadEntries();
    renderEntries(entries);
    const { host, port } = await getServerConfig();
    setStatus(`${entries.length} entries · ${host}:${port}`);
  } catch (error) {
    renderEntries([]);
    setStatus(
      "cotp-web not reachable. Run: cotp-web cotp-web.yaml (or -t 60 for background)",
      true,
    );
  }
}

async function init() {
  const { port } = await getServerConfig();
  portEl.value = String(port);
  portEl.addEventListener("change", async () => {
    const value = Number(portEl.value);
    if (!Number.isFinite(value) || value < 1 || value > 65535) {
      return;
    }
    const config = await getServerConfig();
    await storageSyncSet({ cotpHost: config.host, cotpPort: value });
    refresh();
  });
  await refresh();
}

init();
