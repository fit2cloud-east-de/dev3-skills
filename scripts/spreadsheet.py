#!/usr/bin/env python3
"""DataEase V3 电子表格 CLI —— 新建、修改本任务所建、发布。

电子表格是与数据源/数据集/数据大屏/仪表板并列的**第五棵独立资源树**
（组织根 id 不同，须用本 CLI 的 resolve-folder 在电子表格树上解析）。

能力边界（强制）：
- 支持新建（多 sheet、单元格值/公式、样式、合并、列宽行高、条件格式）
- 仅支持修改**当前任务内创建**的电子表格（edit 须 --session-created）
- 不支持修改已存在的电子表格

环境变量同 datasource.py：DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY / DE_ALLOWED_WRITE_SCOPE
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError
from datasource import (
    _assert_within_write_scope,
    _remind_backup_and_admin,
    _resolve_folder,
)
from de_ids import snowflake_id

# Univer 条件格式规则在快照 resources 中的资源名
CF_RESOURCE_NAME = "SHEET_CONDITIONAL_FORMATTING_PLUGIN"

PUBLISH_STATUS = {"unpublished": 0, "published": 1, "saved_unpublished": 2}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load_json(raw: Optional[str], file_path: Optional[str]) -> Any:
    if file_path:
        import pathlib

        return json.loads(pathlib.Path(file_path).read_text(encoding="utf-8"))
    if raw:
        return json.loads(raw)
    return None


# ---------------------------------------------------------------------------
# A1 引用与解析
# ---------------------------------------------------------------------------

def _col_letters_to_index(letters: str) -> int:
    n = 0
    for ch in letters.strip().upper():
        if not ("A" <= ch <= "Z"):
            raise DataEaseClientError(f"非法列标: {letters!r}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _ref_to_rc(ref: str) -> tuple[int, int]:
    """'B3' -> (2, 1)"""
    ref = ref.strip().replace("$", "")
    i = 0
    while i < len(ref) and ref[i].isalpha():
        i += 1
    if i == 0 or i == len(ref):
        raise DataEaseClientError(f"非法单元格引用: {ref!r}，应为如 B3")
    col = _col_letters_to_index(ref[:i])
    try:
        row = int(ref[i:]) - 1
    except ValueError:
        raise DataEaseClientError(f"非法单元格引用: {ref!r}，应为如 B3")
    if row < 0:
        raise DataEaseClientError(f"非法单元格引用: {ref!r}")
    return row, col


def _range_to_irange(rng: str) -> dict:
    """'A1:C10' -> {startRow, startColumn, endRow, endColumn}"""
    rng = rng.strip()
    if ":" not in rng:
        r, c = _ref_to_rc(rng)
        return {"startRow": r, "startColumn": c, "endRow": r, "endColumn": c}
    a, b = rng.split(":", 1)
    r1, c1 = _ref_to_rc(a)
    r2, c2 = _ref_to_rc(b)
    return {
        "startRow": min(r1, r2),
        "startColumn": min(c1, c2),
        "endRow": max(r1, r2),
        "endColumn": max(c1, c2),
    }


# ---------------------------------------------------------------------------
# 样式 DSL → Univer IStyleData
# ---------------------------------------------------------------------------

_ALIGN = {"left": 1, "center": 2, "right": 3, "justified": 4}
_VALIGN = {"top": 1, "middle": 2, "bottom": 3}


def _normalize_color(color: Optional[str]) -> Optional[dict]:
    if not color:
        return None
    c = color.strip().lstrip("#")
    if len(c) == 6:
        c = "FF" + c.upper()
    elif len(c) == 8:
        c = c.upper()
    else:
        raise DataEaseClientError(f"非法颜色值: {color!r}，应为 #RRGGBB 或 #AARRGGBB")
    return {"rgb": "#" + c}


def _style_to_univer(style: dict, *, name: str = "") -> dict:
    """友好样式键 → Univer IStyleData（同时用于单元格样式与条件格式内联样式）。"""
    out: dict = {}
    if style.get("font"):
        out["ff"] = style["font"]
    if style.get("fontSize") is not None:
        out["fs"] = style["fontSize"]
    if style.get("bold"):
        out["bl"] = 1
    if style.get("italic"):
        out["it"] = 1
    if style.get("underline"):
        out["ul"] = {"s": 1}
    if style.get("strike"):
        out["st"] = {"s": 1}
    bg = _normalize_color(style.get("bg"))
    if bg:
        out["bg"] = bg
    cl = _normalize_color(style.get("color"))
    if cl:
        out["cl"] = cl
    if style.get("align") is not None:
        a = style["align"]
        if a not in _ALIGN:
            raise DataEaseClientError(f"样式 {name}: align 仅支持 {sorted(_ALIGN)}")
        out["ht"] = _ALIGN[a]
    if style.get("valign") is not None:
        v = style["valign"]
        if v not in _VALIGN:
            raise DataEaseClientError(f"样式 {name}: valign 仅支持 {sorted(_VALIGN)}")
        out["vt"] = _VALIGN[v]
    if style.get("wrap"):
        out["tb"] = 2  # WrapStrategy.WRAP
    if style.get("numberFormat"):
        out["n"] = {"pattern": style["numberFormat"]}
    border = style.get("border")
    if border:
        # border: "all" | "outline" | "top" | "bottom" | "left" | "right"
        edge_style = {"s": 1}  # BorderStyleTypes.THIN
        bcolor = _normalize_color(style.get("borderColor") or "#FF999999")
        edge = {**edge_style, "cl": bcolor}
        bd: dict = {}
        keys = {
            "top": "t", "bottom": "b", "left": "l", "right": "r",
            "all": "tbrl", "outline": "tbrl",
        }
        ks = keys.get(border)
        if not ks:
            raise DataEaseClientError(f"样式 {name}: border 仅支持 {sorted(keys)}")
        for k in ks:
            bd[k] = edge
        out["bd"] = bd
    return out


# ---------------------------------------------------------------------------
# 主题预设：一套色板 + 字号阶梯，产出可直接引用的命名样式
# ---------------------------------------------------------------------------

_FONT = "Microsoft YaHei"

_THEME_SPECS: dict[str, dict] = {
    "business": {
        "label": "企业蓝（默认）",
        "primary": "#1F4E79",
        "soft": "#DCE9F7",
        "accent": "#2E75B6",
        "text": "#262626",
        "textSecondary": "#595959",
        "border": "#BFD4EA",
        "grid": "#E3EAF2",
        "zebra": "#F6FAFE",
        "success": ("#E9F5EC", "#2E7D32"),
        "warn": ("#FFF4E1", "#A96A00"),
        "danger": ("#FDE8E8", "#C0392B"),
    },
    "finance": {
        "label": "金融深蓝",
        "primary": "#0F2A4A",
        "soft": "#E3EAF3",
        "accent": "#B8860B",
        "text": "#1C1C1C",
        "textSecondary": "#5A6470",
        "border": "#C9D4E2",
        "grid": "#E4E9EF",
        "zebra": "#F7F9FC",
        "success": ("#E8F2EA", "#2F6B45"),
        "warn": ("#FBF1DC", "#8A6100"),
        "danger": ("#F8E7E7", "#A93226"),
    },
    "fresh": {
        "label": "清新绿",
        "primary": "#2F6B4F",
        "soft": "#E4F1EA",
        "accent": "#3E9C6D",
        "text": "#22312B",
        "textSecondary": "#566660",
        "border": "#C9DED3",
        "grid": "#E4EFE9",
        "zebra": "#F5FAF7",
        "success": ("#E4F3E9", "#2C6B41"),
        "warn": ("#FDF3DF", "#96690A"),
        "danger": ("#FBE9E7", "#B3452F"),
    },
    "minimal": {
        "label": "极简黑白",
        "primary": "#1A1A1A",
        "soft": "#F2F2F2",
        "accent": "#4D4D4D",
        "text": "#1A1A1A",
        "textSecondary": "#595959",
        "border": "#BFBFBF",
        "grid": "#E6E6E6",
        "zebra": "#FAFAFA",
        "success": ("#EDF5EE", "#2E6B36"),
        "warn": ("#FBF3E4", "#8A6206"),
        "danger": ("#F7E9E9", "#A33A32"),
    },
}


def theme_styles(theme: str) -> dict:
    """主题 → 一组命名样式（spec.styles 可同名覆盖）。"""
    key = (theme or "business").strip().lower()
    if key not in _THEME_SPECS:
        raise DataEaseClientError(
            f"未知主题 theme={theme!r}，可选: {sorted(_THEME_SPECS)}"
        )
    t = _THEME_SPECS[key]
    ok_bg, ok_fg = t["success"]
    wn_bg, wn_fg = t["warn"]
    dg_bg, dg_fg = t["danger"]
    return {
        # 文档标题区
        "title": {
            "font": _FONT, "fontSize": 20, "bold": True, "color": t["primary"],
            "align": "center", "valign": "middle",
        },
        "subtitle": {
            "font": _FONT, "fontSize": 11, "color": t["textSecondary"],
            "align": "center", "valign": "middle",
        },
        "section": {
            "font": _FONT, "fontSize": 12, "bold": True, "color": t["primary"],
            "align": "left", "valign": "middle",
        },
        # 表头
        "header": {
            "font": _FONT, "fontSize": 11, "bold": True, "bg": t["soft"],
            "color": t["primary"], "align": "center", "valign": "middle",
            "border": "all", "borderColor": t["border"],
        },
        "headerLeft": {
            "font": _FONT, "fontSize": 11, "bold": True, "bg": t["soft"],
            "color": t["primary"], "align": "left", "valign": "middle",
            "border": "all", "borderColor": t["border"],
        },
        # 数据区
        "cell": {
            "font": _FONT, "fontSize": 11, "color": t["text"],
            "align": "center", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "cellText": {
            "font": _FONT, "fontSize": 11, "color": t["text"],
            "align": "left", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "qty": {
            "font": _FONT, "fontSize": 11, "color": t["text"], "numberFormat": "#,##0",
            "align": "center", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "money": {
            "font": _FONT, "fontSize": 11, "color": t["text"], "numberFormat": "#,##0.00",
            "align": "right", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "pct": {
            "font": _FONT, "fontSize": 11, "color": t["text"], "numberFormat": "0.0%",
            "align": "right", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "date": {
            "font": _FONT, "fontSize": 11, "color": t["text"],
            "align": "center", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        # 合计行（主结构线加强）
        "total": {
            "font": _FONT, "fontSize": 11, "bold": True, "bg": t["soft"],
            "color": t["primary"], "align": "left", "valign": "middle",
            "border": "all", "borderColor": t["border"],
        },
        "totalMoney": {
            "font": _FONT, "fontSize": 11, "bold": True, "bg": t["soft"],
            "color": t["primary"], "numberFormat": "#,##0.00",
            "align": "right", "valign": "middle",
            "border": "all", "borderColor": t["border"],
        },
        # 辅注与语义色
        "note": {
            "font": _FONT, "fontSize": 10, "italic": True, "color": t["textSecondary"],
            "align": "left", "valign": "middle",
        },
        "zebra": {
            "font": _FONT, "fontSize": 11, "color": t["text"], "bg": t["zebra"],
            "align": "center", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "zebraText": {
            "font": _FONT, "fontSize": 11, "color": t["text"], "bg": t["zebra"],
            "align": "left", "valign": "middle",
            "border": "all", "borderColor": t["grid"],
        },
        "success": {"font": _FONT, "fontSize": 11, "bg": ok_bg, "color": ok_fg, "align": "center"},
        "warn": {"font": _FONT, "fontSize": 11, "bg": wn_bg, "color": wn_fg, "align": "center"},
        "danger": {"font": _FONT, "fontSize": 11, "bg": dg_bg, "color": dg_fg, "align": "center"},
    }


def theme_colors(theme: str) -> dict:
    key = (theme or "business").strip().lower()
    if key not in _THEME_SPECS:
        raise DataEaseClientError(
            f"未知主题 theme={theme!r}，可选: {sorted(_THEME_SPECS)}"
        )
    return dict(_THEME_SPECS[key])


# ---------------------------------------------------------------------------
# 规格编译：spec JSON → 工作簿快照
# ---------------------------------------------------------------------------

def _freeze_to_univer(freeze: Any) -> dict:
    """'B2' → 冻结首行首列；或 {xSplit, ySplit, startRow, startColumn}。"""
    if isinstance(freeze, str):
        row, col = _ref_to_rc(freeze)
        return {"xSplit": col, "ySplit": row, "startRow": row, "startColumn": col}
    if isinstance(freeze, dict) and {"xSplit", "ySplit", "startRow", "startColumn"} <= set(freeze):
        return {
            "xSplit": int(freeze["xSplit"]),
            "ySplit": int(freeze["ySplit"]),
            "startRow": int(freeze["startRow"]),
            "startColumn": int(freeze["startColumn"]),
        }
    raise DataEaseClientError(f"freeze 须为单元格引用（如 'B2'）或 {{xSplit,ySplit,startRow,startColumn}}，收到: {freeze!r}")


def _build_rich_text(runs: list) -> dict:
    """[{text, style}] → 单元格富文本文档（cell.p）。"""
    if not isinstance(runs, list) or not runs:
        raise DataEaseClientError("richText 须为非空数组 [{text, style}]")
    text = "".join(str(r.get("text", "")) for r in runs)
    if not text:
        raise DataEaseClientError("richText 所有分段均为空")
    data_stream = text + "\r\n"
    text_runs = []
    offset = 0
    for i, r in enumerate(runs):
        seg = str(r.get("text", ""))
        ts = _style_to_univer(r.get("style") or {}, name=f"richText[{i}]")
        if ts:
            text_runs.append({"st": offset, "ed": offset + len(seg), "ts": ts})
        offset += len(seg)
    body: dict = {"dataStream": data_stream}
    if text_runs:
        body["textRuns"] = text_runs
    body["paragraphs"] = [{"startIndex": max(len(text), 0)}]
    return {
        "id": f"doc_{uuid.uuid4().hex[:12]}",
        "body": body,
        "documentStyle": {},
    }


def _compile_validation(item: dict, sheet_id: str, idx: int) -> dict:
    """数据验证 DSL → 内核规则。"""
    vt = item.get("type")
    dv_types = (
        "list", "listMultiple", "decimal", "whole", "textLength",
        "date", "time", "checkbox", "custom", "any",
    )
    if vt not in dv_types:
        raise DataEaseClientError(
            f"validations[{idx}] type 须为 {dv_types} 之一，收到: {vt!r}"
        )
    rule: dict = {
        "uid": f"dv_{uuid.uuid4().hex[:16]}",
        "type": vt,
        "ranges": [_range_to_irange(str(item.get("range") or "A1"))],
    }
    if vt in ("list", "listMultiple"):
        # 下拉渲染方式：arrow(默认，文字+下拉箭头) / text(纯文字) / chip(彩色芯片)
        mode = (item.get("renderMode") or "arrow").strip().lower()
        mode_map = {"text": 0, "arrow": 1, "chip": 2}
        if mode not in mode_map:
            raise DataEaseClientError(
                f"validations[{idx}] renderMode 须为 text/arrow/chip，收到: {mode!r}"
            )
        rule["renderMode"] = mode_map[mode]
    op = item.get("operator")
    if op:
        rule["operator"] = op
    formula1 = item.get("formula1") or item.get("formula")
    if formula1 is None and item.get("values") is not None:
        vals = item["values"]
        if vt in ("list", "listMultiple"):
            # 下拉选项以 JSON 数组字符串写入（与产品面板一致，勿用带引号逗号串）
            formula1 = json.dumps([str(v) for v in vals], ensure_ascii=False)
        elif isinstance(vals, (list, tuple)):
            if len(vals) >= 2:
                formula1, formula2 = str(vals[0]), str(vals[1])
                rule["formula1"], rule["formula2"] = formula1, formula2
            else:
                formula1 = str(vals[0])
        else:
            formula1 = str(vals)
    if formula1 is not None:
        rule.setdefault("formula1", str(formula1))
    if item.get("values2") is not None:
        rule.setdefault("formula2", str(item["values2"]))
    rule.setdefault("allowBlank", bool(item.get("allowBlank", True)))
    if item.get("promptTitle") or item.get("prompt"):
        rule["showInputMessage"] = True
        if item.get("promptTitle"):
            rule["promptTitle"] = item["promptTitle"]
        if item.get("prompt"):
            rule["prompt"] = item["prompt"]
    if item.get("errorTitle") or item.get("error"):
        rule["showErrorMessage"] = True
        if item.get("errorTitle"):
            rule["errorTitle"] = item["errorTitle"]
        if item.get("error"):
            rule["error"] = item["error"]
    return rule


def _compile_filter_columns(columns: list, base_range: dict, idx: int) -> list:
    """筛选列 DSL → filterColumns。col 为绝对列标（如 'B'），colId 为范围内偏移。"""
    out = []
    for ci, col_spec in enumerate(columns or []):
        col_letter = str(col_spec.get("col") or "")
        if ":" in col_letter:
            raise DataEaseClientError(f"filters[{idx}].columns[{ci}] col 不支持区间，单列单条")
        col_abs = _col_letters_to_index(col_letter)
        offset = col_abs - base_range["startColumn"]
        if offset < 0 or offset > (base_range["endColumn"] - base_range["startColumn"]):
            raise DataEaseClientError(
                f"filters[{idx}].columns[{ci}] 列 {col_letter} 不在筛选范围内"
            )
        entry: dict = {"colId": offset}
        if col_spec.get("values") is not None:
            entry["filters"] = {"filters": [str(v) for v in col_spec["values"]]}
        if col_spec.get("blank") is True:
            entry.setdefault("filters", {})["blank"] = True
        custom = col_spec.get("custom")
        if custom:
            conds = custom if isinstance(custom, list) else [custom]
            compiled = [
                {"val": c.get("val"), **({"operator": c["operator"]} if c.get("operator") else {})}
                for c in conds
            ]
            if not compiled:
                raise DataEaseClientError(f"filters[{idx}].columns[{ci}] custom 条件为空")
            entry["customFilters"] = {
                "and": 1 if isinstance(custom, dict) and custom.get("and") else None,
                "customFilters": compiled,
            }
            entry["customFilters"] = {
                k: v for k, v in entry["customFilters"].items() if v is not None
            }
        if "filters" not in entry and "customFilters" not in entry:
            raise DataEaseClientError(
                f"filters[{idx}].columns[{ci}] 须提供 values / blank / custom 之一"
            )
        out.append(entry)
    return out


def compile_workbook(spec: dict) -> dict:
    """将简化规格编译为工作簿快照。

    spec 结构见 references/spreadsheet.md：
    {theme, styles, sheets: [{name, cells, merges, freeze, ...}], conditionalFormats,
     validations, filters, notes, slashCells, datasetTables, filterComponents}
    """
    if not isinstance(spec, dict):
        raise DataEaseClientError("规格须为 JSON 对象")
    styles_dsl = spec.get("styles") or {}
    if not isinstance(styles_dsl, dict):
        raise DataEaseClientError("styles 须为对象: {样式名: {...}}")
    if spec.get("theme"):
        # 主题给出整套命名样式与色板；spec.styles 同名项可覆盖
        merged = theme_styles(spec["theme"])
        merged.update(styles_dsl)
        styles_dsl = merged
    styles_map = {
        f"s_{name}": _style_to_univer(s, name=name) for name, s in styles_dsl.items()
    }

    sheets_spec = spec.get("sheets") or []
    if not isinstance(sheets_spec, list) or not sheets_spec:
        raise DataEaseClientError("sheets 须为非空数组")
    sheet_id_by_name: dict[str, str] = {}
    sheets: dict[str, dict] = {}
    sheet_order: list[str] = []
    for idx, sh in enumerate(sheets_spec, start=1):
        if not isinstance(sh, dict) or not sh.get("name"):
            raise DataEaseClientError(f"sheets[{idx}] 缺少 name")
        name = str(sh["name"])
        if name in sheet_id_by_name:
            raise DataEaseClientError(f"sheet 名重复: {name}")
        sid = f"sheet-{idx:02d}"
        sheet_id_by_name[name] = sid

        row_count = int(sh.get("rowCount") or 1000)
        col_count = int(sh.get("columnCount") or 26)
        cell_data: dict[int, dict[int, dict]] = {}

        def ensure(row: int, col: int) -> dict:
            return cell_data.setdefault(row, {}).setdefault(col, {})

        cells = sh.get("cells") or {}
        if not isinstance(cells, dict):
            raise DataEaseClientError(f"sheet「{name}」cells 须为对象: {单元格引用: {...}}")
        for ref, cell in cells.items():
            row, col = _ref_to_rc(str(ref))
            if row >= row_count:
                row_count = row + 10
            if col >= col_count:
                col_count = col + 5
            if not isinstance(cell, dict):
                cell = {"v": cell}
            target = ensure(row, col)
            if "v" in cell and cell["v"] is not None:
                target["v"] = cell["v"]
            f = cell.get("f") or cell.get("formula")
            if f:
                f = str(f).strip()
                if not f.startswith("="):
                    f = "=" + f
                target["f"] = f
            if cell.get("style"):
                sname = str(cell["style"])
                if sname not in styles_dsl:
                    raise DataEaseClientError(
                        f"单元格 {ref} 引用了未定义样式「{sname}」。已定义: {sorted(styles_dsl)}"
                    )
                target["s"] = f"s_{sname}"
            elif isinstance(cell.get("inlineStyle"), dict):
                target["s"] = _style_to_univer(cell["inlineStyle"], name=f"{ref}#inline")
            if isinstance(cell.get("richText"), list):
                if "v" in target or "f" in target:
                    raise DataEaseClientError(f"单元格 {ref}: richText 与 v/f 互斥")
                target["p"] = _build_rich_text(cell["richText"])
            if cell.get("type") == "text":
                target["t"] = 4  # CellValueType.FORCE_STRING：强制文本（保留前导零等）
            elif cell.get("type") == "number":
                target["t"] = 2

        merge_data = [_range_to_irange(str(m)) for m in sh.get("merges") or []]

        column_data: dict[str, dict] = {}
        for span, w in (sh.get("columnWidths") or {}).items():
            if ":" in str(span):
                a, b = str(span).split(":", 1)
                cols = range(_col_letters_to_index(a), _col_letters_to_index(b) + 1)
            else:
                cols = [_col_letters_to_index(str(span))]
            for c in cols:
                column_data[str(c)] = {"w": int(w)}

        row_data: dict[str, dict] = {}
        for span, h in (sh.get("rowHeights") or {}).items():
            if ":" in str(span):
                a, b = str(span).split(":", 1)
                rows = range(int(a), int(b) + 1)
            else:
                rows = [int(span)]
            for r in rows:
                row_data[str(r - 1)] = {"h": int(h)}

        sheet_obj: dict = {
            "id": sid,
            "name": name,
            "rowCount": row_count,
            "columnCount": col_count,
            "zoomRatio": 1,
            "scrollTop": 0,
            "scrollLeft": 0,
            "defaultColumnWidth": int(sh.get("defaultColumnWidth") or 93),
            "defaultRowHeight": int(sh.get("defaultRowHeight") or 27),
            "mergeData": merge_data,
            "cellData": cell_data,
            "columnData": column_data,
            "rowData": row_data,
            "showGridlines": 0 if sh.get("showGridlines") is False else 1,
            "rowHeader": {"width": 46, "hidden": 0},
            "columnHeader": {"height": 20, "hidden": 0},
            "selections": ["A1"],
            "rightToLeft": 1 if sh.get("rightToLeft") else 0,
        }
        if sh.get("freeze"):
            sheet_obj["freeze"] = _freeze_to_univer(sh["freeze"])
        if sh.get("hidden"):
            sheet_obj["hidden"] = 1
        tab_color = _normalize_color(sh.get("tabColor"))
        if tab_color:
            sheet_obj["tabColor"] = tab_color["rgb"]
        sheets[sid] = sheet_obj
        sheet_order.append(sid)

    workbook: dict = {
        "id": "workbook-01",
        "name": "Workbook",
        "locale": "zhCN",
        "styles": styles_map,
        "sheetOrder": sheet_order,
        "sheets": sheets,
    }

    resources: list[dict] = []
    unit_id = "workbook-01"

    def _sheet_id_of(section: str, i: int, default_first: bool = False) -> str:
        sheet_name = str(spec_item_sheet(section, i, default_first))
        if sheet_name not in sheet_id_by_name:
            raise DataEaseClientError(
                f"{section}[{i}] 引用未知 sheet「{sheet_name}」。已有: {sorted(sheet_id_by_name)}"
            )
        return sheet_id_by_name[sheet_name]

    def spec_item_sheet(section: str, i: int, default_first: bool = False) -> Any:
        item = spec.get(section)[i]
        return item.get("sheet") or (sheets_spec[0].get("name") if default_first and sheets_spec else None)

    # --- 条件格式 → SHEET_CONDITIONAL_FORMATTING_PLUGIN ({unitId: {sheetId: [rules]}}) ---
    cf_spec = spec.get("conditionalFormats") or []
    if cf_spec:
        rules_by_sheet: dict[str, list] = {}
        for i, item in enumerate(cf_spec):
            sid = _sheet_id_of("conditionalFormats", i, default_first=True)
            rule_dsl = item.get("rule")
            if not isinstance(rule_dsl, dict):
                raise DataEaseClientError(f"conditionalFormats[{i}] 缺少 rule")
            rule = dict(rule_dsl)
            if rule.get("type") == "highlightCell" and isinstance(rule.get("style"), dict):
                rule["style"] = _style_to_univer(rule["style"], name=f"cf[{i}]")
            irange = _range_to_irange(str(item.get("range") or item.get("ranges") or "A1"))
            rules_by_sheet.setdefault(sid, []).append(
                {
                    "cfId": f"cf_{uuid.uuid4().hex[:16]}",
                    "ranges": [irange],
                    "stopIfTrue": bool(item.get("stopIfTrue")),
                    "rule": rule,
                }
            )
        resources.append(
            {
                "name": CF_RESOURCE_NAME,
                "data": json.dumps({unit_id: rules_by_sheet}, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 数据验证 → SHEET_DATA_VALIDATION_PLUGIN ({sheetId: [rules]}) ---
    dv_spec = spec.get("validations") or []
    if dv_spec:
        dv_by_sheet: dict[str, list] = {}
        for i, item in enumerate(dv_spec):
            sid = _sheet_id_of("validations", i, default_first=True)
            dv_by_sheet.setdefault(sid, []).append(_compile_validation(item, sid, i))
        resources.append(
            {
                "name": "SHEET_DATA_VALIDATION_PLUGIN",
                "data": json.dumps(dv_by_sheet, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 自动筛选 → SHEET_FILTER_PLUGIN ({sheetId: {ref, filterColumns}}) ---
    fl_spec = spec.get("filters") or []
    if fl_spec:
        fl_by_sheet: dict[str, dict] = {}
        for i, item in enumerate(fl_spec):
            sid = _sheet_id_of("filters", i, default_first=True)
            ref = _range_to_irange(str(item.get("range") or "A1"))
            fl_by_sheet[sid] = {
                "ref": ref,
                "filterColumns": _compile_filter_columns(item.get("columns") or [], ref, i),
            }
        resources.append(
            {
                "name": "SHEET_FILTER_PLUGIN",
                "data": json.dumps(fl_by_sheet, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 批注 → SHEET_NOTE_PLUGIN ({sheetId: {row: {col: note}}}) ---
    note_spec = spec.get("notes") or []
    if note_spec:
        note_by_sheet: dict[str, dict] = {}
        for i, item in enumerate(note_spec):
            sid = _sheet_id_of("notes", i, default_first=True)
            row, col = _ref_to_rc(str(item.get("cell") or "A1"))
            note_by_sheet.setdefault(sid, {}).setdefault(str(row), {})[str(col)] = {
                "id": f"note_{uuid.uuid4().hex[:12]}",
                "row": row,
                "col": col,
                "width": int(item.get("width") or 160),
                "height": int(item.get("height") or 120),
                "note": str(item.get("text") or ""),
                "show": False,
            }
        resources.append(
            {
                "name": "SHEET_NOTE_PLUGIN",
                "data": json.dumps(note_by_sheet, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 斜线格 → SHEET_DATAEASE_SLASH_CELL_PLUGIN ([items]) ---
    slash_spec = spec.get("slashCells") or []
    if slash_spec:
        slash_items = []
        for i, item in enumerate(slash_spec):
            sid = _sheet_id_of("slashCells", i, default_first=True)
            row, col = _ref_to_rc(str(item.get("cell") or "A1"))
            st = item.get("type") or "two"
            if st not in ("two", "three"):
                raise DataEaseClientError(f"slashCells[{i}] type 须为 two / three")
            slash_items.append(
                {"unitId": unit_id, "sheetId": sid, "row": row, "col": col, "type": st}
            )
        resources.append(
            {
                "name": "SHEET_DATAEASE_SLASH_CELL_PLUGIN",
                "data": json.dumps(slash_items, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 明细表（数据集绑定）→ SHEET_DATAEASE_DETAIL_TABLE_PLUGIN ([configs]) ---
    dt_spec = spec.get("datasetTables") or []
    dt_infos: list[dict] = []
    if dt_spec:
        dt_configs = []
        for i, item in enumerate(dt_spec):
            if not item.get("datasetId"):
                raise DataEaseClientError(f"datasetTables[{i}] 缺少 datasetId")
            sid = _sheet_id_of("datasetTables", i, default_first=True)
            dt_id = f"detail_{uuid.uuid4().hex[:12]}"
            block_name = str(item.get("blockName") or "")
            dt_infos.append(
                {"id": dt_id, "blockName": block_name, "datasetId": str(item["datasetId"])}
            )
            dt_configs.append(
                {
                    "id": dt_id,
                    "type": "detail",
                    "data": {
                        "datasetId": str(item["datasetId"]),
                        "zones": {"fields": item.get("fields") or []},
                        "customFilter": item.get("customFilter") or {},
                        "queryFilter": [],
                        "resultLimit": int(item.get("resultLimit") or 100),
                    },
                    "placement": {
                        "sheetId": sid,
                        "sheetName": next(
                            s["name"] for s_id, s in sheets.items() if s_id == sid
                        ),
                        "startCell": str(item.get("startCell") or "A1"),
                    },
                    "style": {
                        "base": {
                            "customBlockName": bool(block_name),
                            "blockName": block_name,
                            "hideHeader": bool(item.get("hideHeader")),
                            "mergeCell": bool(item.get("mergeCell")),
                        }
                    },
                    "senior": {},
                }
            )
        resources.append(
            {
                "name": "SHEET_DATAEASE_DETAIL_TABLE_PLUGIN",
                "data": json.dumps(dt_configs, ensure_ascii=False, separators=(",", ":")),
            }
        )

    # --- 查询组件 → SHEET_DATAEASE_FILTER_PLUGIN（单对象 config）---
    fc_spec = spec.get("filterComponents") or []
    if fc_spec:
        if len(fc_spec) > 1:
            raise DataEaseClientError("filterComponents 至多一条（查询组件为工作簿级单例）")
        item = fc_spec[0]
        sid = _sheet_id_of("filterComponents", 0, default_first=True)
        conditions = []
        for ci, cond in enumerate(item.get("conditions") or []):
            if not cond.get("fieldId") or not cond.get("fieldName"):
                raise DataEaseClientError(
                    f"filterComponents[0].conditions[{ci}] 缺少 fieldId / fieldName"
                )
            display_type = cond.get("displayType") or (
                "time" if cond.get("granularity") else "textSelect"
            )
            c: dict = {
                "id": f"condition_{uuid.uuid4().hex[:12]}",
                "name": str(cond.get("name") or cond["fieldName"]),
                "visible": cond.get("visible", True),
                "required": bool(cond.get("required")),
                "displayType": display_type,
                "optionSource": cond.get("optionSource") or "auto",
                "queryFieldId": str(cond["fieldId"]),
                "queryFieldName": str(cond["fieldName"]),
                "linkedFields": [],
            }
            if display_type == "time":
                granularity = cond.get("granularity") or "date"
                if granularity not in ("year", "month", "date", "datetime"):
                    raise DataEaseClientError(
                        f"filterComponents conditions[{ci}] granularity 须为 year/month/date/datetime"
                    )
                c["timeGranularity"] = granularity
            if cond.get("multiple"):
                c["multiple"] = True
            # 关联明细表：linkPlugin 指定 blockName/明细表标识，缺省关联全部明细表
            targets = dt_infos
            link = cond.get("linkPlugin")
            if link:
                targets = [t for t in dt_infos if t["blockName"] == link or t["id"] == link]
                if not targets:
                    raise DataEaseClientError(
                        f"filterComponents conditions[{ci}] linkPlugin「{link}」未匹配任何明细表"
                    )
            for t in targets:
                c["linkedFields"].append(
                    {
                        "pluginId": t["id"],
                        "pluginName": t["blockName"] or "明细表",
                        "fieldId": str(cond["fieldId"]),
                        "fieldName": str(cond["fieldName"]),
                        "datasetId": t["datasetId"],
                        "groupType": cond.get("groupType") or "d",
                        "deType": cond.get("deType") if cond.get("deType") is not None else 0,
                    }
                )
            if not c["linkedFields"]:
                raise DataEaseClientError(
                    f"filterComponents conditions[{ci}] 无可关联明细表：请先在 datasetTables 中绑定数据集"
                )
            conditions.append(c)
        fc_config: dict = {
            "id": "spreadsheet_filter",
            "type": "filter",
            "visible": item.get("visible", True),
            "placement": {
                "sheetId": sid,
                "sheetName": next(s["name"] for s_id, s in sheets.items() if s_id == sid),
                "startCell": str(item.get("startCell") or "A1"),
            },
            "conditions": conditions,
            "style": {
                "base": {
                    "paddingMode": "uniform",
                    "padding": {"top": 16, "right": 16, "bottom": 16, "left": 16},
                    "radius": 0,
                    "backgroundEnabled": False,
                    "backgroundColor": "#ffffff",
                    "layout": "horizontal",
                    "align": "left",
                    "gap": 16,
                },
                "condition": {
                    "fillEnabled": False,
                    "fillColor": "#ffffff",
                    "borderEnabled": False,
                    "borderColor": "#d9dcdf",
                    "borderWidth": 1,
                    "color": "#1f2329",
                    "fontSize": 12,
                    "fontWeight": "normal",
                    "fontStyle": "normal",
                },
                "conditionName": {
                    "show": True,
                    "position": "top",
                    "color": "#1f2329",
                    "fontSize": 12,
                    "fontWeight": "normal",
                    "fontStyle": "normal",
                    "gap": 8,
                },
                "button": {
                    "btnList": ["sure"],
                    "primaryColor": "#3370ff",
                    "textColor": "#ffffff",
                    "fontSize": 12,
                    "fontWeight": "normal",
                    "fontStyle": "normal",
                },
            },
        }
        resources.append(
            {
                "name": "SHEET_DATAEASE_FILTER_PLUGIN",
                "data": json.dumps(fc_config, ensure_ascii=False, separators=(",", ":")),
            }
        )

    if resources:
        workbook["resources"] = resources

    return workbook


# ---------------------------------------------------------------------------
# 离线自检（lint）：create / edit 之前发现「界面不会产生的状态」
# ---------------------------------------------------------------------------

# 产品服务端对明细表取数的默认上限（超出会被截断）
RESULT_LIMIT_MAX = 100000


def _iter_range(rng: dict):
    for r in range(rng["startRow"], rng["endRow"] + 1):
        for c in range(rng["startColumn"], rng["endColumn"] + 1):
            yield r, c


def _ranges_intersect(a: dict, b: dict) -> bool:
    return not (
        a["endRow"] < b["startRow"]
        or b["endRow"] < a["startRow"]
        or a["endColumn"] < b["startColumn"]
        or b["endColumn"] < a["startColumn"]
    )


def lint_spec(spec: dict) -> list[dict]:
    """检查规格中与产品界面行为不一致、或结构上不成立的地方。

    返回问题清单 [{level, code, msg, hint}]；level ∈ error / warn / info。
    纯本地运算，不访问网络。
    """
    issues: list[dict] = []

    def add(level: str, code: str, msg: str, hint: str = "") -> None:
        issues.append({"level": level, "code": code, "msg": msg, "hint": hint})

    try:
        wb = compile_workbook(spec)
    except DataEaseClientError as e:
        add("error", "compile", f"规格无法编译：{e}", "字段与取值范围见 references/spreadsheet.md")
        return issues

    sheets: dict = wb.get("sheets") or {}

    # ---- 1. 合并区：界面合并会清空左上角以外的内容 ----
    for sh in sheets.values():
        cell_data = sh.get("cellData") or {}
        merges = sh.get("mergeData") or []
        for rng in merges:
            cleared = []
            for r, c in _iter_range(rng):
                if r == rng["startRow"] and c == rng["startColumn"]:
                    continue
                cell = (cell_data.get(r) or {}).get(c) or {}
                if any(k in cell for k in ("v", "f", "p")):
                    cleared.append((r, c))
            if cleared:
                add(
                    "error",
                    "merge_value",
                    f"工作表「{sh.get('name')}」合并区内有 {len(cleared)} 个单元格带值/公式，"
                    "界面上合并单元格会清空左上角以外的内容，这些值不会显示",
                    "把值集中到合并区左上角，或缩小合并范围",
                )
        # 合并区超出工作表边界
        for rng in merges:
            if rng["endRow"] >= sh.get("rowCount", 0) or rng["endColumn"] >= sh.get("columnCount", 0):
                add(
                    "warn",
                    "merge_out_of_bounds",
                    f"工作表「{sh.get('name')}」有合并区超出 rowCount/columnCount",
                    "扩大 rowCount/columnCount，或缩小合并范围",
                )
                break
        # 合并区互相重叠
        for i in range(len(merges)):
            for j in range(i + 1, len(merges)):
                if _ranges_intersect(merges[i], merges[j]):
                    add(
                        "error",
                        "merge_overlap",
                        f"工作表「{sh.get('name')}」存在相互重叠的合并区",
                        "重叠的合并在界面上无法产生，须改为不重叠的范围",
                    )
                    break

    # ---- 2. 界面无入口的写法（界面上改不回来，只能回到 skill 改） ----
    type_cells: dict[str, list] = {}
    for sh_spec in spec.get("sheets") or []:
        name = str(sh_spec.get("name") or "")
        if sh_spec.get("rightToLeft"):
            add(
                "warn",
                "ui_unreachable",
                f"工作表「{name}」设置了 rightToLeft，界面没有该开关",
                "确认确有必要；此后只能通过 skill 调整，用户无法在界面改回",
            )
        if sh_spec.get("showGridlines") is False:
            add(
                "warn",
                "ui_unreachable",
                f"工作表「{name}」关闭了网格线，界面没有该开关",
                "关闭网格线属打印/展示向的取舍；交付时说明「以后只能通过 skill 恢复」",
            )
        for ref, cell in (sh_spec.get("cells") or {}).items():
            if isinstance(cell, dict) and cell.get("type") in ("text", "number"):
                type_cells.setdefault(name, []).append(str(ref))
    for name, refs in type_cells.items():
        sample = "、".join(refs[:5]) + ("等" if len(refs) > 5 else "")
        add(
            "warn",
            "ui_unreachable",
            f"工作表「{name}」有 {len(refs)} 个单元格强制了值类型（{sample}），"
            "界面没有「转文本 / 转数字」入口",
            "适合编码类（保留前导零）；若这些列以后需要在界面上换算，改用 numberFormat 而非强制类型",
        )

    # ---- 3. 数据验证 ----
    for i, rule in enumerate((spec.get("validations") or [])):
        rng = _range_to_irange(str(rule.get("range") or "A1"))
        if rule.get("type") in ("list", "listMultiple"):
            has_opts = rule.get("values") is not None or rule.get("formula") or rule.get("formula1")
            if not has_opts:
                add(
                    "error",
                    "dv_no_options",
                    f"validations[{i}]（下拉）没有提供选项",
                    "用 values 传选项数组，或用 formula 引用选项区域",
                )
            mode = (rule.get("renderMode") or "arrow").strip().lower()
            if mode == "chip" and not rule.get("chipColors"):
                add(
                    "info",
                    "dv_chip_default",
                    f"validations[{i}] 使用 chip 渲染但未配配色，界面会落到默认灰底芯片",
                    "需要芯片样式时逐项配色并保证对比度；一般用 arrow",
                )
        sid = rule.get("sheet")
        sh = next((s for s in sheets.values() if s.get("name") == sid), None)
        if sh and (rng["endRow"] >= sh.get("rowCount", 0) or rng["endColumn"] >= sh.get("columnCount", 0)):
            add("warn", "dv_out_of_bounds", f"validations[{i}] 范围超出行列数")

    # ---- 4. 自动筛选 ----
    for i, item in enumerate(spec.get("filters") or []):
        sid = item.get("sheet")
        sh = next((s for s in sheets.values() if s.get("name") == sid), None)
        if not sh:
            continue
        rng = _range_to_irange(str(item.get("range") or "A1"))
        header = (sh.get("cellData") or {}).get(rng["startRow"]) or {}
        if not any(
            (header.get(c) or {}).get("v") not in (None, "")
            for c in range(rng["startColumn"], rng["endColumn"] + 1)
        ):
            add(
                "warn",
                "filter_empty_header",
                f"filters[{i}] 范围首行是空的，筛选按钮会落在没有标题的行上",
                "把 range 指向真正的表头行",
            )
        if item.get("columns"):
            add(
                "info",
                "filter_preset",
                f"filters[{i}] 预置了筛选条件，界面一打开就处于已筛选状态",
                "交付时告知用户「已按 X 筛选，表头可调整」；通常只给范围更稳妥",
            )

    # ---- 5. 明细表 ----
    for i, item in enumerate(spec.get("datasetTables") or []):
        fields = item.get("fields") or []
        if not fields:
            add(
                "error",
                "dt_no_fields",
                f"datasetTables[{i}] 没有提供 fields",
                "用 dataset.py get 取数据集字段后填入",
            )
        for f in fields:
            if not f.get("dataeaseName"):
                add(
                    "warn",
                    "dt_field_incomplete",
                    f"datasetTables[{i}] 字段「{f.get('name')}」缺少 dataeaseName",
                    "dataeaseName 缺失会导致渲染取数对不上字段",
                )
                break
        limit = int(item.get("resultLimit") or 100)
        if limit > RESULT_LIMIT_MAX:
            add(
                "warn",
                "dt_limit_clamped",
                f"datasetTables[{i}] resultLimit={limit} 超过服务端上限 {RESULT_LIMIT_MAX}，会被截断",
                "改为 ≤ 100000 的值，避免与实际取数条数不一致",
            )
        # 明细表渲染块与手工单元格/合并重叠
        sid = item.get("sheet")
        sh = next((s for s in sheets.values() if s.get("name") == sid), None)
        if sh and fields:
            try:
                start = _ref_to_rc(str(item.get("startCell") or "A1"))
            except DataEaseClientError:
                continue
            block = {
                "startRow": start[0],
                "startColumn": start[1],
                "endRow": start[0] + 1,
                "endColumn": start[1] + max(len(fields) - 1, 0),
            }
            for rng in sh.get("mergeData") or []:
                if _ranges_intersect(rng, block):
                    add(
                        "warn",
                        "dt_overlap",
                        f"datasetTables[{i}] 的起始区域与合并单元格重叠",
                        "明细表会盖住手工内容，把 startCell 移到空白区域",
                    )
                    break
            occupied = [
                (r, c)
                for r, row in (sh.get("cellData") or {}).items()
                for c, cell in row.items()
                if cell.get("v") not in (None, "") and _ranges_intersect(
                    {"startRow": r, "endRow": r, "startColumn": c, "endColumn": c}, block
                )
            ]
            if occupied:
                add(
                    "warn",
                    "dt_overlap",
                    f"datasetTables[{i}] 起始区域内有 {len(occupied)} 个手工单元格，会被明细表覆盖",
                    "把 startCell 移到空白区域",
                )

    # ---- 6. 查询组件 ----
    for i, item in enumerate(spec.get("filterComponents") or []):
        if not item.get("conditions"):
            add(
                "error",
                "fc_no_conditions",
                f"filterComponents[{i}] 没有 conditions，查询组件会是一个空壳",
                "至少给出一个过滤条件；不用查询组件就不要声明 filterComponents",
            )

    # ---- 7. 空表 ----
    for sh in sheets.values():
        has_cells = any(
            any(cell.get("v") not in (None, "") or cell.get("f") or cell.get("p")
                for cell in row.values())
            for row in (sh.get("cellData") or {}).values()
        )
        if not has_cells and not spec.get("datasetTables"):
            add(
                "warn",
                "empty_sheet",
                f"工作表「{sh.get('name')}」没有任何内容",
                "确认是否需要该工作表",
            )

    return issues


# ---------------------------------------------------------------------------
# 规格元信息注册表：类型 / 默认值 / 界面位置 / 可达性（单一事实来源）
# 文档与 defaults 命令都据此输出，避免"文档写的默认值"与"代码实际默认值"漂移。
# ---------------------------------------------------------------------------

UI_OK, UI_WARN, UI_NONE = "ok", "warn", "none"
UI_MARK = {UI_OK: "✅", UI_WARN: "⚠️", UI_NONE: "⛔"}
UI_LABEL = {UI_OK: "界面可编辑", UI_WARN: "界面受限", UI_NONE: "界面无入口"}


def _f(key: str, typ: str, default: str, ui: str, where: str, note: str = "") -> dict:
    return {"key": key, "type": typ, "default": default, "ui": ui, "uiWhere": where, "note": note}


SPEC_SCHEMA: list[dict] = [
    {
        "group": "顶层（spec）",
        "items": [
            _f("theme", "business|finance|fresh|minimal", "无（不注入主题样式；`template` 命令默认 business）", UI_NONE,
               "无直接入口（主题只是样式集合）", "不写 theme 时须自建 styles 或接受默认外观"),
            _f("styles", "对象 {样式名: 样式}", "{}", UI_OK, "功能区·字体/版式/数字格式", "单元格用 style 引用，同一份样式可复用"),
            _f("sheets", "数组", "必填（≥1 个）", UI_OK, "工作表标签", "顺序即展示顺序"),
            _f("conditionalFormats", "数组", "[]", UI_OK, "功能区·条件格式"),
            _f("validations", "数组", "[]", UI_OK, "功能区·数据验证"),
            _f("filters", "数组", "[]", UI_OK, "功能区·筛选（表头按钮）", "每表一条"),
            _f("notes", "数组", "[]", UI_OK, "功能区·插入 → 批注"),
            _f("slashCells", "数组", "[]", UI_OK, "功能区·斜线格"),
            _f("datasetTables", "数组", "[]", UI_OK, "功能区·插入 → 明细表"),
            _f("filterComponents", "数组", "[]", UI_OK, "功能区·查询组件", "至多一条（工作簿级单例）"),
        ],
    },
    {
        "group": "sheets[] 工作表",
        "items": [
            _f("name", "字符串", "必填", UI_OK, "工作表标签（双击重命名）"),
            _f("rowCount", "整数", "1000", UI_OK, "右键·插入行"),
            _f("columnCount", "整数", "26", UI_OK, "右键·插入列"),
            _f("defaultColumnWidth", "整数(px)", "93", UI_OK, "拖拽列宽"),
            _f("defaultRowHeight", "整数(px)", "27", UI_OK, "拖拽行高"),
            _f("freeze", "'B2' 或 {xSplit,ySplit,startRow,startColumn}", "无（不冻结）", UI_OK, "功能区·冻结"),
            _f("hidden", "布尔", "false", UI_OK, "工作表标签右键"),
            _f("tabColor", "#RRGGBB", "无（默认标签色）", UI_OK, "工作表标签右键"),
            _f("showGridlines", "布尔", "true", UI_NONE, "无（开关原在菜单栏，菜单栏不显示）", "写 false 后用户无法在界面恢复"),
            _f("rightToLeft", "布尔", "false", UI_NONE, "无", "写 true 后用户无法在界面改回"),
            _f("merges", "['A1:C1', …]", "[]", UI_OK, "功能区·合并单元格", "合并会清空左上角以外的内容"),
            _f("columnWidths", "{'A':120,'B:D':90}", "{}（用 defaultColumnWidth）", UI_OK, "拖拽列宽"),
            _f("rowHeights", "{'1':32,'2:3':24}（1 起始）", "{}（用 defaultRowHeight）", UI_OK, "拖拽行高"),
            _f("cells", "{单元格引用: 单元格}", "{}", UI_OK, "单元格内编辑"),
        ],
    },
    {
        "group": "cells{} 单元格",
        "items": [
            _f("v", "数字/字符串", "无（空单元格）", UI_OK, "单元格内输入"),
            _f("f", "字符串（可不带 =，自动补）", "无", UI_OK, "单元格内输入 / 函数下拉"),
            _f("style", "命名样式名", "无（无样式，走产品默认外观）", UI_OK, "功能区·字体/版式/数字格式"),
            _f("inlineStyle", "对象（键同 styles）", "无", UI_OK, "同上"),
            _f("richText", "[{text, style}]", "无（与 v/f 互斥）", UI_OK, "单元格内富文本编辑"),
            _f("type", "text|number", "无（自动识别值类型）", UI_NONE, "无（'文本转数字'被隐藏，无反向操作）",
               "写入后不可逆；仅用于编码类保留前导零"),
        ],
    },
    {
        "group": "styles{} 样式键（不设置 = 继承单元格/产品默认）",
        "items": [
            _f("bold / italic / underline / strike", "布尔", "false", UI_OK, "功能区·字体组"),
            _f("font", "字体名", "无（产品默认字体）", UI_OK, "功能区·字体"),
            _f("fontSize", "数字(pt)", "无（产品默认字号）", UI_OK, "功能区·字号"),
            _f("bg", "#RRGGBB", "无（透明）", UI_OK, "功能区·背景色"),
            _f("color", "#RRGGBB", "无（默认字色）", UI_OK, "功能区·文字颜色"),
            _f("align", "left|center|right|justified", "无（常规，按值类型自动）", UI_OK, "功能区·水平对齐"),
            _f("valign", "top|middle|bottom", "无（走产品默认）", UI_OK, "功能区·垂直对齐"),
            _f("wrap", "布尔", "false", UI_OK, "功能区·自动换行"),
            _f("numberFormat", "如 #,##0.00 / 0.0% / ¥#,##0.00", "无（常规）", UI_OK, "功能区·数字格式/百分比/货币"),
            _f("border", "all|outline|top|bottom|left|right", "无（无边框）", UI_OK, "功能区·边框",
               "线型固定为细线"),
            _f("borderColor", "#RRGGBB", "#999999（仅在 border 存在时生效）", UI_OK, "功能区·边框颜色"),
        ],
    },
    {
        "group": "validations[] 数据验证",
        "items": [
            _f("sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("range", "'B4:B20'", "'A1'", UI_OK, "数据验证面板·作用范围"),
            _f("type", "list|listMultiple|decimal|whole|textLength|date|time|checkbox|custom|any", "必填", UI_OK, "数据验证·条件类型"),
            _f("renderMode", "arrow|text|chip", "arrow（产品缺省其实是 chip，脚本刻意改为 arrow）", UI_WARN,
               "数据验证·渲染方式", "chip 需逐项配色，缺省会灰底浅字"),
            _f("values", "数组", "无（list 必填之一）", UI_OK, "数据验证·选项来源=自定义"),
            _f("formula", "如 =$F$2:$F$5", "无", UI_OK, "数据验证·选项来源=引用数据"),
            _f("operator", "同条件格式数值比较", "无", UI_OK, "数据验证·条件"),
            _f("allowBlank", "布尔", "true", UI_OK, "数据验证·忽略空值"),
            _f("promptTitle / prompt", "字符串", "无（不显示输入提示）", UI_OK, "数据验证·输入提示"),
            _f("errorTitle / error", "字符串", "无（不显示错误提示）", UI_OK, "数据验证·错误提示"),
        ],
    },
    {
        "group": "filters[] 自动筛选",
        "items": [
            _f("sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("range", "'A3:F200'（首行为表头）", "'A1'", UI_OK, "功能区·筛选"),
            _f("columns", "数组", "[]（只给范围，表头出现筛选按钮）", UI_OK, "表头筛选面板", "预置条件会让表一打开就处于筛选态"),
            _f("columns[].col", "'C'（单列）", "必填", UI_OK, "表头筛选面板"),
            _f("columns[].values", "数组", "无", UI_OK, "表头筛选·按值"),
            _f("columns[].blank", "布尔", "无（不筛空值）", UI_OK, "表头筛选·空值"),
            _f("columns[].custom", "对象/数组", "无", UI_OK, "表头筛选·按条件"),
        ],
    },
    {
        "group": "conditionalFormats[] 条件格式",
        "items": [
            _f("sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("range", "'F3:F200'", "'A1'", UI_OK, "条件格式面板·作用范围"),
            _f("stopIfTrue", "布尔", "false", UI_OK, "条件格式·若为真则停止"),
            _f("rule", "对象", "必填", UI_OK, "条件格式·规则"),
            _f("rule.type", "highlightCell|dataBar|colorScale|iconSet", "必填", UI_OK, "条件格式·规则类型"),
            _f("rule.style", "内联样式（键同 styles）", "无（无格式变化）", UI_OK, "条件格式·格式"),
        ],
    },
    {
        "group": "notes[] 批注 / slashCells[] 斜线格",
        "items": [
            _f("notes[].sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("notes[].cell", "'D3'", "'A1'", UI_OK, "插入 → 批注"),
            _f("notes[].text", "字符串", "''（空批注）", UI_OK, "批注框"),
            _f("notes[].width / height", "整数(px)", "160 / 120", UI_OK, "拖拽批注框"),
            _f("notes[].show", "布尔", "false（不常显，悬停显示）", UI_OK, "批注显示方式"),
            _f("slashCells[].sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("slashCells[].cell", "'F1'", "'A1'", UI_OK, "功能区·斜线格"),
            _f("slashCells[].type", "two|three", "two", UI_OK, "斜线格·二分/三分"),
        ],
    },
    {
        "group": "datasetTables[] 明细表",
        "items": [
            _f("sheet", "字符串", "第一个工作表", UI_OK, "—"),
            _f("startCell", "'A7'", "'A1'", UI_OK, "插入后拖拽放置"),
            _f("datasetId", "字符串", "必填", UI_OK, "明细表·数据集"),
            _f("fields", "数组", "[]（空则报错）", UI_OK, "明细表·字段"),
            _f("blockName", "字符串", "''（用默认块名）", UI_OK, "明细表·自定义块名"),
            _f("resultLimit", "整数", "100", UI_OK, "明细表·结果条数上限", "服务端上限 100000，超出被截断"),
            _f("hideHeader", "布尔", "false", UI_OK, "明细表·隐藏表头"),
            _f("mergeCell", "布尔", "false", UI_OK, "明细表·合并单元格"),
            _f("customFilter", "对象", "{}（不过滤）", UI_OK, "明细表·过滤条件"),
            _f("queryFilter", "数组", "[]", UI_WARN, "由查询组件写入", "一般不要手填，交给 filterComponents"),
        ],
    },
    {
        "group": "filterComponents[] 查询组件",
        "items": [
            _f("sheet / startCell", "字符串", "第一个工作表 / 'A1'", UI_OK, "查询组件拖拽放置"),
            _f("visible", "布尔", "true", UI_OK, "查询组件·显示"),
            _f("conditions", "数组", "必填（非空，否则报错）", UI_OK, "查询组件·查询条件"),
            _f("conditions[].name", "字符串", "取 fieldName", UI_OK, "条件·显示名"),
            _f("conditions[].fieldId / fieldName", "字符串", "必填", UI_OK, "条件·绑定字段"),
            _f("conditions[].displayType", "time|textSelect|numberRange…", "有 granularity → time，否则 textSelect", UI_OK, "条件·类型"),
            _f("conditions[].granularity", "year|month|date|datetime", "date（仅 displayType=time）", UI_OK, "条件·时间粒度"),
            _f("conditions[].optionSource", "auto|…", "auto", UI_OK, "条件·选项来源"),
            _f("conditions[].required", "布尔", "false", UI_OK, "条件·必填"),
            _f("conditions[].multiple", "布尔", "false", UI_OK, "条件·多选"),
            _f("conditions[].visible", "布尔", "true", UI_OK, "条件·显示"),
            _f("conditions[].linkPlugin", "blockName / 块 id", "无（关联全部明细表）", UI_OK, "条件·关联范围"),
            _f("（样式）base.padding / gap", "整数(px)", "16 / 16", UI_OK, "样式面板"),
            _f("（样式）base.layout / align", "字符串", "horizontal / left", UI_OK, "样式面板"),
            _f("（样式）condition.color / fontSize", "字符串 / 整数", "#1f2329 / 12", UI_OK, "样式面板"),
            _f("（样式）conditionName.show / position", "布尔 / 字符串", "true / top", UI_OK, "样式面板"),
            _f("（样式）button.btnList", "数组", "['sure']", UI_OK, "样式面板·按钮"),
            _f("（样式）button.primaryColor", "#RRGGBB", "#3370ff", UI_OK, "样式面板·按钮颜色"),
        ],
    },
    {
        "group": "固定值（不可配，写出即为下列值）",
        "items": [
            _f("workbook.id / name / locale", "字符串", "workbook-01 / Workbook / zhCN", UI_NONE, "—"),
            _f("sheet.zoomRatio / scrollTop / scrollLeft", "数字", "1 / 0 / 0", UI_OK, "视图缩放与滚动（用户可改，不持久）"),
            _f("sheet.selections", "数组", "['A1']", UI_OK, "当前选区"),
            _f("sheet.rowHeader", "对象", "{width:46, hidden:0}", UI_OK, "行头宽度"), 
            _f("sheet.columnHeader", "对象", "{height:20, hidden:0}", UI_OK, "列头高度"),
        ],
    },
]


def cmd_defaults(_client: Optional[DataEaseClient], args: argparse.Namespace) -> int:
    """输出规格各项的类型 / 默认值 / 界面位置 / 可达性（离线）。"""
    groups = SPEC_SCHEMA
    kw = (getattr(args, "key", None) or "").strip().lower()
    if kw:
        groups = [
            {"group": g["group"], "items": [i for i in g["items"] if kw in i["key"].lower()]}
            for g in groups
        ]
        groups = [g for g in groups if g["items"]]
    if args.output_json:
        _print_json(groups)
        return 0
    if getattr(args, "markdown", False):
        print("# 电子表格规格默认值全表\n")
        print("> 本文件由 `python spreadsheet.py defaults --markdown` 生成，请勿手改；")
        print("> 与代码不一致时以命令输出为准。\n")
        print("**档位**：✅ 界面可编辑 · ⚠️ 界面受限 · ⛔ 界面无入口（写入后用户无法在界面改回）\n")
        for g in groups:
            print(f"## {g['group']}\n")
            print("| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |")
            print("|----|------|--------|----------|--------|------|")
            for it in g["items"]:
                def esc(s: str) -> str:
                    return str(s).replace("|", "\\|") or "—"

                print(
                    f"| `{it['key']}` | {esc(it['type'])} | {esc(it['default'])} | {esc(it['uiWhere'])} "
                    f"| {UI_MARK[it['ui']]} {UI_LABEL[it['ui']]} | {esc(it['note'])} |"
                )
            print()
        return 0
    if not groups:
        print(f"未找到匹配 {kw!r} 的键。")
        return 1
    for g in groups:
        print(f"\n== {g['group']} ==")
        for it in g["items"]:
            print(f"  {it['key']}")
            print(f"      类型: {it['type']}")
            print(f"      默认: {it['default']}")
            print(f"      界面: {UI_MARK[it['ui']]} {UI_LABEL[it['ui']]} · {it['uiWhere']}")
            if it["note"]:
                print(f"      说明: {it['note']}")
    print("\n提示：✅ 界面可编辑 / ⚠️ 界面受限 / ⛔ 界面无入口（写入后用户无法在界面改回）")
    return 0


def cmd_lint(_client: Optional[DataEaseClient], args: argparse.Namespace) -> int:
    """离线自检：编译规格并输出界面一致性 / 结构风险。"""
    spec = _load_json(args.json, args.file)
    if spec is None:
        raise DataEaseClientError("请用 --file 或 --json 提供规格")
    issues = lint_spec(spec)
    counts = {lv: sum(1 for x in issues if x["level"] == lv) for lv in ("error", "warn", "info")}
    if args.output_json:
        _print_json(
            {
                "ok": counts["error"] == 0,
                "counts": counts,
                "issues": issues,
            }
        )
        return 1 if counts["error"] else 0

    icons = {"error": "✗", "warn": "!", "info": "i"}
    if not issues:
        print("自检通过：未发现界面一致性或结构风险。")
        return 0
    for it in issues:
        print(f"[{icons[it['level']]}] {it['code']}: {it['msg']}")
        if it["hint"]:
            print(f"      → {it['hint']}")
    print()
    print(f"合计：error {counts['error']} / warn {counts['warn']} / info {counts['info']}")
    if counts["error"]:
        print("存在 error：修正后再 create / edit。")
        return 1
    print("无 error：可以继续；warn 项建议逐条确认。")
    return 0


# ---------------------------------------------------------------------------
# 命令
# ---------------------------------------------------------------------------

def cmd_tree(client: DataEaseClient, args: argparse.Namespace) -> None:
    body: dict = {"busiFlag": "spreadsheet"}
    if args.name:
        body["name"] = args.name
    _print_json(client.post("/spreadsheet/tree", body))


def cmd_resolve_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    """在电子表格树上解析文件夹（第五棵树，勿用其它树的组织根 id）。"""
    from datasource import cmd_resolve_folder as _ds_resolve

    args.kind = "spreadsheet"
    _ds_resolve(client, args)


def _fetch_edit_vo(client: DataEaseClient, sheet_id: str) -> dict:
    vo = client.post("/spreadsheet/findEditById", {"id": sheet_id})
    if not isinstance(vo, dict) or not vo.get("id"):
        raise DataEaseClientError(f"无法获取电子表格编辑稿: {sheet_id}")
    return vo


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    _print_json(client.post("/spreadsheet/findById", {"id": args.id}))


def cmd_get_edit(client: DataEaseClient, args: argparse.Namespace) -> None:
    _print_json(_fetch_edit_vo(client, args.id))


def _resolve_workbook_payload(args: argparse.Namespace) -> str:
    spec = _load_json(args.json, args.file)
    if spec is None:
        raise DataEaseClientError("须提供 --file 或 --json（规格 JSON 或 --raw 工作簿 JSON）")
    if args.raw:
        if not isinstance(spec, dict) or not spec.get("sheets"):
            raise DataEaseClientError("--raw 模式要求完整 Univer 工作簿 JSON（含 sheets）")
        return json.dumps(spec, ensure_ascii=False, separators=(",", ":"))
    # 结构守卫：把这些状态写进去后界面既看不到也改不回来，必须在这里拦死。
    issues = lint_spec(spec)
    errors = [x for x in issues if x["level"] == "error"]
    warns = [x for x in issues if x["level"] == "warn"]
    if errors and not getattr(args, "allow_lint_errors", False):
        detail = "\n".join(
            f"  - [{x['code']}] {x['msg']}" + (f"\n      → {x['hint']}" if x["hint"] else "")
            for x in errors
        )
        raise DataEaseClientError(
            "规格未通过自检，已阻止写入（下列状态界面不会产生，写入后用户无法在界面修复）：\n"
            f"{detail}\n"
            "修正后重试；如确需写入，加 --allow-lint-errors（不推荐，交付时须向用户说明）。"
        )
    if warns:
        print(f"自检提示：{len(warns)} 项需留意（不阻断写入）", file=sys.stderr)
        for x in warns:
            print(f"  ! [{x['code']}] {x['msg']}", file=sys.stderr)
    return json.dumps(compile_workbook(spec), ensure_ascii=False, separators=(",", ":"))


def cmd_create(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    if args.folder_name:
        pid = _resolve_folder(client, folder_name=args.folder_name, kind="spreadsheet")
    else:
        if args.pid is None:
            raise DataEaseClientError("必须指定目标文件夹：--pid 或 --folder-name（电子表格树）")
        pid = _resolve_folder(client, folder_id=args.pid, kind="spreadsheet")
    _assert_within_write_scope(client, pid, role="写入父目录", kind="spreadsheet")

    sheet_data = _resolve_workbook_payload(args)
    body = {
        "name": args.name or "未命名电子表格",
        "pid": pid,
        "nodeType": "sheet",
        "sheetData": sheet_data,
    }
    if args.remark:
        body["remark"] = args.remark
    data = client.post("/spreadsheet/create", body)
    print(
        f"已创建电子表格 id={data.get('id') if isinstance(data, dict) else data}，"
        "修改请使用 edit --session-created，完成后可 publish 发布。",
        file=sys.stderr,
    )
    _print_json(data)


def cmd_edit(client: DataEaseClient, args: argparse.Namespace) -> None:
    """修改电子表格内容。仅限当前任务内创建的表格，须显式 --session-created。"""
    _remind_backup_and_admin(client, mutating=True)
    if not args.session_created:
        raise DataEaseClientError(
            "本 skill 仅支持修改当前任务内创建的电子表格，不支持修改已存在的电子表格。"
            "若确认该表格为本次任务所建，请附加 --session-created 后重试。"
        )
    _assert_within_write_scope(client, args.id, role="编辑目标", kind="spreadsheet")
    vo = _fetch_edit_vo(client, args.id)

    body = {
        "id": str(args.id),
        "name": args.name or vo.get("name"),
        "pid": vo.get("pid"),
        "nodeType": "sheet",
        "sheetData": _resolve_workbook_payload(args),
        # 版本号 +1：编辑器的本地草稿按「草稿版本 == 服务端版本」恢复，
        # 不提升版本会让用户继续看到浏览器里缓存的旧草稿。
        "version": int(vo.get("version") or 0) + 1,
    }
    data = client.post("/spreadsheet/update", body)
    _print_json(data)


def cmd_publish(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    _assert_within_write_scope(client, args.id, role="发布目标", kind="spreadsheet")
    data = client.post("/spreadsheet/updateStatus", {"id": str(args.id), "status": 1})
    _print_json(data)


def cmd_template(client: DataEaseClient, args: argparse.Namespace) -> None:
    """输出高质量规格模板（默认套用主题；可直接改内容后 create）。"""
    theme = getattr(args, "theme", None) or "business"
    tc = theme_colors(theme)
    dg_bg, dg_fg = tc["danger"]
    wn_bg, wn_fg = tc["warn"]
    tpl = {
        "theme": theme,
        "sheets": [
            {
                "name": "销售明细",
                "freeze": "A3",
                "tabColor": tc["primary"],
                "rowCount": 200,
                "columnCount": 10,
                "columnWidths": {"A": 150, "B": 80, "C": 110, "D": 120, "E": 80, "F": 90},
                "rowHeights": {"1": 40, "2": 22, "3": 28},
                "merges": ["A1:F1", "A2:F2"],
                "cells": {
                    "A1": {"v": "月度销售分析", "style": "title"},
                    "A2": {"v": "统计周期：2026-09-01 ~ 2026-09-30　｜　单位：元", "style": "subtitle"},
                    "A3": {"v": "产品名称", "style": "headerLeft"},
                    "B3": {"v": "数量", "style": "header"},
                    "C3": {"v": "单价", "style": "header"},
                    "D3": {"v": "金额", "style": "header"},
                    "E3": {"v": "占比", "style": "header"},
                    "F3": {"v": "状态", "style": "header"},
                    "A4": {"v": "智能手表", "style": "cellText"},
                    "B4": {"v": 12, "style": "qty"},
                    "C4": {"v": 899, "style": "money"},
                    "D4": {"f": "=B4*C4", "style": "money"},
                    "E4": {"f": "=D4/$D$7", "style": "pct"},
                    "F4": {"v": "已结算", "style": "success"},
                    "A5": {"v": "无线耳机", "style": "zebraText"},
                    "B5": {"v": 30, "style": "zebra"},
                    "C5": {"v": 299.5, "style": "zebra"},
                    "D5": {"f": "=B5*C5", "style": "zebra"},
                    "E5": {"f": "=D5/$D$7", "style": "zebra"},
                    "F5": {"v": "待结算", "style": "warn"},
                    "A6": {"v": "蓝牙音箱", "style": "cellText"},
                    "B6": {"v": 8, "style": "qty"},
                    "C6": {"v": 459, "style": "money"},
                    "D6": {"f": "=B6*C6", "style": "money"},
                    "E6": {"f": "=D6/$D$7", "style": "pct"},
                    "F6": {"v": "已结算", "style": "success"},
                    "A7": {"v": "合计", "style": "total"},
                    "B7": {"f": "=SUM(B4:B6)", "style": "total"},
                    "D7": {"f": "=SUM(D4:D6)", "style": "totalMoney"},
                    "E7": {"v": "100.0%", "style": "totalMoney"},
                    "A9": {"v": "注：金额列为公式计算；状态列提供下拉；表头支持点选筛选。", "style": "note"},
                },
            }
        ],
        "conditionalFormats": [
            {
                "sheet": "销售明细",
                "range": "D4:D6",
                "rule": {
                    "type": "highlightCell",
                    "subType": "number",
                    "operator": "lessThan",
                    "value": 5000,
                    "style": {"bg": dg_bg, "color": dg_fg, "bold": True},
                },
            },
            {
                "sheet": "销售明细",
                "range": "B4:B6",
                "rule": {
                    "type": "highlightCell",
                    "subType": "number",
                    "operator": "lessThanOrEqual",
                    "value": 10,
                    "style": {"bg": wn_bg, "color": wn_fg},
                },
            },
        ],
        "validations": [
            {
                "sheet": "销售明细",
                "range": "F4:F200",
                "type": "list",
                "values": ["已结算", "待结算", "已作废"],
                "promptTitle": "状态",
                "prompt": "从下拉列表中选择",
            }
        ],
        "filters": [
            # 默认只给范围：表头出现筛选按钮，由使用者自行勾选。
            # 预置 columns 条件会让表格一打开就处于已筛选态，容易被误判为"数据缺失"。
            {
                "sheet": "销售明细",
                "range": "A3:F200",
            }
        ],
        "notes": [
            {
                "sheet": "销售明细",
                "cell": "D3",
                "text": "金额 = 数量 × 单价；合计行为 SUM 公式",
            }
        ],
    }
    _print_json(tpl)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 电子表格 CLI（第五棵树）")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("tree", help="电子表格资源树")
    t.add_argument("--name", default=None)
    t.set_defaults(func=cmd_tree)

    rf = sub.add_parser("resolve-folder", help="在电子表格树上按 id/名称解析文件夹")
    rf.add_argument("--id", default=None)
    rf.add_argument("--name", default=None)
    rf.set_defaults(func=cmd_resolve_folder)

    g = sub.add_parser("get", help="电子表格详情（发布视图 findById）")
    g.add_argument("--id", required=True)
    g.set_defaults(func=cmd_get)

    ge = sub.add_parser("get-edit", help="电子表格编辑稿（findEditById，含未发布改动）")
    ge.add_argument("--id", required=True)
    ge.set_defaults(func=cmd_get_edit)

    cr = sub.add_parser("create", help="新建电子表格（编译规格后保存到目标文件夹）")
    cr.add_argument("--name", required=True, help="电子表格名称")
    cr.add_argument("--pid", type=int, default=None, help="目标文件夹 id（电子表格树）")
    cr.add_argument("--folder-name", default=None, help="目标文件夹名称（须唯一）")
    cr.add_argument("--file", help="规格 JSON 文件（或 --raw 时为完整工作簿 JSON）")
    cr.add_argument("--json", help="规格 JSON 字符串")
    cr.add_argument("--raw", action="store_true", help="--file/--json 为完整 Univer 工作簿 JSON，直接使用")
    cr.add_argument(
        "--allow-lint-errors",
        action="store_true",
        help="跳过自检拦截（不推荐；仅在已确认这些状态确有必要时使用）",
    )
    cr.add_argument("--remark", default=None)
    cr.set_defaults(func=cmd_create)

    ed = sub.add_parser("edit", help="修改电子表格内容（仅限本任务创建，须 --session-created）")
    ed.add_argument("--id", required=True)
    ed.add_argument("--name", default=None, help="可选，同时改名")
    ed.add_argument("--file", help="新规格 JSON 文件（整表替换）")
    ed.add_argument("--json", help="新规格 JSON 字符串")
    ed.add_argument("--raw", action="store_true", help="--file/--json 为完整 Univer 工作簿 JSON")
    ed.add_argument(
        "--allow-lint-errors",
        action="store_true",
        help="跳过自检拦截（不推荐；仅在已确认这些状态确有必要时使用）",
    )
    ed.add_argument(
        "--session-created",
        action="store_true",
        help="声明该电子表格为当前任务创建（必须，否则拒绝；不支持修改已存在的电子表格）",
    )
    ed.set_defaults(func=cmd_edit)

    pb = sub.add_parser("publish", help="发布电子表格（updateStatus status=1）")
    pb.add_argument("--id", required=True)
    pb.set_defaults(func=cmd_publish)

    tp = sub.add_parser("template", help="输出高质量规格模板 JSON（默认商务主题）")
    tp.add_argument(
        "--theme",
        default="business",
        choices=sorted(_THEME_SPECS),
        help="主题（business/finance/fresh/minimal），影响排版配色预设",
    )
    tp.set_defaults(func=cmd_template)

    ln = sub.add_parser(
        "lint",
        help="离线自检规格：查界面一致性（界面不会产生的状态）与结构风险，不写数据",
    )
    ln.add_argument("--file", help="规格 JSON 文件")
    ln.add_argument("--json", help="规格 JSON 字符串")
    ln.add_argument("--output-json", action="store_true", help="以 JSON 输出，便于程序判定")
    ln.set_defaults(func=cmd_lint)

    df = sub.add_parser(
        "defaults",
        help="离线查询各项的类型 / 默认值 / 界面位置 / 可达性（不确定默认值时先查这里）",
    )
    df.add_argument("--key", default=None, help="按关键字过滤，如 --key rowCount")
    df.add_argument("--output-json", action="store_true", help="以 JSON 输出")
    df.add_argument("--markdown", action="store_true", help="以 Markdown 表格输出（用于生成参考文档）")
    df.set_defaults(func=cmd_defaults)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        # template / lint / defaults 为纯本地命令，无需连接配置
        if args.func.__name__ in ("cmd_template", "cmd_lint", "cmd_defaults"):
            rc = args.func(None, args)
        else:
            rc = args.func(DataEaseClient(), args)
        return rc or 0
    except DataEaseClientError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
