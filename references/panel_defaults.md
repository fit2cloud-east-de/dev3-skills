# 数据大屏 / 仪表板 默认配置总表

> 由 `python datav.py defaults --markdown --all` 生成，请勿手改。
> 单独查一项：`python datav.py defaults --key customAttr.label.show`。

**可达性图例**：✅ 界面可配 ｜ ⚠️ 界面可配但有前置条件或易踩坑 ｜ ⛔ 界面无入口（仅接口字段）

## 面板级全局配置（canvasStyleData）

由 `python datav.py defaults --group canvas --markdown`（或 `python dashboard.py defaults`）生成，请勿手改。

| 配置项 | 含义 | 类型 | 数据大屏默认 | 仪表板默认 | 界面可达性 | 界面位置 | 说明 |
|---|---|---|---|---|---|---|---|
| `width` | 画布宽度 | int | `1920` | 同上 | ✅ 界面可配 | 画布右键/页面设置 · 尺寸 | — |
| `height` | 画布高度 | int | `1080` | 同上 | ✅ 界面可配 | 画布右键/页面设置 · 尺寸 | — |
| `screenAdaptor` | 屏幕适配方式 | enum | `widthFirst` | 同上 | ✅ 界面可配 | 页面设置 · 屏幕适配 | widthFirst=宽度优先（默认）/ heightFirst=高度优先 / full=铺满全屏 / keepSize=不缩放 |
| `dashboardAdaptor` | 预览适配方式 | enum | `keepHeightAndWidth` | 同上 | ✅ 界面可配 | 页面设置 · 预览适配 | keepHeightAndWidth=高度宽度独立缩放（默认）/ withWidth=跟随宽度 |
| `scale` | 编辑缩放百分比 | int | `100` | `60` | ✅ 界面可配 | 底部缩放条 | 大屏按实际尺寸保存，仅外层 transform 缩放 |
| `scaleWidth` | 编辑缩放-宽 | int | `100` | `60` | ⛔ 界面无入口 | — | — |
| `scaleHeight` | 编辑缩放-高 | int | `100` | `60` | ⛔ 界面无入口 | — | — |
| `tScale` | transform 缩放（宽高同值） | float | `1` | `0.6` | ⛔ 界面无入口 | — | — |
| `tScaleWidth` | transform 缩放-宽 | float | `1` | `0.6` | ⛔ 界面无入口 | — | — |
| `tScaleHeight` | transform 缩放-高 | float | `1` | `0.6` | ⛔ 界面无入口 | — | — |
| `dataVActualSizeVersion` | 大屏实际尺寸模型版本 | int | `1` | — | ⛔ 界面无入口 | — | 大屏固定 1 |
| `dvType` | 面板类型 | enum | `dataV` | `dashboard` | ⛔ 界面无入口 | — | dataV / dashboard，决定渲染分支 |
| `enableSvgRenderer` | 使用 SVG 渲染器 | bool | `False` | 同上 | ⚠️ 界面可配·注意 | 页面设置 · 渲染 | 默认 Canvas 渲染；SVG 下部分滤镜/图片效果不同 |
| `refreshBrowserEnable` | 定时刷新-整页 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | — |
| `refreshBrowserTime` | 整页刷新间隔 | int | `5` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | — |
| `refreshBrowserUnit` | 整页刷新单位 | enum | `minute` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | second / minute / hour |
| `refreshViewEnable` | 定时刷新-图表 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | — |
| `refreshTime` | 图表刷新间隔 | int | `5` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | — |
| `refreshUnit` | 图表刷新单位 | enum | `minute` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | second / minute / hour |
| `refreshViewLoading` | 刷新时显示 loading | bool | `True` | 同上 | ✅ 界面可配 | 页面设置 · 定时刷新 | — |
| `popupAvailable` | 允许弹窗区域 | bool | `True` | 同上 | ✅ 界面可配 | 页面设置 · 工具栏 | — |
| `popupButtonAvailable` | 弹窗内显示按钮 | bool | `True` | 同上 | ✅ 界面可配 | 页面设置 · 工具栏 | — |
| `suspensionButtonAvailable` | 显示悬浮按钮 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 工具栏 | — |
| `suspensionViewButtonAvailable` | 图表悬浮按钮可用 | bool | `True` | 同上 | ✅ 界面可配 | 页面设置 · 工具栏 | — |
| `backgroundColorSelect` | 启用自定义底色 | bool | `True` | 同上 | ✅ 界面可配 | 页面设置 · 背景 | — |
| `backgroundColor` | 画布底色 | color | `#020408` | `#f5f6f7` | ✅ 界面可配 | 页面设置 · 背景 | — |
| `backgroundImageEnable` | 启用背景图 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 背景 | 与 background 成对使用 |
| `background` | 背景图地址 | url | `（空）` | 同上 | ✅ 界面可配 | 页面设置 · 背景 | 支持外链与产品内上传路径 |
| `backgroundType` | 背景类型（历史字段） | enum | `backgroundColor` | 同上 | ⛔ 界面无入口 | — | 已废弃，勿依赖 |
| `opacity` | 整页透明度（历史字段） | float | `1` | 同上 | ⛔ 界面无入口 | — | 已废弃，勿依赖 |
| `color` | 全局文字色 | color | `#fff` | `#000000` | ✅ 界面可配 | 页面设置 · 字体 | — |
| `fontSize` | 全局字号 | int | `14` | 同上 | ✅ 界面可配 | 页面设置 · 字体 | — |
| `fontFamily` | 全局字体 | string | `PingFang` | 同上 | ✅ 界面可配 | 页面设置 · 字体 | — |
| `themeId` | 主题 ID | string | `10002` | `10001` | ⛔ 界面无入口 | — | 10002=暗色（大屏）/ 10001=亮色（仪表板） |
| `dialogBackgroundColor` | 弹窗底色 | color | `#fff` | 同上 | ✅ 界面可配 | 页面设置 · 弹窗 | — |
| `dialogButton` | 弹窗按钮色 | color | `#020408` | 同上 | ✅ 界面可配 | 页面设置 · 弹窗 | — |
| `dashboard.gap` | 启用组件间隙 | enum | `yes` | 同上 | ✅ 界面可配 | 页面设置 · 栅格 | yes / no |
| `dashboard.gapSize` | 组件间隙像素 | int | `5` | 同上 | ✅ 界面可配 | 页面设置 · 栅格 | — |
| `dashboard.gapMode` | 间隙归属 | enum | `middle` | 同上 | ✅ 界面可配 | 页面设置 · 栅格 | middle=组件之间（默认）/ outer=外侧 / inner=内侧 |
| `dashboard.showGrid` | 编辑时显示网格 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 栅格 | 仅编辑器可见 |
| `dashboard.matrixBase` | 矩阵基数 | int | `4` | 同上 | ⛔ 界面无入口 | — | 当前矩阵 = 72×36 的 1/4 进制步长 |
| `dashboard.resultMode` | 面板结果集模式 | enum | `all` | 同上 | ✅ 界面可配 | 页面设置 · 数据 | all=全部 / custom=自定义条数 |
| `dashboard.resultCount` | 面板结果集条数 | int | `1000` | 同上 | ✅ 界面可配 | 页面设置 · 数据 | — |
| `dashboard.themeColor` | 面板明暗主题 | enum | `dark` | `light` | ✅ 界面可配 | 页面设置 · 主题 | dark / light |
| `dashboard.mobileSetting.customSetting` | 移动端独立配置 | bool | `False` | 同上 | ✅ 界面可配 | 页面设置 · 移动端 | — |
| `dashboard.mobileSetting.backgroundType` | 移动端背景类型 | enum | `image` | 同上 | ✅ 界面可配 | 页面设置 · 移动端 | image / color |
| `dashboard.mobileSetting.imageUrl` | 移动端背景图 | url | — | 同上 | ✅ 界面可配 | 页面设置 · 移动端 | — |
| `dashboard.mobileSetting.color` | 移动端背景色 | color | `#fff` | `#000` | ✅ 界面可配 | 页面设置 · 移动端 | — |
| `component.chartTitle.show` | 统一显示组件标题 | bool | `True` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.fontSize` | 统一标题字号 | int | `16` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.color` | 统一标题颜色 | color | `#ffffff` | `#000000` | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.hPosition` | 统一标题水平位置 | enum | `left` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | left / center / right |
| `component.chartTitle.vPosition` | 统一标题垂直位置 | enum | `top` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | top / middle / bottom |
| `component.chartTitle.isBolder` | 统一标题加粗 | bool | `True` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.isItalic` | 统一标题斜体 | bool | `False` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.remarkShow` | 统一显示标题备注 | bool | `False` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.fontFamily` | 统一标题字体 | string | `Microsoft YaHei` | 同上 | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartTitle.remarkBackgroundColor` | 标题备注底色 | color | `#5A5C62` | `#ffffff` | ✅ 界面可配 | 主题 · 组件标题 | — |
| `component.chartCommonStyle.backgroundColorSelect` | 统一组件底色开关 | bool | `False` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.backgroundColor` | 统一组件底色 | color | `#131E42` | `rgba(255,255,255,1)` | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.backgroundImageEnable` | 统一组件背景图开关 | bool | `False` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.backgroundType` | 统一组件背景类型 | enum | `innerImage` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | innerImage=产品内置边框（board/board_N.svg）/ outerImage=自定义图片 |
| `component.chartCommonStyle.innerImage` | 内置边框素材 | string | `board/board_1.svg` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.outerImage` | 自定义边框图 | url | — | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.innerImageColor` | 边框着色 | color | `#1094E5` | `rgba(16, 148, 229,1)` | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.innerPadding` | 统一内边距 | object | `{"mode": "uniform", "top": 12}` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | mode: uniform（四边同值）/ single（分边） |
| `component.chartCommonStyle.borderRadius` | 统一圆角 | object | `{"mode": "uniform", "topLeft": 0}` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.backdropFilterEnable` | 启用毛玻璃 | bool | `False` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartCommonStyle.backdropFilter` | 毛玻璃半径 | int | `4` | 同上 | ✅ 界面可配 | 主题 · 组件背景 | — |
| `component.chartColor.basicStyle.colorScheme` | 统一配色方案 | enum | `default` | 同上 | ⚠️ 界面可配·注意 | 主题 · 配色 | 大屏默认走图表自身 colors，仪表板走面板统一配色 |
| `component.chartColor.basicStyle.colors` | 统一配色序列 | array | `["#1E90FF","#90EE90","#00CED1","#E2BD84","#7A90E0","#3BA272","#2BE7FF","#0A8ADA","#FFD700"]` | 同上 | ⚠️ 界面可配·注意 | 主题 · 配色 | 仪表板才有；大屏请在图表 extraView.customAttr.basicStyle.colors 单独设 |
| `component.filterStyle.layout` | 查询组件排列 | enum | `horizontal` | 同上 | ✅ 界面可配 | 主题 · 查询组件 | horizontal / vertical |
| `component.filterStyle.titleLayout` | 查询组件标题位置 | enum | `left` | 同上 | ✅ 界面可配 | 主题 · 查询组件 | left / top |
| `component.filterStyle.labelColor` | 查询组件标签色 | color | `#ffffff` | `#1f2329` | ✅ 界面可配 | 主题 · 查询组件 | — |
| `component.filterStyle.borderColor` | 查询组件边框色 | color | `#505050` | `#D9DCDF` | ✅ 界面可配 | 主题 · 查询组件 | — |
| `component.filterStyle.bgColor` | 查询组件背景色 | color | `#131C42` | `#FFFFFF` | ✅ 界面可配 | 主题 · 查询组件 | — |
| `component.tabStyle.headPosition` | Tab 页签位置 | enum | `left` | 同上 | ✅ 界面可配 | 主题 · Tab | left / top / right / bottom |
| `component.seniorStyleSetting.linkageIconColor` | 联动角标颜色 | color | `#ffffff` | `#a6a6a6` | ✅ 界面可配 | 主题 · 高级 | — |
| `component.seniorStyleSetting.drillLayerColor` | 钻取层级文字色 | color | `#ffffff` | `#a6a6a6` | ✅ 界面可配 | 主题 · 高级 | — |
| `component.seniorStyleSetting.pagerColor` | 翻页器颜色 | color | `#ffffff` | `#a6a6a6` | ✅ 界面可配 | 主题 · 高级 | — |
| `component.seniorStyleSetting.pagerSize` | 翻页器字号 | int | `14` | 同上 | ✅ 界面可配 | 主题 · 高级 | — |


