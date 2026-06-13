"""TextFilter 单元测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch

# 最小 Config mock
def _make_config(min_len=2, max_len=2000, debounce_ms=0):
    cfg = MagicMock()
    cfg.min_length = min_len
    cfg.max_length = max_len
    cfg.debounce_ms = debounce_ms
    return cfg


@pytest.fixture(autouse=True)
def qt_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_too_short_rejected():
    from speak_helper.text_filter import TextFilter
    cfg = _make_config(min_len=5)
    f = TextFilter(cfg)
    received = []
    f.text_accepted.connect(received.append)
    f.feed("hi")
    assert received == []


def test_text_accepted():
    from speak_helper.text_filter import TextFilter
    cfg = _make_config(debounce_ms=0)
    f = TextFilter(cfg)
    received = []
    f.text_accepted.connect(received.append)
    f.feed("hello world")
    # 因 debounce_ms=0，QTimer 需要事件循环触发
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    assert "hello world" in received


def test_dedup():
    from speak_helper.text_filter import TextFilter
    cfg = _make_config(debounce_ms=0)
    f = TextFilter(cfg)
    received = []
    f.text_accepted.connect(received.append)
    f.feed("same text")
    f.feed("same text")
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    assert len(received) == 1


def test_truncation():
    from speak_helper.text_filter import TextFilter
    cfg = _make_config(max_len=10, debounce_ms=0)
    f = TextFilter(cfg)
    received = []
    f.text_accepted.connect(received.append)
    f.feed("1234567890ABCDEF")
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    assert received and len(received[0]) == 10


def test_reset_dedup_allows_repeat():
    from speak_helper.text_filter import TextFilter
    cfg = _make_config(debounce_ms=0)
    f = TextFilter(cfg)
    received = []
    f.text_accepted.connect(received.append)
    f.feed("repeat me")
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    f.reset_dedup()
    f.feed("repeat me")
    QApplication.processEvents()
    assert len(received) == 2
