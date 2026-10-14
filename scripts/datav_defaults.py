"""数据大屏默认画布/组件/图表骨架（暗色 1920×1080）。"""

from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any, Optional

# 与前端 chart.ts / ChartRenderType 一致：这三类注册在 render=custom 下
CUSTOM_RENDER_TYPES = frozenset({"rich-text", "picture-group", "indicator"})


def chart_render(chart_type: str) -> str:
    """界面选图表时写入的 render：custom | antv。"""
    return "custom" if chart_type in CUSTOM_RENDER_TYPES else "antv"


# 图表类型：value → (分类, 中文名, 轴约束说明)
CHART_TYPES: dict[str, dict[str, Any]] = {
    "indicator": {"category": "quota", "label": "指标卡", "axes": "yAxis(1 数值指标)"},
    "gauge": {"category": "quota", "label": "仪表盘", "axes": "yAxis(1)"},
    "liquid": {"category": "quota", "label": "水波图", "axes": "yAxis(1)"},
    "table-info": {"category": "table", "label": "明细表", "axes": "xAxis(列，d/q 均可)"},
    "table-normal": {"category": "table", "label": "汇总表", "axes": "xAxis(维)+yAxis(指标)"},
    "table-pivot": {"category": "table", "label": "透视表", "axes": "行列维+指标"},
    "line": {"category": "trend", "label": "折线图", "axes": "xAxis(d)+yAxis(q)；可选 xAxisExt"},
    "area": {"category": "trend", "label": "面积图", "axes": "xAxis(d)+yAxis(q)"},
    "area-stack": {"category": "trend", "label": "堆叠面积图", "axes": "xAxis+yAxis+extStack"},
    "bar": {"category": "compare", "label": "柱状图", "axes": "xAxis(d)+yAxis(q)"},
    "bar-stack": {"category": "compare", "label": "堆叠柱状图", "axes": "xAxis+yAxis+extStack"},
    "bar-group": {"category": "compare", "label": "分组柱状图", "axes": "xAxis+xAxisExt+yAxis"},
    "bar-horizontal": {"category": "compare", "label": "条形图", "axes": "xAxis(d)+yAxis(q)"},
    "waterfall": {"category": "compare", "label": "瀑布图", "axes": "xAxis+yAxis"},
    "pie": {"category": "distribute", "label": "饼图", "axes": "xAxis(d)+yAxis(1 指标)"},
    "pie-donut": {"category": "distribute", "label": "环形图", "axes": "xAxis(d)+yAxis(1)"},
    "radar": {"category": "distribute", "label": "雷达图", "axes": "xAxis+yAxis"},
    "treemap": {"category": "distribute", "label": "矩形树图", "axes": "xAxis+yAxis"},
    "word-cloud": {"category": "distribute", "label": "词云", "axes": "xAxis+yAxis"},
    "scatter": {"category": "relation", "label": "散点图", "axes": "xAxis+yAxis"},
    "funnel": {"category": "relation", "label": "漏斗图", "axes": "xAxis+yAxis"},
    "map": {"category": "map", "label": "地图", "axes": "需地理字段与地图配置"},
    "rich-text": {"category": "other", "label": "富文本", "axes": "可选绑定字段"},
}

# 装饰/非图表组件（大屏左栏可用）
DECORATION_KINDS: dict[str, dict[str, Any]] = {
    "ScrollText": {"component": "ScrollText", "label": "滚动文字", "needs": "propValue 文本"},
    "Picture": {"component": "Picture", "label": "图片", "needs": "propValue.url 或 outerImage"},
    "RectShape": {"component": "RectShape", "label": "矩形色块", "needs": "style 背景色"},
    "CircleShape": {"component": "CircleShape", "label": "圆形", "needs": "style"},
    "SvgTriangle": {"component": "SvgTriangle", "label": "三角形", "needs": "style"},
    "CanvasBoard": {"component": "CanvasBoard", "label": "边框素材", "needs": "innerType board_1..9"},
    "DeDecoration": {"component": "DeDecoration", "label": "装饰条", "needs": "innerType DeDecoration1..5"},
    "CanvasIcon": {"component": "CanvasIcon", "label": "图标", "needs": "innerType"},
    "DeTimeClock": {"component": "DeTimeClock", "label": "时间器", "needs": "-"},
    "DeVideo": {"component": "DeVideo", "label": "视频", "needs": "视频地址"},
    "VQuery": {"component": "VQuery", "label": "查询组件", "needs": "propValue 条件 + canvasViewInfo"},
}

SUMMARY_OPTIONS = (
    "sum",
    "avg",
    "max",
    "min",
    "count",
    "count_distinct",
    "stddev_pop",
    "var_pop",
)

COMMON_BG_SCREEN = {
    "backgroundColorSelect": False,
    "backdropFilterEnable": False,
    "backgroundImageEnable": False,
    "backgroundType": "innerImage",
    "innerImage": "board/board_1.svg",
    "outerImage": None,
    "innerPadding": {"mode": "uniform", "top": 12},
    "borderRadius": {"mode": "uniform", "topLeft": 0},
    "backdropFilter": 4,
    "backgroundColor": "#131E42",
    "innerImageColor": "#1094E5",
}