## 单个图表配置（canvasViewInfo[组件id]）

由 `python datav.py defaults --group chart --markdown`（或 `python dashboard.py defaults`）生成，请勿手改。

| 配置项 | 含义 | 类型 | 数据大屏默认 | 仪表板默认 | 界面可达性 | 界面位置 | 说明 |
|---|---|---|---|---|---|---|---|
| `resultCount` | 结果集条数 | int | `1000` | 同上 | ✅ 界面可配 | 图表 · 数据 | — |
| `resultMode` | 结果集模式 | enum | `custom` | 同上 | ⚠️ 界面可配·注意 | 图表 · 数据 | 图表级默认 custom；跟随面板时与 canvasStyleData.dashboard.resultMode 一致 |
| `refreshViewEnable` | 该图表定时刷新 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 数据 | — |
| `refreshTime` | 刷新间隔 | int | `5` | 同上 | ✅ 界面可配 | 图表 · 数据 | — |
| `refreshUnit` | 刷新单位 | enum | `minute` | 同上 | ✅ 界面可配 | 图表 · 数据 | second / minute / hour |
| `customFilter` | 图表内过滤 | object | `{}` | 同上 | ✅ 界面可配 | 图表 · 过滤 | FilterTree：{logic, items:[{type,fieldId,term,value}]} |
| `linkageActive` | 启用联动（运行时开关） | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动 | — |
| `jumpActive` | 启用跳转（运行时开关） | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转 | — |
| `customAttr.basicStyle.colorScheme` | 配色方案 | enum | `default` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | default / elegant / future / gradual … |
| `customAttr.basicStyle.colors` | 配色序列 | array | `["#5470c6","#91cc75","#fac858","#ee6666","#73c0de","#3ba272","#fc8452","#9a60b4","#ea7ccc"]` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | — |
| `customAttr.basicStyle.alpha` | 色彩透明度 | int | `100` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | 0–100 |
| `customAttr.basicStyle.gradient` | 柱条/面积渐变 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | — |
| `customAttr.basicStyle.columnWidthRatio` | 柱宽占比 | int | `60` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | — |
| `customAttr.basicStyle.radius` | 饼图半径 | int | `90` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | — |
| `customAttr.basicStyle.innerRadius` | 环形内半径 | int | `60` | 同上 | ✅ 界面可配 | 图表 · 样式 · 配色 | — |
| `customAttr.basicStyle.mapStyle` | 地图底图风格 | enum | `darkblue` | `normal` | ✅ 界面可配 | 图表 · 样式 · 地图 | normal / darkblue / … |
| `customAttr.label.show` | 显示标签 | bool | `False` | 同上 | ⚠️ 界面可配·注意 | 图表 · 样式 · 标签 | 饼图/矩形树图在创建时会被打开 |
| `customAttr.label.position` | 标签位置 | enum | `top` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | top / bottom / left / right / inside / outside / center |
| `customAttr.label.fontSize` | 标签字号 | int | `12` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.label.color` | 标签颜色 | color | `#ffffff` | `#333333` | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.label.showDimension` | 标签含维度名 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.label.showQuota` | 标签含指标值 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.label.showProportion` | 标签含占比 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.label.reserveDecimalCount` | 标签保留小数位 | int | `2` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标签 | — |
| `customAttr.tooltip.show` | 显示提示框 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 提示 | — |
| `customAttr.tooltip.trigger` | 触发方式 | enum | `item` | 同上 | ✅ 界面可配 | 图表 · 样式 · 提示 | item=数据项 / axis=坐标轴 |
| `customAttr.tooltip.confine` | 限制在图形内 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 提示 | — |
| `customAttr.tooltip.fontSize` | 提示字号 | int | `12` | 同上 | ✅ 界面可配 | 图表 · 样式 · 提示 | — |
| `customAttr.tooltip.color` | 提示文字色 | color | `#000000` | 同上 | ⚠️ 界面可配·注意 | 图表 · 样式 · 提示 | 默认白底黑字，大屏上勿改成白色 |
| `customAttr.tooltip.backgroundColor` | 提示底色 | color | `#ffffff` | `#5A5C62` | ✅ 界面可配 | 图表 · 样式 · 提示 | — |
| `customAttr.tooltip.showQuota` | 提示含指标 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 样式 · 提示 | — |
| `customAttr.indicator.show` | 显示指标值 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicator.fontSize` | 指标值字号 | int | `36` | 同上 | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicator.color` | 指标值颜色 | color | `#ffffff` | `#0C296E` | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicator.isBolder` | 指标值加粗 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicatorName.show` | 显示指标名 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicatorName.fontSize` | 指标名字号 | int | `16` | 同上 | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.indicatorName.color` | 指标名颜色 | color | `#cccccc` | `#646A73` | ✅ 界面可配 | 图表 · 样式 · 指标卡 | — |
| `customAttr.tableHeader.tableHeaderBgColor` | 表头底色 | color | `#1E90FF` | 同上 | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customAttr.tableHeader.tableHeaderFontColor` | 表头文字色 | color | `#FFFFFF` | 同上 | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customAttr.tableCell.tableItemBgColor` | 单元格底色 | color | `#131E42` | `#FFFFFF` | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customAttr.tableCell.tableFontColor` | 单元格文字色 | color | `#ffffff` | `#000000` | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customAttr.tableCell.tableItemSubBgColor` | 斑马纹底色 | color | `#1E90FF` | 同上 | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customAttr.tableTotal` | 合计行样式 | object | `{}` | 同上 | ✅ 界面可配 | 图表 · 样式 · 表格 | — |
| `customStyle.text.show` | 显示图表标题 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.text.fontSize` | 标题字号 | int | `16` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.text.color` | 标题颜色 | color | `#ffffff` | `#000000` | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.text.hPosition` | 标题水平位置 | enum | `left` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | left / center / right |
| `customStyle.text.vPosition` | 标题垂直位置 | enum | `top` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | top / middle / bottom |
| `customStyle.text.isBolder` | 标题加粗 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.text.isItalic` | 标题斜体 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.text.fontFamily` | 标题字体 | string | `Microsoft YaHei` | 同上 | ✅ 界面可配 | 图表 · 样式 · 标题 | — |
| `customStyle.legend.show` | 显示图例 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | — |
| `customStyle.legend.hPosition` | 图例水平位置 | enum | `center` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | left / center / right |
| `customStyle.legend.vPosition` | 图例垂直位置 | enum | `bottom` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | top / middle / bottom |
| `customStyle.legend.orient` | 图例排列方向 | enum | `horizontal` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | horizontal / vertical |
| `customStyle.legend.icon` | 图例图标 | enum | `circle` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | circle / rect / roundRect / triangle / diamond |
| `customStyle.legend.color` | 图例文字色 | color | `#ffffff` | `#333333` | ✅ 界面可配 | 图表 · 样式 · 图例 | — |
| `customStyle.legend.fontSize` | 图例字号 | int | `12` | 同上 | ✅ 界面可配 | 图表 · 样式 · 图例 | — |
| `customStyle.xAxis.show` | 显示 X 轴 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.xAxis.position` | X 轴位置 | enum | `bottom` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | bottom / top |
| `customStyle.xAxis.color` | X 轴文字色 | color | `#ffffff` | `#333333` | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.xAxis.fontSize` | X 轴字号 | int | `12` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.yAxis.show` | 显示 Y 轴 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.yAxis.position` | Y 轴位置 | enum | `left` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | left / right |
| `customStyle.yAxis.color` | Y 轴文字色 | color | `#ffffff` | `#333333` | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.yAxis.fontSize` | Y 轴字号 | int | `12` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.yAxisExt.show` | 显示副轴 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | — |
| `customStyle.yAxisExt.position` | 副轴位置 | enum | `right` | 同上 | ✅ 界面可配 | 图表 · 样式 · 轴 | right / left |
| `senior.functionCfg.emptyDataStrategy` | 空值处理策略 | enum | `ignoreData` | 同上 | ✅ 界面可配 | 图表 · 高级 · 空值 | ignoreData=忽略空值（默认）/ breakLine=折线断点 |
| `senior.functionCfg.sliderShow` | 开启缩放滑块 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 缩放 | — |
| `senior.assistLineCfg.enable` | 辅助线 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 辅助线 | — |
| `senior.threshold.enable` | 阈值告警 | bool | `False` | 同上 | ⚠️ 界面可配·注意 | 图表 · 高级 · 阈值 | 阈值在发布时统一处理，未发布不生效 |
| `senior.scrollCfg.open` | 自动滚动 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 滚动 | — |
| `senior.useGlobalAreaMapping` | 沿用面板级区域映射 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 地图 | — |
| `drillFields` | 钻取字段 | array | `[]` | 同上 | ✅ 界面可配 | 图表 · 钻取 | — |
| `xAxisExt` | 副维度 | array | `[]` | 同上 | ✅ 界面可配 | 图表 · 数据 | 分组柱/分组折线用 |
| `extStack` | 堆叠维度 | array | `[]` | 同上 | ✅ 界面可配 | 图表 · 数据 | 堆叠图用 |


