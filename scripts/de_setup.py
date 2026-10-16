#!/usr/bin/env python3
"""连接配置（连接制）：向用户索取 DataEase V3 连接信息、保存并验证。

本 skill 始终基于连接制：任何业务操作前都需要「部署地址 + Access Key + Secret Key」。
首次使用请先向用户索取三项信息，再执行：

    python de_setup.py save --base-url <地址> --access-key <AK> --secret-key <SK> [--write-scope <id,id>]
    python de_setup.py check

配置优先级：命令行参数 > 环境变量（DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY）> 本地配置文件
（默认 `~/.dataease-de3/config.json`，0600 权限，可用 DE_CONFIG_FILE 指定其它路径）。

check 会验证连通性、展示当前账号，并自动发现五棵资源树的组织根 id，给出可直接粘贴的
DE_ALLOWED_WRITE_SCOPE 建议值。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

from de_client import (
    DataEaseClient,
    DataEaseClientError,
    config_file_path,
    load_saved_config,
    mask_secret,
    save_config_file,
)
from datasource import _fetch_person, _is_admin_account, _walk_tree_index

# 五棵资源树：(名称, 树接口, busiFlag)
TREE_KINDS = [
    ("数据源", "/datasource/tree", "datasource"),
    ("数据集", "/datasetTree/tree", "dataset"),
    ("数据大屏", "/dataVisualization/tree", "dataV"),
    ("仪表板", "/dataVisualization/tree", "dashboard"),
    ("电子表格", "/spreadsheet/tree", "spreadsheet"),
]


def _resolve_source(name: str, env_key: str) -> tuple[str, str]:
    """返回 (值, 来源描述)。"""
    if os.environ.get(env_key):
        return os.environ[env_key], f"环境变量 {env_key}"
    saved = load_saved_config()
    field = {"DE_BASE_URL": "baseUrl", "DE_ACCESS_KEY": "accessKey", "DE_SECRET_KEY": "secretKey"}[env_key]
    if saved.get(field):
        return str(saved[field]), f"配置文件 {config_file_path()}"
    return "", "未配置"


def cmd_show(_client: Optional[DataEaseClient], _args: argparse.Namespace) -> None:
    """展示当前生效的连接配置（密钥脱敏）。"""
    print("== 当前连接配置（连接制）==")
    for label, env_key in [
        ("部署地址", "DE_BASE_URL"),
        ("Access Key", "DE_ACCESS_KEY"),
        ("Secret Key", "DE_SECRET_KEY"),
    ]:
        value, source = _resolve_source(label, env_key)
        shown = value if env_key == "DE_BASE_URL" else mask_secret(value)
        print(f"  {label:<11}: {shown or '(未配置)'}   ← {source}")
    saved = load_saved_config()
    scope = saved.get("writeScope") or os.environ.get("DE_ALLOWED_WRITE_SCOPE") or ""
    print(f"  写入范围    : {scope or '(未限制)'}   (DE_ALLOWED_WRITE_SCOPE)")
    print(f"  配置文件    : {config_file_path()}")


def cmd_save(_client: Optional[DataEaseClient], args: argparse.Namespace) -> None:
    """保存连接配置到本地配置文件（合并写入，密钥仅本地保存）。"""
    path = args.config or config_file_path()
    current = load_saved_config(path)
    changed = []
    if args.base_url:
        current["baseUrl"] = args.base_url.rstrip("/")
        changed.append("baseUrl")
    if args.access_key:
        current["accessKey"] = args.access_key.strip()
        changed.append("accessKey")
    if args.secret_key:
        current["secretKey"] = args.secret_key.strip()
        changed.append("secretKey")
    if args.write_scope is not None:
        current["writeScope"] = args.write_scope.strip()
        changed.append("writeScope")
    if not changed:
        raise DataEaseClientError("未提供任何配置项：--base-url / --access-key / --secret-key / --write-scope")
    saved_path = save_config_file(current, path)
    print(f"已保存连接配置（{', '.join(changed)}）→ {saved_path}")
    print("提示：密钥仅写入本地文件（0600），请勿提交到任何代码仓库。下一步执行 `python de_setup.py check` 验证。")


def cmd_check(_client: Optional[DataEaseClient], _args: argparse.Namespace) -> None:
    """验证连接可用性，并自动发现五棵树的组织根（给出写入范围建议）。"""
    client = DataEaseClient()  # 缺配置时先给出引导性报错，不打印半张配置表
    cmd_show(None, argparse.Namespace())
    print()
    print(f"== 连通性验证：{client.base_url} ==")
    person = _fetch_person(client)
    print(
        "  账号: "
        + str(person.get("account") or person.get("name") or "(未知)")
        + (f" | 用户名: {person.get('name')}" if person.get("name") else "")
    )
    if _is_admin_account(person):
        print("  ⚠️ 当前为 admin 账号：权限过大，建议改用「数据分析师」等业务角色，操作前务必备份。")

    print("\n== 五棵资源树的组织根（同名组织的 id 通常不同，勿混用）==")
    roots: list[str] = []
    for label, path, busi in TREE_KINDS:
        tree = client.post(path, {"busiFlag": busi})
        index = _walk_tree_index(tree)
        nodes = [
            {"id": nid, "name": info.get("name"), "path": info.get("path")}
            for nid, info in index.items()
            if info.get("orgRoot")
        ]
        if not nodes:
            print(f"  {label:<6}: (未发现组织根，请确认 Key 对该树的可见性)")
            continue
        for n in nodes:
            roots.append(n["id"])
            print(f"  {label:<6}: {n['id']}  {n['name']}  ({n['path']})")
    if roots:
        uniq = list(dict.fromkeys(roots))
        print("\n建议写入范围（如与用户确认一致，可保存）：")
        print(f"  DE_ALLOWED_WRITE_SCOPE={','.join(uniq)}")
        print("  保存：python de_setup.py save --write-scope " + ",".join(uniq))
    print("\n连接可用 ✓（后续脚本可直接执行业务命令）")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="DataEase V3 连接配置（连接制）：索取 / 保存 / 验证连接信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python de_setup.py save --base-url https://de.example.com --access-key AK --secret-key SK\n"
            "  python de_setup.py check\n"
            "  python de_setup.py show"
        ),
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("check", help="验证连接并发现各树组织根（默认命令）").set_defaults(func=cmd_check)
    sub.add_parser("show", help="展示当前连接配置（密钥脱敏）").set_defaults(func=cmd_show)
    sv = sub.add_parser("save", help="保存连接配置到本地文件")
    sv.add_argument("--base-url", default=None, help="部署地址，如 https://de.example.com")
    sv.add_argument("--access-key", default=None)
    sv.add_argument("--secret-key", default=None)
    sv.add_argument("--write-scope", default=None, help="允许写入的组织根/文件夹 id，逗号分隔")
    sv.add_argument("--config", default=None, help="配置文件路径（默认 ~/.dataease-de3/config.json）")
    sv.set_defaults(func=cmd_save)
    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        args.func = cmd_check
    try:
        args.func(None, args)
        return 0
    except DataEaseClientError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
