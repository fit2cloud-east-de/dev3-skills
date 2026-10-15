# 电子表格：新建、修改与发布

电子表格是与数据源 / 数据集 / 数据大屏 / 仪表板并列的**第五棵独立资源树**。表体为在线电子表格快照：多 Sheet、单元格值与公式、富文本、样式、合并、列宽行高、冻结、数据验证（下拉等）、自动筛选、批注、斜线格、条件格式、明细表（数据集绑定）。

## 能力边界（强制）

- ✅ **新建**电子表格（本文全部特性）
- ✅ **修改当前任务内创建**的电子表格：`edit` 必须加 `--session-created`，否则拒绝
- ❌ **不支持修改已存在的电子表格**（既有表格请用户在产品界面操作）
- ❌ 不提供删除命令

## 流程与视图语义

1. `spreadsheet.py resolve-folder --name "目标文件夹"`（电子表格树，勿用其它树组织根 id）
2. 编写规格 JSON（可用 `spreadsheet.py template` 生成模板）
3. `spreadsheet.py create --name "名称" --folder-name "目标文件夹" --file spec.json`
4. （迭代）调整规格后 `spreadsheet.py edit --id <ID> --session-created --file spec_v2.json`
5. 用户确认内容后 `spreadsheet.py publish --id <ID>`

**两个视图**：`get`（findById）返回**发布版**——未发布的新改动不在其中；`get-edit`（findEditById）返回**编辑稿**（含全部改动）。校验最近一次编辑结果请用 `get-edit`；发布后两者一致（status: 0 未发布 / 1 已发布 / 2 已保存未发布）。

---

## 规格 JSON（spec）

顶层结构：

| 键 | 类型 | 说明 |
|----|------|------|
| `styles` | `{名: 样式}` | 命名样式表；单元格 `"style": "名"` 引用 |
| `sheets` | `数组` | 工作表列表，至少 1 个；顺序即展示顺序 |
| `conditionalFormats` | `数组` | 条件格式 |
| `validations` | `数组` | 数据验证（下拉列表 / 数值范围 / 自定义公式等） |
| `filters` | `数组` | 自动筛选（每表一条：范围 + 各列条件） |
| `notes` | `数组` | 批注（纯文本） |
| `slashCells` | `数组` | 斜线格（二分/三分） |
| `datasetTables` | `数组` | 明细表：把数据集字段绑定到某起始格渲染 |

### sheets[] 工作表

| 键 | 说明 |
|----|------|
| `name` | 工作表名（不可重复） |
| `rowCount` / `columnCount` | 行数 / 列数，默认 1000 / 26 |
| `freeze` | 冻结至某格，如 `"A2"` 冻结首行；或 `{xSplit,ySplit,startRow,startColumn}` |
| `hidden` | `true` 隐藏该工作表 |
| `tabColor` | 工作表标签颜色 `#RRGGBB` |
| `showGridlines` | `false` 隐藏网格线 |
| `rightToLeft` | `true` 从右到左 |
| `columnWidths` | `{"A": 120, "B:D": 90}` 列宽（支持区间） |
| `rowHeights` | `{"1": 32, "2:3": 24}` 行高（1 起始，支持区间） |
| `merges` | `["A1:E1", ...]` 合并单元格 |
| `cells` | `{单元格引用: 单元格}` |

### cells 单元格

| 键 | 说明 |
|----|------|
| `v` | 值（数字或字符串） |
| `f` | 公式，如 `"=SUM(B3:B4)"`（可不带 =，自动补） |
| `style` / `inlineStyle` | 命名样式 / 内联样式（键同命名样式） |
| `richText` | 富文本 `[{text, style}]`，与 `v`/`f` 互斥；分段样式键同命名样式 |
| `type` | `"text"` 强制文本（保留前导零）；`"number"` 强制数值 |

### styles 样式键

| 键 | 取值 | 说明 |
|----|------|------|
| `bold` / `italic` | true | 加粗 / 斜体 |
| `underline` / `strike` | true | 下划线 / 删除线 |
| `font` / `fontSize` | 字体名 / 数值 | |
| `bg` / `color` | `#RRGGBB` | 背景色 / 字色 |
| `align` | left / center / right | 水平对齐 |
| `valign` | top / middle / bottom | 垂直对齐 |
| `wrap` | true | 自动换行 |
| `numberFormat` | 如 `#,##0.00`、`0.0%`、`¥#,##0.00` | 数字格式 |
| `border` / `borderColor` | all / outline / top / bottom / left / right；`#RRGGBB` | 边框（默认 `#999999`） |

---

## conditionalFormats 条件格式

每条：`{"sheet", "range", "stopIfTrue", "rule"}`

