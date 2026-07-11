/**
 * Fill login forms on the active tab (Teleport and generic login pages).
 */

const ext = globalThis.browser ?? globalThis.chrome;

function setNativeValue(element, value) {
  const proto =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
  if (descriptor?.set) {
    descriptor.set.call(element, value);
  } else {
    element.value = value;
  }
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function isVisible(element) {
  if (!element || element.disabled || element.readOnly) {
    return false;
  }
  const style = window.getComputedStyle(element);
  return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
}

function queryVisible(selector) {
  return [...document.querySelectorAll(selector)].find(isVisible) || null;
}

function findUsernameField() {
  const selectors = [
    'input[autocomplete="username"]',
    'input[name="user"]',
    'input[name="username"]',
    'input[id="username"]',
    'input[data-testid="username"]',
    'input[placeholder*="user" i]',
    'input[type="email"]',
  ];
  for (const selector of selectors) {
    const field = queryVisible(selector);
    if (field) {
      return field;
    }
  }
  const password = findPasswordField();
  const textInputs = [...document.querySelectorAll('input[type="text"], input:not([type])')].filter(
    isVisible,
  );
  if (password) {
    const beforePassword = textInputs.find((el) => {
      return (
        (el.compareDocumentPosition(password) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0 &&
        el !== password
      );
    });
    if (beforePassword) {
      return beforePassword;
    }
  }
  return textInputs[0] || null;
}

function findPasswordField() {
  return queryVisible('input[autocomplete="current-password"]') || queryVisible('input[type="password"]');
}

function findOtpField() {
  const selectors = [
    'input[autocomplete="one-time-code"]',
    'input[name="otp"]',
    'input[name="totp"]',
    'input[name="mfa"]',
    'input[id="otp"]',
    'input[data-testid="otp"]',
    'input[placeholder*="otp" i]',
    'input[placeholder*="authenticator" i]',
    'input[inputmode="numeric"]',
  ];
  for (const selector of selectors) {
    const field = queryVisible(selector);
    if (field && field.type !== "password") {
      return field;
    }
  }
  return null;
}

function findSubmitControl() {
  const explicit = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button[data-testid="submit"]',
    'button[data-testid="login"]',
  ];
  for (const selector of explicit) {
    const control = queryVisible(selector);
    if (control) {
      return control;
    }
  }

  const labels = [
    "sign in",
    "log in",
    "login",
    "continue",
    "next",
    "submit",
    "authenticate",
  ];
  const buttons = [...document.querySelectorAll("button, input[type='button'], a[role='button']")].filter(
    isVisible,
  );
  for (const button of buttons) {
    const text = (button.innerText || button.value || "").trim().toLowerCase();
    if (labels.some((label) => text === label || text.includes(label))) {
      return button;
    }
  }
  return buttons[0] || null;
}

function fillCredentials(credentials) {
  const filled = { username: false, password: false, otp: false, submitted: false };
  const usernameField = findUsernameField();
  const passwordField = findPasswordField();
  const otpField = credentials.otp ? findOtpField() : null;

  if (usernameField && credentials.username) {
    setNativeValue(usernameField, credentials.username);
    filled.username = true;
  }
  if (passwordField && credentials.password) {
    setNativeValue(passwordField, credentials.password);
    filled.password = true;
  }
  if (otpField && credentials.otp) {
    setNativeValue(otpField, credentials.otp);
    filled.otp = true;
  }

  const submit = findSubmitControl();
  if (submit) {
    submit.click();
    filled.submitted = true;
  }
  return filled;
}

ext.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "COTP_FILL") {
    return false;
  }
  try {
    const result = fillCredentials(message.credentials);
    sendResponse({ ok: true, result });
  } catch (error) {
    sendResponse({ ok: false, error: String(error?.message || error) });
  }
  return true;
});
