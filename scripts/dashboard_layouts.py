"""仪表板矩阵排版模板（pcMatrixCount 72×36，1-based x/y）。

各 slot 返回 {x, y, sizeX, sizeY}；打开编辑器后由前端按容器再算像素。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from dashboard_defaults import MATRIX_X, MATRIX_Y


def _cell(x: int, y: int, size_x: int, size_y: int) -> dict[str, int]:
    return {"x": int(x), "y": int(y), "sizeX": int(size_x), "sizeY": int(size_y)}


def layout_grid_2x2() -> dict[str, Any]:
    """顶栏标题 + 2×2 等内容区。"""
    title_h = 4
    body_y = title_h + 1
    body_h = MATRIX_Y - title_h
    half_x = MATRIX_X // 2
    half_y = body_h // 2
    slots = {
        "title": _cell(1, 1, MATRIX_X, title_h),
        "c0": _cell(1, body_y, half_x, half_y),
        "c1": _cell(half_x + 1, body_y, MATRIX_X - half_x, half_y),
        "c2": _cell(1, body_y + half_y, half_x, body_h - half_y),
        "c3": _cell(half_x + 1, body_y + half_y, MATRIX_X - half_x, body_h - half_y),
    }
    content = ["c0", "c1", "c2", "c3"]
    return {
        "id": "grid_2x2",
        "name": "平均分布 2×2",
        "aliases": ["平均分布2x2", "平均分布2*2", "grid_2x2", "grid2x2", "2x2"],
        "description": "顶栏大标题 + 2 行 × 2 列等大内容格，适合概览看板。",
        "matrix": {"x": MATRIX_X, "y": MATRIX_Y},
        "titleSlot": "title",
        "contentSlots": content,
        "slotOrder": ["title"] + content,
        "slots": slots,
    }


def layout_grid_3x2() -> dict[str, Any]:
    """顶栏标题 + 3 列 × 2 行。"""
    title_h = 4
    body_y = title_h + 1
    body_h = MATRIX_Y - title_h
    cols, rows = 3, 2
    cell_w = MATRIX_X // cols
    cell_h = body_h // rows
    slots: dict[str, dict[str, int]] = {"title": _cell(1, 1, MATRIX_X, title_h)}
    content: list[str] = []
    for r in range(rows):
        for c in range(cols):
            name = f"c{r * cols + c}"
            # 末列/末行吃掉余数，铺满矩阵
            sx = cell_w if c < cols - 1 else MATRIX_X - c * cell_w
            sy = cell_h if r < rows - 1 else body_h - r * cell_h
            slots[name] = _cell(1 + c * cell_w, body_y + r * cell_h, sx, sy)
            content.append(name)
    return {
        "id": "grid_3x2",
        "name": "平均分布 3×2",
        "aliases": ["平均分布3x2", "平均分布3*2", "grid_3x2", "grid3x2", "3x2"],
        "description": "顶栏大标题 + 3 列 × 2 行共 6 个内容格。",
        "matrix": {"x": MATRIX_X, "y": MATRIX_Y},
        "titleSlot": "title",
        "contentSlots": content,
        "slotOrder": ["title"] + content,
        "slots": slots,
    }


def layout_kpi_charts() -> dict[str, Any]:
    """顶栏标题 + 一行 4 指标卡 + 底栏 2 大图。"""
    title_h = 4
    kpi_h = 8
    kpi_y = title_h + 1
    chart_y = kpi_y + kpi_h
    chart_h = MATRIX_Y - title_h - kpi_h
    kpi_w = MATRIX_X // 4
    half_x = MATRIX_X // 2
    slots = {
        "title": _cell(1, 1, MATRIX_X, title_h),
        "k0": _cell(1, kpi_y, kpi_w, kpi_h),
        "k1": _cell(1 + kpi_w, kpi_y, kpi_w, kpi_h),
        "k2": _cell(1 + 2 * kpi_w, kpi_y, kpi_w, kpi_h),
        "k3": _cell(1 + 3 * kpi_w, kpi_y, MATRIX_X - 3 * kpi_w, kpi_h),
        "c0": _cell(1, chart_y, half_x, chart_h),
        "c1": _cell(half_x + 1, chart_y, MATRIX_X - half_x, chart_h),
    }
    content = ["k0", "k1", "k2", "k3", "c0", "c1"]
    return {
        "id": "kpi_charts",
        "name": "指标卡 + 双图",
        "aliases": ["指标双图", "kpi_charts", "kpi+charts", "kpi"],
        "description": "顶栏标题 + 一行 4 指标卡 + 底栏左右两大图，常见经营看板结构。",
        "matrix": {"x": MATRIX_X, "y": MATRIX_Y},
        "titleSlot": "title",
        "contentSlots": content,
        "slotOrder": ["title"] + content,
        "kpiSlots": ["k0", "k1", "k2", "k3"],
        "chartSlots": ["c0", "c1"],
        "slots": slots,
    }


LAYOUT_BUILDERS = {
    "grid_2x2": layout_grid_2x2,
    "grid_3x2": layout_grid_3x2,
    "kpi_charts": layout_kpi_charts,
}


def all_layouts() -> list[dict[str, Any]]:
    return [fn() for fn in LAYOUT_BUILDERS.values()]


def resolve_layout_id(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = str(name).strip().lower().replace("×", "x").replace("*", "x").replace(" ", "")
    raw = str(name).strip()
    for lid, fn in LAYOUT_BUILDERS.items():
        meta = fn()
        aliases = [meta["id"], meta["name"]] + list(meta.get("aliases") or [])
        for a in aliases:
            an = str(a).strip().lower().replace("×", "x").replace("*", "x").replace(" ", "")
            if key == an or raw == a:
                return lid
    return None


def get_layout(name: str) -> dict[str, Any]:
    lid = resolve_layout_id(name)
    if not lid:
        known = [f"{fn()['id']}（{fn()['name']}）" for fn in LAYOUT_BUILDERS.values()]
        raise ValueError(f"未知仪表板布局「{name}」。可选：{', '.join(known)}")
    return LAYOUT_BUILDERS[lid]()


def _has_matrix_layout(item: dict) -> bool:
    lay = item.get("layout") or {}
    return all(k in lay for k in ("x", "y", "sizeX", "sizeY"))


def apply_template_to_plan(plan: dict) -> dict:
    """若 plan 含 layout，则为缺失矩阵坐标的标题/图表填入槽位。"""
    out = deepcopy(plan)
    layout_name = out.get("layout") or out.get("layoutTemplate") or out.get("template")
    if not layout_name:
        return out

    tpl = get_layout(str(layout_name))
    out["_resolvedLayout"] = {"id": tpl["id"], "name": tpl["name"]}
    slots = tpl["slots"]
    title_slot = tpl["titleSlot"]
    title_text = out.get("title") or out.get("name") or "仪表板"

    decorations = list(out.get("decorations") or [])
    if not any(d.get("slot") == title_slot for d in decorations):
        decorations.insert(
            0,
            {
                "kind": "rich-text",
                "role": "title",
                "slot": title_slot,
                "text": title_text,
                "layout": dict(slots[title_slot]),
            },
        )
    else:
        for d in decorations:
            if d.get("slot") == title_slot and not _has_matrix_layout(d):
                d["layout"] = dict(slots[title_slot])
    out["decorations"] = decorations

    charts = list(out.get("charts") or [])
    used: set[str] = set()
    for ch in charts:
        slot = ch.get("slot")
        if slot and slot in slots and not _has_matrix_layout(ch):
            ch["layout"] = dict(slots[slot])
            used.add(slot)
    free = [s for s in tpl["contentSlots"] if s not in used]
    fi = 0
    for ch in charts:
        if _has_matrix_layout(ch):
            continue
        if ch.get("slot") and ch["slot"] in slots:
            continue
        if fi >= len(free):
            break
        slot = free[fi]
        fi += 1
        ch["slot"] = slot
        ch["layout"] = dict(slots[slot])
    out["charts"] = charts
    return out