`rule.type=highlightCell`（最常用）——`subType` 判据：

| subType | 必填字段 | 说明 |
|---------|----------|------|
| `number` | `operator` + `value` | 数值比较；operator：greaterThan / lessThan / equal / notEqual / between（value 传 `[下,上]`）/ notBetween |
| `text` | `operator` + `value?` | containsText / notContainsText / beginsWith / endsWith / equal / notEqual / containsBlanks / notContainsBlanks |
| `formula` | `value` | 公式为真命中，如 `"=$B2>1000"` |
| `timePeriod` | `operator` | today / yesterday / last7Days / thisMonth 等 |
| `rank` | `value` + `isBottom` + `isPercent` | 前 / 后 N 名 |
| `average` | `operator` | 与平均值比较 |
| `uniqueValues` / `duplicateValues` | — | 唯一 / 重复值 |

`rule.style` 为内联样式（键同命名样式）。

`dataBar` / `colorScale` / `iconSet`（数据条 / 色阶 / 图标）按产品内核原生结构传入（`isShowValue`、`config.min/max`、`positiveColor` 等），CLI 原样透传。

## validations 数据验证

每条：`{"sheet", "range", "type", ...}`

| type | 字段 | 说明 |
|------|------|------|
| `list` / `listMultiple` | `values: [选项]` | 下拉列表（单选/多选）；选项值勿含英文逗号，或直接传 `formula` 引用单元格区域 |
| `decimal` / `whole` | `operator` + `values` | 小数 / 整数范围；operator 同条件格式数值比较 |
| `textLength` | `operator` + `values` | 文本长度限制 |
| `date` / `time` | `operator` + `values` | 日期 / 时间范围 |
| `checkbox` | — | 复选框 |
| `custom` | `formula: "=..."` | 自定义公式校验 |
| `any` | — | 任意值（仅带提示） |

可选：`allowBlank`（默认 true）、`promptTitle`/`prompt`（输入提示）、`errorTitle`/`error`（错误提示）。

## filters 自动筛选

每表一条：`{"sheet", "range": "A1:E100", "columns": [...]}`（range 首行为表头行）

每列：`{"col": "C", "values": ["是", "否"]}` 按值筛选；或 `{"col": "B", "custom": [{"val": 100, "operator": "greaterThan"}]}` 自定义条件（operator：equal / notEqual / greaterThan / greaterThanOrEqual / lessThan / lessThanOrEqual）。

## notes 批注 / slashCells 斜线格

```json
{"sheet": "Sheet1", "cell": "A1", "text": "批注内容", "width": 160, "height": 120}
{"sheet": "Sheet1", "cell": "F1", "type": "two"}
```

斜线格 `type`：`two`（二分）/ `three`（三分）。

## datasetTables 明细表（数据集绑定）

把数据集字段绑定到某起始格，查看时按 `resultLimit` 渲染明细：

```json
{
  "sheet": "Sheet1", "startCell": "A7", "datasetId": "<数据集ID>",
  "resultLimit": 100, "blockName": "明细数据",
  "fields": [
    {"id": "<字段ID>", "name": "<字段名>", "dataeaseName": "<f_xxxx>",
     "groupType": "d", "deType": 0, "extField": 0}
  ]
}
```

`fields` 须为数据集真实字段：先用 `dataset.py get --id <数据集ID>` 取 `allFields`，摘取 `id / name / dataeaseName / groupType / deType / extField`。可选 `hideHeader`、`mergeCell`。

**注意**：明细表引用已有数据集属**读取**行为，不修改数据集；但修改/删除该数据集会导致表格渲染失败，删改前仍须遵守[common.md](common.md)的血缘分析与确认流程，并在风险说明中提及此表格。

---

## 范围外（请用户在产品界面操作）

超链接（富文本链接）、透视表、表格内查询/过滤组件、单元格图片与浮动图片、明细表/透视表的高级样式（表头/斑马纹/汇总行等）。

## 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /de2api/spreadsheet/tree | `{busiFlag: "spreadsheet"}` |
| POST | /de2api/spreadsheet/create | `{name, pid, nodeType: "sheet", sheetData}` |
| POST | /de2api/spreadsheet/update | 同上 + `id`、`version` |
| POST | /de2api/spreadsheet/findById | `{id}` 发布视图 |
| POST | /de2api/spreadsheet/findEditById | `{id}` 编辑稿（含未发布改动） |
| POST | /de2api/spreadsheet/updateStatus | `{id, status: 1}` 发布 |
| POST | /de2api/spreadsheet/nameCheck | 同名检查 |

`sheetData` 为工作簿快照 JSON 字符串。查询 `get --id` 得到的 `sheetData` 也可改后经 `edit --raw` 提交（进阶用法）。
