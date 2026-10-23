# 电子表格规格默认值全表

> 本文件由 `python spreadsheet.py defaults --markdown` 生成，请勿手改；
> 与代码不一致时以命令输出为准。

**档位**：✅ 界面可编辑 · ⚠️ 界面受限 · ⛔ 界面无入口（写入后用户无法在界面改回）

## 顶层（spec）

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `theme` | business\|finance\|fresh\|minimal | 无（不注入主题样式；`template` 命令默认 business） | 无直接入口（主题只是样式集合） | ⛔ 界面无入口 | 不写 theme 时须自建 styles 或接受默认外观 |
| `styles` | 对象 {样式名: 样式} | {} | 功能区·字体/版式/数字格式 | ✅ 界面可编辑 | 单元格用 style 引用，同一份样式可复用 |
| `sheets` | 数组 | 必填（≥1 个） | 工作表标签 | ✅ 界面可编辑 | 顺序即展示顺序 |
| `conditionalFormats` | 数组 | [] | 功能区·条件格式 | ✅ 界面可编辑 | — |
| `validations` | 数组 | [] | 功能区·数据验证 | ✅ 界面可编辑 | — |
| `filters` | 数组 | [] | 功能区·筛选（表头按钮） | ✅ 界面可编辑 | 每表一条 |
| `notes` | 数组 | [] | 功能区·插入 → 批注 | ✅ 界面可编辑 | — |
| `slashCells` | 数组 | [] | 功能区·斜线格 | ✅ 界面可编辑 | — |
| `datasetTables` | 数组 | [] | 功能区·插入 → 明细表 | ✅ 界面可编辑 | — |
| `filterComponents` | 数组 | [] | 功能区·查询组件 | ✅ 界面可编辑 | 至多一条（工作簿级单例） |

## sheets[] 工作表

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `name` | 字符串 | 必填 | 工作表标签（双击重命名） | ✅ 界面可编辑 | — |
| `rowCount` | 整数 | 1000 | 右键·插入行 | ✅ 界面可编辑 | — |
| `columnCount` | 整数 | 26 | 右键·插入列 | ✅ 界面可编辑 | — |
| `defaultColumnWidth` | 整数(px) | 93 | 拖拽列宽 | ✅ 界面可编辑 | — |
| `defaultRowHeight` | 整数(px) | 27 | 拖拽行高 | ✅ 界面可编辑 | — |
| `freeze` | 'B2' 或 {xSplit,ySplit,startRow,startColumn} | 无（不冻结） | 功能区·冻结 | ✅ 界面可编辑 | — |
| `hidden` | 布尔 | false | 工作表标签右键 | ✅ 界面可编辑 | — |
| `tabColor` | #RRGGBB | 无（默认标签色） | 工作表标签右键 | ✅ 界面可编辑 | — |
| `showGridlines` | 布尔 | true | 无（开关原在菜单栏，菜单栏不显示） | ⛔ 界面无入口 | 写 false 后用户无法在界面恢复 |
| `rightToLeft` | 布尔 | false | 无 | ⛔ 界面无入口 | 写 true 后用户无法在界面改回 |
| `merges` | ['A1:C1', …] | [] | 功能区·合并单元格 | ✅ 界面可编辑 | 合并会清空左上角以外的内容 |
| `columnWidths` | {'A':120,'B:D':90} | {}（用 defaultColumnWidth） | 拖拽列宽 | ✅ 界面可编辑 | — |
| `rowHeights` | {'1':32,'2:3':24}（1 起始） | {}（用 defaultRowHeight） | 拖拽行高 | ✅ 界面可编辑 | — |
| `cells` | {单元格引用: 单元格} | {} | 单元格内编辑 | ✅ 界面可编辑 | — |

## cells{} 单元格

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `v` | 数字/字符串 | 无（空单元格） | 单元格内输入 | ✅ 界面可编辑 | — |
| `f` | 字符串（可不带 =，自动补） | 无 | 单元格内输入 / 函数下拉 | ✅ 界面可编辑 | — |
| `style` | 命名样式名 | 无（无样式，走产品默认外观） | 功能区·字体/版式/数字格式 | ✅ 界面可编辑 | — |
| `inlineStyle` | 对象（键同 styles） | 无 | 同上 | ✅ 界面可编辑 | — |
| `richText` | [{text, style}] | 无（与 v/f 互斥） | 单元格内富文本编辑 | ✅ 界面可编辑 | — |
| `type` | text\|number | 无（自动识别值类型） | 无（'文本转数字'被隐藏，无反向操作） | ⛔ 界面无入口 | 写入后不可逆；仅用于编码类保留前导零 |

