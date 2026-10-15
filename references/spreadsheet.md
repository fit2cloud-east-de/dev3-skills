# 电子表格：新建、修改与发布

电子表格是与数据源 / 数据集 / 数据大屏 / 仪表板并列的**第五棵独立资源树**。表体为在线电子表格快照（多 sheet、单元格值与公式、样式、合并、列宽行高、条件格式）。

## 能力边界（强制）

- ✅ **新建**电子表格（含多 sheet、公式、样式、条件格式等）
- ✅ **修改当前任务内创建**的电子表格：`edit` 必须加 `--session-created`，否则拒绝
- ❌ **不支持修改已存在的电子表格**（既有表格请用户在产品界面操作）
- ❌ 不提供删除命令

## 流程

1. `spreadsheet.py resolve-folder --name "目标文件夹"`（电子表格树，勿用其它树组织根 id）
2. 编写规格 JSON（见下，可用 `spreadsheet.py template` 生成模板）
3. `spreadsheet.py create --name "名称" --folder-name "目标文件夹" --file spec.json`
4. （迭代）调整规格后 `spreadsheet.py edit --id <ID> --session-created --file spec_v2.json`
5. 用户确认内容后 `spreadsheet.py publish --id <ID>`（status: 0 未发布 → 1 已发布）

---

## 规格 JSON（spec）

顶层结构：

| 键 | 类型 | 说明 |
|----|------|------|
| `styles` | `{名: 样式}` | 命名样式表；单元格通过 `"style": "名"` 引用 |
| `sheets` | `数组` | 工作表列表，至少 1 个；顺序即展示顺序 |
| `conditionalFormats` | `数组` | 条件格式规则，逐条声明（见下） |

### sheets[] 每个工作表

| 键 | 说明 |
|----|------|
| `name` | 工作表名（不可重复） |
| `rowCount` / `columnCount` | 行数 / 列数，默认 1000 / 26 |
| `columnWidths` | `{"A": 120, "B:D": 90}` 列宽（支持区间） |
| `rowHeights` | `{"1": 32, "2:3": 24}` 行高（1 起始，支持区间） |
| `merges` | `["A1:E1", ...]` 合并单元格 |
| `cells` | `{单元格引用: 单元格}`，如 `{"B3": {...}}` |

### cells 单元格

| 键 | 说明 |
|----|------|
| `v` | 值（数字或字符串；数字原样保留精度） |
| `f` | 公式，如 `"=SUM(B3:B4)"`（可不带 =，自动补） |
| `style` | 引用 styles 中的命名样式 |
| `inlineStyle` | 内联样式对象（键同命名样式，优先于 style） |
| `type` | `"text"` 强制文本（保留前导零，如 `"00120"`）；`"number"` 强制数值 |

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
| `border` | all / outline / top / bottom / left / right | 边框 |
| `borderColor` | `#RRGGBB` | 边框色，默认 `#999999` |

---

## 条件格式 conditionalFormats[]

每条：`{"sheet": "工作表名", "range": "B3:B10", "stopIfTrue": false, "rule": {...}}`

`rule` 按类型（`type`）：

### highlightCell（高亮单元格，最常用）

`rule = {"type": "highlightCell", "subType": <判据>, "operator": <比较符>, "value": <阈值>, "style": {内联样式，键同上表}}`

| subType | 必填字段 | 说明 |
|---------|----------|------|
| `number` | `operator` + `value` | 数值比较；operator：greaterThan / lessThan / equal / notEqual / between（value 传 `[下,上]`）/ notBetween |
| `text` | `operator` + `value?` | 文本判据；operator：containsText / notContainsText / beginsWith / endsWith / equal / notEqual / containsBlanks / notContainsBlanks |
| `formula` | `value` | 公式为真时命中，如 `"=$B2>1000"` |
| `timePeriod` | `operator` | today / yesterday / tomorrow / last7Days / thisMonth / lastMonth 等 |
| `rank` | `value` + `isBottom` + `isPercent` | 前/后 N 名 |
| `average` | `operator` | 与平均值比较 |
| `uniqueValues` / `duplicateValues` | — | 唯一值 / 重复值 |

### dataBar / colorScale / iconSet（数据条 / 色阶 / 图标）

config 按产品内核原生结构传入（`isShowValue`、`config.min/max`、`positiveColor` 等），CLI 原样透传；`range` 与 `cfId`、`stopIfTrue` 由 CLI 组装。

---

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

`sheetData` 为工作簿快照 JSON 字符串；`status`：0 未发布 / 1 已发布 / 2 已保存未发布。查询 `get --id` 得到的 `sheetData` 也可直接改后经 `edit --raw` 提交（进阶用法）。
