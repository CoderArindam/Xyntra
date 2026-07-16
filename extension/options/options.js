document.addEventListener('DOMContentLoaded', () => {
  const backendUrlInput = document.getElementById('backendUrl');
  const apiKeyInput = document.getElementById('apiKey');
  const saveBtn = document.getElementById('saveBtn');
  const statusEl = document.getElementById('status');

  // Load saved settings
  chrome.storage.local.get(['backendUrl', 'apiKey'], (result) => {
    if (result.backendUrl) backendUrlInput.value = result.backendUrl;
    if (result.apiKey) apiKeyInput.value = result.apiKey;
  });

  // Save settings
  saveBtn.addEventListener('click', () => {
    const backendUrl = backendUrlInput.value.trim();
    const apiKey = apiKeyInput.value.trim();

    chrome.storage.local.set({ backendUrl, apiKey }, () => {
      statusEl.textContent = 'Settings saved successfully!';
      setTimeout(() => {
        statusEl.textContent = '';
      }, 3000);
      
      // Notify background script to re-register
      chrome.runtime.sendMessage({ type: "SETTINGS_UPDATED" });
    });
  });
});