## 图表联动（/linkage/*）

由 `python datav.py defaults --group linkage --markdown`（或 `python dashboard.py defaults`）生成，请勿手改。

| 配置项 | 含义 | 类型 | 数据大屏默认 | 仪表板默认 | 界面可达性 | 界面位置 | 说明 |
|---|---|---|---|---|---|---|---|
| `linkage[].source` | 源图表 | string | `（必填）` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动设置 | 写图表标题或组件 id；解析不到会报错并列出候选 |
| `linkage[].targets` | 联动目标图表 | array | `（必填）` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动设置 | 目标图表标题或 id 列表；源图表自身会被自动跳过 |
| `linkage[].fields` | 关联字段映射 | array | `[{"source": "字段A", "target": "字段A"}]` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动设置 · 关联字段 | 省略则按同名字段自动配对；同数据集字段 id 天然一致，跨数据集按名称匹配 |
| `linkage[].active` | 该目标启用联动 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动设置 · 目标前勾选 | 为 false 时保存后不写入关联字段（后端只在 active 时落库） |
| `linkageActive` | 源图表联动总开关 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 高级 · 联动 | 运行时还会校验：源图表 linkage_active=true 且存在启用中的联动关系，缺一不生效 |
| `actionSelection.linkageActive` | 点击行为 | enum | `custom` | 同上 | ✅ 界面可配 | 画布 · 联动设置（悬浮工具条） | custom=弹出浮框由用户选择联动或下钻（默认）/ auto=同时触发联动和下钻 |