## styles{} 样式键（不设置 = 继承单元格/产品默认）

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `bold / italic / underline / strike` | 布尔 | false | 功能区·字体组 | ✅ 界面可编辑 | — |
| `font` | 字体名 | 无（产品默认字体） | 功能区·字体 | ✅ 界面可编辑 | — |
| `fontSize` | 数字(pt) | 无（产品默认字号） | 功能区·字号 | ✅ 界面可编辑 | — |
| `bg` | #RRGGBB | 无（透明） | 功能区·背景色 | ✅ 界面可编辑 | — |
| `color` | #RRGGBB | 无（默认字色） | 功能区·文字颜色 | ✅ 界面可编辑 | — |
| `align` | left\|center\|right\|justified | 无（常规，按值类型自动） | 功能区·水平对齐 | ✅ 界面可编辑 | — |
| `valign` | top\|middle\|bottom | 无（走产品默认） | 功能区·垂直对齐 | ✅ 界面可编辑 | — |
| `wrap` | 布尔 | false | 功能区·自动换行 | ✅ 界面可编辑 | — |
| `numberFormat` | 如 #,##0.00 / 0.0% / ¥#,##0.00 | 无（常规） | 功能区·数字格式/百分比/货币 | ✅ 界面可编辑 | — |
| `border` | all\|outline\|top\|bottom\|left\|right | 无（无边框） | 功能区·边框 | ✅ 界面可编辑 | 线型固定为细线 |
| `borderColor` | #RRGGBB | #999999（仅在 border 存在时生效） | 功能区·边框颜色 | ✅ 界面可编辑 | — |

## validations[] 数据验证

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `range` | 'B4:B20' | 'A1' | 数据验证面板·作用范围 | ✅ 界面可编辑 | — |
| `type` | list\|listMultiple\|decimal\|whole\|textLength\|date\|time\|checkbox\|custom\|any | 必填 | 数据验证·条件类型 | ✅ 界面可编辑 | — |
| `renderMode` | arrow\|text\|chip | arrow（产品缺省其实是 chip，脚本刻意改为 arrow） | 数据验证·渲染方式 | ⚠️ 界面受限 | chip 需逐项配色，缺省会灰底浅字 |
| `values` | 数组 | 无（list 必填之一） | 数据验证·选项来源=自定义 | ✅ 界面可编辑 | — |
| `formula` | 如 =$F$2:$F$5 | 无 | 数据验证·选项来源=引用数据 | ✅ 界面可编辑 | — |
| `operator` | 同条件格式数值比较 | 无 | 数据验证·条件 | ✅ 界面可编辑 | — |
| `allowBlank` | 布尔 | true | 数据验证·忽略空值 | ✅ 界面可编辑 | — |
| `promptTitle / prompt` | 字符串 | 无（不显示输入提示） | 数据验证·输入提示 | ✅ 界面可编辑 | — |
| `errorTitle / error` | 字符串 | 无（不显示错误提示） | 数据验证·错误提示 | ✅ 界面可编辑 | — |

## filters[] 自动筛选

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `range` | 'A3:F200'（首行为表头） | 'A1' | 功能区·筛选 | ✅ 界面可编辑 | — |
| `columns` | 数组 | []（只给范围，表头出现筛选按钮） | 表头筛选面板 | ✅ 界面可编辑 | 预置条件会让表一打开就处于筛选态 |
| `columns[].col` | 'C'（单列） | 必填 | 表头筛选面板 | ✅ 界面可编辑 | — |
| `columns[].values` | 数组 | 无 | 表头筛选·按值 | ✅ 界面可编辑 | — |
| `columns[].blank` | 布尔 | 无（不筛空值） | 表头筛选·空值 | ✅ 界面可编辑 | — |
| `columns[].custom` | 对象/数组 | 无 | 表头筛选·按条件 | ✅ 界面可编辑 | — |

## conditionalFormats[] 条件格式

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `range` | 'F3:F200' | 'A1' | 条件格式面板·作用范围 | ✅ 界面可编辑 | — |
| `stopIfTrue` | 布尔 | false | 条件格式·若为真则停止 | ✅ 界面可编辑 | — |
| `rule` | 对象 | 必填 | 条件格式·规则 | ✅ 界面可编辑 | — |
| `rule.type` | highlightCell\|dataBar\|colorScale\|iconSet | 必填 | 条件格式·规则类型 | ✅ 界面可编辑 | — |
| `rule.style` | 内联样式（键同 styles） | 无（无格式变化） | 条件格式·格式 | ✅ 界面可编辑 | — |

## notes[] 批注 / slashCells[] 斜线格

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `notes[].sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `notes[].cell` | 'D3' | 'A1' | 插入 → 批注 | ✅ 界面可编辑 | — |
| `notes[].text` | 字符串 | ''（空批注） | 批注框 | ✅ 界面可编辑 | — |
| `notes[].width / height` | 整数(px) | 160 / 120 | 拖拽批注框 | ✅ 界面可编辑 | — |
| `notes[].show` | 布尔 | false（不常显，悬停显示） | 批注显示方式 | ✅ 界面可编辑 | — |
| `slashCells[].sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `slashCells[].cell` | 'F1' | 'A1' | 功能区·斜线格 | ✅ 界面可编辑 | — |
| `slashCells[].type` | two\|three | two | 斜线格·二分/三分 | ✅ 界面可编辑 | — |

