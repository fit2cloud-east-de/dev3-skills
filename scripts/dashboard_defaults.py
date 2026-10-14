"""仪表板（dashboard）默认画布/组件骨架（亮色矩阵布局）。

与 dataV 差异：
- type / busiFlag = dashboard；主题 light；背景 #f5f6f7
- 组件定位以矩阵 x/y/sizeX/sizeY 为准（pcMatrixCount 72×36）
- style.left/top/width/height 由矩阵按参考画布推算，打开编辑器时会再适配
"""

from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any, Optional

from datav_defaults import (
    CHART_TYPES,
    DECORATION_KINDS,
    SUMMARY_OPTIONS,
    chart_render,
    normalize_decoration_kind,
)

# 与前端 dvMain.pcMatrixCount 一致
MATRIX_X = 72
MATRIX_Y = 36
CANVAS_W = 1920
CANVAS_H = 1080

COMMON_BG_LIGHT = {
    "backgroundColorSelect": True,
    "backdropFilterEnable": False,
    "backgroundImageEnable": False,
    "backgroundType": "innerImage",
    "innerImage": "board/board_1.svg",
    "outerImage": None,
    "innerPadding": {"mode": "uniform", "top": 12},
    "borderRadius": {"mode": "uniform", "topLeft": 0},
    "backdropFilter": 4,
    "backgroundColor": "rgba(255,255,255,1)",
    "innerImageColor": "rgba(16, 148, 229,1)",
}

COMMON_BG_MEDIA_LIGHT = {
    **COMMON_BG_LIGHT,
    "backgroundColorSelect": False,
    "backgroundColor": "transparent",
    "innerImage": None,
}


def matrix_to_pixels(
    x: int,
    y: int,
    size_x: int,
    size_y: int,
    *,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
) -> dict[str, int]:
    """矩阵格 → 参考画布像素（baseMargin=0）。"""
    bw = float(canvas_w) / MATRIX_X
    bh = float(canvas_h) / MATRIX_Y
    return {
        "left": int(round(bw * (int(x) - 1))),
        "top": int(round(bh * (int(y) - 1))),
        "width": int(round(bw * int(size_x))),
        "height": int(round(bh * int(size_y))),
    }


def default_canvas_style(
    *,
    width: int = CANVAS_W,
    height: int = CANVAS_H,
    background_color: str = "#f5f6f7",
) -> dict:
    """对齐 DEFAULT_CANVAS_STYLE_DATA_LIGHT（精简可保存字段）。"""
    return {
        "width": width,
        "height": height,
        "refreshBrowserEnable": False,
        "refreshBrowserUnit": "minute",
        "refreshBrowserTime": 5,
        "refreshViewEnable": False,
        "refreshViewLoading": True,
        "refreshUnit": "minute",
        "refreshTime": 5,
        "popupAvailable": True,
        "popupButtonAvailable": True,
        "suspensionButtonAvailable": False,
        "suspensionViewButtonAvailable": True,
        "enableSvgRenderer": False,
        "screenAdaptor": "widthFirst",
        "dashboardAdaptor": "keepHeightAndWidth",
        "scale": 60,
        "scaleWidth": 60,
        "scaleHeight": 60,
        "dvType": "dashboard",
        "tScale": 0.6,
        "tScaleWidth": 0.6,
        "tScaleHeight": 0.6,
        "backgroundColorSelect": True,
        "backgroundImageEnable": False,
        "backgroundType": "backgroundColor",
        "background": "",
        "openCommonStyle": True,
        "opacity": 1,
        "fontSize": 14,
        "fontFamily": "PingFang",
        "themeId": "10001",
        "color": "#000000",
        "backgroundColor": background_color,
        "dialogBackgroundColor": "#fff",
        "dialogButton": "#020408",
        "dashboard": {
            "gap": "yes",
            "gapSize": 5,
            "gapMode": "middle",
            "showGrid": False,
            "matrixBase": 4,
            "resultMode": "all",
            "resultCount": 1000,
            "themeColor": "light",
            "mobileSetting": {
                "customSetting": False,
                "imageUrl": None,
                "backgroundType": "image",
                "color": "#000",
            },
        },
        "component": {
            "chartTitle": {
                "show": True,
                "fontSize": 16,
                "color": "#000000",
                "hPosition": "left",
                "vPosition": "top",
                "isBolder": True,
                "isItalic": False,
                "remarkShow": False,
                "fontFamily": "Microsoft YaHei",
                "remarkBackgroundColor": "#ffffff",
            },
            "chartCommonStyle": deepcopy(COMMON_BG_LIGHT),
            "chartColor": {
                "basicStyle": {
                    "colorScheme": "default",
                    "colors": [
                        "#1E90FF",
                        "#90EE90",
                        "#00CED1",
                        "#E2BD84",
                        "#7A90E0",
                        "#3BA272",
                        "#2BE7FF",
                        "#0A8ADA",
                        "#FFD700",
                    ],
                    "alpha": 100,
                    "gradient": False,
                }
            },
            "filterStyle": {
                "layout": "horizontal",
                "titleLayout": "left",
                "labelColor": "#1f2329",
                "titleColor": "#1f2329",
                "color": "#1f2329",
                "borderColor": "#D9DCDF",
                "text": "#1f2329",
                "bgColor": "#FFFFFF",
            },
            "seniorStyleSetting": {
                "linkageIconColor": "#a6a6a6",
                "drillLayerColor": "#a6a6a6",
                "pagerColor": "#a6a6a6",
                "pagerSize": 14,
            },
        },
    }


