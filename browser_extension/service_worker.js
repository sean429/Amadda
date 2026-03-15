const API_URL = "http://127.0.0.1:8765/browser/snapshot";

async function collectCurrentWindowTabs() {
  const tabs = await chrome.tabs.query({ currentWindow: true });
  return tabs
    .filter((tab) => Boolean(tab.url))
    .map((tab) => ({
      url: tab.url,
      title: tab.title || tab.url,
      active: Boolean(tab.active),
    }));
}

async function sendSnapshot() {
  const tabs = await collectCurrentWindowTabs();
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      browser: "chrome",
      tabs,
    }),
  });

  if (!response.ok) {
    throw new Error(`Amadda backend returned ${response.status}`);
  }

  return response.json();
}

async function setBadge(text, color) {
  await chrome.action.setBadgeText({ text });
  await chrome.action.setBadgeBackgroundColor({ color });
}

chrome.action.onClicked.addListener(async () => {
  try {
    const result = await sendSnapshot();
    console.log("Amadda browser snapshot saved:", result);
    await setBadge("OK", "#2d8a34");
  } catch (error) {
    console.error("Amadda browser snapshot failed:", error);
    await setBadge("ERR", "#b42318");
  }

  setTimeout(() => {
    chrome.action.setBadgeText({ text: "" });
  }, 3000);
});
