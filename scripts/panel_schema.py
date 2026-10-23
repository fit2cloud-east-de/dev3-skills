"""数据大屏 / 仪表板的全局配置、图表配置、联动与跳转默认值注册表。

这里是唯一事实来源：`datav.py defaults`、`dashboard.py defaults` 与
`references/panel_defaults.md` 都由本文件生成，避免文档与代码各写一套而漂移。

三层配置回顾：
1. 面板级 —— `canvasStyleData`（JSON 字符串），整块面板的全局默认
2. 图表级 —— `canvasViewInfo[组件id]`，单个图表的样式与行为
3. 关系级 —— 联动 `linkage` / 跳转 `linkJump`，独立接口保存，不在画布 JSON 里
"""

from __future__ import annotations

from typing import Any, Optional

UI_OK = "ok"        # 界面可配
UI_WARN = "warn"    # 界面可配但易踩坑 / 需前置条件
UI_NONE = "none"    # 界面无入口（仅接口字段）

UI_MARK = {UI_OK: "✅", UI_WARN: "⚠️", UI_NONE: "⛔"}
UI_LABEL = {UI_OK: "界面可配", UI_WARN: "界面可配·注意", UI_NONE: "界面无入口"}

# 大屏 / 仪表板两条分支的默认值不同；相同值渲染时折叠为「同上」
SAME = "\x00same"
# 该面板没有这个字段
NONE = "\x01none"


def _f(
    key: str,
    label: str,
    typ: str,
    dv: Any,
    db: Optional[Any] = None,
    ui: str = UI_OK,
    where: str = "",
    note: str = "",
) -> dict:
    return {
        "key": key,
        "label": label,
        "type": typ,
        "dv": dv,
        "db": dv if db is None else db,
        "ui": ui,
        "where": where,
        "note": note,
    }


