// content/GoogleMeetDOMAdapter.js

class GoogleMeetDOMAdapter {
  constructor() {
    // A fallback local ID map if stable IDs aren't found
    this._localIdMap = new Map(); // displayName -> uuid
  }

  /**
   * Find the main participant list container in the DOM.
   * Meet uses different classes over time, so we look for common aria labels or roles.
   */
  getParticipantListContainer() {
    // Common selectors for the right sidebar participant list
    return document.querySelector('[aria-label="Participants"]') || 
           document.querySelector('[data-requested-participant-id]')?.closest('[role="list"]') ||
           document.querySelector('.zWGUib') || // A historical class for the list
           document.querySelector('[role="list"][aria-label="Participants"]');
  }

  /**
   * Parse a participant DOM element to extract their details.
   * Priority: Stable DOM ID -> aria-attributes -> display name -> temporary UUID
   */
  extractParticipantInfo(element) {
    if (!element) return null;
    
    // 1. Try to find a stable ID from data attributes
    // Meet often exposes a data-participant-id or similar
    let stableId = element.getAttribute('data-participant-id') || 
                   element.dataset?.participantId || 
                   element.getAttribute('data-initial-participant-id');
                   
    // 2. Try aria-labels or internal text if stable ID not found
    const nameEl = element.querySelector('[class*="name"], [class*="title"], span[dir="ltr"]');
    const displayName = nameEl ? nameEl.textContent.trim() : (element.getAttribute('aria-label') || '').replace(/.*participant /, '').trim();
    
    if (!displayName) {
      return null; // Can't identify
    }
    
    // 3. Fallback to temporary UUID if no stable ID
    if (!stableId) {
      if (!this._localIdMap.has(displayName)) {
        this._localIdMap.set(displayName, crypto.randomUUID());
      }
      stableId = this._localIdMap.get(displayName);
    }
    
    return {
      id: stableId,
      displayName: displayName
    };
  }

  /**
   * Determine if the element is an actual participant item.
   */
  isParticipantElement(element) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return false;
    
    // Check for common roles or structure
    return element.getAttribute('role') === 'listitem' || 
           element.hasAttribute('data-participant-id') ||
           (element.classList && Array.from(element.classList).some(c => c.length === 6 && c === c.toLowerCase())); // Meet's generated class heuristics
  }
}

window.GoogleMeetDOMAdapter = GoogleMeetDOMAdapter;