## 图表跳转（/linkJump/*）

由 `python datav.py defaults --group jump --markdown`（或 `python dashboard.py defaults`）生成，请勿手改。

| 配置项 | 含义 | 类型 | 数据大屏默认 | 仪表板默认 | 界面可达性 | 界面位置 | 说明 |
|---|---|---|---|---|---|---|---|
| `jump[].source` | 源图表 | string | `（必填）` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 | 写图表标题或组件 id |
| `jump[].field` | 触发字段 | string | `（必填）` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 选择字段 | 必须是该图表已使用的字段（xAxis/xAxisExt/extStack/yAxis）；否则界面里不会出现该字段 |
| `jump[].linkType` | 跳转类型 | enum | `outer` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 跳转类型 | outer=外部链接 / inner=仪表板·数据大屏 |
| `jump[].jumpType` | 打开方式 | enum | `_blank` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 打开方式 | _self=当前页面 / _blank=新开页面（默认）/ newPop=弹窗页面 |
| `jump[].windowSize` | 弹窗大小 | enum | `middle` | 同上 | ⚠️ 界面可配·注意 | 图表 · 高级 · 跳转设置 · 窗口大小 | large=大 / middle=中 / small=小；仅 jumpType=newPop 时生效 |
| `jump[].content` | 外部链接内容 | string | `http://` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 链接内容 | linkType=outer 必填，≤4000 字符。字段占位写成 [字段名]，保存时会转成 [字段id]，点击时替换为实际值 |
| `jump[].attachParams` | 附加点击参数 | bool | `False` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 | 把当前图表过滤条件作为外部参数带给目标（仅内部跳转） |
| `jump[].targetDvId` | 目标仪表板/大屏 ID | string | `（空）` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 选择仪表板/数据大屏 | linkType=inner 必填 |
| `jump[].checked` | 该字段启用跳转 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 字段前勾选 | — |
| `jump[].targets` | 跳转目标映射 | array | `[]` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转设置 · 关联图表 | linkType=inner 时每项写 {view, type, fields}；type: view=图表 / filter=过滤组件 / outParams=外部参数 |
| `jumpActive` | 源图表跳转总开关 | bool | `True` | 同上 | ✅ 界面可配 | 图表 · 高级 · 跳转 | 运行时还会校验字段级 checked=true，缺一不生效 |


