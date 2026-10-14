"""DataEase V3 API Key 客户端。"""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Optional
from uuid import uuid4

import jwt
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class DataEaseClientError(RuntimeError):
    pass


def _aes_encrypt(src: str, secret_key: str, iv: str) -> str:
    cipher = AES.new(secret_key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    encrypted = cipher.encrypt(pad(src.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def encode_configuration(config: Any) -> str:
    """将 configuration 对象编码为接口所需的 Base64(JSON) 字符串。"""
    if isinstance(config, str):
        # 已是 Base64 或原始 JSON 字符串时，若能当 JSON 解析则再编码
        try:
            json.loads(config)
            return base64.b64encode(config.encode("utf-8")).decode("utf-8")
        except json.JSONDecodeError:
            return config
    payload = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def decode_configuration(encoded: Optional[str]) -> Any:
    if not encoded:
        return None
    try:
        raw = base64.b64decode(encoded).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return encoded


class DataEaseClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        timeout: int = 60,
    ):
        self.base_url = (base_url or os.environ.get("DE_BASE_URL", "")).rstrip("/")
        self.access_key = access_key or os.environ.get("DE_ACCESS_KEY", "")
        self.secret_key = secret_key or os.environ.get("DE_SECRET_KEY", "")
        self.timeout = timeout
        if not self.base_url or not self.access_key or not self.secret_key:
            raise DataEaseClientError(
                "缺少连接配置。请设置环境变量 DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY，"
                "或在构造参数中传入。"
            )

    def _headers(self) -> dict:
        unique_id = str(uuid4())
        timestamp = str(time.time_ns() // 1000000)
        signature = _aes_encrypt(
            f"{self.access_key}|{unique_id}|{timestamp}",
            self.secret_key,
            self.access_key,
        )
        token = jwt.encode(
            {"accessKey": self.access_key, "signature": signature},
            self.secret_key,
            algorithm="HS256",
        )
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "accessKey": self.access_key,
            "signature": signature,
            "x-de-ask-token": token,
        }

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        if path.startswith("/de2api"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/de2api{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: Any = None,
        files: Any = None,
        params: Any = None,
    ) -> Any:
        headers = self._headers()
        # multipart 时不要强制 Content-Type
        if files is not None:
            headers.pop("Content-Type", None)
        resp = requests.request(
            method=method.upper(),
            url=self._url(path),
            headers=headers,
            json=json_body,
            data=data,
            files=files,
            params=params,
            timeout=self.timeout,
        )
        try:
            body = resp.json()
        except Exception:
            raise DataEaseClientError(f"HTTP {resp.status_code}: 非 JSON 响应: {resp.text[:500]}")

        # DataEase 常见包装: {code, msg, data}
        if isinstance(body, dict) and "code" in body:
            code = body.get("code")
            data = body.get("data", body)
            msg = body.get("msg") or body.get("message")
            # 部分接口 HTTP/code 仍为成功，但 data 为权限错误文案
            if isinstance(data, str) and (
                "没有访问权限" in data or "无权限" in data or "权限" in data and len(data) < 40
            ):
                raise DataEaseClientError(f"接口失败 path={path} msg={data}")
            if code not in (0, 200, "0", "200", None):
                raise DataEaseClientError(
                    f"接口失败 code={code} msg={msg} path={path}"
                )
            return data

        if resp.status_code >= 400:
            raise DataEaseClientError(f"HTTP {resp.status_code}: {body}")
        return body

    def get(self, path: str, **kwargs) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json_body: Any = None, **kwargs) -> Any:
        return self.request("POST", path, json_body=json_body, **kwargs)