def apply_light_view_theme(view: dict) -> dict:
    """把大屏暗色默认改成仪表板亮色可读色。"""
    ca = view.setdefault("customAttr", {})
    lab = ca.setdefault("label", {})
    if lab.get("color") in (None, "", "#ffffff", "#fff"):
        lab["color"] = "#333333"
    ind = ca.setdefault("indicator", {})
    if ind.get("color") in (None, "", "#ffffff", "#fff"):
        ind["color"] = "#0C296E"
    indn = ca.setdefault("indicatorName", {})
    if indn.get("color") in (None, "", "#cccccc", "#ffffff", "#fff"):
        indn["color"] = "#646A73"

    cs = view.setdefault("customStyle", {})
    text = cs.setdefault("text", {})
    text["color"] = "#000000"
    legend = cs.setdefault("legend", {})
    legend["color"] = "#333333"
    for ax in ("xAxis", "yAxis"):
        node = cs.setdefault(ax, {})
        if isinstance(node, dict):
            node["color"] = "#333333"
    return view


def rich_text_centered_html(
    text: str,
    *,
    font_size: int = 28,
    color: str = "#000000",
    bold: bool = True,
) -> str:
    inner = escape(text or "")
    weight = f"<strong>{inner}</strong>" if bold else inner
    return (
        f'<p style="text-align: center;">'
        f'<span style="font-size: {int(font_size)}px; color: {color};">{weight}</span>'
        f"</p>"
    )


def user_view_component(
    *,
    cid: str,
    chart_type: str,
    title: str,
    x: int,
    y: int,
    size_x: int,
    size_y: int,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
) -> dict:
    meta = CHART_TYPES.get(chart_type, {"label": chart_type})
    px = matrix_to_pixels(x, y, size_x, size_y, canvas_w=canvas_w, canvas_h=canvas_h)
    return {
        "id": cid,
        "component": "UserView",
        "name": meta.get("label") or title,
        "label": meta.get("label") or title,
        "innerType": chart_type,
        "render": chart_render(chart_type),
        "propValue": {"textValue": "", "urlList": []},
        "icon": chart_type,
        "editing": False,
        "canvasActive": False,
        "actionSelection": {"linkageActive": "custom"},
        "x": int(x),
        "y": int(y),
        "sizeX": int(size_x),
        "sizeY": int(size_y),
        "style": {
            "adaptation": "adaptation",
            "width": px["width"],
            "height": px["height"],
            "left": px["left"],
            "top": px["top"],
            "rotate": 0,
            "opacity": 1,
            "borderActive": False,
            "borderWidth": 1,
            "borderRadius": 5,
            "borderStyle": "solid",
            "borderColor": "#cccccc",
            "color": "#000000",
            "fontSize": 16,
            "fontWeight": 400,
        },
        "matrixStyle": {},
        "canvasId": "canvas-main",
        "category": "base",
        "isLock": False,
        "isShow": True,
        "dashboardHidden": False,
        "events": {},
        "carousel": {"enable": False, "time": 10},
        "commonBackground": deepcopy(COMMON_BG_LIGHT),
        "state": "ready",
        "linkageFilters": [],
    }