COMMON_BG_DECOR = {
    **COMMON_BG_SCREEN,
    "backgroundColorSelect": True,
    "backgroundType": "color",
    "innerImage": None,
    "backgroundColor": "rgba(19,28,66,0.6)",
}

def default_canvas_style(*, width: int = 1920, height: int = 1080, background_color: str = "#020408") -> dict:
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
        "scale": 100,
        "scaleWidth": 100,
        "scaleHeight": 100,
        "dataVActualSizeVersion": 1,
        "dvType": "dataV",
        "tScale": 1,
        "tScaleWidth": 1,
        "tScaleHeight": 1,
        "backgroundColorSelect": True,
        "backgroundImageEnable": False,
        "backgroundType": "backgroundColor",
        "background": "",
        "openCommonStyle": True,
        "opacity": 1,
        "fontSize": 14,
        "fontFamily": "PingFang",
        "themeId": "10002",
        "color": "#fff",
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
            "themeColor": "dark",
            "mobileSetting": {"customSetting": False, "imageUrl": None, "backgroundType": "image", "color": "#fff"},
        },
        "component": {
            "chartTitle": {
                "show": True,
                "fontSize": 16,
                "color": "#ffffff",
                "hPosition": "left",
                "vPosition": "top",
                "isBolder": True,
                "isItalic": False,
                "remarkShow": False,
                "fontFamily": "Microsoft YaHei",
            },
            "chartCommonStyle": deepcopy(COMMON_BG_SCREEN),
        },
    }


def base_view_config() -> dict:
    return {
        "id": "",
        "title": "图表",
        "sceneId": "0",
        "tableId": "",
        "type": "bar",
        "render": "antv",
        "resultCount": 1000,
        "resultMode": "custom",
        "refreshViewEnable": False,
        "refreshTime": 5,
        "refreshUnit": "minute",
        "chartType": "private",
        "dataFrom": "dataset",
        "xAxis": [],
        "xAxisExt": [],
        "yAxis": [],
        "yAxisExt": [],
        "extStack": [],
        "drillFields": [],
        "viewFields": [],
        "extBubble": [],
        "extLabel": [],
        "extTooltip": [],
        "customFilter": {},
        "sortPriority": [],
        "customAttr": {
            "basicStyle": {
                "alpha": 100,
                "colorScheme": "default",
                "colors": [
                    "#5470c6",
                    "#91cc75",
                    "#fac858",
                    "#ee6666",
                    "#73c0de",
                    "#3ba272",
                    "#fc8452",
                    "#9a60b4",
                    "#ea7ccc",
                ],
                "gradient": False,
                "columnWidthRatio": 60,
                "radius": 90,
                "innerRadius": 60,
            },
            "label": {"show": False, "position": "top", "fontSize": 12, "color": "#ffffff"},
            # 提示框默认白底黑字，勿用白色字（与背景冲突看不见）
            "tooltip": {
                "show": True,
                "trigger": "item",
                "confine": True,
                "fontSize": 12,
                "color": "#000000",
                "backgroundColor": "#ffffff",
                "showQuota": False,
                "seriesTooltipFormatter": [],
            },
            "misc": {},
            "tableTotal": {},
            "tableHeader": {},
            "tableCell": {},
            "indicator": {
                "show": True,
                "fontSize": 36,
                "color": "#ffffff",
                "fontFamily": "Microsoft YaHei",
                "isBolder": True,
            },
            "indicatorName": {
                "show": True,
                "fontSize": 16,
                "color": "#cccccc",
                "fontFamily": "Microsoft YaHei",
            },
            "map": {"id": "", "level": "world"},
        },
        "customStyle": {
            "text": {
                "show": True,
                "fontSize": 16,
                "color": "#ffffff",
                "hPosition": "left",
                "vPosition": "top",
                "isBolder": True,
                "isItalic": False,
                "remarkShow": False,
                "fontFamily": "Microsoft YaHei",
            },
            "legend": {
                "show": True,
                "hPosition": "center",
                "vPosition": "bottom",
                "orient": "horizontal",
                "icon": "circle",
                "color": "#ffffff",
                "fontSize": 12,
            },
            "xAxis": {"show": True, "position": "bottom", "color": "#ffffff", "fontSize": 12},
            "yAxis": {"show": True, "position": "left", "color": "#ffffff", "fontSize": 12},
            "yAxisExt": {"show": True, "position": "right"},
            "misc": {},
        },
        "senior": {
            "functionCfg": {
                "emptyDataStrategy": "ignoreData",
                "sliderShow": False,
                "emptyDataFieldCtrl": [],
            },
            "assistLineCfg": {"enable": False},
            "threshold": {"enable": False},
            "scrollCfg": {"open": False},
            "areaMapping": {},
            "useGlobalAreaMapping": False,
        },
        "flowMapStartName": [],
        "flowMapEndName": [],
    }


