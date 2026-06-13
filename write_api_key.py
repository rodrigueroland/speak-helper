"""
直接将 API Key 写入配置文件。
用法（在 speak_helper 目录下执行）：
    python write_api_key.py sk-你的key
"""
import sys
import json
import pathlib

if len(sys.argv) < 2:
    print("用法: python write_api_key.py <你的APIKey>")
    sys.exit(1)

api_key = sys.argv[1].strip()
cfg_path = pathlib.Path.home() / "AppData" / "Local" / "speak_helper" / "speak_helper" / "config.json"

if not cfg_path.exists():
    print(f"配置文件不存在：{cfg_path}")
    sys.exit(1)

data = json.loads(cfg_path.read_text(encoding="utf-8"))
data.setdefault("tts", {})["api_key"] = api_key
cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"API Key 已写入（长度 {len(api_key)}）：{cfg_path}")
print("请重启 speak_helper 使配置生效。")
