"""数据大屏内置排版模板：平均分布 3×4、居中结构-形式二。

画布默认 1920×1080。各 slot 返回 {left, top, width, height}（像素）。
内容槽可放任意图表/表格/指标卡等；标题槽通常用 ScrollText / rich-text。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

CANVAS_W = 1920
CANVAS_H = 1080
MARGIN = 24
GAP = 16
TITLE_H = 72


def _rect(left: int, top: int, width: int, height: int) -> dict[str, int]:
    return {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
    }


def layout_grid_3x4(
    *,
    width: int = CANVAS_W,
    height: int = CANVAS_H,
    margin: int = MARGIN,
    gap: int = GAP,
    title_h: int = TITLE_H,
) -> dict[str, Any]:
    """平均分布 3×4：顶栏大标题 + 3 行 × 4 列等分内容区。"""
    title = _rect(margin, margin, width - 2 * margin, title_h)
    body_top = margin + title_h + gap
    body_h = height - body_top - margin
    body_w = width - 2 * margin
    cols, rows = 4, 3
    cell_w = (body_w - (cols - 1) * gap) // cols
    cell_h = (body_h - (rows - 1) * gap) // rows
    slots: dict[str, dict[str, int]] = {"title": title}
    order = ["title"]
    for r in range(rows):
        for c in range(cols):
            name = f"c{r * cols + c}"
            slots[name] = _rect(
                margin + c * (cell_w + gap),
                body_top + r * (cell_h + gap),
                cell_w,
                cell_h,
            )
            order.append(name)
    return {
        "id": "grid_3x4",
        "name": "平均分布 3×4",
        "aliases": ["平均分布", "平均分布3*4", "平均分布3x4", "grid_3x4", "grid3x4"],
        "description": "顶部大标题 + 12 个等大内容格（3 行 4 列），适合多图均分展示。",
        "canvas": {"width": width, "height": height},
        "titleSlot": "title",
        "contentSlots": [s for s in order if s != "title"],
        "slotOrder": order,
        "slots": slots,
    }


def layout_center_v2(
    *,
    width: int = CANVAS_W,
    height: int = CANVAS_H,
    margin: int = MARGIN,
    gap: int = GAP,
    title_h: int = TITLE_H,
) -> dict[str, Any]:
    """居中结构-形式二：大标题 + 中央主视觉 + 左右各 2 次要 + 主视觉下方 1 次要。"""
    title = _rect(margin, margin, width - 2 * margin, title_h)
    body_top = margin + title_h + gap
    body_h = height - body_top - margin
    body_w = width - 2 * margin
    # 左右较窄、中间较宽（约 1 : 2.2 : 1）
    side_w = (body_w - 2 * gap) * 22 // 100
    center_w = body_w - 2 * side_w - 2 * gap
    # 中间：主视觉约占 62%，下方次要约占 38%
    main_h = (body_h - gap) * 62 // 100
    bottom_h = body_h - gap - main_h
    side_cell_h = (body_h - gap) // 2

    left_x = margin
    center_x = margin + side_w + gap
    right_x = center_x + center_w + gap

    slots = {
        "title": title,
        "main": _rect(center_x, body_top, center_w, main_h),
        "secondary_bottom": _rect(center_x, body_top + main_h + gap, center_w, bottom_h),
        "secondary_left_top": _rect(left_x, body_top, side_w, side_cell_h),
        "secondary_left_bottom": _rect(left_x, body_top + side_cell_h + gap, side_w, side_cell_h),
        "secondary_right_top": _rect(right_x, body_top, side_w, side_cell_h),
        "secondary_right_bottom": _rect(right_x, body_top + side_cell_h + gap, side_w, side_cell_h),
    }
    # 填充顺序：主视觉优先，再环绕次要（左上→右上→左下→右下→底）
    content = [
        "main",
        "secondary_left_top",
        "secondary_right_top",
        "secondary_left_bottom",
        "secondary_right_bottom",
        "secondary_bottom",
    ]
    return {
        "id": "center_v2",
        "name": "居中结构-形式二",
        "aliases": ["居中结构", "居中结构形式二", "居中结构-形式二", "center_v2", "center"],
        "description": "顶部大标题；中央主内容（地图/主图表）；左右各两块次要；主内容下方一块次要辅助。",
        "canvas": {"width": width, "height": height},
        "titleSlot": "title",
        "contentSlots": content,
        "slotOrder": ["title"] + content,
        "primarySlots": ["main"],
        "secondarySlots": [s for s in content if s != "main"],
        "slots": slots,
    }


LAYOUT_BUILDERS = {
    "grid_3x4": layout_grid_3x4,
    "center_v2": layout_center_v2,
}


def all_layouts(*, width: int = CANVAS_W, height: int = CANVAS_H) -> list[dict[str, Any]]:
    return [fn(width=width, height=height) for fn in LAYOUT_BUILDERS.values()]


def resolve_layout_id(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = str(name).strip().lower().replace("×", "x").replace("*", "x").replace(" ", "")
    # normalize chinese-ish keys too
    raw = str(name).strip()
    for lid, fn in LAYOUT_BUILDERS.items():
        meta = fn()
        aliases = [meta["id"], meta["name"]] + list(meta.get("aliases") or [])
        for a in aliases:
            an = str(a).strip().lower().replace("×", "x").replace("*", "x").replace(" ", "")
            if key == an or raw == a:
                return lid
    return None


def get_layout(name: str, *, width: int = CANVAS_W, height: int = CANVAS_H) -> dict[str, Any]:
    lid = resolve_layout_id(name)
    if not lid:
        known = []
        for fn in LAYOUT_BUILDERS.values():
            m = fn()
            known.append(f"{m['id']}（{m['name']}）")
        raise ValueError(f"未知布局模板「{name}」。可选：{', '.join(known)}")
    return LAYOUT_BUILDERS[lid](width=width, height=height)


def apply_template_to_plan(plan: dict) -> dict:
    """
    若 plan 含 layout / layoutTemplate，则为缺失 layout 的标题装饰与 charts 填入 slot 坐标。
    已显式写 layout.left/top 的项不覆盖。
    """
    out = deepcopy(plan)
    layout_name = out.get("layout") or out.get("layoutTemplate") or out.get("template")
    if not layout_name:
        return out

    canvas = out.get("canvas") or {}
    w = int(canvas.get("width") or CANVAS_W)
    h = int(canvas.get("height") or CANVAS_H)
    tpl = get_layout(str(layout_name), width=w, height=h)
    out["_resolvedLayout"] = {"id": tpl["id"], "name": tpl["name"]}
    out.setdefault("canvas", {})
    out["canvas"].setdefault("width", w)
    out["canvas"].setdefault("height", h)

    slots = tpl["slots"]
    title_slot = tpl["titleSlot"]
    title_text = out.get("title") or out.get("name") or "数据大屏"

    # 标题装饰：无 decorations 含 title 槽或显式 title 装饰时自动补 ScrollText
    decorations = list(out.get("decorations") or [])
    has_title_dec = any(
        (d.get("slot") == title_slot)
        or (d.get("kind") in ("ScrollText", "rich-text") and not (d.get("layout") or {}).get("left") is None and d.get("role") == "title")
        for d in decorations
    )
    # 更稳：若没有任何 slot=title 的装饰，则插入
    if not any(d.get("slot") == title_slot for d in decorations):
        decorations.insert(
            0,
            {
                "slot": title_slot,
                "kind": "ScrollText",
                "role": "title",
                "text": title_text,
                "layout": dict(slots[title_slot]),
                "style": {
                    "fontSize": 36,
                    "color": "#ffffff",
                    "fontWeight": 700,
                    "backgroundColor": "transparent",
                },
            },
        )
    else:
        for d in decorations:
            if d.get("slot") == title_slot and not _has_explicit_box(d.get("layout")):
                d["layout"] = dict(slots[title_slot])
    out["decorations"] = decorations

    content_slots = list(tpl["contentSlots"])
    charts = list(out.get("charts") or [])
    used = set()
    # 先处理带 slot 名的
    for ch in charts:
        sn = ch.get("slot")
        if sn and sn in slots:
            if not _has_explicit_box(ch.get("layout")):
                ch["layout"] = dict(slots[sn])
            used.add(sn)
    # 再按顺序填未指定 layout/slot 的图
    free = [s for s in content_slots if s not in used]
    fi = 0
    for ch in charts:
        if _has_explicit_box(ch.get("layout")) or ch.get("slot"):
            continue
        if fi >= len(free):
            break
        sn = free[fi]
        fi += 1
        ch["slot"] = sn
        ch["layout"] = dict(slots[sn])
        used.add(sn)
    out["charts"] = charts

    # 装饰（非标题）也可按 slot 填
    for d in out["decorations"]:
        sn = d.get("slot")
        if sn and sn in slots and sn != title_slot and not _has_explicit_box(d.get("layout")):
            d["layout"] = dict(slots[sn])

    return out


def _has_explicit_box(layout: Any) -> bool:
    if not isinstance(layout, dict):
        return False
    return all(k in layout for k in ("left", "top", "width", "height"))
