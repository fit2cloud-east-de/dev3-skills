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

# 居中主视觉「宏大感」：按图种视觉冲击加权（不是单纯放大像素）
# 面状/纪念碑式柱体优先；密表、细条、纯数字不宜占主舞台
HERO_VISUAL_WEIGHT: dict[str, int] = {
    "map": 100,
    "treemap": 92,
    "bar": 85,
    "bar-group": 82,
    "bar-stack": 75,
    "waterfall": 72,
    "pie-donut": 68,
    "pie": 64,
    "funnel": 62,
    "area": 58,
    "area-stack": 56,
    "radar": 50,
    "line": 42,
    "bar-horizontal": 36,
    "bar-stack-horizontal": 34,
    "gauge": 32,
    "liquid": 32,
    "indicator": 28,
    "word-cloud": 45,
    "scatter": 40,
    "table-info": 12,
    "table-normal": 12,
    "table-pivot": 10,
    "rich-text": 8,
}


def hero_weight(chart_type: Optional[str]) -> int:
    if not chart_type:
        return 0
    return int(HERO_VISUAL_WEIGHT.get(str(chart_type), 40))


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
    """居中结构-形式二：大标题 + 中央主视觉舞台 + 左右陪衬 + 底栏辅图。

    构图原则（宏大 ≠ 单纯放大）：
    - 中栏更宽、主舞台更高，形成明确视觉重心；
    - 左右变窄作「翼」；底栏变扁作「基座」，衬托主视觉；
    - 主槽宜放 treemap/map/柱体等面状或纪念碑式图种，忌密条/明细表占中。
    """
    # 略收边距，让主舞台更「压得住」画面
    margin = max(16, int(margin))
    gap = max(12, int(gap))
    title_h = max(64, int(title_h))

    title = _rect(margin, margin, width - 2 * margin, title_h)
    body_top = margin + title_h + gap
    body_h = height - body_top - margin
    body_w = width - 2 * margin
    # 翼 : 舞台 : 翼 ≈ 0.16 : 0.68 : 0.16（原约 0.22:0.56:0.22）
    side_w = (body_w - 2 * gap) * 16 // 100
    center_w = body_w - 2 * side_w - 2 * gap
    # 主舞台约 72%，底栏基座约 28%（原 62/38）
    main_h = (body_h - gap) * 72 // 100
    bottom_h = body_h - gap - main_h
    # 左右翼：上格略高（与主舞台上沿对齐感），下格略矮
    side_top_h = (body_h - gap) * 48 // 100
    side_bot_h = body_h - gap - side_top_h

    left_x = margin
    center_x = margin + side_w + gap
    right_x = center_x + center_w + gap

    slots = {
        "title": title,
        "main": _rect(center_x, body_top, center_w, main_h),
        "secondary_bottom": _rect(center_x, body_top + main_h + gap, center_w, bottom_h),
        "secondary_left_top": _rect(left_x, body_top, side_w, side_top_h),
        "secondary_left_bottom": _rect(left_x, body_top + side_top_h + gap, side_w, side_bot_h),
        "secondary_right_top": _rect(right_x, body_top, side_w, side_top_h),
        "secondary_right_bottom": _rect(
            right_x, body_top + side_top_h + gap, side_w, side_bot_h
        ),
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
        "description": (
            "顶栏标题 + 中央主视觉舞台（宜 map/treemap/柱体等宏大图种）"
            " + 左右窄翼陪衬 + 底栏扁基座辅图。宏大靠构图层级与图种，而非只放大像素。"
        ),
        "canvas": {"width": width, "height": height},
        "titleSlot": "title",
        "contentSlots": content,
        "slotOrder": ["title"] + content,
        "primarySlots": ["main"],
        "secondarySlots": [s for s in content if s != "main"],
        "heroHint": {
            "prefer": ["map", "treemap", "bar", "bar-group", "bar-stack", "pie-donut"],
            "avoid": ["table-info", "table-normal", "bar-stack-horizontal", "indicator", "rich-text"],
            "note": "主槽选面状/纪念碑式图种；密条、明细、小指标放翼或底栏",
        },
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

    # 大标题：用富文本（界面「居中对齐」写入 propValue.textValue），不用滚动文字
    decorations = list(out.get("decorations") or [])
    if not any(d.get("slot") == title_slot for d in decorations):
        decorations.insert(
            0,
            {
                "slot": title_slot,
                "kind": "rich-text",
                "role": "title",
                "text": title_text,
                "layout": dict(slots[title_slot]),
                "fontSize": 36,
                "color": "#ffffff",
            },
        )
    else:
        for d in decorations:
            if d.get("slot") != title_slot:
                continue
            if not _has_explicit_box(d.get("layout")):
                d["layout"] = dict(slots[title_slot])
            # 若仍是滚动文字，升级为富文本居中（与产品配置一致）
            if (d.get("kind") or d.get("component")) == "ScrollText":
                d["kind"] = "rich-text"
            d.setdefault("text", title_text)
            d.setdefault("fontSize", 36)
            d.setdefault("color", "#ffffff")
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

    # 居中结构：按视觉冲击把更「宏大」的图种换到 main（可 plan.compose=false 关闭）
    if tpl["id"] == "center_v2" and out.get("compose", True) is not False:
        out["charts"] = promote_hero_to_main(out["charts"], slots)

    # 装饰（非标题）也可按 slot 填
    for d in out["decorations"]:
        sn = d.get("slot")
        if sn and sn in slots and sn != title_slot and not _has_explicit_box(d.get("layout")):
            d["layout"] = dict(slots[sn])

    return out


def promote_hero_to_main(charts: list, slots: dict[str, dict]) -> list:
    """若 main 图种冲击力明显弱于其它槽，交换 slot/layout，形成主视觉重心。"""
    if not charts or "main" not in slots:
        return charts
    main_i = next((i for i, ch in enumerate(charts) if ch.get("slot") == "main"), None)
    if main_i is None:
        return charts
    main_w = hero_weight(charts[main_i].get("type"))
    best_i, best_w = main_i, main_w
    for i, ch in enumerate(charts):
        if i == main_i:
            continue
        w = hero_weight(ch.get("type"))
        if w > best_w:
            best_i, best_w = i, w
    # 需明显更强才换（避免无意义对调）
    if best_i == main_i or best_w < main_w + 15:
        return charts

    cur, hero = charts[main_i], charts[best_i]
    other_slot = hero.get("slot") or "secondary_bottom"
    cur["slot"], hero["slot"] = other_slot, "main"
    cur["layout"] = dict(slots.get(other_slot) or slots.get("secondary_bottom") or {})
    hero["layout"] = dict(slots["main"])
    cur["_composeNote"] = f"主视觉让位给更高冲击图种 {hero.get('type')}"
    hero["_composeNote"] = "提升为主视觉（宏大构图）"
    return charts


def _has_explicit_box(layout: Any) -> bool:
    if not isinstance(layout, dict):
        return False
    return all(k in layout for k in ("left", "top", "width", "height"))
