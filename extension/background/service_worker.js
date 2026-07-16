const EXTENSION_VERSION = "1.0.0";
const SCHEMA_VERSION = "1.0";

let backendUrl = "";
let apiKey = "";
let extensionId = null;
let isRegistered = false;

// Queue of events to be sent to backend
let eventQueue = [];
let isFlushing = false;

// Track active content scripts (tabId -> { sessionId, url, timestamp })
let activeTabs = {};

// Initialize from storage
chrome.storage.local.get(['backendUrl', 'apiKey', 'eventQueue'], (result) => {
  backendUrl = result.backendUrl || "";
  apiKey = result.apiKey || "";
  eventQueue = result.eventQueue || [];
  
  if (backendUrl && apiKey) {
    registerWithBackend();
  }
});

// Listen for updates from options page or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SETTINGS_UPDATED") {
    chrome.storage.local.get(['backendUrl', 'apiKey'], (result) => {
      backendUrl = result.backendUrl || "";
      apiKey = result.apiKey || "";
      registerWithBackend();
    });
  } else if (message.type === "PRESENCE_EVENT") {
    handleNewEvent(message.payload);
  } else if (message.type === "GET_SESSION_STATUS") {
    sendResponse({ isRegistered, extensionId });
  } else if (message.type === "PING") {
    sendResponse({
      type: "PONG",
      extension_version: EXTENSION_VERSION,
      manifest_version: chrome.runtime.getManifest().manifest_version,
      build_version: chrome.runtime.getManifest().version,
      timestamp: Date.now(),
      active_tabs: activeTabs
    });
  } else if (message.type === "CONTENT_SCRIPT_READY") {
    if (sender.tab) {
      activeTabs[sender.tab.id] = {
        session_id: message.payload.session_id,
        url: sender.tab.url,
        timestamp: Date.now()
      };
      console.log(`KAIO: Content script ready on tab ${sender.tab.id} for session ${message.payload.session_id}`);
      sendResponse({ status: "ACK" });
    }
  }
});

// Clean up disconnected tabs
chrome.tabs.onRemoved.addListener((tabId) => {
  if (activeTabs[tabId]) {
    delete activeTabs[tabId];
  }
});

async function registerWithBackend() {
  if (!backendUrl || !apiKey) return;
  
  try {
    const response = await fetch(`${backendUrl}/meeting/presence/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({ extension_version: EXTENSION_VERSION })
    });
    
    if (response.ok) {
      const data = await response.json();
      extensionId = data.extension_id;
      isRegistered = true;
      console.log("Registered with backend:", data);
      
      // Flush any queued events
      flushQueue();
    } else {
      console.error("Registration failed:", response.status);
      isRegistered = false;
    }
  } catch (error) {
    console.error("Registration network error:", error);
    isRegistered = false;
    // Retry registration later
    setTimeout(registerWithBackend, 5000);
  }
}

function handleNewEvent(payload) {
  const eventId = payload.event_id || crypto.randomUUID();
  payload.event_id = eventId;
  
  if (payload.event_type === "Heartbeat") {
    payload.active_tabs = Object.keys(activeTabs).length;
    payload.content_script_connected = Object.keys(activeTabs).length > 0;
  }
  
  const wrappedEvent = {
    schema_version: SCHEMA_VERSION,
    extension_version: EXTENSION_VERSION,
    event_type: payload.event_type,
    payload: payload
  };
  
  // Add to queue
  eventQueue.push({
    id: eventId,
    session_id: payload.session_id,
    data: wrappedEvent,
    timestamp: Date.now()
  });
  
  saveQueue();
  flushQueue();
}

function saveQueue() {
  chrome.storage.local.set({ eventQueue });
}

async function flushQueue() {
  if (isFlushing || eventQueue.length === 0 || !isRegistered || !backendUrl) return;
  isFlushing = true;
  
  const eventsToSend = [...eventQueue];
  
  for (const item of eventsToSend) {
    try {
      const response = await fetch(`${backendUrl}/meeting/presence/session/${item.session_id}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(item.data)
      });
      
      if (response.ok) {
        const ack = await response.json();
        // Remove from queue on successful ACK
        eventQueue = eventQueue.filter(e => e.id !== item.id);
        saveQueue();
      } else if (response.status === 401 || response.status === 403) {
        console.error("Unauthorized, stopping flush.");
        isRegistered = false;
        break; // Stop flushing, we need to re-auth
      } else {
        console.warn("Failed to send event, status:", response.status);
        break; // Stop flushing on error, will retry later
      }
    } catch (error) {
      console.error("Network error during flush:", error);
      break; // Stop flushing, wait for network recovery
    }
  }
  
  isFlushing = false;
  
  if (eventQueue.length > 0 && isRegistered) {
    // Retry remaining events later
    setTimeout(flushQueue, 2000);
  }
}

// Periodic flush attempt just in case
setInterval(() => {
  if (eventQueue.length > 0 && !isFlushing) {
    flushQueue();
  }
}, 10000);