def rich_text_centered_html(
    text: str,
    *,
    font_size: int = 36,
    color: str = "#ffffff",
    bold: bool = True,
) -> str:
    """富文本在编辑器点「居中对齐」后写入 propValue.textValue 的典型 HTML。"""
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
    left: int,
    top: int,
    width: int,
    height: int,
) -> dict:
    meta = CHART_TYPES.get(chart_type, {"label": chart_type})
    return {
        "id": cid,
        "component": "UserView",
        "name": meta.get("label") or title,
        "label": meta.get("label") or title,
        "innerType": chart_type,
        # 必须与界面 findNewComponentFromList → getViewConfig(innerType).render 一致
        "render": chart_render(chart_type),
        "propValue": {"textValue": "", "urlList": []},
        "icon": chart_type,
        "editing": False,
        "canvasActive": False,
        "actionSelection": {"linkageActive": "custom"},
        "x": 1,
        "y": 1,
        "sizeX": 36,
        "sizeY": 14,
        "style": {
            "adaptation": "adaptation",
            "width": width,
            "height": height,
            "left": left,
            "top": top,
            "rotate": 0,
            "opacity": 1,
            "borderActive": False,
            "borderWidth": 1,
            "borderRadius": 5,
            "borderStyle": "solid",
            "borderColor": "#cccccc",
            "color": "#ffffff",
            "fontSize": 16,
            "fontWeight": 400,
        },
        "matrixStyle": {},
        "canvasId": "canvas-main",
        "category": "base",
        "isLock": False,
        "isShow": True,
        "events": {},
        "carousel": {"enable": False, "time": 10},
        "commonBackground": deepcopy(COMMON_BG_SCREEN),
        "state": "ready",
        "linkageFilters": [],
    }


def rich_text_title_component(
    *,
    cid: str,
    text: str,
    left: int,
    top: int,
    width: int,
    height: int,
    font_size: int = 36,
    color: str = "#ffffff",
) -> tuple[dict, dict]:
    """
    大标题用「富文本」组件（界面可配居中），而非滚动文字。
    返回 (componentData 项, canvasViewInfo 项)。
    """
    comp = user_view_component(
        cid=cid,
        chart_type="rich-text",
        title=text or "大标题",
        left=left,
        top=top,
        width=width,
        height=height,
    )
    comp["name"] = "富文本"
    comp["label"] = "富文本"
    comp["icon"] = "rich-text"
    comp["render"] = "custom"
    # 与界面 TinyMCE 保存一致：textValue + verticalAlign（工具栏居中/垂直居中）
    comp["propValue"] = {
        "textValue": rich_text_centered_html(text, font_size=font_size, color=color, bold=True),
        "verticalAlign": "center-align",
        "urlList": [],
    }
    comp["commonBackground"] = {
        **deepcopy(COMMON_BG_SCREEN),
        "backgroundColorSelect": False,
        "backgroundColor": "transparent",
        "innerImage": None,
    }
    view = base_view_config()
    view["id"] = cid
    view["type"] = "rich-text"
    view["render"] = "custom"
    view["title"] = text or "大标题"
    view["tableId"] = ""
    view["customStyle"]["text"]["show"] = False
    return comp, view


def decoration_component(
    *,
    cid: str,
    kind: str,
    left: int,
    top: int,
    width: int,
    height: int,
    prop_value: Any = None,
    style_extra: Optional[dict] = None,
    inner_type: Optional[str] = None,
) -> dict:
    meta = DECORATION_KINDS.get(kind) or {"component": kind, "label": kind}
    component = meta["component"]
    style = {
        "adaptation": "adaptation",
        "width": width,
        "height": height,
        "left": left,
        "top": top,
        "rotate": 0,
        "opacity": 1,
        "color": "#ffffff",
        "fontSize": 28,
        "fontWeight": 600,
        "backgroundColor": "rgba(64,158,255,0.35)",
        "borderActive": False,
        "borderWidth": 0,
        "borderRadius": 0,
        "borderStyle": "solid",
        "borderColor": "#cccccc",
    }
    if component == "ScrollText":
        style.update(
            {
                "textAlign": "center",
                "verticalAlign": "middle",
                "letterSpacing": 0,
                "padding": 4,
                "scrollSpeed": 0,
                "backgroundColor": "transparent",
            }
        )
    if style_extra:
        style.update(style_extra)
    pv = prop_value
    if pv is None:
        if component == "ScrollText":
            pv = "数据大屏"
        elif component == "Picture":
            pv = {"url": "", "urlList": []}
        else:
            pv = ""
    return {
        "id": cid,
        "component": component,
        "name": meta.get("label") or kind,
        "label": meta.get("label") or kind,
        "innerType": inner_type or component,
        "propValue": pv,
        "icon": component,
        "editing": False,
        "canvasActive": False,
        "actionSelection": {"linkageActive": "custom"},
        "x": 1,
        "y": 1,
        "sizeX": 10,
        "sizeY": 4,
        "style": style,
        "matrixStyle": {},
        "canvasId": "canvas-main",
        "category": "base",
        "isLock": False,
        "isShow": True,
        "events": {},
        "carousel": {"enable": False, "time": 10},
        "commonBackground": deepcopy(COMMON_BG_DECOR),
        "state": "ready",
        "linkageFilters": [],
    }
