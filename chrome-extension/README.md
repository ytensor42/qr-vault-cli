# cotp fill — Chrome extension

Fill **username**, **password**, and **OTP** on the active browser tab from a running [**cotp-web**](../README.md) server. Pick an entry in the popup; the extension does not map URLs to vault entries (same login URL, many users is fine).

## Prerequisites

1. **cotp-web** running locally (foreground or 1-hour background):

   ```bash
   cotp-web cotp-web.yaml
   # answer y to: Run in background for 1 hour?
   ```

2. Default API: `http://127.0.0.1:8765`

## Install (unpacked)

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select this `chrome-extension/` folder
4. Pin **cotp fill** to the toolbar

Change the port in the popup footer if cotp-web uses a non-default port.

After editing extension files, open `chrome://extensions` and click **Reload** on **cotp fill** (reopening the popup alone is not enough).

## Usage (e.g. Teleport)

1. Open the login page in a tab
2. Click the extension icon
3. Choose **account / username** from the list
4. The extension fills visible fields and clicks the primary **Sign in / Continue / Log in** control

If the page was open before installing the extension, **reload the tab** once so the content script loads.

## Limits

- **One-shot fill:** If Teleport uses a separate MFA step after password, you may need to click the entry again on the OTP screen.
- **Heuristic selectors:** Works on common login forms (including many Teleport layouts); unusual UIs may need selector tweaks in `content.js`.
- **Chrome only** in this folder (Firefox/Safari need separate packaging).

## Security

- Talks only to `127.0.0.1` / `localhost`
- Secrets are fetched from cotp-web only when you click an entry
- No vault file access from the extension
