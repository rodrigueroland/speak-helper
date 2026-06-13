"""设置对话框：左侧 Tab + 右侧表单，暗色风格"""
from __future__ import annotations

import threading

import httpx
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QRadioButton, QSlider, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ..config import Config

_EDGE_VOICES = [
    "zh-CN-XiaoxiaoNeural",    # 女声，温柔自然（推荐）
    "zh-CN-YunxiNeural",       # 男声，活泼
    "zh-CN-YunjianNeural",     # 男声，播报
    "zh-CN-XiaoyiNeural",      # 女声，活泼
    "zh-CN-YunyangNeural",     # 男声，新闻
    "zh-TW-HsiaoChenNeural",   # 台湾女声
    "zh-TW-YunJheNeural",      # 台湾男声
    "zh-HK-HiuMaanNeural",     # 粤语女声
    "en-US-JennyNeural",       # 英文女声
    "en-US-GuyNeural",         # 英文男声
]

_COMMON_MODELS = [
    "FunAudioLLM/CosyVoice2-0.5B",
    "fnlp/MOSS-TTSD-v0.5",
    "tts-1",
    "tts-1-hd",
]
# SiliconFlow voice 格式：model:voice_name；OpenAI 格式：voice_name
_COMMON_VOICES = [
    "FunAudioLLM/CosyVoice2-0.5B:anna",
    "FunAudioLLM/CosyVoice2-0.5B:alex",
    "FunAudioLLM/CosyVoice2-0.5B:bella",
    "FunAudioLLM/CosyVoice2-0.5B:benjamin",
    "FunAudioLLM/CosyVoice2-0.5B:charles",
    "FunAudioLLM/CosyVoice2-0.5B:claire",
    "FunAudioLLM/CosyVoice2-0.5B:david",
    "FunAudioLLM/CosyVoice2-0.5B:diana",
    "fnlp/MOSS-TTSD-v0.5:anna",
    "fnlp/MOSS-TTSD-v0.5:alex",
    "alloy", "echo", "fable", "nova", "onyx", "shimmer",  # OpenAI 备用
]
_BASE_URL_PRESETS = [
    "https://api.siliconflow.cn/v1",
    "https://api.openai.com/v1",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
]
_STYLE_DARK = """
    QDialog, QWidget { background: #FFFFFF; color: #111827; font-size: 13px; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background: #F9FAFB; border: 1px solid #D1D5DB;
        border-radius: 6px; padding: 5px 8px; color: #111827;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #3B82F6;
        background: #FFFFFF; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background: #FFFFFF; color: #111827;
        selection-background-color: #EFF6FF; selection-color: #1D4ED8; }
    QPushButton {
        background: #F3F4F6; border: 1px solid #D1D5DB;
        border-radius: 6px; padding: 5px 14px; color: #374151;
    }
    QPushButton:hover { background: #E5E7EB; border-color: #9CA3AF; }
    QPushButton#primary { background: #3B82F6; border: none; color: #fff; font-weight: 600; }
    QPushButton#primary:hover { background: #2563EB; }
    QLabel { color: #374151; }
    QLabel#section { color: #9CA3AF; font-size: 11px; }
    QRadioButton { color: #374151; }
    QRadioButton::indicator { width: 15px; height: 15px; border-radius: 8px;
        border: 1.5px solid #D1D5DB; background: #FFFFFF; }
    QRadioButton::indicator:checked { border-color: #3B82F6;
        background: qradialgradient(cx:0.5,cy:0.5,radius:0.4,
            fx:0.5,fy:0.5, stop:0 #3B82F6, stop:0.45 #3B82F6,
            stop:0.5 #FFFFFF, stop:1 #FFFFFF); }
    QCheckBox { color: #374151; }
    QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;
        border: 1.5px solid #D1D5DB; background: #FFFFFF; }
    QCheckBox::indicator:checked { background: #3B82F6; border-color: #3B82F6; }
    QSlider::groove:horizontal { height: 4px; background: #E5E7EB; border-radius: 2px; }
    QSlider::handle:horizontal {
        width: 14px; height: 14px; margin: -5px 0;
        background: #3B82F6; border-radius: 7px; border: 2px solid #FFFFFF;
    }
    QSlider::sub-page:horizontal { background: #3B82F6; border-radius: 2px; }
    QListWidget { background: #F9FAFB; border: none; border-right: 1px solid #E5E7EB;
        font-size: 13px; }
    QListWidget::item { padding: 10px 16px; color: #6B7280; }
    QListWidget::item:selected { background: #EFF6FF; color: #2563EB;
        border-left: 2px solid #3B82F6; }
    QFrame#sep { background: #E5E7EB; }
    QDialogButtonBox QPushButton { min-width: 72px; }
"""


