const API_URL = "http://127.0.0.1:8765/browser/snapshot";
const ALARM_NAME = "amadda-auto-snapshot";
const ALARM_PERIOD_MINUTES = 15;

async function collectCurrentWindowTabs() {
  const win = await chrome.windows.getLastFocused({
    populate: true,
    windowTypes: ["normal"],
  });
  if (!win || !win.tabs) return [];
  return win.tabs
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

function ensureAlarm() {
  chrome.alarms.get(ALARM_NAME, (alarm) => {
    if (!alarm) {
      chrome.alarms.create(ALARM_NAME, { periodInMinutes: ALARM_PERIOD_MINUTES });
      console.log(`Amadda: auto-snapshot alarm set (every ${ALARM_PERIOD_MINUTES}min)`);
    }
  });
}

// 설치 및 업데이트 시 알람 등록
chrome.runtime.onInstalled.addListener(() => {
  ensureAlarm();
});

// service worker 재시작 시 알람 복원
chrome.runtime.onStartup.addListener(() => {
  ensureAlarm();
});

// 주기적 자동 전송
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  try {
    await sendSnapshot();
    console.log("Amadda: auto browser snapshot saved");
  } catch (error) {
    // 백엔드가 꺼져 있으면 조용히 실패
    console.warn("Amadda: auto browser snapshot skipped:", error.message);
  }
});

// 수동 클릭 (배지 피드백 포함)
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
