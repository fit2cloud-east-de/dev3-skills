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
    op = item.get("operator")
    if op:
        rule["operator"] = op
    formula1 = item.get("formula1") or item.get("formula")
    if formula1 is None and item.get("values") is not None:
        vals = item["values"]
        if vt in ("list", "listMultiple"):
            formula1 = '"' + ",".join(str(v) for v in vals) + '"'
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
    {styles, sheets: [{name, cells, merges, freeze, ...}], conditionalFormats,
     validations, filters, notes, slashCells, datasetTables}
    """
    if not isinstance(spec, dict):
        raise DataEaseClientError("规格须为 JSON 对象")
    styles_dsl = spec.get("styles") or {}
    if not isinstance(styles_dsl, dict):
        raise DataEaseClientError("styles 须为对象: {样式名: {...}}")
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
    if dt_spec:
        dt_configs = []
        for i, item in enumerate(dt_spec):
            if not item.get("datasetId"):
                raise DataEaseClientError(f"datasetTables[{i}] 缺少 datasetId")
            sid = _sheet_id_of("datasetTables", i, default_first=True)
            dt_configs.append(
                {
                    "id": f"detail_{uuid.uuid4().hex[:12]}",
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
                            "customBlockName": bool(item.get("blockName")),
                            "blockName": str(item.get("blockName") or ""),
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

    if resources:
        workbook["resources"] = resources

    return workbook


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
        "version": vo.get("version"),
    }
    data = client.post("/spreadsheet/update", body)
    _print_json(data)


def cmd_publish(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    _assert_within_write_scope(client, args.id, role="发布目标", kind="spreadsheet")
    data = client.post("/spreadsheet/updateStatus", {"id": str(args.id), "status": 1})
    _print_json(data)


def cmd_template(client: DataEaseClient, args: argparse.Namespace) -> None:
    """输出可编辑的规格模板（覆盖主要能力）。"""
    tpl = {
        "styles": {
            "title": {
                "bold": True, "fontSize": 14, "font": "Microsoft YaHei",
                "align": "center", "valign": "middle", "bg": "#FFF2CC", "color": "#333333",
                "border": "all", "borderColor": "#CCCCCC",
            },
            "num2": {"numberFormat": "#,##0.00"},
            "pct": {"numberFormat": "0.0%"},
        },
        "sheets": [
            {
                "name": "Sheet1",
                "rowCount": 200,
                "columnCount": 12,
                "freeze": "A2",
                "tabColor": "#4472C4",
                "columnWidths": {"A": 120, "B:D": 90},
                "rowHeights": {"1": 32},
                "merges": ["A1:D1"],
                "cells": {
                    "A1": {"v": "销售汇总", "style": "title"},
                    "A2": {"v": "产品"}, "B2": {"v": "销售额", "style": "num2"},
                    "A3": {"v": "产品A"}, "B3": {"v": 1200.5, "style": "num2"},
                    "A4": {"v": "产品B"}, "B4": {"v": 890.25, "style": "num2"},
                    "B5": {"f": "=SUM(B3:B4)", "style": "num2"},
                    "C3": {"v": 0.82, "style": "pct"},
                    "D3": {"v": "0012", "type": "text"},
                    "E1": {"richText": [
                        {"text": "重点", "style": {"color": "#CC0000", "bold": True}},
                        {"text": "说明", "style": {"italic": True}},
                    ]},
                },
            },
        ],
        "conditionalFormats": [
            {
                "sheet": "Sheet1", "range": "B3:B5",
                "rule": {
                    "type": "highlightCell", "subType": "number",
                    "operator": "greaterThan", "value": 1000,
                    "style": {"bg": "#FFE0E0", "color": "#CC0000", "bold": True},
                },
            },
        ],
        "validations": [
            {
                "sheet": "Sheet1", "range": "D3:D20", "type": "list",
                "values": ["0012", "0013", "0014"],
                "promptTitle": "编码", "prompt": "从下拉列表选择",
            },
            {
                "sheet": "Sheet1", "range": "B3:B100", "type": "decimal",
                "operator": "greaterThanOrEqual", "values": [0],
                "errorTitle": "非法输入", "error": "销售额须 ≥ 0",
            },
        ],
        "filters": [
            {
                "sheet": "Sheet1", "range": "A2:D100",
                "columns": [{"col": "A", "values": ["产品A"]}],
            }
        ],
        "notes": [{"sheet": "Sheet1", "cell": "A1", "text": "表头行已冻结"}],
        "slashCells": [{"sheet": "Sheet1", "cell": "F1", "type": "two"}],
        "datasetTables": [
            {
                "sheet": "Sheet1", "startCell": "H2", "datasetId": "<数据集ID>",
                "resultLimit": 100,
                "fields": [
                    {
                        "id": "<字段ID>", "name": "<字段名>", "dataeaseName": "<f_xxxx>",
                        "groupType": "d", "deType": 0,
                    }
                ],
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
    cr.add_argument("--remark", default=None)
    cr.set_defaults(func=cmd_create)

    ed = sub.add_parser("edit", help="修改电子表格内容（仅限本任务创建，须 --session-created）")
    ed.add_argument("--id", required=True)
    ed.add_argument("--name", default=None, help="可选，同时改名")
    ed.add_argument("--file", help="新规格 JSON 文件（整表替换）")
    ed.add_argument("--json", help="新规格 JSON 字符串")
    ed.add_argument("--raw", action="store_true", help="--file/--json 为完整 Univer 工作簿 JSON")
    ed.add_argument(
        "--session-created",
        action="store_true",
        help="声明该电子表格为当前任务创建（必须，否则拒绝；不支持修改已存在的电子表格）",
    )
    ed.set_defaults(func=cmd_edit)

    pb = sub.add_parser("publish", help="发布电子表格（updateStatus status=1）")
    pb.add_argument("--id", required=True)
    pb.set_defaults(func=cmd_publish)

    tp = sub.add_parser("template", help="输出规格模板 JSON")
    tp.set_defaults(func=cmd_template)

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
