# cotp fill — browser extension

Fill **username**, **password**, and **OTP** on the active browser tab from a running [**cotp-web**](../README.md) server. Pick an entry in the popup; the extension does not map URLs to vault entries (same login URL, many users is fine).

Works in **Chrome** and **Firefox** (Manifest V3).

## Prerequisites

1. **cotp-web** running locally:

   ```bash
   cotp-web cotp-web.yaml
   # or background: cotp-web cotp-web.yaml -t 60
   ```

2. Default API: `http://127.0.0.1:8765`

## Install — Chrome

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select this `browser-extension/` folder
4. Pin **cotp fill** to the toolbar

After editing extension files, click **Reload** on the extension card (reopening the popup alone is not enough).

## Install — Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Choose `manifest.json` inside this `browser-extension/` folder
4. Pin **cotp fill** from the toolbar extensions menu

Temporary add-ons are removed when Firefox quits; reload the same way after a restart or after code changes.

## Usage (e.g. Teleport)

1. Open the login page in a tab
2. Click the extension icon
3. Choose **account / username** from the list
4. The extension fills visible fields and clicks the primary **Sign in / Continue / Log in** control

If the page was open before installing the extension, **reload the tab** once so the content script loads.

Change the port in the popup footer if cotp-web uses a non-default port.

## Limits

- **One-shot fill:** If Teleport uses a separate MFA step after password, you may need to click the entry again on the OTP screen.
- **Heuristic selectors:** Works on common login forms (including many Teleport layouts); unusual UIs may need selector tweaks in `content.js`.

## Security

- Talks only to `127.0.0.1` / `localhost`
- Secrets are fetched from cotp-web only when you click an entry
- No vault file access from the extension
