#!/usr/bin/env python3
"""DataEase V3 仪表板（dashboard）CLI —— 矩阵排版创建/发布。

环境变量同 datasource.py：DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY / DE_ALLOWED_WRITE_SCOPE

与 dataV 共用图表取数与数据集纪律；布局用矩阵 x/y/sizeX/sizeY（72×36），亮色主题。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError
from de_ids import snowflake_id
from dashboard_defaults import (
    CHART_TYPES,
    DECORATION_KINDS,
    SUMMARY_OPTIONS,
    apply_light_view_theme,
    decoration_component,
    default_canvas_style,
    normalize_decoration_kind,
    rich_text_title_component,
    user_view_component,
)
from dashboard_layouts import all_layouts, apply_template_to_plan, get_layout
from datav import build_chart_view, cmd_datasets, cmd_fields, cmd_preview_chart
from datav_defaults import base_view_config
from datasource import (
    _assert_within_write_scope,
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


def _resolve_dashboard_pid(client: DataEaseClient, args: argparse.Namespace) -> str:
    if getattr(args, "folder_name", None):
        return _resolve_folder(client, folder_name=args.folder_name, kind="dashboard")
    if getattr(args, "pid", None) is None:
        raise DataEaseClientError("必须指定目标文件夹 --pid 或 --folder-name（仪表板树）")
    return _resolve_folder(client, folder_id=args.pid, kind="dashboard")


def cmd_catalog(_client: DataEaseClient, _args: argparse.Namespace) -> None:
    layouts = [
        {
            "id": m["id"],
            "name": m["name"],
            "aliases": m.get("aliases"),
            "description": m.get("description"),
            "contentSlots": m.get("contentSlots"),
            "titleSlot": m.get("titleSlot"),
        }
        for m in all_layouts()
    ]
    _print_json(
        {
            "charts": [
                {"type": k, **v}
                for k, v in CHART_TYPES.items()
                if v.get("category") != "other" or k == "rich-text"
            ],
            "decorations": [{"kind": k, **v} for k, v in DECORATION_KINDS.items()],
            "layouts": layouts,
            "summaries": list(SUMMARY_OPTIONS),
            "notes": [
                "仪表板 type/busiFlag=dashboard；亮色主题；矩阵 72×36（x/y/sizeX/sizeY）",
                "布局：grid_2x2 / grid_3x2 / kpi_charts；plan 设 layout 后自动填槽位",
                "勿与 dataV 组织根/文件夹 id 混用；写入 scope 须含仪表板树节点",
                "图表取数与大屏相同；保存前预览失败则中止",
                "标题用富文本 render=custom + 居中 textValue（亮色字）",
            ],
        }
    )


def cmd_layouts(_client: DataEaseClient, args: argparse.Namespace) -> None:
    if args.id or args.name:
        try:
            tpl = get_layout(args.id or args.name)
        except ValueError as e:
            raise DataEaseClientError(str(e)) from e
        _print_json(tpl)
        return
    _print_json(all_layouts())


def cmd_tree(client: DataEaseClient, args: argparse.Namespace) -> None:
    body: dict[str, Any] = {"busiFlag": "dashboard"}
    if args.name:
        body["name"] = args.name
    _print_json(client.post("/dataVisualization/tree", body))


def cmd_resolve_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    from datasource import cmd_resolve_folder as _ds_resolve

    args.kind = "dashboard"
    _ds_resolve(client, args)


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    body = {
        "id": args.id,
        "busiFlag": "dashboard",
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
                "type": data.get("type") or "dashboard",
                "resourceTable": args.resource_table,
                "componentCount": len(comps) if isinstance(comps, list) else 0,
                "viewCount": len(views) if isinstance(views, dict) else 0,
                "components": [
                    {
                        "id": c.get("id"),
                        "component": c.get("component"),
                        "innerType": c.get("innerType"),
                        "name": c.get("name"),
                        "x": c.get("x"),
                        "y": c.get("y"),
                        "sizeX": c.get("sizeX"),
                        "sizeY": c.get("sizeY"),
                    }
                    for c in (comps if isinstance(comps, list) else [])
                ],
            }
        )
        return
    _print_json(data)


def cmd_publish(client: DataEaseClient, args: argparse.Namespace) -> None:
    if not args.i_confirm_publish:
        raise DataEaseClientError(
            "发布会把编辑镜像同步到正式预览。请确认后加 --i-confirm-publish"
        )
    _remind_backup_and_admin(client, mutating=True)
    _assert_within_write_scope(client, args.id, role="发布仪表板", kind="dashboard")
    snap = client.post(
        "/dataVisualization/findById",
        {
            "id": args.id,
            "busiFlag": "dashboard",
            "resourceTable": "snapshot",
            "source": "main-edit",
        },
    )
    if not isinstance(snap, dict):
        raise DataEaseClientError(f"找不到仪表板 id={args.id}")
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
            "type": "dashboard",
        },
    )
    _print_json({"id": str(args.id), "status": status, "activeViewIds": active})


def cmd_create_empty(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    pid = _resolve_dashboard_pid(client, args)
    _assert_within_write_scope(client, pid, role="写入父目录", kind="dashboard")
    style = default_canvas_style(
        width=args.width,
        height=args.height,
        background_color=args.background_color,
    )
    payload = {
        "name": args.name,
        "pid": pid,
        "type": "dashboard",
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
    _print_json(
        {"id": new_id, "name": args.name, "pid": pid, "type": "dashboard", "status": 0}
    )


def _matrix_layout(item: dict, defaults: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    lay = item.get("layout") or {}
    x, y, sx, sy = defaults
    return (
        int(lay.get("x", x)),
        int(lay.get("y", y)),
        int(lay.get("sizeX", sx)),
        int(lay.get("sizeY", sy)),
    )


def build_from_plan(client: DataEaseClient, plan: dict, *, scene_id: str) -> tuple[list, dict, dict]:
    if plan.get("_resolvedLayout"):
        print(
            f"layout={plan['_resolvedLayout'].get('id')} ({plan['_resolvedLayout'].get('name')})",
            file=sys.stderr,
        )

    components: list = []
    views: dict = {}
    canvas_over = plan.get("canvas") or {}

    for i, dec in enumerate(plan.get("decorations") or []):
        kind_raw = dec.get("kind") or dec.get("component")
        if not kind_raw:
            raise DataEaseClientError(f"decorations[{i}] 缺少 kind")
        kind = normalize_decoration_kind(str(kind_raw))
        x, y, sx, sy = _matrix_layout(dec, (1 + i, 1, 18, 4))
        cid = str(dec.get("id") or snowflake_id())
        if kind in ("rich-text", "UserView") and (
            dec.get("role") == "title"
            or dec.get("innerType") == "rich-text"
            or kind == "rich-text"
        ):
            text = (
                dec.get("text")
                or (dec.get("propValue") or {}).get("textValue")
                or plan.get("title")
                or "大标题"
            )
            if isinstance(dec.get("propValue"), dict) and dec["propValue"].get("textValue"):
                comp = user_view_component(
                    cid=cid,
                    chart_type="rich-text",
                    title=str(text)[:40],
                    x=x,
                    y=y,
                    size_x=sx,
                    size_y=sy,
                )
                comp["name"] = "富文本"
                comp["label"] = "富文本"
                comp["icon"] = "rich-text"
                comp["render"] = "custom"
                comp["propValue"] = dict(dec["propValue"])
                comp["propValue"].setdefault("verticalAlign", "center-align")
                view = base_view_config()
                view["id"] = cid
                view["type"] = "rich-text"
                view["render"] = "custom"
                view["title"] = str(text)[:40]
                view["tableId"] = ""
                view["customStyle"]["text"]["show"] = False
                apply_light_view_theme(view)
            else:
                comp, view = rich_text_title_component(
                    cid=cid,
                    text=str(text),
                    x=x,
                    y=y,
                    size_x=sx,
                    size_y=sy,
                    font_size=int(dec.get("fontSize") or 28),
                    color=str(dec.get("color") or "#000000"),
                )
            view["sceneId"] = str(scene_id)
            view["render"] = "custom"
            if isinstance(dec.get("commonBackground"), dict):
                bg = dict(comp.get("commonBackground") or {})
                bg.update(dec["commonBackground"])
                comp["commonBackground"] = bg
            components.append(comp)
            views[cid] = view
            continue
        if kind == "Picture":
            media_url = dec.get("url")
            pv = dec.get("propValue")
            if not media_url and isinstance(pv, dict):
                media_url = pv.get("url")
            if not media_url:
                raise DataEaseClientError(f"decorations[{i}] Picture 缺少 url")
            components.append(
                decoration_component(
                    cid=cid,
                    kind="Picture",
                    x=x,
                    y=y,
                    size_x=sx,
                    size_y=sy,
                    prop_value=pv if isinstance(pv, dict) else None,
                    url=str(media_url),
                    style_extra=dec.get("style"),
                )
            )
            continue
        components.append(
            decoration_component(
                cid=cid,
                kind=kind,
                x=x,
                y=y,
                size_x=sx,
                size_y=sy,
                prop_value=dec.get("propValue", dec.get("text")),
                style_extra=dec.get("style"),
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
        # 默认：两列瀑布式占位
        col = i % 2
        row = i // 2
        x, y, sx, sy = _matrix_layout(
            ch, (1 + col * 36, 5 + row * 16, 36, 16)
        )
        cid = str(ch.get("id") or snowflake_id())
        components.append(
            user_view_component(
                cid=cid,
                chart_type=chart_type,
                title=title,
                x=x,
                y=y,
                size_x=sx,
                size_y=sy,
            )
        )
        if isinstance(ch.get("commonBackground"), dict):
            bg = dict(components[-1].get("commonBackground") or {})
            bg.update(ch["commonBackground"])
            components[-1]["commonBackground"] = bg
        if chart_type == "rich-text" and not dataset_id:
            view = base_view_config()
            view["id"] = cid
            view["sceneId"] = str(scene_id)
            view["type"] = "rich-text"
            view["render"] = "custom"
            view["title"] = title
            view["tableId"] = ""
            apply_light_view_theme(view)
            views[cid] = view
            components[-1]["render"] = "custom"
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
                extra_view=ch.get("extraView") or ch.get("view"),
            )
            apply_light_view_theme(view)
            if not ch.get("skipPreview"):
                try:
                    client.post("/chartData/getData", view)
                    print(f"preview ok chart={title} type={chart_type}", file=sys.stderr)
                except DataEaseClientError as e:
                    raise DataEaseClientError(
                        f"图表「{title}」取数预览失败，已中止保存: {e}"
                    ) from e
            views[cid] = view

    return components, views, canvas_over


def cmd_apply(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    plan = _load_json(args.json, args.file)
    if not isinstance(plan, dict):
        raise DataEaseClientError("apply 需要 --file/--json 计划对象")
    try:
        plan = apply_template_to_plan(plan)
    except ValueError as e:
        raise DataEaseClientError(str(e)) from e

    dv_id = args.id or plan.get("id")
    current: Optional[dict] = None
    if dv_id:
        _assert_within_write_scope(client, dv_id, role="更新仪表板", kind="dashboard")
        current = client.post(
            "/dataVisualization/findById",
            {
                "id": dv_id,
                "busiFlag": "dashboard",
                "resourceTable": "snapshot",
                "source": "main-edit",
            },
        )
        if not isinstance(current, dict):
            raise DataEaseClientError(f"找不到仪表板 id={dv_id}")
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
                kind="dashboard",
            )
        elif pid is not None:
            pid = _resolve_folder(client, folder_id=pid, kind="dashboard")
        else:
            raise DataEaseClientError("新建仪表板须在 plan 中提供 pid 或 folderName")
        _assert_within_write_scope(client, pid, role="写入父目录", kind="dashboard")
        name = plan.get("name") or "未命名仪表板"
        style = default_canvas_style()
        empty = {
            "name": name,
            "pid": pid,
            "type": "dashboard",
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
        print(f"created empty dashboard id={scene_id}", file=sys.stderr)

    components, views, canvas_over = build_from_plan(client, plan, scene_id=scene_id)
    if canvas_over:
        for k, v in canvas_over.items():
            style[k] = v
    style["dvType"] = "dashboard"
    if "dashboard" in style and isinstance(style["dashboard"], dict):
        style["dashboard"].setdefault("themeColor", "light")

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
        "type": "dashboard",
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
            "type": "dashboard",
            "layout": (plan.get("_resolvedLayout") or {}).get("id"),
            "charts": len(plan.get("charts") or []),
            "decorations": len(plan.get("decorations") or []),
            "result": result,
        }
    )


def cmd_plan_example(_client: DataEaseClient, args: argparse.Namespace) -> None:
    layout = getattr(args, "layout", None) or "grid_2x2"
    if layout in ("free", "none", "manual"):
        _print_json(
            {
                "name": "销售运营仪表板",
                "folderName": "目标文件夹",
                "datasetId": "<DATASET_ID>",
                "canvas": {"backgroundColor": "#f5f6f7"},
                "charts": [
                    {
                        "type": "bar",
                        "title": "示例图",
                        "xAxis": ["省份"],
                        "yAxis": [{"name": "销售量", "summary": "sum"}],
                        "layout": {"x": 1, "y": 5, "sizeX": 36, "sizeY": 16},
                    }
                ],
            }
        )
        return
    try:
        tpl = get_layout(layout)
    except ValueError as e:
        raise DataEaseClientError(str(e)) from e
    charts = []
    if tpl["id"] == "kpi_charts":
        sample_types = ["indicator", "indicator", "indicator", "indicator", "bar", "pie"]
    else:
        sample_types = ["indicator", "bar", "pie", "line", "table-info", "bar"]
    for i, slot in enumerate(tpl["contentSlots"]):
        t = sample_types[i % len(sample_types)]
        ch: dict[str, Any] = {
            "slot": slot,
            "type": t,
            "title": f"内容-{slot}",
            "datasetId": "<DATASET_ID>",
            "yAxis": [{"name": "销售量", "summary": "sum"}],
        }
        if t != "indicator":
            ch["xAxis"] = ["省份"]
        if t == "table-info":
            ch["xAxis"] = ["省份", "销售量"]
            ch.pop("yAxis", None)
        if t == "indicator":
            ch.pop("xAxis", None)
        charts.append(ch)
    _print_json(
        {
            "name": "模板仪表板示例",
            "title": "经营概览",
            "folderName": "目标文件夹",
            "layout": tpl["id"],
            "datasetId": "<DATASET_ID>",
            "canvas": {"backgroundColor": "#f5f6f7"},
            "charts": charts,
            "_layoutMeta": {
                "name": tpl["name"],
                "contentSlots": tpl["contentSlots"],
                "hint": "指定 layout 后写矩阵槽位；也可用 layout:{x,y,sizeX,sizeY} 手写",
            },
        }
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 仪表板 dashboard CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="图表类型与布局模板清单").set_defaults(func=cmd_catalog)

    ly = sub.add_parser("layouts", help="列出或查看矩阵布局槽位")
    ly.add_argument("--id", default=None)
    ly.add_argument("--name", default=None)
    ly.set_defaults(func=cmd_layouts)

    t = sub.add_parser("tree", help="仪表板资源树")
    t.add_argument("--name", default=None)
    t.set_defaults(func=cmd_tree)

    rf = sub.add_parser("resolve-folder", help="在仪表板树上解析文件夹")
    rf.add_argument("--id", default=None)
    rf.add_argument("--name", default=None)
    rf.set_defaults(func=cmd_resolve_folder)

    ds = sub.add_parser("datasets", help="列出数据集（选型，不修改）")
    ds.add_argument("--name", default=None)
    ds.add_argument("--flat", action="store_true")
    ds.set_defaults(func=cmd_datasets)

    f = sub.add_parser("fields", help="数据集维度/指标字段")
    f.add_argument("--dataset-id", required=True)
    f.add_argument("--chart-id", default=None)
    f.add_argument("--simplify", action="store_true")
    f.set_defaults(func=cmd_fields)

    g = sub.add_parser("get", help="仪表板详情")
    g.add_argument("--id", required=True)
    g.add_argument(
        "--resource-table",
        default="snapshot",
        choices=["core", "snapshot"],
    )
    g.add_argument("--summary", action="store_true")
    g.set_defaults(func=cmd_get)

    pub = sub.add_parser("publish", help="发布/取消发布仪表板")
    pub.add_argument("--id", required=True)
    pub.add_argument("--name", default=None)
    pub.add_argument("--unpublish", action="store_true")
    pub.add_argument("--i-confirm-publish", action="store_true")
    pub.set_defaults(func=cmd_publish)

    ce = sub.add_parser("create-empty", help="新建空仪表板")
    ce.add_argument("--name", required=True)
    ce.add_argument("--pid", type=int, default=None)
    ce.add_argument("--folder-name", default=None)
    ce.add_argument("--width", type=int, default=1920)
    ce.add_argument("--height", type=int, default=1080)
    ce.add_argument("--background-color", default="#f5f6f7")
    ce.set_defaults(func=cmd_create_empty)

    pv = sub.add_parser("preview-chart", help="图表取数预览")
    pv.add_argument("--file")
    pv.add_argument("--json")
    pv.add_argument("--dataset-id")
    pv.add_argument("--type")
    pv.add_argument("--title")
    pv.add_argument("--chart-id")
    pv.add_argument("--scene-id")
    pv.add_argument("--x-axis")
    pv.add_argument("--y-axis")
    pv.add_argument("--x-axis-ext")
    pv.add_argument("--ext-stack")
    pv.add_argument("--custom-filter")
    pv.set_defaults(func=cmd_preview_chart)

    ap = sub.add_parser("apply", help="按 plan JSON 创建/更新仪表板")
    ap.add_argument("--id", default=None)
    ap.add_argument("--file")
    ap.add_argument("--json")
    ap.add_argument("--append", action="store_true")
    ap.set_defaults(func=cmd_apply)

    pe = sub.add_parser("plan-example", help="打印 plan JSON 示例")
    pe.add_argument("--layout", default="grid_2x2", help="grid_2x2|grid_3x2|kpi_charts|free")
    pe.set_defaults(func=cmd_plan_example)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        offline = {"plan-example", "catalog", "layouts"}
        if args.command in offline:
            args.func(None, args)  # type: ignore[arg-type]
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
