// content/meet_observer.js

class MeetObserver {
  constructor() {
    this.adapter = new GoogleMeetDOMAdapter();
    this.observer = null;
    this.currentParticipants = new Map(); // id -> displayName
    this.sessionId = this._extractSessionId();
    this.containerSearchInterval = null;
    
    // Debounce timers
    this.renameTimers = new Map();
    this.generalMutationTimer = null;
  }

  _extractSessionId() {
    // A meeting URL is typically meet.google.com/abc-defg-hij
    const match = window.location.pathname.match(/\/([a-z0-9-]+)$/);
    return match ? match[1] : 'unknown-session';
  }

  start() {
    this.findAndObserveContainer();
    this.startHeartbeat();
  }

  findAndObserveContainer() {
    // Periodically check if container exists or was rebuilt
    this.containerSearchInterval = setInterval(() => {
      const container = this.adapter.getParticipantListContainer();
      
      if (container && !this.observer) {
        this.attachObserver(container);
        this.fullSync(container);
      } else if (!container && this.observer) {
        // Container lost (Meet rebuilt UI or panel closed)
        this.observer.disconnect();
        this.observer = null;
      }
    }, 2000);
  }

  attachObserver(container) {
    this.observer = new MutationObserver((mutations) => {
      this.handleMutations(mutations, container);
    });
    
    this.observer.observe(container, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  fullSync(container) {
    const listItems = container.querySelectorAll('[role="listitem"], .zWGUib, [data-participant-id]');
    
    const newSnapshot = new Map();
    
    listItems.forEach(item => {
      const info = this.adapter.extractParticipantInfo(item);
      if (info) {
        newSnapshot.set(info.id, info.displayName);
        
        // If not in current, they joined
        if (!this.currentParticipants.has(info.id)) {
          this.emitEvent("ParticipantJoined", { participant_id: info.id, display_name: info.displayName });
        } else if (this.currentParticipants.get(info.id) !== info.displayName) {
          // Name changed
          this.handleRename(info.id, info.displayName);
        }
      }
    });
    
    // Check for left participants
    for (const [id, name] of this.currentParticipants.entries()) {
      if (!newSnapshot.has(id)) {
        this.emitEvent("ParticipantLeft", { participant_id: id });
      }
    }
    
    this.currentParticipants = newSnapshot;
  }

  handleMutations(mutations, container) {
    // We use a general debounce for DOM churn (150ms) unless it's a direct child addition/removal
    if (this.generalMutationTimer) {
      clearTimeout(this.generalMutationTimer);
    }
    
    let needsSync = false;
    
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        // Evaluate additions
        mutation.addedNodes.forEach(node => {
          if (this.adapter.isParticipantElement(node)) {
            const info = this.adapter.extractParticipantInfo(node);
            if (info && !this.currentParticipants.has(info.id)) {
              this.currentParticipants.set(info.id, info.displayName);
              this.emitEvent("ParticipantJoined", { participant_id: info.id, display_name: info.displayName });
            }
          } else {
            needsSync = true;
          }
        });
        
        // Evaluate removals
        mutation.removedNodes.forEach(node => {
          if (this.adapter.isParticipantElement(node)) {
            const info = this.adapter.extractParticipantInfo(node);
            if (info && this.currentParticipants.has(info.id)) {
              this.currentParticipants.delete(info.id);
              this.emitEvent("ParticipantLeft", { participant_id: id });
            }
          } else {
            needsSync = true;
          }
        });
      } else if (mutation.type === 'characterData') {
        needsSync = true;
      }
    }
    
    if (needsSync) {
      this.generalMutationTimer = setTimeout(() => {
        this.fullSync(container);
      }, 150);
    }
  }

  handleRename(id, newName) {
    // Rename debounced to 250ms
    if (this.renameTimers.has(id)) {
      clearTimeout(this.renameTimers.get(id));
    }
    
    this.renameTimers.set(id, setTimeout(() => {
      this.emitEvent("ParticipantRenamed", { participant_id: id, new_display_name: newName });
      this.currentParticipants.set(id, newName);
      this.renameTimers.delete(id);
    }, 250));
  }

  emitEvent(eventType, payload) {
    payload.session_id = this.sessionId;
    payload.timestamp = new Date().toISOString();
    
    chrome.runtime.sendMessage({
      type: "PRESENCE_EVENT",
      payload: {
        event_type: eventType,
        ...payload
      }
    });
  }

  startHeartbeat() {
    setInterval(() => {
      this.emitEvent("Heartbeat", {});
    }, 30000); // 30 seconds
  }
}

// Start observer
const observer = new MeetObserver();
observer.start();

// Notify Service Worker
chrome.runtime.sendMessage({
  type: "CONTENT_SCRIPT_READY",
  payload: { session_id: observer.sessionId }
});