# ---------------------------------------------------------------- 面板级全局
CANVAS_SCHEMA: list[dict] = [
    # —— 尺寸与适配
    _f("width", "画布宽度", "int", 1920, SAME, UI_OK, "画布右键/页面设置 · 尺寸"),
    _f("height", "画布高度", "int", 1080, SAME, UI_OK, "画布右键/页面设置 · 尺寸"),
    _f(
        "screenAdaptor",
        "屏幕适配方式",
        "enum",
        "widthFirst",
        SAME,
        UI_OK,
        "页面设置 · 屏幕适配",
        "widthFirst=宽度优先（默认）/ heightFirst=高度优先 / full=铺满全屏 / keepSize=不缩放",
    ),
    _f(
        "dashboardAdaptor",
        "预览适配方式",
        "enum",
        "keepHeightAndWidth",
        SAME,
        UI_OK,
        "页面设置 · 预览适配",
        "keepHeightAndWidth=高度宽度独立缩放（默认）/ withWidth=跟随宽度",
    ),
    _f("scale", "编辑缩放百分比", "int", 100, 60, UI_OK, "底部缩放条", "大屏按实际尺寸保存，仅外层 transform 缩放"),
    _f("scaleWidth", "编辑缩放-宽", "int", 100, 60, UI_NONE),
    _f("scaleHeight", "编辑缩放-高", "int", 100, 60, UI_NONE),
    _f("tScale", "transform 缩放（宽高同值）", "float", 1, 0.6, UI_NONE),
    _f("tScaleWidth", "transform 缩放-宽", "float", 1, 0.6, UI_NONE),
    _f("tScaleHeight", "transform 缩放-高", "float", 1, 0.6, UI_NONE),
    _f("dataVActualSizeVersion", "大屏实际尺寸模型版本", "int", 1, NONE, UI_NONE, "", "大屏固定 1"),
    _f("dvType", "面板类型", "enum", "dataV", "dashboard", UI_NONE, "", "dataV / dashboard，决定渲染分支"),
    _f("enableSvgRenderer", "使用 SVG 渲染器", "bool", False, SAME, UI_WARN, "页面设置 · 渲染", "默认 Canvas 渲染；SVG 下部分滤镜/图片效果不同"),
    # —— 定时刷新
    _f("refreshBrowserEnable", "定时刷新-整页", "bool", False, SAME, UI_OK, "页面设置 · 定时刷新"),
    _f("refreshBrowserTime", "整页刷新间隔", "int", 5, SAME, UI_OK, "页面设置 · 定时刷新"),
    _f(
        "refreshBrowserUnit",
        "整页刷新单位",
        "enum",
        "minute",
        SAME,
        UI_OK,
        "页面设置 · 定时刷新",
        "second / minute / hour",
    ),
    _f("refreshViewEnable", "定时刷新-图表", "bool", False, SAME, UI_OK, "页面设置 · 定时刷新"),
    _f("refreshTime", "图表刷新间隔", "int", 5, SAME, UI_OK, "页面设置 · 定时刷新"),
    _f("refreshUnit", "图表刷新单位", "enum", "minute", SAME, UI_OK, "页面设置 · 定时刷新", "second / minute / hour"),
    _f("refreshViewLoading", "刷新时显示 loading", "bool", True, SAME, UI_OK, "页面设置 · 定时刷新"),
    # —— 边框栏按钮
    _f("popupAvailable", "允许弹窗区域", "bool", True, SAME, UI_OK, "页面设置 · 工具栏"),
    _f("popupButtonAvailable", "弹窗内显示按钮", "bool", True, SAME, UI_OK, "页面设置 · 工具栏"),
    _f("suspensionButtonAvailable", "显示悬浮按钮", "bool", False, SAME, UI_OK, "页面设置 · 工具栏"),
    _f("suspensionViewButtonAvailable", "图表悬浮按钮可用", "bool", True, SAME, UI_OK, "页面设置 · 工具栏"),
    # —— 底色 / 底图
    _f("backgroundColorSelect", "启用自定义底色", "bool", True, SAME, UI_OK, "页面设置 · 背景"),
    _f("backgroundColor", "画布底色", "color", "#020408", "#f5f6f7", UI_OK, "页面设置 · 背景"),
    _f(
        "backgroundImageEnable",
        "启用背景图",
        "bool",
        False,
        SAME,
        UI_OK,
        "页面设置 · 背景",
        "与 background 成对使用",
    ),
    _f("background", "背景图地址", "url", "", SAME, UI_OK, "页面设置 · 背景", "支持外链与产品内上传路径"),
    _f("backgroundType", "背景类型（历史字段）", "enum", "backgroundColor", SAME, UI_NONE, "", "已废弃，勿依赖"),
    _f("opacity", "整页透明度（历史字段）", "float", 1, SAME, UI_NONE, "", "已废弃，勿依赖"),
    _f("color", "全局文字色", "color", "#fff", "#000000", UI_OK, "页面设置 · 字体"),
    _f("fontSize", "全局字号", "int", 14, SAME, UI_OK, "页面设置 · 字体"),
    _f("fontFamily", "全局字体", "string", "PingFang", SAME, UI_OK, "页面设置 · 字体"),
    _f("themeId", "主题 ID", "string", "10002", "10001", UI_NONE, "", "10002=暗色（大屏）/ 10001=亮色（仪表板）"),
    _f("dialogBackgroundColor", "弹窗底色", "color", "#fff", SAME, UI_OK, "页面设置 · 弹窗"),
    _f("dialogButton", "弹窗按钮色", "color", "#020408", SAME, UI_OK, "页面设置 · 弹窗"),
    # —— 栅格 / 结果集
    _f("dashboard.gap", "启用组件间隙", "enum", "yes", SAME, UI_OK, "页面设置 · 栅格", "yes / no"),
    _f("dashboard.gapSize", "组件间隙像素", "int", 5, SAME, UI_OK, "页面设置 · 栅格"),
    _f(
        "dashboard.gapMode",
        "间隙归属",
        "enum",
        "middle",
        SAME,
        UI_OK,
        "页面设置 · 栅格",
        "middle=组件之间（默认）/ outer=外侧 / inner=内侧",
    ),
    _f("dashboard.showGrid", "编辑时显示网格", "bool", False, SAME, UI_OK, "页面设置 · 栅格", "仅编辑器可见"),
    _f("dashboard.matrixBase", "矩阵基数", "int", 4, SAME, UI_NONE, "", "当前矩阵 = 72×36 的 1/4 进制步长"),
    _f(
        "dashboard.resultMode",
        "面板结果集模式",
        "enum",
        "all",
        SAME,
        UI_OK,
        "页面设置 · 数据",
        "all=全部 / custom=自定义条数",
    ),
    _f("dashboard.resultCount", "面板结果集条数", "int", 1000, SAME, UI_OK, "页面设置 · 数据"),
    _f("dashboard.themeColor", "面板明暗主题", "enum", "dark", "light", UI_OK, "页面设置 · 主题", "dark / light"),
    _f("dashboard.mobileSetting.customSetting", "移动端独立配置", "bool", False, SAME, UI_OK, "页面设置 · 移动端"),
    _f(
        "dashboard.mobileSetting.backgroundType",
        "移动端背景类型",
        "enum",
        "image",
        SAME,
        UI_OK,
        "页面设置 · 移动端",
        "image / color",
    ),
    _f("dashboard.mobileSetting.imageUrl", "移动端背景图", "url", None, SAME, UI_OK, "页面设置 · 移动端"),
    _f("dashboard.mobileSetting.color", "移动端背景色", "color", "#fff", "#000", UI_OK, "页面设置 · 移动端"),
    # —— 组件统一风格（面板级默认，作用于所有组件）
    _f("component.chartTitle.show", "统一显示组件标题", "bool", True, SAME, UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.fontSize", "统一标题字号", "int", 16, SAME, UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.color", "统一标题颜色", "color", "#ffffff", "#000000", UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.hPosition", "统一标题水平位置", "enum", "left", SAME, UI_OK, "主题 · 组件标题", "left / center / right"),
    _f("component.chartTitle.vPosition", "统一标题垂直位置", "enum", "top", SAME, UI_OK, "主题 · 组件标题", "top / middle / bottom"),
    _f("component.chartTitle.isBolder", "统一标题加粗", "bool", True, SAME, UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.isItalic", "统一标题斜体", "bool", False, SAME, UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.remarkShow", "统一显示标题备注", "bool", False, SAME, UI_OK, "主题 · 组件标题"),
    _f("component.chartTitle.fontFamily", "统一标题字体", "string", "Microsoft YaHei", SAME, UI_OK, "主题 · 组件标题"),
    _f(
        "component.chartTitle.remarkBackgroundColor",
        "标题备注底色",
        "color",
        "#5A5C62",
        "#ffffff",
        UI_OK,
        "主题 · 组件标题",
    ),
    _f("component.chartCommonStyle.backgroundColorSelect", "统一组件底色开关", "bool", False, SAME, UI_OK, "主题 · 组件背景"),
    _f("component.chartCommonStyle.backgroundColor", "统一组件底色", "color", "#131E42", "rgba(255,255,255,1)", UI_OK, "主题 · 组件背景"),
    _f(
        "component.chartCommonStyle.backgroundImageEnable",
        "统一组件背景图开关",
        "bool",
        False,
        SAME,
        UI_OK,
        "主题 · 组件背景",
    ),
    _f(
        "component.chartCommonStyle.backgroundType",
        "统一组件背景类型",
        "enum",
        "innerImage",
        SAME,
        UI_OK,
        "主题 · 组件背景",
        "innerImage=产品内置边框（board/board_N.svg）/ outerImage=自定义图片",
    ),
    _f("component.chartCommonStyle.innerImage", "内置边框素材", "string", "board/board_1.svg", SAME, UI_OK, "主题 · 组件背景"),
    _f("component.chartCommonStyle.outerImage", "自定义边框图", "url", None, SAME, UI_OK, "主题 · 组件背景"),
    _f("component.chartCommonStyle.innerImageColor", "边框着色", "color", "#1094E5", "rgba(16, 148, 229,1)", UI_OK, "主题 · 组件背景"),
    _f(
        "component.chartCommonStyle.innerPadding",
        "统一内边距",
        "object",
        '{"mode": "uniform", "top": 12}',
        SAME,
        UI_OK,
        "主题 · 组件背景",
        "mode: uniform（四边同值）/ single（分边）",
    ),
    _f(
        "component.chartCommonStyle.borderRadius",
        "统一圆角",
        "object",
        '{"mode": "uniform", "topLeft": 0}',
        SAME,
        UI_OK,
        "主题 · 组件背景",
    ),
    _f("component.chartCommonStyle.backdropFilterEnable", "启用毛玻璃", "bool", False, SAME, UI_OK, "主题 · 组件背景"),
    _f("component.chartCommonStyle.backdropFilter", "毛玻璃半径", "int", 4, SAME, UI_OK, "主题 · 组件背景"),
    _f("component.chartColor.basicStyle.colorScheme", "统一配色方案", "enum", "default", SAME, UI_WARN, "主题 · 配色", "大屏默认走图表自身 colors，仪表板走面板统一配色"),
    _f(
        "component.chartColor.basicStyle.colors",
        "统一配色序列",
        "array",
        '["#1E90FF","#90EE90","#00CED1","#E2BD84","#7A90E0","#3BA272","#2BE7FF","#0A8ADA","#FFD700"]',
        SAME,
        UI_WARN,
        "主题 · 配色",
        "仪表板才有；大屏请在图表 extraView.customAttr.basicStyle.colors 单独设",
    ),
    _f("component.filterStyle.layout", "查询组件排列", "enum", "horizontal", SAME, UI_OK, "主题 · 查询组件", "horizontal / vertical"),
    _f("component.filterStyle.titleLayout", "查询组件标题位置", "enum", "left", SAME, UI_OK, "主题 · 查询组件", "left / top"),
    _f("component.filterStyle.labelColor", "查询组件标签色", "color", "#ffffff", "#1f2329", UI_OK, "主题 · 查询组件"),
    _f("component.filterStyle.borderColor", "查询组件边框色", "color", "#505050", "#D9DCDF", UI_OK, "主题 · 查询组件"),
    _f("component.filterStyle.bgColor", "查询组件背景色", "color", "#131C42", "#FFFFFF", UI_OK, "主题 · 查询组件"),
    _f("component.tabStyle.headPosition", "Tab 页签位置", "enum", "left", SAME, UI_OK, "主题 · Tab", "left / top / right / bottom"),
    _f("component.seniorStyleSetting.linkageIconColor", "联动角标颜色", "color", "#ffffff", "#a6a6a6", UI_OK, "主题 · 高级"),
    _f("component.seniorStyleSetting.drillLayerColor", "钻取层级文字色", "color", "#ffffff", "#a6a6a6", UI_OK, "主题 · 高级"),
    _f("component.seniorStyleSetting.pagerColor", "翻页器颜色", "color", "#ffffff", "#a6a6a6", UI_OK, "主题 · 高级"),
    _f("component.seniorStyleSetting.pagerSize", "翻页器字号", "int", 14, SAME, UI_OK, "主题 · 高级"),
]

# ---------------------------------------------------------------- 单个图表
CHART_SCHEMA: list[dict] = [
    # —— 数据
    _f("resultCount", "结果集条数", "int", 1000, SAME, UI_OK, "图表 · 数据"),
    _f("resultMode", "结果集模式", "enum", "custom", SAME, UI_WARN, "图表 · 数据", "图表级默认 custom；跟随面板时与 canvasStyleData.dashboard.resultMode 一致"),
    _f("refreshViewEnable", "该图表定时刷新", "bool", False, SAME, UI_OK, "图表 · 数据"),
    _f("refreshTime", "刷新间隔", "int", 5, SAME, UI_OK, "图表 · 数据"),
    _f("refreshUnit", "刷新单位", "enum", "minute", SAME, UI_OK, "图表 · 数据", "second / minute / hour"),
    _f("customFilter", "图表内过滤", "object", "{}", SAME, UI_OK, "图表 · 过滤", "FilterTree：{logic, items:[{type,fieldId,term,value}]}"),
    _f("linkageActive", "启用联动（运行时开关）", "bool", False, SAME, UI_OK, "图表 · 高级 · 联动"),
    _f("jumpActive", "启用跳转（运行时开关）", "bool", False, SAME, UI_OK, "图表 · 高级 · 跳转"),
    # —— 配色
    _f("customAttr.basicStyle.colorScheme", "配色方案", "enum", "default", SAME, UI_OK, "图表 · 样式 · 配色", "default / elegant / future / gradual …"),
    _f(
        "customAttr.basicStyle.colors",
        "配色序列",
        "array",
        '["#5470c6","#91cc75","#fac858","#ee6666","#73c0de","#3ba272","#fc8452","#9a60b4","#ea7ccc"]',
        SAME,
        UI_OK,
        "图表 · 样式 · 配色",
    ),
    _f("customAttr.basicStyle.alpha", "色彩透明度", "int", 100, SAME, UI_OK, "图表 · 样式 · 配色", "0–100"),
    _f("customAttr.basicStyle.gradient", "柱条/面积渐变", "bool", False, SAME, UI_OK, "图表 · 样式 · 配色"),
    _f("customAttr.basicStyle.columnWidthRatio", "柱宽占比", "int", 60, SAME, UI_OK, "图表 · 样式 · 配色"),
    _f("customAttr.basicStyle.radius", "饼图半径", "int", 90, SAME, UI_OK, "图表 · 样式 · 配色"),
    _f("customAttr.basicStyle.innerRadius", "环形内半径", "int", 60, SAME, UI_OK, "图表 · 样式 · 配色"),
    _f("customAttr.basicStyle.mapStyle", "地图底图风格", "enum", "darkblue", "normal", UI_OK, "图表 · 样式 · 地图", "normal / darkblue / …"),
    # —— 标签
    _f("customAttr.label.show", "显示标签", "bool", False, SAME, UI_WARN, "图表 · 样式 · 标签", "饼图/矩形树图在创建时会被打开"),
    _f("customAttr.label.position", "标签位置", "enum", "top", SAME, UI_OK, "图表 · 样式 · 标签", "top / bottom / left / right / inside / outside / center"),
    _f("customAttr.label.fontSize", "标签字号", "int", 12, SAME, UI_OK, "图表 · 样式 · 标签"),
    _f("customAttr.label.color", "标签颜色", "color", "#ffffff", "#333333", UI_OK, "图表 · 样式 · 标签"),
    _f("customAttr.label.showDimension", "标签含维度名", "bool", True, SAME, UI_OK, "图表 · 样式 · 标签"),
    _f("customAttr.label.showQuota", "标签含指标值", "bool", False, SAME, UI_OK, "图表 · 样式 · 标签"),
    _f("customAttr.label.showProportion", "标签含占比", "bool", True, SAME, UI_OK, "图表 · 样式 · 标签"),
    _f("customAttr.label.reserveDecimalCount", "标签保留小数位", "int", 2, SAME, UI_OK, "图表 · 样式 · 标签"),
    # —— 提示框
    _f("customAttr.tooltip.show", "显示提示框", "bool", True, SAME, UI_OK, "图表 · 样式 · 提示"),
    _f("customAttr.tooltip.trigger", "触发方式", "enum", "item", SAME, UI_OK, "图表 · 样式 · 提示", "item=数据项 / axis=坐标轴"),
    _f("customAttr.tooltip.confine", "限制在图形内", "bool", True, SAME, UI_OK, "图表 · 样式 · 提示"),
    _f("customAttr.tooltip.fontSize", "提示字号", "int", 12, SAME, UI_OK, "图表 · 样式 · 提示"),
    _f("customAttr.tooltip.color", "提示文字色", "color", "#000000", SAME, UI_WARN, "图表 · 样式 · 提示", "默认白底黑字，大屏上勿改成白色"),
    _f("customAttr.tooltip.backgroundColor", "提示底色", "color", "#ffffff", "#5A5C62", UI_OK, "图表 · 样式 · 提示"),
    _f("customAttr.tooltip.showQuota", "提示含指标", "bool", False, SAME, UI_OK, "图表 · 样式 · 提示"),
    # —— 指标卡
    _f("customAttr.indicator.show", "显示指标值", "bool", True, SAME, UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicator.fontSize", "指标值字号", "int", 36, SAME, UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicator.color", "指标值颜色", "color", "#ffffff", "#0C296E", UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicator.isBolder", "指标值加粗", "bool", True, SAME, UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicatorName.show", "显示指标名", "bool", True, SAME, UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicatorName.fontSize", "指标名字号", "int", 16, SAME, UI_OK, "图表 · 样式 · 指标卡"),
    _f("customAttr.indicatorName.color", "指标名颜色", "color", "#cccccc", "#646A73", UI_OK, "图表 · 样式 · 指标卡"),
    # —— 表格
    _f("customAttr.tableHeader.tableHeaderBgColor", "表头底色", "color", "#1E90FF", SAME, UI_OK, "图表 · 样式 · 表格"),
    _f("customAttr.tableHeader.tableHeaderFontColor", "表头文字色", "color", "#FFFFFF", SAME, UI_OK, "图表 · 样式 · 表格"),
    _f("customAttr.tableCell.tableItemBgColor", "单元格底色", "color", "#131E42", "#FFFFFF", UI_OK, "图表 · 样式 · 表格"),
    _f("customAttr.tableCell.tableFontColor", "单元格文字色", "color", "#ffffff", "#000000", UI_OK, "图表 · 样式 · 表格"),
    _f("customAttr.tableCell.tableItemSubBgColor", "斑马纹底色", "color", "#1E90FF", SAME, UI_OK, "图表 · 样式 · 表格"),
    _f("customAttr.tableTotal", "合计行样式", "object", "{}", SAME, UI_OK, "图表 · 样式 · 表格"),
    # —— 标题
    _f("customStyle.text.show", "显示图表标题", "bool", True, SAME, UI_OK, "图表 · 样式 · 标题"),
    _f("customStyle.text.fontSize", "标题字号", "int", 16, SAME, UI_OK, "图表 · 样式 · 标题"),
    _f("customStyle.text.color", "标题颜色", "color", "#ffffff", "#000000", UI_OK, "图表 · 样式 · 标题"),
    _f("customStyle.text.hPosition", "标题水平位置", "enum", "left", SAME, UI_OK, "图表 · 样式 · 标题", "left / center / right"),
    _f("customStyle.text.vPosition", "标题垂直位置", "enum", "top", SAME, UI_OK, "图表 · 样式 · 标题", "top / middle / bottom"),
    _f("customStyle.text.isBolder", "标题加粗", "bool", True, SAME, UI_OK, "图表 · 样式 · 标题"),
    _f("customStyle.text.isItalic", "标题斜体", "bool", False, SAME, UI_OK, "图表 · 样式 · 标题"),
    _f("customStyle.text.fontFamily", "标题字体", "string", "Microsoft YaHei", SAME, UI_OK, "图表 · 样式 · 标题"),
    # —— 图例
    _f("customStyle.legend.show", "显示图例", "bool", True, SAME, UI_OK, "图表 · 样式 · 图例"),
    _f("customStyle.legend.hPosition", "图例水平位置", "enum", "center", SAME, UI_OK, "图表 · 样式 · 图例", "left / center / right"),
    _f("customStyle.legend.vPosition", "图例垂直位置", "enum", "bottom", SAME, UI_OK, "图表 · 样式 · 图例", "top / middle / bottom"),
    _f("customStyle.legend.orient", "图例排列方向", "enum", "horizontal", SAME, UI_OK, "图表 · 样式 · 图例", "horizontal / vertical"),
    _f("customStyle.legend.icon", "图例图标", "enum", "circle", SAME, UI_OK, "图表 · 样式 · 图例", "circle / rect / roundRect / triangle / diamond"),
    _f("customStyle.legend.color", "图例文字色", "color", "#ffffff", "#333333", UI_OK, "图表 · 样式 · 图例"),
    _f("customStyle.legend.fontSize", "图例字号", "int", 12, SAME, UI_OK, "图表 · 样式 · 图例"),
    # —— 坐标轴
    _f("customStyle.xAxis.show", "显示 X 轴", "bool", True, SAME, UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.xAxis.position", "X 轴位置", "enum", "bottom", SAME, UI_OK, "图表 · 样式 · 轴", "bottom / top"),
    _f("customStyle.xAxis.color", "X 轴文字色", "color", "#ffffff", "#333333", UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.xAxis.fontSize", "X 轴字号", "int", 12, SAME, UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.yAxis.show", "显示 Y 轴", "bool", True, SAME, UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.yAxis.position", "Y 轴位置", "enum", "left", SAME, UI_OK, "图表 · 样式 · 轴", "left / right"),
    _f("customStyle.yAxis.color", "Y 轴文字色", "color", "#ffffff", "#333333", UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.yAxis.fontSize", "Y 轴字号", "int", 12, SAME, UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.yAxisExt.show", "显示副轴", "bool", True, SAME, UI_OK, "图表 · 样式 · 轴"),
    _f("customStyle.yAxisExt.position", "副轴位置", "enum", "right", SAME, UI_OK, "图表 · 样式 · 轴", "right / left"),
    # —— 高级
    _f(
        "senior.functionCfg.emptyDataStrategy",
        "空值处理策略",
        "enum",
        "ignoreData",
        SAME,
        UI_OK,
        "图表 · 高级 · 空值",
        "ignoreData=忽略空值（默认）/ breakLine=折线断点",
    ),
    _f("senior.functionCfg.sliderShow", "开启缩放滑块", "bool", False, SAME, UI_OK, "图表 · 高级 · 缩放"),
    _f("senior.assistLineCfg.enable", "辅助线", "bool", False, SAME, UI_OK, "图表 · 高级 · 辅助线"),
    _f("senior.threshold.enable", "阈值告警", "bool", False, SAME, UI_WARN, "图表 · 高级 · 阈值", "阈值在发布时统一处理，未发布不生效"),
    _f("senior.scrollCfg.open", "自动滚动", "bool", False, SAME, UI_OK, "图表 · 高级 · 滚动"),
    _f("senior.useGlobalAreaMapping", "沿用面板级区域映射", "bool", False, SAME, UI_OK, "图表 · 高级 · 地图"),
    _f("drillFields", "钻取字段", "array", "[]", SAME, UI_OK, "图表 · 钻取"),
    _f("xAxisExt", "副维度", "array", "[]", SAME, UI_OK, "图表 · 数据", "分组柱/分组折线用"),
    _f("extStack", "堆叠维度", "array", "[]", SAME, UI_OK, "图表 · 数据", "堆叠图用"),
]

# ---------------------------------------------------------------- 联动
LINKAGE_SCHEMA: list[dict] = [
    _f(
        "linkage[].source",
        "源图表",
        "string",
        "（必填）",
        SAME,
        UI_OK,
        "图表 · 高级 · 联动设置",
        "写图表标题或组件 id；解析不到会报错并列出候选",
    ),
    _f(
        "linkage[].targets",
        "联动目标图表",
        "array",
        "（必填）",
        SAME,
        UI_OK,
        "图表 · 高级 · 联动设置",
        "目标图表标题或 id 列表；源图表自身会被自动跳过",
    ),
    _f(
        "linkage[].fields",
        "关联字段映射",
        "array",
        '[{"source": "字段A", "target": "字段A"}]',
        SAME,
        UI_OK,
        "图表 · 高级 · 联动设置 · 关联字段",
        "省略则按同名字段自动配对；同数据集字段 id 天然一致，跨数据集按名称匹配",
    ),
    _f(
        "linkage[].active",
        "该目标启用联动",
        "bool",
        True,
        SAME,
        UI_OK,
        "图表 · 高级 · 联动设置 · 目标前勾选",
        "为 false 时保存后不写入关联字段（后端只在 active 时落库）",
    ),
    _f(
        "linkageActive",
        "源图表联动总开关",
        "bool",
        True,
        SAME,
        UI_OK,
        "图表 · 高级 · 联动",
        "运行时还会校验：源图表 linkage_active=true 且存在启用中的联动关系，缺一不生效",
    ),
    _f(
        "actionSelection.linkageActive",
        "点击行为",
        "enum",
        "custom",
        SAME,
        UI_OK,
        "画布 · 联动设置（悬浮工具条）",
        "custom=弹出浮框由用户选择联动或下钻（默认）/ auto=同时触发联动和下钻",
    ),
]


# ---------------------------------------------------------------- 跳转
JUMP_SCHEMA: list[dict] = [
    _f(
        "jump[].source",
        "源图表",
        "string",
        "（必填）",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置",
        "写图表标题或组件 id",
    ),
    _f(
        "jump[].field",
        "触发字段",
        "string",
        "（必填）",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 选择字段",
        "必须是该图表已使用的字段（xAxis/xAxisExt/extStack/yAxis）；否则界面里不会出现该字段",
    ),
    _f(
        "jump[].linkType",
        "跳转类型",
        "enum",
        "outer",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 跳转类型",
        "outer=外部链接 / inner=仪表板·数据大屏",
    ),
    _f(
        "jump[].jumpType",
        "打开方式",
        "enum",
        "_blank",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 打开方式",
        "_self=当前页面 / _blank=新开页面（默认）/ newPop=弹窗页面",
    ),
    _f(
        "jump[].windowSize",
        "弹窗大小",
        "enum",
        "middle",
        SAME,
        UI_WARN,
        "图表 · 高级 · 跳转设置 · 窗口大小",
        "large=大 / middle=中 / small=小；仅 jumpType=newPop 时生效",
    ),
    _f(
        "jump[].content",
        "外部链接内容",
        "string",
        "http://",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 链接内容",
        "linkType=outer 必填，≤4000 字符。字段占位写成 [字段名]，保存时会转成 [字段id]，点击时替换为实际值",
    ),
    _f(
        "jump[].attachParams",
        "附加点击参数",
        "bool",
        False,
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置",
        "把当前图表过滤条件作为外部参数带给目标（仅内部跳转）",
    ),
    _f(
        "jump[].targetDvId",
        "目标仪表板/大屏 ID",
        "string",
        "",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 选择仪表板/数据大屏",
        "linkType=inner 必填",
    ),
    _f(
        "jump[].checked",
        "该字段启用跳转",
        "bool",
        True,
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 字段前勾选",
    ),
    _f(
        "jump[].targets",
        "跳转目标映射",
        "array",
        "[]",
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转设置 · 关联图表",
        "linkType=inner 时每项写 {view, type, fields}；type: view=图表 / filter=过滤组件 / outParams=外部参数",
    ),
    _f(
        "jumpActive",
        "源图表跳转总开关",
        "bool",
        True,
        SAME,
        UI_OK,
        "图表 · 高级 · 跳转",
        "运行时还会校验字段级 checked=true，缺一不生效",
    ),
]

GROUPS: list[tuple[str, str, list[dict]]] = [
    ("canvas", "面板级全局配置（canvasStyleData）", CANVAS_SCHEMA),
    ("chart", "单个图表配置（canvasViewInfo[组件id]）", CHART_SCHEMA),
    ("linkage", "图表联动（/linkage/*）", LINKAGE_SCHEMA),
    ("jump", "图表跳转（/linkJump/*）", JUMP_SCHEMA),
]

_ALL = {g[0]: g for g in GROUPS}


def find_group(name: str) -> Optional[tuple[str, str, list[dict]]]:
    alias = {
        "global": "canvas",
        "canvas": "canvas",
        "panel": "canvas",
        "view": "chart",
        "chart": "chart",
        "linkage": "linkage",
        "jump": "jump",
        "linkjump": "jump",
    }.get((name or "").strip().lower())
    return _ALL.get(alias) if alias else None


def iter_entries() -> list[dict]:
    out = []
    for gid, gname, items in GROUPS:
        for it in items:
            out.append({"group": gid, "groupName": gname, **it})
    return out


def lookup(key: str) -> Optional[dict]:
    k = (key or "").strip()
    if not k:
        return None
    for it in iter_entries():
        if it["key"] == k:
            return it
    low = k.lower()
    for it in iter_entries():
        if it["key"].lower() == low or it["label"] == k:
            return it
    # 允许省略容器前缀：label.show → customAttr.label.show
    tail = [it for it in iter_entries() if it["key"].lower().endswith("." + low)]
    if len(tail) == 1:
        return tail[0]
    return None


def normalize_defaults(entry: dict) -> dict:
    """把内部哨兵值还原成可读值。"""
    out = dict(entry)
    db = out.get("db")
    if isinstance(db, str) and db == SAME:
        out["db"] = out.get("dv")
    elif isinstance(db, str) and db == NONE:
        out["db"] = None
    return out


def suggest(key: str, limit: int = 5) -> list[str]:
    """给错误 key 找近似项，避免用户盲猜。"""
    import difflib

    keys = [it["key"] for it in iter_entries()]
    return difflib.get_close_matches(key or "", keys, n=limit, cutoff=0.3)


def set_path(target: dict, dotted: str, value: Any) -> None:
    """按 a.b.c 写入嵌套字典，缺层自动补。"""
    parts = [p for p in str(dotted).split(".") if p]
    if not parts:
        return
    node = target
    for p in parts[:-1]:
        nxt = node.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            node[p] = nxt
        node = nxt
    node[parts[-1]] = value


def get_path(target: dict, dotted: str, default: Any = None) -> Any:
    node: Any = target
    for p in str(dotted).split("."):
        if not isinstance(node, dict) or p not in node:
            return default
        node = node[p]
    return node


# ---------------------------------------------------------------- markdown 渲染


def _cell(value: Any) -> str:
    from html import escape

    if value is None:
        return "—"
    text = value if isinstance(value, str) else str(value)
    if text == "":
        return "`（空）`"
    # 代码块内不需要转义引号，只需处理会破坏表格的竖线
    return ("`" + escape(text, quote=False) + "`").replace("|", "\\|")


def render_markdown(group: str, *, title: str = "") -> str:
    g = find_group(group)
    if not g:
        raise ValueError(f"未知分组: {group}")
    gid, gname, items = g
    head = [
        f"## {title or gname}",
        "",
        "由 `python datav.py defaults --group "
        f"{gid} --markdown`（或 `python dashboard.py defaults`）生成，请勿手改。",
        "",
        "| 配置项 | 含义 | 类型 | 数据大屏默认 | 仪表板默认 | 界面可达性 | 界面位置 | 说明 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    rows = []
    for it in items:
        dv = it["dv"]
        db = it["db"]
        if db is NONE:
            db_cell = "—"
        elif db is SAME or db == dv:
            db_cell = "同上"
        else:
            db_cell = _cell(db)
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(it["key"]),
                    it["label"],
                    it["type"],
                    _cell(dv),
                    db_cell,
                    UI_MARK[it["ui"]] + " " + UI_LABEL[it["ui"]],
                    it["where"] or "—",
                    (it["note"] or "").replace("|", "\\|") or "—",
                ]
            )
            + " |"
        )
    return "\n".join(head + rows) + "\n"


def render_full_markdown() -> str:
    parts = [
        "# 数据大屏 / 仪表板 默认配置总表",
        "",
        "> 由 `python datav.py defaults --markdown --all` 生成，请勿手改。",
        "> 单独查一项：`python datav.py defaults --key customAttr.label.show`。",
        "",
        "**可达性图例**：✅ 界面可配 ｜ ⚠️ 界面可配但有前置条件或易踩坑 ｜ ⛔ 界面无入口（仅接口字段）",
        "",
    ]
    for gid, gname, _items in GROUPS:
        parts.append(render_markdown(gid, title=gname))
        parts.append("")
    return "\n".join(parts)


def render_json(group: str) -> dict:
    g = find_group(group)
    if not g:
        raise ValueError(f"未知分组: {group}")
    gid, gname, items = g
    return {"group": gid, "name": gname, "items": [normalize_defaults(x) for x in items]}


def render_entry_json(entry: dict) -> dict:
    return {
        **normalize_defaults(entry),
        "uiLabel": UI_LABEL[entry["ui"]],
        "uiMark": UI_MARK[entry["ui"]],
    }


__all__ = [
    "UI_OK",
    "UI_WARN",
    "UI_NONE",
    "SAME",
    "CANVAS_SCHEMA",
    "CHART_SCHEMA",
    "LINKAGE_SCHEMA",
    "JUMP_SCHEMA",
    "GROUPS",
    "find_group",
    "iter_entries",
    "lookup",
    "normalize_defaults",
    "suggest",
    "set_path",
    "get_path",
    "render_markdown",
    "render_full_markdown",
    "render_json",
    "render_entry_json",
]
