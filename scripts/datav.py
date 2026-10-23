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
import panel_link
import panel_schema
from datav_defaults import (
    CHART_TYPES,
    DECORATION_KINDS,
    SUMMARY_OPTIONS,
    base_view_config,
    chart_render,
    decoration_component,
    default_canvas_style,
    normalize_decoration_kind,
    rich_text_title_component,
    user_view_component,
)
from datav_layouts import all_layouts, apply_template_to_plan, get_layout
from datasource import (
    _assert_within_write_scope,
    _load_tree_index,
    _remind_backup_and_admin,
    _resolve_folder,
)
from panel_schema import set_path


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
                {"type": k, **v} for k, v in CHART_TYPES.items() if v.get("category") != "other" or k == "rich-text"
            ],
            "decorations": [{"kind": k, **v} for k, v in DECORATION_KINDS.items()],
            "layouts": layouts,
            "summaries": list(SUMMARY_OPTIONS),
            "notes": [
                "大屏画布默认 1920×1080 暗色；组件用 style.left/top/width/height（像素）",
                "布局模板：grid_3x4（平均分布 3×4）、center_v2（居中结构-形式二）；plan 设 layout 后自动填槽位",
                "UserView 的 id 必须与 canvasViewInfo 的 key 一致",
                "聚合 summary 配在指标字段上，不是图表顶层",
                "图表样式用 charts[].config + 友好键（label.show / legend.show / xAxis.color），先 defaults --group chart 查清单",
                "联动写 plan.linkage，跳转写 plan.jump；也可用 linkage/jump 子命令单独维护（图表需先保存）",
                "全局默认配置（刷新/适配/栅格/统一组件风格）写在 plan.canvas，支持 component.chartTitle.show 这类点号路径",
                "图片 Picture：decorations 写 kind=Picture + url（写入 propValue.url）；可选 adaptation",
                "视频 DeVideo：decorations 写 kind=DeVideo + url（写入 videoLinks.web.src）；勿把地址塞进 propValue",
                "美化示范：canvas.background + 组件 commonBackground.outerImage；配色用 charts[].extraView；见 examples/datav_showcase_center_beautify.md",
                "视觉规范：references/datav_visual.md（主视觉层级、淡彩/渐变、外框色系统一）",
                "生成的美化图只放用户工作区，禁止写入正式 skill 目录",
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


# 图表样式容器的归属：友好键首段 → 实际存放位置
# xAxis/yAxis 在顶层是「字段数组」，样式则放在 customStyle 下，故此处按样式处理
_CHART_ATTR_ROOTS = {
    "basicStyle": "customAttr",
    "label": "customAttr",
    "tooltip": "customAttr",
    "indicator": "customAttr",
    "indicatorName": "customAttr",
    "tableHeader": "customAttr",
    "tableCell": "customAttr",
    "tableTotal": "customAttr",
    "misc": "customAttr",
    "map": "customAttr",
    "text": "customStyle",
    "legend": "customStyle",
    "xAxis": "customStyle",
    "yAxis": "customStyle",
    "yAxisExt": "customStyle",
    "senior": "senior",
}
_DIRECT_ROOTS = ("customAttr", "customStyle", "senior")
_CHART_TOP_KEYS = {
    "title",
    "resultCount",
    "resultMode",
    "refreshViewEnable",
    "refreshTime",
    "refreshUnit",
    "linkageActive",
    "jumpActive",
    "customFilter",
    "xAxisExt",
    "extStack",
    "drillFields",
}


def resolve_chart_path(key: str) -> str:
    """把配置项名解析成视图里的真实路径；无法识别则报错并给近似项。"""
    k = str(key or "").strip()
    if not k:
        raise DataEaseClientError("图表配置项名不能为空")
    if k in _CHART_TOP_KEYS:
        return k
    head = k.split(".")[0]
    if head in _DIRECT_ROOTS:
        return k
    if "." in k:
        root = _CHART_ATTR_ROOTS.get(head)
        if root:
            full = f"{root}.{k}"
            # 简写形式必须命中注册表，防止 label.shw 这类笔误被静默写进视图
            if panel_schema.lookup(full):
                return full
            sug = panel_schema.suggest(full)
            hint = f"你是否想配：{', '.join(sug)}" if sug else "运行 defaults --group chart 查看全部可配项"
            raise DataEaseClientError(f"不认识的图表配置项「{k}」。{hint}")
    if panel_schema.lookup(k):
        # 注册表里有，但不在图表视图上（例如面板级配置）
        raise DataEaseClientError(f"「{k}」是面板级配置，请写在 plan 的 canvas 里，不要写进 charts[].config")
    sug = panel_schema.suggest(k)
    hint = f"你是否想配：{', '.join(sug)}" if sug else "运行 defaults --group chart 查看全部可配项"
    raise DataEaseClientError(f"不认识的图表配置项「{k}」。{hint}")


def apply_chart_overrides(view: dict, overrides: Any) -> dict:
    """按友好键写入图表配置，键名必须在注册表内，避免臆造字段。"""
    if not overrides:
        return view
    if not isinstance(overrides, dict):
        raise DataEaseClientError("charts[].config 必须是对象，如 {\"label.show\": true}")
    for key, value in overrides.items():
        set_path(view, resolve_chart_path(key), value)
    return view


def lint_plan(plan: dict) -> list[dict]:
    """离线自检：只查结构性错误，不需要连接、不读数据集。"""
    issues: list[dict] = []

    def add(level: str, code: str, msg: str, where: str = "") -> None:
        issues.append({"level": level, "code": code, "message": msg, "where": where})

    if not isinstance(plan, dict):
        add("error", "plan_not_object", "plan 必须是 JSON 对象")
        return issues

    canvas = plan.get("canvas") or {}
    try:
        cw = int(canvas.get("width") or 1920)
        chh = int(canvas.get("height") or 1080)
    except (TypeError, ValueError):
        cw, chh = 1920, 1080
        add("warn", "canvas_size_invalid", "canvas 的 width/height 不是整数，按 1920×1080 处理")

    if not plan.get("id"):
        if not (plan.get("pid") or plan.get("folderName") or plan.get("folder_name")):
            add("error", "no_target", "新建大屏须给 pid 或 folderName；更新已有大屏须给 id")

    titles: dict[str, int] = {}
    charts = plan.get("charts") or []
    if not isinstance(charts, list):
        add("error", "charts_not_list", "charts 必须是数组")
        charts = []

    for i, c in enumerate(charts):
        where = f"charts[{i}]"
        if not isinstance(c, dict):
            add("error", "chart_not_object", f"{where} 必须是对象", where)
            continue
        ctype = c.get("type")
        if not ctype:
            add("error", "chart_no_type", f"{where} 缺少 type（图种）", where)
            continue
        if ctype not in CHART_TYPES:
            add("error", "chart_type_unknown", f"{where} 图种「{ctype}」不在清单内，catalog 可查", where)
        dataset_id = c.get("datasetId") or c.get("tableId") or plan.get("datasetId")
        if not dataset_id and ctype != "rich-text":
            add("error", "chart_no_dataset", f"{where} 在 plan 与自身都没给 datasetId", where)

        xa = c.get("xAxis") or []
        ya = c.get("yAxis") or []
        if ctype == "indicator":
            if xa:
                add("error", "indicator_has_xaxis", f"{where} 指标卡只吃 yAxis，xAxis 必须为空", where)
            if len(ya) != 1:
                add("error", "indicator_yaxis_count", f"{where} 指标卡 yAxis 必须正好 1 个数值指标", where)
        if ctype in ("pie", "pie-donut", "pie-rose", "pie-donut-rose", "treemap", "gauge", "liquid"):
            if len(ya) > 1:
                add("error", "single_quota_only", f"{where} 图种「{ctype}」只支持 1 个指标", where)
        if ctype == "table-info":
            if ya:
                add("error", "table_info_has_yaxis", f"{where} 明细表列放 xAxis，yAxis 必须为空", where)
            if not xa:
                add("error", "table_info_no_columns", f"{where} 明细表至少要给 1 个 xAxis 列", where)
        if ctype in ("bar-stack", "bar-stack-horizontal", "area-stack") and not (
            c.get("extStack") or c.get("xAxisExt")
        ):
            add("warn", "stack_without_stack_field", f"{where} 堆叠图未给 extStack，会退化成普通图", where)

        cfg = c.get("config")
        if cfg is not None:
            if not isinstance(cfg, dict):
                add("error", "chart_config_not_object", f"{where} config 必须是对象", where)
            else:
                for k in cfg:
                    try:
                        resolve_chart_path(k)
                    except DataEaseClientError as e:
                        add("error", "chart_config_unknown", str(e), where)

        for misplaced in ("jump", "jumps", "linkage", "linkages"):
            if c.get(misplaced):
                add(
                    "warn",
                    "interaction_misplaced",
                    f"{where} 下的 {misplaced} 不会被读取：联动/跳转写在 plan 顶层，"
                    f"用 source 指定源图表，如 plan.{'jump' if misplaced.startswith('jump') else 'linkage'}[]",
                    where,
                )
                break

        lay = c.get("layout") or {}
        if isinstance(lay, dict) and lay:
            if {"x", "y", "sizeX", "sizeY"} & set(lay):
                # 仪表板矩阵坐标：72×36，1-based
                try:
                    mx = int(lay.get("x", 1))
                    my = int(lay.get("y", 1))
                    msx = int(lay.get("sizeX", 1))
                    msy = int(lay.get("sizeY", 1))
                except (TypeError, ValueError):
                    add("warn", "chart_layout_invalid", f"{where} layout 矩阵值必须是整数", where)
                else:
                    if msx <= 0 or msy <= 0:
                        add("warn", "chart_layout_empty", f"{where} layout sizeX/sizeY 必须为正", where)
                    if mx < 1 or my < 1:
                        add("warn", "chart_layout_negative", f"{where} 矩阵坐标从 1 开始", where)
                    if mx + msx - 1 > 72 or my + msy - 1 > 36:
                        add(
                            "warn",
                            "chart_layout_out_of_bounds",
                            f"{where} 超出 72×36 矩阵：x+sizeX-1={mx + msx - 1}, y+sizeY-1={my + msy - 1}",
                            where,
                        )
            elif {"left", "top", "width", "height"} & set(lay):
                # 大屏像素坐标
                try:
                    left = int(lay.get("left", 0))
                    top = int(lay.get("top", 0))
                    w = int(lay.get("width", 0))
                    h = int(lay.get("height", 0))
                except (TypeError, ValueError):
                    add("warn", "chart_layout_invalid", f"{where} layout 像素必须是整数", where)
                else:
                    if w <= 0 or h <= 0:
                        add("warn", "chart_layout_empty", f"{where} layout 宽高必须为正", where)
                    if left < 0 or top < 0:
                        add("warn", "chart_layout_negative", f"{where} layout 坐标不能为负", where)
                    if left + w > cw or top + h > chh:
                        add(
                            "warn",
                            "chart_layout_out_of_bounds",
                            f"{where} 超出画布（{cw}×{chh}）：left+width={left + w}, top+height={top + h}",
                            where,
                        )
        title = c.get("title") or c.get("name")
        if title:
            titles[str(title)] = titles.get(str(title), 0) + 1

    for t, n in titles.items():
        if n > 1:
            add(
                "warn",
                "duplicate_chart_title",
                f"图表标题「{t}」出现 {n} 次；联动/跳转按标题定位会失败，请改成唯一标题或改用组件 id",
            )

    deco = plan.get("decorations") or []
    for i, d in enumerate(deco):
        if not isinstance(d, dict):
            add("error", "decoration_not_object", f"decorations[{i}] 必须是对象")
            continue
        if not (d.get("kind") or d.get("component")):
            add("error", "decoration_no_kind", f"decorations[{i}] 缺少 kind")

    for i, item in enumerate(plan.get("linkage") or []):
        where = f"linkage[{i}]"
        if not isinstance(item, dict):
            add("error", "linkage_not_object", f"{where} 必须是对象", where)
            continue
        if not (item.get("source") or item.get("sourceView")):
            add("error", "linkage_no_source", f"{where} 缺少 source", where)
        if not (item.get("targets") or item.get("targetViews") or item.get("target")):
            add("error", "linkage_no_target", f"{where} 缺少 targets", where)

    for i, item in enumerate(plan.get("jump") or []):
        where = f"jump[{i}]"
        if not isinstance(item, dict):
            add("error", "jump_not_object", f"{where} 必须是对象", where)
            continue
        if not (item.get("source") or item.get("sourceView")):
            add("error", "jump_no_source", f"{where} 缺少 source", where)
        if not (item.get("field") or item.get("fields")):
            add("error", "jump_no_field", f"{where} 缺少 field（触发字段）", where)
        link_type = item.get("linkType") or "outer"
        if link_type not in panel_link.LINK_TYPES:
            add("error", "jump_bad_link_type", f"{where} linkType 只能是 {panel_link.LINK_TYPES}", where)
        if link_type == "inner":
            if not item.get("targetDvId"):
                add("error", "jump_inner_no_target", f"{where} 内部跳转必须给 targetDvId", where)
            if not item.get("targets"):
                add("error", "jump_inner_no_targets", f"{where} 内部跳转必须给 targets", where)
        else:
            if not item.get("content"):
                add("error", "jump_outer_no_content", f"{where} 外部链接必须给 content", where)
            elif len(str(item["content"])) > panel_link.CONTENT_MAX:
                add("error", "jump_content_too_long", f"{where} content 超过 {panel_link.CONTENT_MAX} 字符", where)

    return issues


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
    view["render"] = chart_render(chart_type)
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
    elif chart_type == "treemap":
        # 与 Treemap.setupDefaultOptions 一致：开标签（维度名+占比），关图例
        view["xAxis"] = _pick_fields(idx, x_axis, expect_group="d")
        view["yAxis"] = _pick_fields(idx, y_axis, expect_group="q", default_summary="sum")[:1]
        lab = view["customAttr"]["label"]
        lab["show"] = True
        lab["showDimension"] = True
        lab["showQuota"] = False
        lab["showProportion"] = True
        lab["reserveDecimalCount"] = 2
        lab["color"] = "#ffffff"
        lab["fontSize"] = 12
        view["customStyle"]["legend"]["show"] = False
    elif chart_type in ("bar-stack", "bar-stack-horizontal"):
        view["xAxis"] = _pick_fields(idx, x_axis, expect_group="d")
        view["yAxis"] = _pick_fields(idx, y_axis, expect_group="q", default_summary="sum")
        if ext_stack:
            view["extStack"] = _pick_fields(idx, ext_stack, expect_group="d")
        elif x_axis_ext:
            # 兼容误把堆叠维写在 xAxisExt
            view["extStack"] = _pick_fields(idx, x_axis_ext, expect_group="d")
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
    """返回 (componentData_list, canvasViewInfo, canvasStyle overlay)。plan 宜已 apply_template_to_plan。"""
    if plan.get("_resolvedLayout"):
        print(
            f"layout={plan['_resolvedLayout'].get('id')} ({plan['_resolvedLayout'].get('name')})",
            file=sys.stderr,
        )

    components: list = []
    views: dict = {}
    canvas_over = plan.get("canvas") or {}

    # 装饰 / 标题先画（底层），图表后叠
    for i, dec in enumerate(plan.get("decorations") or []):
        kind_raw = dec.get("kind") or dec.get("component")
        if not kind_raw:
            raise DataEaseClientError(f"decorations[{i}] 缺少 kind")
        kind = normalize_decoration_kind(str(kind_raw))
        left, top, width, height = _layout(dec, (40 + i * 20, 40, 400, 80))
        cid = str(dec.get("id") or snowflake_id())
        # 大标题等：富文本（界面居中对齐 → propValue.textValue），会进 canvasViewInfo
        if kind in ("rich-text", "UserView") and (
            dec.get("role") == "title" or dec.get("innerType") == "rich-text" or kind == "rich-text"
        ):
            text = dec.get("text") or (dec.get("propValue") or {}).get("textValue") or plan.get("title") or "大标题"
            # 若已带完整 propValue（用户从界面导出），优先原样使用
            if isinstance(dec.get("propValue"), dict) and dec["propValue"].get("textValue"):
                comp = user_view_component(
                    cid=cid,
                    chart_type="rich-text",
                    title=str(text)[:40],
                    left=left,
                    top=top,
                    width=width,
                    height=height,
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
            else:
                comp, view = rich_text_title_component(
                    cid=cid,
                    text=str(text),
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    font_size=int(dec.get("fontSize") or 36),
                    color=str(dec.get("color") or "#ffffff"),
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
        # 图片 / 视频：字段与界面媒体组件一致（不进 canvasViewInfo）
        if kind == "Picture":
            media_url = dec.get("url")
            pv = dec.get("propValue")
            if not media_url and isinstance(pv, dict):
                media_url = pv.get("url")
            elif not media_url and isinstance(pv, str):
                media_url = pv
            if not media_url:
                raise DataEaseClientError(
                    f"decorations[{i}] Picture 缺少 url（界面「图片」写入 propValue.url）"
                )
            components.append(
                decoration_component(
                    cid=cid,
                    kind="Picture",
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    prop_value=pv if isinstance(pv, dict) else None,
                    url=str(media_url),
                    adaptation=dec.get("adaptation") or (dec.get("style") or {}).get("adaptation"),
                    flip=dec.get("flip"),
                    style_extra=dec.get("style"),
                    inner_type=dec.get("innerType") or "Picture",
                )
            )
            continue
        if kind == "DeVideo":
            vlinks = dec.get("videoLinks") if isinstance(dec.get("videoLinks"), dict) else None
            media_url = dec.get("url") or dec.get("src")
            if not media_url and vlinks:
                vt = vlinks.get("videoType") or "web"
                node = vlinks.get(vt)
                media_url = node.get("src") if isinstance(node, dict) else None
            pv = dec.get("propValue")
            if not media_url and isinstance(pv, dict):
                media_url = pv.get("url") or pv.get("src")
            if not media_url and isinstance(pv, str):
                media_url = pv
            if not media_url:
                raise DataEaseClientError(
                    f"decorations[{i}] DeVideo 缺少 url（界面「视频」写入 videoLinks.web.src）"
                )
            components.append(
                decoration_component(
                    cid=cid,
                    kind="DeVideo",
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    url=str(media_url),
                    video_links=vlinks,
                    autoplay=dec.get("autoplay"),
                    loop=dec.get("loop"),
                    muted=dec.get("muted"),
                    video_type=dec.get("videoType") or (vlinks or {}).get("videoType"),
                    style_extra=dec.get("style"),
                    inner_type=dec.get("innerType") or "DeVideo",
                )
            )
            continue
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
        # 美化边框等：与界面 commonBackground（outerImage/GIF）一致，禁止臆造字段
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
            apply_chart_overrides(view, ch.get("config"))
            views[cid] = view
            # 组件 render 与界面 getViewConfig 一致
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
            apply_chart_overrides(view, ch.get("config"))
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
    try:
        plan = apply_template_to_plan(plan)
    except ValueError as e:
        raise DataEaseClientError(str(e)) from e

    issues = lint_plan(plan)
    errors = [x for x in issues if x["level"] == "error"]
    warns = [x for x in issues if x["level"] == "warn"]
    for x in warns:
        print(f"WARN[{x['code']}] {x['message']}", file=sys.stderr)
    if errors and not getattr(args, "allow_lint_errors", False):
        detail = "\n".join(f"  - [{x['code']}] {x['message']}" for x in errors)
        raise DataEaseClientError(
            "规格未通过自检，已阻止写入（不会产生半成品大屏）：\n"
            f"{detail}\n"
            "修正后重试；确认要强行写入请加 --allow-lint-errors"
        )

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
            # 支持 canvas 里写 "component.chartTitle.show" 这类嵌套全局配置
            if "." in str(k):
                set_path(style, str(k), v)
            else:
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

    # 联动 / 跳转是独立接口，必须在图表视图落库之后再写，否则找不到目标图表
    linkage_items = plan.get("linkage") or plan.get("linkages") or []
    jump_items = plan.get("jump") or plan.get("jumps") or []
    linkage_report: list = []
    jump_report: list = []
    tips: list[str] = []
    if linkage_items or jump_items:
        live_views = panel_link.get_panel_views(client, str(scene_id), busi_flag="dataV")
        if linkage_items:
            linkage_report = panel_link.apply_linkage(
                client, str(scene_id), live_views, linkage_items, replace=True
            )
            for t in panel_link.self_check({"linkage": linkage_report}):
                panel_link.warn(t)
                tips.append(t)
        if jump_items:
            jump_report = panel_link.apply_jump(
                client, str(scene_id), live_views, jump_items, replace=True
            )
            for t in panel_link.self_check({"jump": jump_report}):
                panel_link.warn(t)
                tips.append(t)

    _print_json(
        {
            "id": str(scene_id),
            "name": name,
            "pid": pid,
            "layout": (plan.get("_resolvedLayout") or {}).get("id"),
            "charts": len(plan.get("charts") or []),
            "decorations": len(plan.get("decorations") or []),
            "linkage": linkage_report,
            "jump": jump_report,
            "tips": tips,
            "result": result,
        }
    )


def cmd_defaults(_client: Optional[DataEaseClient], args: argparse.Namespace) -> None:
    """离线查默认值：面板级全局配置 / 图表配置 / 联动 / 跳转。"""
    if args.key:
        hit = panel_schema.lookup(args.key)
        if not hit:
            sug = panel_schema.suggest(args.key)
            hint = f"你是不是想查：{', '.join(sug)}" if sug else "运行 defaults --group canvas 看全部"
            raise DataEaseClientError(f"没有名为「{args.key}」的配置项。{hint}")
        _print_json(panel_schema.render_entry_json(hit))
        return
    if args.markdown:
        text = (
            panel_schema.render_full_markdown()
            if args.all
            else panel_schema.render_markdown(args.group)
        )
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            _print_json({"written": args.output, "bytes": len(text.encode("utf-8")), "lines": text.count("\n")})
        else:
            print(text)
        return
    if args.all:
        _print_json({gid: panel_schema.render_json(gid) for gid, _n, _i in panel_schema.GROUPS})
        return
    _print_json(panel_schema.render_json(args.group))


def cmd_lint_plan(_client: Optional[DataEaseClient], args: argparse.Namespace) -> None:
    """离线自检 plan，不连接、不写入。"""
    plan = _load_json(args.json, args.file)
    if not isinstance(plan, dict):
        raise DataEaseClientError("lint-plan 需要 --file/--json 计划对象")
    try:
        plan = apply_template_to_plan(plan)
    except ValueError as e:
        raise DataEaseClientError(str(e)) from e
    issues = lint_plan(plan)
    errors = [x for x in issues if x["level"] == "error"]
    _print_json(
        {
            "ok": not errors,
            "errorCount": len(errors),
            "warnCount": len([x for x in issues if x["level"] == "warn"]),
            "issues": issues,
        }
    )
    if errors:
        raise DataEaseClientError(f"自检发现 {len(errors)} 处错误，见 issues")


def _plan_extras() -> dict:
    """plan 里联动 / 跳转 / 图表配置的写法示范（apply 会忽略 _ 前缀键）。"""
    return {
        "_configDemo": {
            "说明": "charts[].config 用友好键，键名必须在 defaults --group chart 清单内",
            "样例": {"label.show": True, "label.color": "#8ab4f8", "legend.show": False, "xAxis.color": "#8ab4f8"},
        },
        "_linkageDemo": {
            "说明": "源图表点击后联动其他图表；fields 省略则按同名自动配对",
            "样例": [{"source": "各省销量", "targets": ["占比"], "fields": [{"source": "省份", "target": "省份"}]}],
        },
        "_jumpDemo": {
            "说明": "linkType=outer 走外部链接（content 里 [字段名] 会被替换成点击值）；inner 走面板跳转",
            "样例": [
                {
                    "source": "各省销量",
                    "field": "省份",
                    "linkType": "outer",
                    "jumpType": "_blank",
                    "content": "https://example.com/detail?prov=[省份]",
                }
            ],
        },
    }


def cmd_plan_example(_client: DataEaseClient, args: argparse.Namespace) -> None:
    layout = getattr(args, "layout", None) or "grid_3x4"
    if layout in ("free", "none", "manual"):
        _print_json(
            {
                "name": "销售运营大屏",
                "folderName": "目标文件夹",
                "datasetId": "<DATASET_ID>",
                "canvas": {"backgroundColor": "#020408", "width": 1920, "height": 1080},
                "charts": [
                    {
                        "type": "bar",
                        "title": "示例图",
                        "xAxis": ["省份"],
                        "yAxis": [{"name": "销售量", "summary": "sum"}],
                        "layout": {"left": 40, "top": 120, "width": 900, "height": 400},
                        "config": {"label.show": True, "legend.show": False},
                    }
                ],
                **_plan_extras(),
            }
        )
        return
    try:
        tpl = get_layout(layout)
    except ValueError as e:
        raise DataEaseClientError(str(e)) from e
    charts = []
    # 居中结构：主槽优先柱/地图类；平均分布：轮换常见图
    if tpl["id"] == "center_v2":
        sample_types = ["bar", "indicator", "pie", "line", "table-info", "bar"]
    else:
        sample_types = ["indicator", "bar", "pie", "line", "table-info", "bar"]
    for i, slot in enumerate(tpl["contentSlots"]):
        charts.append(
            {
                "slot": slot,
                "type": sample_types[i % len(sample_types)],
                "title": f"内容-{slot}",
                "datasetId": "<DATASET_ID>",
                "xAxis": ["省份"] if sample_types[i % len(sample_types)] != "indicator" else None,
                "yAxis": [{"name": "销售量", "summary": "sum"}],
            }
        )
    for ch in charts:
        if ch["type"] == "indicator":
            ch.pop("xAxis", None)
        if ch["type"] == "table-info":
            ch["xAxis"] = ["省份", "销售量"]
            ch.pop("yAxis", None)
    _print_json(
        {
            "name": "模板大屏示例",
            "title": "大标题",
            "folderName": "目标文件夹",
            "layout": tpl["id"],
            "datasetId": "<DATASET_ID>",
            "canvas": {"backgroundColor": "#020408", "width": 1920, "height": 1080},
            "charts": charts,
            "_layoutMeta": {
                "name": tpl["name"],
                "contentSlots": tpl["contentSlots"],
                "hint": "指定 layout 后可不写像素；也可用 slot 指定落入哪一格",
            },
            **_plan_extras(),
        }
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 数据大屏 dataV CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog", help="图表类型、装饰与布局模板清单").set_defaults(func=cmd_catalog)

    ly = sub.add_parser("layouts", help="列出或查看布局模板槽位像素")
    ly.add_argument("--id", default=None, help="grid_3x4 / center_v2")
    ly.add_argument("--name", default=None, help="中文名如 平均分布3x4 / 居中结构")
    ly.set_defaults(func=cmd_layouts)

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
    ap.add_argument("--allow-lint-errors", action="store_true", help="自检有 error 仍强行写入（不推荐）")
    ap.set_defaults(func=cmd_apply)

    df = sub.add_parser("defaults", help="查默认值（离线）：全局配置 / 图表配置 / 联动 / 跳转")
    df.add_argument(
        "--group",
        default="canvas",
        choices=["canvas", "chart", "linkage", "jump"],
        help="canvas=面板级全局 / chart=单图表 / linkage=联动 / jump=跳转",
    )
    df.add_argument("--key", default=None, help="只查一项，如 customAttr.label.show")
    df.add_argument("--all", action="store_true", help="输出全部分组")
    df.add_argument("--markdown", action="store_true", help="输出 markdown 表格")
    df.add_argument("--output", default=None, help="配合 --markdown 写到文件")
    df.set_defaults(func=cmd_defaults)

    lp = sub.add_parser("lint-plan", help="离线自检 plan（不连接、不写入）")
    lp.add_argument("--file")
    lp.add_argument("--json")
    lp.set_defaults(func=cmd_lint_plan)

    panel_link.add_linkage_parser(sub, busi_flag="dataV", label="数据大屏")
    panel_link.add_jump_parser(sub, busi_flag="dataV", label="数据大屏")

    pe = sub.add_parser("plan-example", help="打印 plan JSON 示例")
    pe.add_argument(
        "--layout",
        default="grid_3x4",
        help="grid_3x4 | center_v2 | free（手写像素）",
    )
    pe.set_defaults(func=cmd_plan_example)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        offline = {"plan-example", "catalog", "layouts", "defaults", "lint-plan"}
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
