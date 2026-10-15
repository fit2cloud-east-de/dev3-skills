#!/usr/bin/env python3
"""DataEase V3 资源血缘（关联分析）CLI。

查询某资源的下游引用（数据集 / 仪表板 / 数据大屏），编辑或删除陌生资源前必须先执行。

环境变量同 datasource.py：DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError

KINDS = ("datasource", "dataset", "dv")

# 关联树中的「可视化」节点类型：修改/删除上游数据会导致这些看板中的图表不可用
VISUAL_TYPES = ("dataV", "dashboard", "panel", "screen")

TYPE_LABELS = {
    "datasource": "数据源",
    "dataset": "数据集",
    "dataV": "数据大屏",
    "dashboard": "仪表板",
    "panel": "仪表板",
    "screen": "数据大屏",
    "folder": "文件夹",
}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def type_label(t: Optional[str]) -> str:
    return TYPE_LABELS.get(t or "", t or "未知")


def fetch_relation(client: DataEaseClient, kind: str, resource_id: Any) -> dict:
    """POST /relation/{kind}/{id}，返回解包后的关联树。"""
    if kind not in KINDS:
        raise DataEaseClientError(f"kind 须为 {'/'.join(KINDS)}，收到: {kind}")
    data = client.post(f"/relation/{kind}/{resource_id}", {})
    if not isinstance(data, dict):
        raise DataEaseClientError(f"血缘接口返回异常: {data}")
    return data


def _flatten(nodes: Any, parent: Optional[dict] = None, out: Optional[list] = None) -> list:
    """展平关联树（list + subRelation），保留父节点用于「经由」信息。"""
    if out is None:
        out = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        out.append({"node": node, "parent": parent})
        _flatten(node.get("subRelation"), node, out)
    return out


def _node_brief(n: dict) -> dict:
    t = n.get("type")
    return {
        "id": n.get("id"),
        "name": n.get("name"),
        "type": t,
        "typeLabel": type_label(t),
        "creator": n.get("creator"),
        "updateTime": n.get("updateTime"),
    }


def summarize_relation(detail: dict) -> dict:
    """从关联树提取摘要：当前资源、上游依赖、下游引用、是否有看板在使用。

    各 kind 的返回形状不同：
    - datasource: {current, list}         —— list 为下游数据集树，看板嵌在 subRelation
    - dataset:    {current, dsList, dvList} —— dsList 为上游数据源，dvList 为使用它的看板
    - dv:         {current, list}         —— list 为其依赖的上游资源树
    """
    current = detail.get("current") or {}
    upstream: list = []
    downstream: list = []
    visual_usage: list = []

    flat = _flatten(detail.get("list"))
    for edge in flat:
        n = edge["node"]
        t = n.get("type")
        item = _node_brief(n)
        if current.get("type") == "datasource":
            # 下游树：数据集 + 嵌套看板
            downstream.append(item)
            if t in VISUAL_TYPES:
                p = edge.get("parent") or {}
                visual_usage.append(
                    {
                        "visualType": t,
                        "visualTypeLabel": type_label(t),
                        "visualId": n.get("id"),
                        "visualName": n.get("name"),
                        "viaType": p.get("type"),
                        "viaId": p.get("id"),
                        "viaName": p.get("name"),
                    }
                )
        else:
            # dv 的 list 是上游依赖
            upstream.append(item)

    for n in detail.get("dsList") or []:
        upstream.append(_node_brief(n))

    for n in detail.get("dvList") or []:
        item = _node_brief(n)
        downstream.append(item)
        if n.get("type") in VISUAL_TYPES:
            visual_usage.append(
                {
                    "visualType": n.get("type"),
                    "visualTypeLabel": type_label(n.get("type")),
                    "visualId": n.get("id"),
                    "visualName": n.get("name"),
                    "viaType": current.get("type"),
                    "viaId": current.get("id"),
                    "viaName": current.get("name"),
                }
            )

    return {
        "current": {
            "id": current.get("id"),
            "name": current.get("name"),
            "type": current.get("type"),
            "typeLabel": type_label(current.get("type")),
        },
        "hasRelations": bool(upstream or downstream),
        "hasVisualUsage": bool(visual_usage),
        "upstream": upstream,
        "downstream": downstream,
        "downstreamCounts": {
            t: sum(1 for x in downstream if x.get("type") == t)
            for t in {x.get("type") for x in downstream}
        },
        "visualUsage": visual_usage,
    }


def format_relation_report(summary: dict) -> str:
    """人类可读的血缘报告（多行文本）。"""
    cur = summary.get("current") or {}
    lines = [
        f"血缘分析：{cur.get('typeLabel')}「{cur.get('name')}」(id={cur.get('id')})"
    ]
    upstream = summary.get("upstream") or []
    if upstream:
        lines.append(f"上游依赖（{len(upstream)}）：")
        for x in upstream:
            lines.append(f"- {x.get('typeLabel')}「{x.get('name')}」 id={x.get('id')}")
    downstream = summary.get("downstream") or []
    if downstream:
        counts = "、".join(
            f"{type_label(t)}×{v}"
            for t, v in (summary.get("downstreamCounts") or {}).items()
        )
        lines.append(f"下游引用（{counts}）：")
        for x in downstream:
            lines.append(
                f"- {x.get('typeLabel')}「{x.get('name')}」 id={x.get('id')} 创建者={x.get('creator') or '未知'}"
            )
    if not upstream and not downstream:
        lines.append("关联关系：无")
    return "\n".join(lines)


def relation_gate(client: DataEaseClient, kind: str, resource_id: Any) -> dict:
    """编辑/删除前的血缘检查：查询并打印报告，返回 summary 供调用方执行分级确认。"""
    detail = fetch_relation(client, kind, resource_id)
    summary = summarize_relation(detail)
    print(format_relation_report(summary), file=sys.stderr)
    return summary


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    detail = fetch_relation(client, args.kind, args.id)
    summary = summarize_relation(detail)
    if args.brief:
        _print_json(summary)
    else:
        _print_json({"summary": summary, "detail": detail})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 资源血缘（关联分析）CLI")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("get", help="查询资源下游引用（编辑/删除前必须先执行）")
    g.add_argument("--kind", required=True, choices=KINDS, help="datasource / dataset / dv")
    g.add_argument("--id", required=True, help="资源 id")
    g.add_argument("--brief", action="store_true", help="仅输出摘要，不含原始树")
    g.set_defaults(func=cmd_get)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        client = DataEaseClient()
        args.func(client, args)
        return 0
    except DataEaseClientError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