def rich_text_title_component(
    *,
    cid: str,
    text: str,
    x: int,
    y: int,
    size_x: int,
    size_y: int,
    font_size: int = 28,
    color: str = "#000000",
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
) -> tuple[dict, dict]:
    from datav_defaults import base_view_config

    comp = user_view_component(
        cid=cid,
        chart_type="rich-text",
        title=text or "大标题",
        x=x,
        y=y,
        size_x=size_x,
        size_y=size_y,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )
    comp["name"] = "富文本"
    comp["label"] = "富文本"
    comp["icon"] = "rich-text"
    comp["render"] = "custom"
    html = rich_text_centered_html(text, font_size=font_size, color=color)
    comp["propValue"] = {
        "textValue": html,
        "urlList": [],
        "verticalAlign": "center-align",
    }
    view = base_view_config()
    view["id"] = cid
    view["type"] = "rich-text"
    view["render"] = "custom"
    view["title"] = str(text or "大标题")[:40]
    view["tableId"] = ""
    view["customStyle"]["text"]["show"] = False
    apply_light_view_theme(view)
    return comp, view


def decoration_component(
    *,
    cid: str,
    kind: str,
    x: int,
    y: int,
    size_x: int,
    size_y: int,
    prop_value: Any = None,
    url: Optional[str] = None,
    style_extra: Optional[dict] = None,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
) -> dict:
    from datav_defaults import ensure_http_url

    kind_n = normalize_decoration_kind(kind)
    meta = DECORATION_KINDS.get(kind_n, {"component": kind_n, "label": kind_n})
    px = matrix_to_pixels(x, y, size_x, size_y, canvas_w=canvas_w, canvas_h=canvas_h)
    comp: dict[str, Any] = {
        "id": cid,
        "component": meta.get("component") or kind_n,
        "name": meta.get("label") or kind_n,
        "label": meta.get("label") or kind_n,
        "innerType": kind_n,
        "propValue": prop_value if prop_value is not None else "",
        "icon": kind_n,
        "editing": False,
        "canvasActive": False,
        "x": int(x),
        "y": int(y),
        "sizeX": int(size_x),
        "sizeY": int(size_y),
        "style": {
            "width": px["width"],
            "height": px["height"],
            "left": px["left"],
            "top": px["top"],
            "rotate": 0,
            "opacity": 1,
            "color": "#000000",
            "fontSize": 16,
            "fontWeight": 400,
            "backgroundColor": "",
        },
        "matrixStyle": {},
        "canvasId": "canvas-main",
        "category": "base",
        "isLock": False,
        "isShow": True,
        "dashboardHidden": False,
        "events": {},
        "carousel": {"enable": False, "time": 10},
        "commonBackground": deepcopy(COMMON_BG_LIGHT),
        "state": "ready",
    }
    if kind_n == "Picture":
        media_url = url
        if isinstance(prop_value, dict):
            media_url = media_url or prop_value.get("url")
            comp["propValue"] = dict(prop_value)
        else:
            comp["propValue"] = {"url": "", "flip": {"horizontal": False, "vertical": False}}
        if media_url:
            comp["propValue"]["url"] = ensure_http_url(str(media_url))
        comp["style"]["adaptation"] = "adaptation"
        comp["commonBackground"] = deepcopy(COMMON_BG_MEDIA_LIGHT)
    if style_extra and isinstance(style_extra, dict):
        comp["style"].update(style_extra)
    return comp


__all__ = [
    "MATRIX_X",
    "MATRIX_Y",
    "CANVAS_W",
    "CANVAS_H",
    "CHART_TYPES",
    "DECORATION_KINDS",
    "SUMMARY_OPTIONS",
    "COMMON_BG_LIGHT",
    "matrix_to_pixels",
    "default_canvas_style",
    "apply_light_view_theme",
    "rich_text_centered_html",
    "user_view_component",
    "rich_text_title_component",
    "decoration_component",
    "chart_render",
    "normalize_decoration_kind",
]
