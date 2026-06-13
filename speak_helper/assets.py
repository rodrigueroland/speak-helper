"""内置 SVG 图标字符串，避免外部文件依赖"""

# 监听中（蓝色）
ICON_IDLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#3B82F6"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="#3B82F6" stroke-width="2"
        stroke-linecap="round" fill="none"/>
  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" stroke="#3B82F6" stroke-width="2"
        stroke-linecap="round" fill="none"/>
</svg>"""

# 朗读中（绿色）
ICON_SPEAKING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#10B981"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="#10B981" stroke-width="2"
        stroke-linecap="round" fill="none"/>
  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" stroke="#10B981" stroke-width="2"
        stroke-linecap="round" fill="none"/>
</svg>"""

# 已暂停（灰色）
ICON_PAUSED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#888888"/>
  <line x1="3" y1="3" x2="21" y2="21" stroke="#EF4444" stroke-width="2"
        stroke-linecap="round"/>
</svg>"""

# 错误（喇叭 + 右上红点）
ICON_ERROR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M11 5L6 9H2v6h4l5 4V5z" fill="#9CA3AF"/>
  <circle cx="19" cy="5" r="4" fill="#EF4444"/>
</svg>"""

# 托盘图标（16×16 友好的小尺寸）
ICON_TRAY = ICON_IDLE