class _TestWorker(QObject):
    result = Signal(bool, str)   # success, message

    def __init__(self, base_url: str, api_key: str, model: str, voice: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.voice = voice

    def run(self) -> None:
        import time
        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    f"{self.base_url.rstrip('/')}/audio/speech",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": "测试", "voice": self.voice,
                          "speed": 1.0, "response_format": "mp3"},
                )
                resp.raise_for_status()
            ms = int((time.monotonic() - t0) * 1000)
            self.result.emit(True, f"连接成功 ({ms}ms)")
        except Exception as exc:
            self.result.emit(False, str(exc)[:80])


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._test_thread: QThread | None = None
        self._test_worker: _TestWorker | None = None
        self.setWindowTitle("⚙  设置")
        self.setMinimumSize(520, 560)
        self.setStyleSheet(_STYLE_DARK)
        self._build_ui()
        # 打开时从磁盘刷新，确保显示最新保存的值
        self._config.reload()
        self._load_values()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧 Tab 列表
        self._tab_list = QListWidget()
        self._tab_list.setFixedWidth(120)
        for name in ["API", "触发", "图片OCR", "外观", "缓存", "关于"]:
            self._tab_list.addItem(name)
        self._tab_list.setCurrentRow(0)
        self._tab_list.currentRowChanged.connect(self._stack.setCurrentIndex
                                                  if hasattr(self, "_stack") else lambda _: None)
        root.addWidget(self._tab_list)

        # 右侧堆叠页面
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_api())
        self._stack.addWidget(self._page_trigger())
        self._stack.addWidget(self._page_ocr())
        self._stack.addWidget(self._page_appearance())
        self._stack.addWidget(self._page_cache())
        self._stack.addWidget(self._page_about())
        root.addWidget(self._stack)
        self._tab_list.currentRowChanged.connect(self._stack.setCurrentIndex)

        # 底部按钮
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(root)
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(1)
        outer.addWidget(sep)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        btns.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        btn_wrap = QWidget()
        btn_layout = QHBoxLayout(btn_wrap)
        btn_layout.setContentsMargins(12, 8, 12, 12)
        btn_layout.addStretch()
        btn_layout.addWidget(btns)
        outer.addWidget(btn_wrap)
        self.setLayout(outer)

    # ── pages ─────────────────────────────────────────────────────────────────

    def _page_api(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # ── 后端选择 ──────────────────────────────────────────────────────────
        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("语音后端"))
        self._backend_edge = QRadioButton("Edge-TTS（微软免费）")
        self._backend_openai = QRadioButton("OpenAI 兼容 API")
        self._backend_edge.toggled.connect(self._on_backend_changed)
        backend_row.addWidget(self._backend_edge)
        backend_row.addWidget(self._backend_openai)
        backend_row.addStretch()
        layout.addLayout(backend_row)

        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ── Edge-TTS 专属区域 ─────────────────────────────────────────────────
        self._edge_group = QWidget()
        edge_form = QFormLayout(self._edge_group)
        edge_form.setSpacing(10)
        edge_form.setContentsMargins(0, 0, 0, 0)
        edge_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._edge_voice = QComboBox()
        self._edge_voice.setEditable(True)
        self._edge_voice.addItems(_EDGE_VOICES)
        edge_form.addRow("音色", self._edge_voice)

        # 测试 Edge
        edge_test_row = QHBoxLayout()
        self._edge_test_btn = QPushButton("测试  ↻")
        self._edge_test_btn.clicked.connect(self._on_test_edge)
        self._edge_test_result = QLabel("")
        edge_test_row.addWidget(self._edge_test_btn)
        edge_test_row.addWidget(self._edge_test_result)
        edge_test_row.addStretch()
        edge_form.addRow("", edge_test_row)
        layout.addWidget(self._edge_group)

        # ── OpenAI 兼容区域 ───────────────────────────────────────────────────
        self._openai_group = QWidget()
        openai_form = QFormLayout(self._openai_group)
        openai_form.setSpacing(10)
        openai_form.setContentsMargins(0, 0, 0, 0)
        openai_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._base_url = QComboBox()
        self._base_url.setEditable(True)
        self._base_url.addItems(_BASE_URL_PRESETS)
        openai_form.addRow("Base URL", self._base_url)

        key_row = QHBoxLayout()
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("sk-…")
        eye_btn = QPushButton("👁")
        eye_btn.setFixedSize(30, 30)
        eye_btn.setStyleSheet("background:transparent;border:none;font-size:14px;")
        eye_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._api_key)
        key_row.addWidget(eye_btn)
        openai_form.addRow("API Key", key_row)

        mv_row = QHBoxLayout()
        self._model = QComboBox()
        self._model.setEditable(True)
        self._model.addItems(_COMMON_MODELS)
        self._voice = QComboBox()
        self._voice.setEditable(True)
        self._voice.addItems(_COMMON_VOICES)
        self._model.currentTextChanged.connect(self._on_model_changed)
        mv_row.addWidget(self._model)
        mv_row.addWidget(self._voice)
        openai_form.addRow("Model / Voice", mv_row)

        fmt_row = QHBoxLayout()
        self._fmt_mp3  = QRadioButton("mp3")
        self._fmt_wav  = QRadioButton("wav")
        self._fmt_opus = QRadioButton("opus")
        self._fmt_mp3.setChecked(True)
        fmt_row.addWidget(self._fmt_mp3)
        fmt_row.addWidget(self._fmt_wav)
        fmt_row.addWidget(self._fmt_opus)
        fmt_row.addStretch()
        openai_form.addRow("Format", fmt_row)

        test_row = QHBoxLayout()
        self._test_btn = QPushButton("测试连接  ↻")
        self._test_btn.clicked.connect(self._on_test)
        self._test_result = QLabel("")
        test_row.addWidget(self._test_btn)
        test_row.addWidget(self._test_result)
        test_row.addStretch()
        openai_form.addRow("", test_row)
        layout.addWidget(self._openai_group)

        # ── 公共 Speed 滑块 ───────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setObjectName("sep")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        common_form = QFormLayout()
        common_form.setSpacing(10)
        common_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        speed_row = QHBoxLayout()
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 200)
        self._speed_label = QLabel("1.2×")
        self._speed_label.setFixedWidth(36)
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(f"{v/100:.1f}×")
        )
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_label)
        common_form.addRow("Speed", speed_row)
        layout.addLayout(common_form)

        layout.addStretch()
        return w

    def _page_trigger(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self._clip_chk = QCheckBox("启用剪贴板监听")
        self._hotkey_chk = QCheckBox("启用全局快捷键")
        layout.addWidget(self._clip_chk)
        layout.addWidget(self._hotkey_chk)

        hk_row = QHBoxLayout()
        hk_row.addWidget(QLabel("快捷键组合"))
        self._hotkey_edit = QLineEdit()
        self._hotkey_edit.setPlaceholderText("例：ctrl+alt+r")
        hk_row.addWidget(self._hotkey_edit)
        layout.addLayout(hk_row)

        layout.addWidget(QLabel("默认模式", objectName="section"))
        self._mode_ask  = QRadioButton("询问（每次弹气泡）")
        self._mode_auto = QRadioButton("自动（直接朗读）")
        layout.addWidget(self._mode_ask)
        layout.addWidget(self._mode_auto)

        form = QFormLayout()
        self._min_len = QSpinBox()
        self._min_len.setRange(1, 100)
        self._max_len = QSpinBox()
        self._max_len.setRange(10, 10000)
        self._debounce = QSpinBox()
        self._debounce.setRange(50, 2000)
        self._debounce.setSuffix(" ms")
        self._sentences_per_chunk = QSpinBox()
        self._sentences_per_chunk.setRange(1, 20)
        self._sentences_per_chunk.setToolTip(
            "每次发送给 API 的句子数。数值越小首句响应越快，数值越大合并停顿更自然。"
        )
        form.addRow("最小长度", self._min_len)
        form.addRow("最大长度", self._max_len)
        form.addRow("防抖延迟", self._debounce)
        form.addRow("每块句数", self._sentences_per_chunk)
        layout.addLayout(form)
        layout.addStretch()
        return w

    def _page_ocr(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self._ocr_enabled_chk = QCheckBox("启用图片 OCR（复制图片时自动识别文字）")
        layout.addWidget(self._ocr_enabled_chk)

        desc = QLabel(
            "复制图片到剪贴板后，将图片发送给 Vision API 提取文字，再朗读识别结果。\n"
            "使用与 TTS 相同的 Base URL 和 API Key。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._ocr_model = QComboBox()
        self._ocr_model.setEditable(True)
        for m in [
            "PaddlePaddle/PaddleOCR-VL-1.5",
            "Qwen/Qwen2-VL-7B-Instruct",
            "Qwen/Qwen2-VL-72B-Instruct",
            "Pro/Qwen/Qwen2-VL-7B-Instruct",
            "gpt-4o",
            "gpt-4o-mini",
        ]:
            self._ocr_model.addItem(m)
        form.addRow("OCR 模型", self._ocr_model)

        self._ocr_quality = QSpinBox()
        self._ocr_quality.setRange(30, 95)
        self._ocr_quality.setSuffix("  (30=低质 / 95=高质)")
        self._ocr_quality.setToolTip("图片压缩质量，越低体积越小、API 消耗越少，但细节可能丢失")
        form.addRow("图片质量", self._ocr_quality)

        layout.addLayout(form)
        layout.addStretch()
        return w

    def _page_appearance(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        self._bubble_timeout = QSpinBox()
        self._bubble_timeout.setRange(2, 30)
        self._bubble_timeout.setSuffix(" 秒")
        form.addRow("气泡显示时长", self._bubble_timeout)
        layout.addLayout(form)

        self._autostart_chk = QCheckBox("开机自动启动")
        layout.addWidget(self._autostart_chk)
        layout.addStretch()
        return w

    def _page_cache(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self._cache_chk = QCheckBox("启用本地音频缓存")
        layout.addWidget(self._cache_chk)

        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel("容量上限"))
        self._cache_mb = QSlider(Qt.Orientation.Horizontal)
        self._cache_mb.setRange(0, 500)
        self._cache_mb_label = QLabel("100 MB")
        self._cache_mb.valueChanged.connect(
            lambda v: self._cache_mb_label.setText(f"{v} MB")
        )
        cap_row.addWidget(self._cache_mb)
        cap_row.addWidget(self._cache_mb_label)
        layout.addLayout(cap_row)

        # 当前用量（动态读取）
        self._cache_usage_label = QLabel()
        layout.addWidget(self._cache_usage_label)

        clear_btn = QPushButton("清空缓存")
        clear_btn.clicked.connect(self._on_clear_cache)
        layout.addWidget(clear_btn)
        layout.addStretch()
        return w

    def _page_about(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 24, 20, 16)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Speak Helper"))
        layout.addWidget(QLabel("版本 0.0.1"))
        layout.addWidget(QLabel("选中文字，一键朗读"))
        layout.addStretch()
        return w

    # ── load / save ───────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        cfg = self._config

        # 后端选择
        is_edge = cfg.backend == "edge"
        self._backend_edge.setChecked(is_edge)
        self._backend_openai.setChecked(not is_edge)
        self._edge_group.setVisible(is_edge)
        self._openai_group.setVisible(not is_edge)

        # Edge 设置
        ev_idx = self._edge_voice.findText(cfg.edge_voice)
        self._edge_voice.setCurrentIndex(ev_idx if ev_idx >= 0 else 0)
        if ev_idx < 0:
            self._edge_voice.setEditText(cfg.edge_voice)

        # OpenAI 设置
        idx = self._base_url.findText(cfg.base_url)
        if idx >= 0:
            self._base_url.setCurrentIndex(idx)
        else:
            self._base_url.setEditText(cfg.base_url)

        self._api_key.setText(cfg.api_key)

        m_idx = self._model.findText(cfg.model)
        self._model.setCurrentIndex(m_idx if m_idx >= 0 else 0)
        self._model.setEditText(cfg.model)

        v_idx = self._voice.findText(cfg.voice)
        self._voice.setCurrentIndex(v_idx if v_idx >= 0 else 0)

        self._speed_slider.setValue(int(cfg.speed * 100))

        fmt = cfg.audio_format
        self._fmt_mp3.setChecked(fmt == "mp3")
        self._fmt_wav.setChecked(fmt == "wav")
        self._fmt_opus.setChecked(fmt == "opus")

        self._clip_chk.setChecked(cfg.clipboard_enabled)
        self._hotkey_chk.setChecked(cfg.hotkey_enabled)
        self._hotkey_edit.setText(cfg.hotkey)
        self._mode_ask.setChecked(cfg.mode == "ask")
        self._mode_auto.setChecked(cfg.mode == "auto")
        self._min_len.setValue(cfg.min_length)
        self._max_len.setValue(cfg.max_length)
        self._debounce.setValue(cfg.debounce_ms)
        self._sentences_per_chunk.setValue(cfg.sentences_per_chunk)

        self._bubble_timeout.setValue(cfg.bubble_timeout_ms // 1000)
        self._autostart_chk.setChecked(bool(cfg.get("ui", "autostart", default=False)))

        self._ocr_enabled_chk.setChecked(cfg.ocr_enabled)
        ocr_idx = self._ocr_model.findText(cfg.ocr_model)
        self._ocr_model.setCurrentIndex(ocr_idx if ocr_idx >= 0 else 0)
        self._ocr_model.setEditText(cfg.ocr_model)
        self._ocr_quality.setValue(cfg.ocr_image_quality)

        self._cache_chk.setChecked(cfg.cache_enabled)
        self._cache_mb.setValue(cfg.cache_max_mb)
        self._refresh_cache_usage()

    def _on_save(self) -> None:
        cfg = self._config

        backend = "edge" if self._backend_edge.isChecked() else "openai"
        cfg.set("tts", "backend", backend)
        cfg.set("tts", "edge_voice", self._edge_voice.currentText().strip())
        cfg.set("tts", "base_url", self._base_url.currentText().strip())
        cfg.api_key = self._api_key.text().strip()
        cfg.set("tts", "model", self._model.currentText().strip())
        cfg.set("tts", "voice", self._voice.currentText())
        cfg.set("tts", "speed", round(self._speed_slider.value() / 100, 2))

        if self._fmt_wav.isChecked():
            cfg.set("tts", "format", "wav")
        elif self._fmt_opus.isChecked():
            cfg.set("tts", "format", "opus")
        else:
            cfg.set("tts", "format", "mp3")

        cfg.set("trigger", "clipboard_enabled", self._clip_chk.isChecked())
        cfg.set("trigger", "hotkey_enabled", self._hotkey_chk.isChecked())
        cfg.set("trigger", "hotkey", self._hotkey_edit.text().strip())
        cfg.set("trigger", "mode", "ask" if self._mode_ask.isChecked() else "auto")
        cfg.set("trigger", "min_length", self._min_len.value())
        cfg.set("trigger", "max_length", self._max_len.value())
        cfg.set("trigger", "debounce_ms", self._debounce.value())
        cfg.set("tts", "sentences_per_chunk", self._sentences_per_chunk.value())

        cfg.set("ui", "bubble_timeout_ms", self._bubble_timeout.value() * 1000)
        cfg.set("ui", "autostart", self._autostart_chk.isChecked())

        cfg.set("ocr", "enabled", self._ocr_enabled_chk.isChecked())
        cfg.set("ocr", "model", self._ocr_model.currentText().strip())
        cfg.set("ocr", "image_quality", self._ocr_quality.value())

        cfg.set("cache", "enabled", self._cache_chk.isChecked())
        cfg.set("cache", "max_mb", self._cache_mb.value())

        cfg.save()
        self.saved.emit()
        self.accept()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _on_backend_changed(self) -> None:
        is_edge = self._backend_edge.isChecked()
        self._edge_group.setVisible(is_edge)
        self._openai_group.setVisible(not is_edge)

    def _on_test_edge(self) -> None:
        import asyncio, tempfile, os
        self._edge_test_btn.setEnabled(False)
        self._edge_test_btn.setText("测试中…")
        self._edge_test_result.setText("")

        voice = self._edge_voice.currentText()
        speed = self._speed_slider.value() / 100
        rate_pct = int(round((speed - 1.0) * 100))
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        import threading, time

        def run():
            import edge_tts
            t0 = time.monotonic()
            try:
                tmp = tempfile.mktemp(suffix=".mp3")
                asyncio.run(
                    edge_tts.Communicate("测试语音", voice, rate=rate_str).save(tmp)
                )
                ms = int((time.monotonic() - t0) * 1000)
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                self._edge_test_result.setStyleSheet("color:#10B981;")
                self._edge_test_result.setText(f"✅ 成功 ({ms}ms)")
            except Exception as e:
                self._edge_test_result.setStyleSheet("color:#EF4444;")
                self._edge_test_result.setText(f"❌ {str(e)[:60]}")
            finally:
                self._edge_test_btn.setEnabled(True)
                self._edge_test_btn.setText("测试  ↻")

        threading.Thread(target=run, daemon=True).start()

    def _on_model_changed(self, model: str) -> None:
        """model 切换时，将 voice 下拉更新为该 model 对应的预设音色"""
        _model_voices: dict[str, list[str]] = {
            "FunAudioLLM/CosyVoice2-0.5B": [
                "FunAudioLLM/CosyVoice2-0.5B:anna",
                "FunAudioLLM/CosyVoice2-0.5B:alex",
                "FunAudioLLM/CosyVoice2-0.5B:bella",
                "FunAudioLLM/CosyVoice2-0.5B:benjamin",
                "FunAudioLLM/CosyVoice2-0.5B:charles",
                "FunAudioLLM/CosyVoice2-0.5B:claire",
                "FunAudioLLM/CosyVoice2-0.5B:david",
                "FunAudioLLM/CosyVoice2-0.5B:diana",
            ],
            "fnlp/MOSS-TTSD-v0.5": [
                "fnlp/MOSS-TTSD-v0.5:anna",
                "fnlp/MOSS-TTSD-v0.5:alex",
                "fnlp/MOSS-TTSD-v0.5:bella",
                "fnlp/MOSS-TTSD-v0.5:benjamin",
                "fnlp/MOSS-TTSD-v0.5:charles",
                "fnlp/MOSS-TTSD-v0.5:claire",
                "fnlp/MOSS-TTSD-v0.5:david",
                "fnlp/MOSS-TTSD-v0.5:diana",
            ],
        }
        voices = _model_voices.get(model, ["alloy", "echo", "fable", "nova", "onyx", "shimmer"])
        current = self._voice.currentText()
        self._voice.blockSignals(True)
        self._voice.clear()
        self._voice.addItems(voices)
        # 尝试保留当前选中项，否则回到第一个
        idx = self._voice.findText(current)
        self._voice.setCurrentIndex(idx if idx >= 0 else 0)
        self._voice.blockSignals(False)

    def _toggle_key_visibility(self) -> None:
        if self._api_key.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._api_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _refresh_cache_usage(self) -> None:
        cache_dir = self._config.cache_dir
        total = sum(p.stat().st_size for p in cache_dir.glob("*") if p.is_file())
        used_mb = total / 1024 / 1024
        self._cache_usage_label.setText(
            f"当前已用：{used_mb:.1f} MB / {self._config.cache_max_mb} MB"
        )

    def _on_clear_cache(self) -> None:
        for p in self._config.cache_dir.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
        self._refresh_cache_usage()

    def _on_test(self) -> None:
        self._test_btn.setEnabled(False)
        self._test_btn.setText("测试中…")
        self._test_result.setText("")

        worker = _TestWorker(
            self._base_url.currentText().strip(),
            self._api_key.text().strip(),
            self._model.currentText().strip(),
            self._voice.currentText(),
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result.connect(self._on_test_result)
        worker.result.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _on_test_result(self, success: bool, msg: str) -> None:
        self._test_btn.setEnabled(True)
        self._test_btn.setText("测试连接  ↻")
        color = "#10B981" if success else "#EF4444"
        icon = "✅" if success else "❌"
        self._test_result.setStyleSheet(f"color:{color};")
        self._test_result.setText(f"{icon} {msg}")
