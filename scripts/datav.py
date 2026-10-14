#!/usr/bin/env python3
"""DataEase V3 数据大屏（dataV）CLI —— 目录/数据集选型/图表预览/排版创建。

环境变量同 datasource.py：DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY / DE_ALLOWED_WRITE_SCOPE

Agent 约束见 references/datav.md：禁止擅自删改/复用他人数据集；冲突则自建。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError
from de_ids import snowflake_id
from datav_defaults import (
    CHART_TYPES,
    DECORATION_KINDS,
    SUMMARY_OPTIONS,
    base_view_config,
    decoration_component,
    default_canvas_style,
    user_view_component,
)
from datasource import (
    _assert_within_write_scope,
    _load_tree_index,
    _remind_backup_and_admin,
    _resolve_folder,
)


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load_json(raw: Optional[str], file_path: Optional[str]) -> Any:
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8-sig"))
    if raw:
        return json.loads(raw)
    return None


def _resolve_datav_pid(client: DataEaseClient, args: argparse.Namespace) -> str:
    if getattr(args, "folder_name", None):
        return _resolve_folder(client, folder_name=args.folder_name, kind="dataV")
    if getattr(args, "pid", None) is None:
        raise DataEaseClientError("必须指定目标文件夹 --pid 或 --folder-name（数据大屏树）")
    return _resolve_folder(client, folder_id=args.pid, kind="dataV")


def cmd_catalog(client: DataEaseClient, _args: argparse.Namespace) -> None:
    _print_json(
        {
            "charts": [
                {"type": k, **v} for k, v in CHART_TYPES.items() if v.get("category") != "other" or k == "rich-text"
            ],
            "decorations": [{"kind": k, **v} for k, v in DECORATION_KINDS.items()],
            "summaries": list(SUMMARY_OPTIONS),
            "notes": [
                "大屏画布默认 1920×1080 暗色；组件用 style.left/top/width/height（像素）",
                "UserView 的 id 必须与 canvasViewInfo 的 key 一致",
                "聚合 summary 配在指标字段上，不是图表顶层",
            ],
        }
    )


def cmd_tree(client: DataEaseClient, args: argparse.Namespace) -> None:
    body: dict[str, Any] = {"busiFlag": "dataV"}
    if args.name:
        body["name"] = args.name
    _print_json(client.post("/dataVisualization/tree", body))


def cmd_resolve_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    from datasource import cmd_resolve_folder as _ds_resolve

    args.kind = "dataV"
    _ds_resolve(client, args)


def cmd_datasets(client: DataEaseClient, args: argparse.Namespace) -> None:
    """列出数据集树（供大屏选型；不修改）。"""
    body: dict[str, Any] = {"busiFlag": "dataset"}
    if args.name:
        body["name"] = args.name
    tree = client.post("/datasetTree/tree", body)
    if args.flat:
        flat = []

        def walk(nodes: Any, path: list) -> None:
            if not nodes:
                return
            if isinstance(nodes, dict):
                nodes = [nodes]
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                name = n.get("name")
                cur = path + ([name] if name else [])
                if n.get("leaf") is True or (n.get("type") and n.get("leaf") is not False and not n.get("children")):
                    # 叶子多为数据集；组织根 folderLike
                    if n.get("leaf") is True:
                        flat.append(
                            {
                                "id": str(n.get("id")),
                                "name": name,
                                "path": "/".join(str(x) for x in cur if x),
                            }
                        )
                if n.get("children"):
                    walk(n["children"], cur)

        walk(tree, [])
        _print_json(flat)
        return
    _print_json(tree)


def cmd_fields(client: DataEaseClient, args: argparse.Namespace) -> None:
    chart_id = args.chart_id or snowflake_id()
    data = client.post(f"/chart/listByDQ/{args.dataset_id}/{chart_id}", {})
    if args.simplify and isinstance(data, dict):
        dims = data.get("dimensionList") or data.get("dimensions") or []
        quotas = data.get("quotaList") or data.get("quota") or data.get("quotas") or []
        # 兼容不同包装
        if not dims and not quotas and "data" in data:
            inner = data["data"]
            dims = inner.get("dimensionList") or []
            quotas = inner.get("quotaList") or []
        rows = []
        for f in dims:
            rows.append(
                {
                    "id": str(f.get("id")),
                    "name": f.get("name") or f.get("originName"),
                    "groupType": "d",
                    "deType": f.get("deType"),
                    "summary": f.get("summary"),
                }
            )
        for f in quotas:
            rows.append(
                {
                    "id": str(f.get("id")),
                    "name": f.get("name") or f.get("originName"),
                    "groupType": "q",
                    "deType": f.get("deType"),
                    "summary": f.get("summary") or "sum",
                }
            )
        _print_json({"datasetId": str(args.dataset_id), "chartId": chart_id, "fields": rows})
        return
    _print_json(data)


def _unwrap_dq(data: Any) -> tuple[list, list]:
    if not isinstance(data, dict):
        return [], []
    if "dimensionList" in data or "quotaList" in data:
        return list(data.get("dimensionList") or []), list(data.get("quotaList") or [])
    inner = data.get("data")
    if isinstance(inner, dict):
        return list(inner.get("dimensionList") or []), list(inner.get("quotaList") or [])
    return [], []


def _field_index(dims: list, quotas: list) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for f in dims + quotas:
        for key in (f.get("name"), f.get("originName"), str(f.get("id"))):
            if key:
                idx[str(key)] = f
    return idx


def _as_view_field(src: dict, *, summary: Optional[str] = None) -> dict:
    item = deepcopy(src)
    gt = item.get("groupType")
    if summary is not None:
        item["summary"] = summary
    elif gt == "q" and not item.get("summary"):
        # 文本/时间类默认 count，数值 sum（与产品一致）
        de = item.get("deType")
        try:
            de_i = int(de)
        except (TypeError, ValueError):
            de_i = -1
        item["summary"] = "count" if de_i in (0, 1, 7) or str(item.get("id")) == "-1" else "sum"
    item.setdefault("sort", "none")
    item.setdefault("filter", [])
    item.setdefault("compareCalc", {"type": "none"})
    item.setdefault("dateStyle", "y_M_d")
    item.setdefault("datePattern", "date_sub")
    return item


def _pick_fields(
    idx: dict[str, dict],
    specs: Any,
    *,
    expect_group: Optional[str] = None,
    default_summary: Optional[str] = None,
) -> list:
    if not specs:
        return []
    if isinstance(specs, str):
        specs = [specs]
    out = []
    for spec in specs:
        if isinstance(spec, str):
            name, summary = spec, default_summary
        elif isinstance(spec, dict):
            name = spec.get("name") or spec.get("field") or spec.get("id")
            summary = spec.get("summary", default_summary)
        else:
            raise DataEaseClientError(f"无法解析字段规格: {spec}")
        src = idx.get(str(name))
        if not src:
            raise DataEaseClientError(f"数据集中找不到字段「{name}」。请先 fields --simplify 核对。")
        if expect_group and src.get("groupType") != expect_group:
            # 允许用户强行使用，但给出可见警告
            print(
                f"WARN: 字段「{name}」groupType={src.get('groupType')}，期望 {expect_group}",
                file=sys.stderr,
            )
        out.append(_as_view_field(src, summary=summary if src.get("groupType") == "q" else None))
    return out


def build_chart_view(
    client: DataEaseClient,
    *,
    chart_id: str,
    scene_id: str,
    dataset_id: str,
    chart_type: str,
    title: str,
    x_axis: Any = None,
    y_axis: Any = None,
    x_axis_ext: Any = None,
    ext_stack: Any = None,
    custom_filter: Optional[dict] = None,
    extra_view: Optional[dict] = None,
) -> dict:
    if chart_type not in CHART_TYPES and chart_type != "rich-text":
        raise DataEaseClientError(f"不支持的图表类型: {chart_type}。请先 catalog 查看清单。")
    dq = client.post(f"/chart/listByDQ/{dataset_id}/{chart_id}", {})
    dims, quotas = _unwrap_dq(dq)
    idx = _field_index(dims, quotas)
    view = base_view_config()
    view["id"] = str(chart_id)
    view["sceneId"] = str(scene_id)
    view["tableId"] = str(dataset_id)
    view["type"] = chart_type
    view["title"] = title

    if chart_type == "indicator":
        view["yAxis"] = _pick_fields(idx, y_axis, expect_group="q", default_summary="sum")[:1]
        view["xAxis"] = []
    elif chart_type == "table-info":
        view["xAxis"] = _pick_fields(idx, x_axis or y_axis)
        view["yAxis"] = []
    elif chart_type in ("pie", "pie-donut", "pie-rose", "pie-donut-rose"):
        view["xAxis"] = _pick_fields(idx, x_axis, expect_group="d")
        view["yAxis"] = _pick_fields(idx, y_axis, expect_group="q", default_summary="sum")[:1]
        view["customAttr"]["label"]["show"] = True
        view["customAttr"]["label"]["position"] = "outer"
        view["customStyle"]["legend"]["show"] = False
    else:
        view["xAxis"] = _pick_fields(idx, x_axis, expect_group="d")
        view["yAxis"] = _pick_fields(idx, y_axis, expect_group="q", default_summary="sum")
        if x_axis_ext:
            view["xAxisExt"] = _pick_fields(idx, x_axis_ext, expect_group="d")
        if ext_stack:
            view["extStack"] = _pick_fields(idx, ext_stack, expect_group="d")

    if custom_filter is not None:
        view["customFilter"] = custom_filter
    if extra_view:
        # 浅合并顶层；customAttr/customStyle 深合并一层
        for k, v in extra_view.items():
            if k in ("customAttr", "customStyle", "senior") and isinstance(v, dict):
                base = view.get(k) or {}
                merged = deepcopy(base)
                for sk, sv in v.items():
                    if isinstance(sv, dict) and isinstance(merged.get(sk), dict):
                        merged[sk] = {**merged[sk], **sv}
                    else:
                        merged[sk] = sv
                view[k] = merged
            else:
                view[k] = v
    return view


def cmd_preview_chart(client: DataEaseClient, args: argparse.Namespace) -> None:
    payload = _load_json(args.json, args.file)
    if not payload:
        # 从参数拼
        if not args.dataset_id or not args.type:
            raise DataEaseClientError("preview-chart 需要 --file/--json，或 --dataset-id + --type + 轴字段")
        payload = build_chart_view(
            client,
            chart_id=args.chart_id or snowflake_id(),
            scene_id=args.scene_id or "0",
            dataset_id=args.dataset_id,
            chart_type=args.type,
            title=args.title or "预览",
            x_axis=json.loads(args.x_axis) if args.x_axis else None,
            y_axis=json.loads(args.y_axis) if args.y_axis else None,
            x_axis_ext=json.loads(args.x_axis_ext) if args.x_axis_ext else None,
            ext_stack=json.loads(args.ext_stack) if args.ext_stack else None,
            custom_filter=json.loads(args.custom_filter) if args.custom_filter else {},
        )
    data = client.post("/chartData/getData", payload)
    _print_json(data)


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    body = {
        "id": args.id,
        "busiFlag": "dataV",
        "resourceTable": args.resource_table,
        "source": "main-edit" if args.resource_table == "snapshot" else "main",
    }
    data = client.post("/dataVisualization/findById", body)
    if args.summary and isinstance(data, dict):
        try:
            comps = json.loads(data.get("componentData") or "[]")
        except json.JSONDecodeError:
            comps = []
        views = data.get("canvasViewInfo") or {}
        _print_json(
            {
                "id": data.get("id"),
                "name": data.get("name"),
                "pid": data.get("pid"),
                "status": data.get("status"),
                "resourceTable": args.resource_table,
                "componentCount": len(comps) if isinstance(comps, list) else 0,
                "viewCount": len(views) if isinstance(views, dict) else 0,
                "components": [
                    {
                        "id": c.get("id"),
                        "component": c.get("component"),
                        "innerType": c.get("innerType"),
                        "name": c.get("name"),
                    }
                    for c in (comps if isinstance(comps, list) else [])
                ],
            }
        )
        return
    _print_json(data)


def cmd_publish(client: DataEaseClient, args: argparse.Namespace) -> None:
    """将 snapshot 发布到 core（status=1）。须 --i-confirm-publish。"""
    if not args.i_confirm_publish:
        raise DataEaseClientError(
            "发布会把编辑镜像同步到正式预览。请确认后加 --i-confirm-publish"
        )
    _remind_backup_and_admin(client, mutating=True)
    _assert_within_write_scope(client, args.id, role="发布大屏", kind="dataV")
    snap = client.post(
        "/dataVisualization/findById",
        {
            "id": args.id,
            "busiFlag": "dataV",
            "resourceTable": "snapshot",
            "source": "main-edit",
        },
    )
    if not isinstance(snap, dict):
        raise DataEaseClientError(f"找不到大屏 id={args.id}")
    views = snap.get("canvasViewInfo") or {}
    active = list(views.keys()) if isinstance(views, dict) else []
    status = 0 if args.unpublish else 1
    client.post(
        "/dataVisualization/updatePublishStatus",
        {
            "id": str(args.id),
            "name": args.name or snap.get("name"),
            "mobileLayout": bool(snap.get("mobileLayout") or False),
            "status": status,
            "activeViewIds": active,
            "type": "dataV",
        },
    )
    _print_json({"id": str(args.id), "status": status, "activeViewIds": active})


def cmd_create_empty(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    pid = _resolve_datav_pid(client, args)
    _assert_within_write_scope(client, pid, role="写入父目录", kind="dataV")
    style = default_canvas_style(
        width=args.width,
        height=args.height,
        background_color=args.background_color,
    )
    payload = {
        "name": args.name,
        "pid": pid,
        "type": "dataV",
        "status": 0,
        "mobileLayout": False,
        "selfWatermarkStatus": True,
        "dataState": "prepare",
        "contentId": str(uuid.uuid4()).replace("-", ""),
        "canvasStyleData": json.dumps(style, ensure_ascii=False, separators=(",", ":")),
        "componentData": "[]",
        "canvasViewInfo": {},
        "appData": None,
        "watermarkInfo": None,
        "nodeType": "panel",
    }
    new_id = client.post("/dataVisualization/saveCanvas", payload)
    _print_json({"id": new_id, "name": args.name, "pid": pid, "type": "dataV", "status": 0})


def _layout(item: dict, defaults: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    lay = item.get("layout") or {}
    left, top, width, height = defaults
    return (
        int(lay.get("left", left)),
        int(lay.get("top", top)),
        int(lay.get("width", width)),
        int(lay.get("height", height)),
    )


def build_from_plan(client: DataEaseClient, plan: dict, *, scene_id: str) -> tuple[list, dict, dict]:
    """返回 (componentData_list, canvasViewInfo, canvasStyle overlay)."""
    components: list = []
    views: dict = {}
    canvas_over = plan.get("canvas") or {}

    # 装饰先画（底层），图表后叠
    for i, dec in enumerate(plan.get("decorations") or []):
        kind = dec.get("kind") or dec.get("component")
        if not kind:
            raise DataEaseClientError(f"decorations[{i}] 缺少 kind")
        left, top, width, height = _layout(dec, (40 + i * 20, 40, 400, 80))
        cid = str(dec.get("id") or snowflake_id())
        components.append(
            decoration_component(
                cid=cid,
                kind=kind,
                left=left,
                top=top,
                width=width,
                height=height,
                prop_value=dec.get("propValue", dec.get("text")),
                style_extra=dec.get("style"),
                inner_type=dec.get("innerType"),
            )
        )

    for i, ch in enumerate(plan.get("charts") or []):
        chart_type = ch.get("type")
        if not chart_type:
            raise DataEaseClientError(f"charts[{i}] 缺少 type")
        dataset_id = ch.get("datasetId") or ch.get("tableId") or plan.get("datasetId")
        if not dataset_id and chart_type != "rich-text":
            raise DataEaseClientError(f"charts[{i}] 缺少 datasetId")
        title = ch.get("title") or ch.get("name") or f"图表{i+1}"
        left, top, width, height = _layout(ch, (40 + (i % 2) * 940, 120 + (i // 2) * 420, 900, 380))
        cid = str(ch.get("id") or snowflake_id())
        components.append(
            user_view_component(
                cid=cid,
                chart_type=chart_type,
                title=title,
                left=left,
                top=top,
                width=width,
                height=height,
            )
        )
        if chart_type == "rich-text" and not dataset_id:
            view = base_view_config()
            view["id"] = cid
            view["sceneId"] = str(scene_id)
            view["type"] = "rich-text"
            view["title"] = title
            view["tableId"] = ""
            views[cid] = view
        else:
            view = build_chart_view(
                client,
                chart_id=cid,
                scene_id=scene_id,
                dataset_id=str(dataset_id),
                chart_type=chart_type,
                title=title,
                x_axis=ch.get("xAxis"),
                y_axis=ch.get("yAxis"),
                x_axis_ext=ch.get("xAxisExt"),
                ext_stack=ch.get("extStack"),
                custom_filter=ch.get("customFilter"),
                extra_view=ch.get("view"),
            )
            if not ch.get("skipPreview"):
                try:
                    client.post("/chartData/getData", view)
                    print(f"preview ok chart={title} type={chart_type}", file=sys.stderr)
                except DataEaseClientError as e:
                    raise DataEaseClientError(f"图表「{title}」取数预览失败，已中止保存: {e}") from e
            views[cid] = view

    return components, views, canvas_over


def cmd_apply(client: DataEaseClient, args: argparse.Namespace) -> None:
    """对已有大屏（或新建）应用 plan JSON：装饰 + 图表排版。"""
    _remind_backup_and_admin(client, mutating=True)
    plan = _load_json(args.json, args.file)
    if not isinstance(plan, dict):
        raise DataEaseClientError("apply 需要 --file/--json 计划对象")

    dv_id = args.id or plan.get("id")
    current: Optional[dict] = None
    if dv_id:
        _assert_within_write_scope(client, dv_id, role="更新大屏", kind="dataV")
        current = client.post(
            "/dataVisualization/findById",
            {
                "id": dv_id,
                "busiFlag": "dataV",
                "resourceTable": "snapshot",
                "source": "main-edit",
            },
        )
        if not isinstance(current, dict):
            raise DataEaseClientError(f"找不到大屏 id={dv_id}")
        scene_id = str(current.get("id") or dv_id)
        try:
            style = json.loads(current.get("canvasStyleData") or "{}")
        except json.JSONDecodeError:
            style = default_canvas_style()
        name = plan.get("name") or current.get("name")
        pid = current.get("pid")
    else:
        pid = plan.get("pid")
        if plan.get("folderName") or plan.get("folder_name"):
            pid = _resolve_folder(
                client,
                folder_name=plan.get("folderName") or plan.get("folder_name"),
                kind="dataV",
            )
        elif pid is not None:
            pid = _resolve_folder(client, folder_id=pid, kind="dataV")
        else:
            raise DataEaseClientError("新建大屏须在 plan 中提供 pid 或 folderName")
        _assert_within_write_scope(client, pid, role="写入父目录", kind="dataV")
        name = plan.get("name") or "未命名数据大屏"
        style = default_canvas_style()
        empty = {
            "name": name,
            "pid": pid,
            "type": "dataV",
            "status": 0,
            "mobileLayout": False,
            "selfWatermarkStatus": True,
            "dataState": "prepare",
            "contentId": str(uuid.uuid4()).replace("-", ""),
            "canvasStyleData": json.dumps(style, ensure_ascii=False, separators=(",", ":")),
            "componentData": "[]",
            "canvasViewInfo": {},
            "appData": None,
            "watermarkInfo": None,
            "nodeType": "panel",
        }
        scene_id = str(client.post("/dataVisualization/saveCanvas", empty))
        print(f"created empty dataV id={scene_id}", file=sys.stderr)

    components, views, canvas_over = build_from_plan(client, plan, scene_id=scene_id)
    if canvas_over:
        for k, v in canvas_over.items():
            style[k] = v

    if args.append and current is not None:
        try:
            old_comps = json.loads(current.get("componentData") or "[]")
        except json.JSONDecodeError:
            old_comps = []
        if not isinstance(old_comps, list):
            old_comps = []
        old_views = current.get("canvasViewInfo") or {}
        if not isinstance(old_views, dict):
            old_views = {}
        components = list(old_comps) + components
        merged = dict(old_views)
        merged.update(views)
        views = merged

    payload = {
        "id": str(scene_id),
        "name": name,
        "pid": pid,
        "type": "dataV",
        "status": 0,
        "mobileLayout": False,
        "canvasStyleData": json.dumps(style, ensure_ascii=False, separators=(",", ":")),
        "componentData": json.dumps(components, ensure_ascii=False, separators=(",", ":")),
        "canvasViewInfo": views,
        "appData": None,
        "watermarkInfo": None,
        "nodeType": "panel",
    }
    result = client.post("/dataVisualization/updateCanvas", payload)
    _print_json(
        {
            "id": str(scene_id),
            "name": name,
            "pid": pid,
            "charts": len(plan.get("charts") or []),
            "decorations": len(plan.get("decorations") or []),
            "result": result,
        }
    )


def cmd_plan_example(_client: DataEaseClient, _args: argparse.Namespace) -> None:
    _print_json(
        {
            "name": "销售运营大屏",
            "folderName": "AI专用组织",
            "datasetId": "<默认数据集，可被单图覆盖>",
            "canvas": {"backgroundColor": "#020408", "width": 1920, "height": 1080},
            "decorations": [
                {
                    "kind": "ScrollText",
                    "text": "销售运营监控大屏",
                    "layout": {"left": 60, "top": 24, "width": 800, "height": 64},
                    "style": {"fontSize": 36, "color": "#ffffff", "fontWeight": 700},
                },
                {
                    "kind": "RectShape",
                    "layout": {"left": 0, "top": 0, "width": 1920, "height": 96},
                    "style": {"backgroundColor": "rgba(16,148,229,0.25)", "opacity": 0.9},
                },
            ],
            "charts": [
                {
                    "type": "indicator",
                    "title": "销售量合计",
                    "datasetId": "<DATASET_ID>",
                    "yAxis": [{"name": "销售量", "summary": "sum"}],
                    "layout": {"left": 60, "top": 120, "width": 420, "height": 220},
                },
                {
                    "type": "bar",
                    "title": "各省销售量",
                    "datasetId": "<DATASET_ID>",
                    "xAxis": ["省份"],
                    "yAxis": [{"name": "销售量", "summary": "sum"}],
                    "layout": {"left": 520, "top": 120, "width": 880, "height": 420},
                    "customFilter": {},
                },
                {
                    "type": "pie",
                    "title": "曝光类型占比",
                    "datasetId": "<DATASET_ID>",
                    "xAxis": ["曝光类型"],
                    "yAxis": [{"name": "销售量", "summary": "sum"}],
                    "layout": {"left": 1420, "top": 120, "width": 440, "height": 420},
                },
                {
                    "type": "line",
                    "title": "按统计日期趋势",
                    "datasetId": "<DATASET_ID>",
                    "xAxis": ["统计日期"],
                    "yAxis": [{"name": "销售量", "summary": "sum"}],
                    "layout": {"left": 60, "top": 580, "width": 1340, "height": 420},
                },
            ],
        }
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 数据大屏 dataV CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="图表类型与装饰组件清单").set_defaults(func=cmd_catalog)

    t = sub.add_parser("tree", help="数据大屏资源树")
    t.add_argument("--name", default=None)
    t.set_defaults(func=cmd_tree)

    rf = sub.add_parser("resolve-folder", help="在数据大屏树上解析文件夹")
    rf.add_argument("--id", default=None)
    rf.add_argument("--name", default=None)
    rf.set_defaults(func=cmd_resolve_folder)

    ds = sub.add_parser("datasets", help="列出数据集（选型，不修改）")
    ds.add_argument("--name", default=None)
    ds.add_argument("--flat", action="store_true", help="扁平列出叶子数据集")
    ds.set_defaults(func=cmd_datasets)

    f = sub.add_parser("fields", help="数据集维度/指标字段（listByDQ）")
    f.add_argument("--dataset-id", required=True)
    f.add_argument("--chart-id", default=None)
    f.add_argument("--simplify", action="store_true")
    f.set_defaults(func=cmd_fields)

    g = sub.add_parser("get", help="大屏详情（编辑内容默认看 snapshot）")
    g.add_argument("--id", required=True)
    g.add_argument(
        "--resource-table",
        default="snapshot",
        choices=["core", "snapshot"],
        help="未发布内容在 snapshot；发布后 core 与之对齐",
    )
    g.add_argument("--summary", action="store_true", help="只打印组件摘要")
    g.set_defaults(func=cmd_get)

    pub = sub.add_parser("publish", help="发布/取消发布大屏")
    pub.add_argument("--id", required=True)
    pub.add_argument("--name", default=None)
    pub.add_argument("--publish", action="store_true", default=True, help="发布 status=1（默认）")
    pub.add_argument("--unpublish", action="store_true", help="取消发布 status=0")
    pub.add_argument("--i-confirm-publish", action="store_true")
    pub.set_defaults(func=cmd_publish)

    ce = sub.add_parser("create-empty", help="新建空数据大屏")
    ce.add_argument("--name", required=True)
    ce.add_argument("--pid", type=int, default=None)
    ce.add_argument("--folder-name", default=None)
    ce.add_argument("--width", type=int, default=1920)
    ce.add_argument("--height", type=int, default=1080)
    ce.add_argument("--background-color", default="#020408")
    ce.set_defaults(func=cmd_create_empty)

    pv = sub.add_parser("preview-chart", help="图表取数预览（保存前必做）")
    pv.add_argument("--file")
    pv.add_argument("--json")
    pv.add_argument("--dataset-id")
    pv.add_argument("--type")
    pv.add_argument("--title")
    pv.add_argument("--chart-id")
    pv.add_argument("--scene-id")
    pv.add_argument("--x-axis", help='JSON，如 ["省份"]')
    pv.add_argument("--y-axis", help='JSON，如 [{"name":"销售量","summary":"sum"}]')
    pv.add_argument("--x-axis-ext")
    pv.add_argument("--ext-stack")
    pv.add_argument("--custom-filter", help="FilterTree JSON")
    pv.set_defaults(func=cmd_preview_chart)

    ap = sub.add_parser("apply", help="按 plan JSON 创建/更新大屏（含预览校验）")
    ap.add_argument("--id", default=None, help="已有大屏 id；省略则新建")
    ap.add_argument("--file")
    ap.add_argument("--json")
    ap.add_argument("--append", action="store_true", help="追加组件而非整页替换")
    ap.set_defaults(func=cmd_apply)

    sub.add_parser("plan-example", help="打印 plan JSON 示例").set_defaults(func=cmd_plan_example)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        # plan-example 可不连后端
        if args.command == "plan-example":
            args.func(None, args)  # type: ignore[arg-type]
            return 0
        if args.command == "catalog":
            # catalog 也可离线
            try:
                client = DataEaseClient()
            except DataEaseClientError:
                client = None  # type: ignore
            if client is None:
                cmd_catalog(None, args)  # type: ignore[arg-type]
            else:
                args.func(client, args)
            return 0
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
