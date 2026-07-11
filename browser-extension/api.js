/** Talk to the local cotp-web HTTP API. */

import { storageSyncGet } from "./browser.js";

export async function getServerConfig() {
  const stored = await storageSyncGet({
    cotpHost: "127.0.0.1",
    cotpPort: 8765,
  });
  return {
    host: stored.cotpHost,
    port: Number(stored.cotpPort),
  };
}

export function baseUrl(host, port) {
  return `http://${host}:${port}`;
}

export async function pingServer() {
  const { host, port } = await getServerConfig();
  const url = `${baseUrl(host, port)}/api/entries`;
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `cotp-web returned ${res.status}`);
  }
  return res.json();
}

export async function loadEntries() {
  const payload = await pingServer();
  return payload.entries || [];
}

async function copyValue(entryId, kind) {
  const { host, port } = await getServerConfig();
  const url = `${baseUrl(host, port)}/api/copy/${kind}/${encodeURIComponent(entryId)}`;
  const res = await fetch(url, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.error || `copy ${kind} failed (${res.status})`);
  }
  return body.value;
}

export async function loadCredentials(entryId, hasOtp) {
  const username = await copyValue(entryId, "username");
  const password = await copyValue(entryId, "password");
  let otp = null;
  if (hasOtp) {
    try {
      otp = await copyValue(entryId, "otp");
    } catch {
      otp = null;
    }
  }
  return { username, password, otp };
}
