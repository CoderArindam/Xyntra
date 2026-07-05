/**
 * Updates the browser's favicon dynamically.
 * If a logoUrl is provided, it sets the favicon to that URL.
 * Otherwise, it generates a simple canvas-based favicon using initials.
 */
export const updateFavicon = (name: string, logoUrl?: string | null) => {
  let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement;
  if (!link) {
    link = document.createElement('link');
    link.rel = 'icon';
    document.getElementsByTagName('head')[0].appendChild(link);
  }

  if (logoUrl) {
    // If the URL is relative and points to the backend, prepend API base URL
    const baseUrl = import.meta.env.VITE_API_BASE_URL ? import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '') : '';
    const fullUrl = logoUrl.startsWith('http') || logoUrl.startsWith('data:') ? logoUrl : `${baseUrl}${logoUrl}`;
    link.href = fullUrl;
    return;
  }

  // Generate initials fallback
  const getInitials = (str: string): string => {
    if (!str) return 'W';
    const words = str.trim().split(/\s+/);
    if (words.length === 0) return 'W';
    if (words.length === 1) return words[0].charAt(0).toUpperCase();
    return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  };

  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');
  
  if (ctx) {
    // Background (using brand primary color: #0052CC)
    ctx.fillStyle = '#0052CC';
    ctx.beginPath();
    ctx.roundRect(0, 0, 64, 64, 12); // Slightly rounded corners
    ctx.fill();

    // Text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 32px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(getInitials(name), 32, 34); // Slight offset for visual balance

    link.href = canvas.toDataURL('image/png');
  }
};