## datasetTables[] 明细表

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `sheet` | 字符串 | 第一个工作表 | — | ✅ 界面可编辑 | — |
| `startCell` | 'A7' | 'A1' | 插入后拖拽放置 | ✅ 界面可编辑 | — |
| `datasetId` | 字符串 | 必填 | 明细表·数据集 | ✅ 界面可编辑 | — |
| `fields` | 数组 | []（空则报错） | 明细表·字段 | ✅ 界面可编辑 | — |
| `blockName` | 字符串 | ''（用默认块名） | 明细表·自定义块名 | ✅ 界面可编辑 | — |
| `resultLimit` | 整数 | 100 | 明细表·结果条数上限 | ✅ 界面可编辑 | 服务端上限 100000，超出被截断 |
| `hideHeader` | 布尔 | false | 明细表·隐藏表头 | ✅ 界面可编辑 | — |
| `mergeCell` | 布尔 | false | 明细表·合并单元格 | ✅ 界面可编辑 | — |
| `customFilter` | 对象 | {}（不过滤） | 明细表·过滤条件 | ✅ 界面可编辑 | — |
| `queryFilter` | 数组 | [] | 由查询组件写入 | ⚠️ 界面受限 | 一般不要手填，交给 filterComponents |

## filterComponents[] 查询组件

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `sheet / startCell` | 字符串 | 第一个工作表 / 'A1' | 查询组件拖拽放置 | ✅ 界面可编辑 | — |
| `visible` | 布尔 | true | 查询组件·显示 | ✅ 界面可编辑 | — |
| `conditions` | 数组 | 必填（非空，否则报错） | 查询组件·查询条件 | ✅ 界面可编辑 | — |
| `conditions[].name` | 字符串 | 取 fieldName | 条件·显示名 | ✅ 界面可编辑 | — |
| `conditions[].fieldId / fieldName` | 字符串 | 必填 | 条件·绑定字段 | ✅ 界面可编辑 | — |
| `conditions[].displayType` | time\|textSelect\|numberRange… | 有 granularity → time，否则 textSelect | 条件·类型 | ✅ 界面可编辑 | — |
| `conditions[].granularity` | year\|month\|date\|datetime | date（仅 displayType=time） | 条件·时间粒度 | ✅ 界面可编辑 | — |
| `conditions[].optionSource` | auto\|… | auto | 条件·选项来源 | ✅ 界面可编辑 | — |
| `conditions[].required` | 布尔 | false | 条件·必填 | ✅ 界面可编辑 | — |
| `conditions[].multiple` | 布尔 | false | 条件·多选 | ✅ 界面可编辑 | — |
| `conditions[].visible` | 布尔 | true | 条件·显示 | ✅ 界面可编辑 | — |
| `conditions[].linkPlugin` | blockName / 块 id | 无（关联全部明细表） | 条件·关联范围 | ✅ 界面可编辑 | — |
| `（样式）base.padding / gap` | 整数(px) | 16 / 16 | 样式面板 | ✅ 界面可编辑 | — |
| `（样式）base.layout / align` | 字符串 | horizontal / left | 样式面板 | ✅ 界面可编辑 | — |
| `（样式）condition.color / fontSize` | 字符串 / 整数 | #1f2329 / 12 | 样式面板 | ✅ 界面可编辑 | — |
| `（样式）conditionName.show / position` | 布尔 / 字符串 | true / top | 样式面板 | ✅ 界面可编辑 | — |
| `（样式）button.btnList` | 数组 | ['sure'] | 样式面板·按钮 | ✅ 界面可编辑 | — |
| `（样式）button.primaryColor` | #RRGGBB | #3370ff | 样式面板·按钮颜色 | ✅ 界面可编辑 | — |

## 固定值（不可配，写出即为下列值）

| 键 | 类型 | 默认值 | 界面位置 | 可达性 | 说明 |
|----|------|--------|----------|--------|------|
| `workbook.id / name / locale` | 字符串 | workbook-01 / Workbook / zhCN | — | ⛔ 界面无入口 | — |
| `sheet.zoomRatio / scrollTop / scrollLeft` | 数字 | 1 / 0 / 0 | 视图缩放与滚动（用户可改，不持久） | ✅ 界面可编辑 | — |
| `sheet.selections` | 数组 | ['A1'] | 当前选区 | ✅ 界面可编辑 | — |
| `sheet.rowHeader` | 对象 | {width:46, hidden:0} | 行头宽度 | ✅ 界面可编辑 | — |
| `sheet.columnHeader` | 对象 | {height:20, hidden:0} | 列头高度 | ✅ 界面可编辑 | — |

