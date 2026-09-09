"""Embedded SVG icons that do not require external asset files."""

# Ready (blue)
ICON_IDLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#3B82F6"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="#3B82F6" stroke-width="2"
        stroke-linecap="round" fill="none"/>
  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" stroke="#3B82F6" stroke-width="2"
        stroke-linecap="round" fill="none"/>
</svg>"""

# Speaking (green)
ICON_SPEAKING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#10B981"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="#10B981" stroke-width="2"
        stroke-linecap="round" fill="none"/>
  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" stroke="#10B981" stroke-width="2"
        stroke-linecap="round" fill="none"/>
</svg>"""

# Paused (gray)
ICON_PAUSED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#888888"/>
  <line x1="3" y1="3" x2="21" y2="21" stroke="#EF4444" stroke-width="2"
        stroke-linecap="round"/>
</svg>"""

# Error (speaker plus red badge)
ICON_ERROR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#9CA3AF"/>
  <circle cx="19" cy="5" r="4" fill="#EF4444"/>
</svg>"""

# Tray icon, designed to remain legible at 16 x 16 pixels.
ICON_TRAY = ICON_IDLE
