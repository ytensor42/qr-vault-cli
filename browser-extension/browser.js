/** Cross-browser WebExtension API (Chrome + Firefox). */

const api = globalThis.browser ?? globalThis.chrome;

if (!api) {
  throw new Error("WebExtension API not available");
}

export const runtime = api.runtime;
export const tabs = api.tabs;

export async function storageSyncGet(defaults) {
  return api.storage.sync.get(defaults);
}

export async function storageSyncSet(values) {
  return api.storage.sync.set(values);
}

export function isRestrictedTabUrl(url) {
  if (!url) {
    return true;
  }
  return (
    url.startsWith("chrome://")
    || url.startsWith("chrome-extension://")
    || url.startsWith("about:")
    || url.startsWith("moz-extension://")
  );
}
