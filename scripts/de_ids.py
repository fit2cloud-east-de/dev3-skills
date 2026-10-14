"""生成与前端相近的雪花风格数字 ID（字符串）。"""

from __future__ import annotations

import time
import threading

_lock = threading.Lock()
_seq = 0
_last_ms = 0


def snowflake_id() -> str:
    global _seq, _last_ms
    with _lock:
        ms = int(time.time() * 1000)
        if ms == _last_ms:
            _seq = (_seq + 1) & 0xFFF
        else:
            _seq = 0
            _last_ms = ms
        # 简化雪花：时间毫秒 << 12 | seq，保证同进程唯一且为十进制数字串
        return str((ms << 12) | _seq)
