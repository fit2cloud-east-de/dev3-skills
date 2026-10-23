# 电子表格：新建、修改与发布

电子表格是与数据源 / 数据集 / 数据大屏 / 仪表板并列的**第五棵独立资源树**。表体为在线电子表格快照：多 Sheet、单元格值与公式、富文本、样式、合并、列宽行高、冻结、数据验证（下拉等）、自动筛选、批注、斜线格、条件格式、明细表（数据集绑定）。

## 能力边界（强制）

- ✅ **新建**电子表格（本文全部特性）
- ✅ **修改当前任务内创建**的电子表格：`edit` 必须加 `--session-created`，否则拒绝
- ❌ **不支持修改已存在的电子表格**（既有表格请用户在产品界面操作）
- ❌ 不提供删除命令

## 交互能力与查看态（重要）

以下能力**只在编辑态可用**，在预览态（模板/表格的预览浮层）下表格为只读，点击不会有任何效果——这是产品设计，不是配置错误：

- 数据验证下拉的**选择与写入**（能看到并点开选项，但预览态下选完不写入）
- 自动筛选的**表头筛选按钮**（应用/取消筛选）
- 查询组件的**条件选择与查询**

因此：**验证这些交互功能时必须在编辑页打开**（电子表格树中进入编辑），不要用预览浮层；向用户交付时也应说明"交互请在产品编辑态使用"。生成内容本身与查看态无关——快照里配置正确，编辑态即生效。

## 流程与视图语义

1. `spreadsheet.py resolve-folder --name "目标文件夹"`（电子表格树，勿用其它树组织根 id）
2. 编写规格 JSON（可用 `spreadsheet.py template` 生成模板）
3. **`spreadsheet.py lint --file spec.json` 预览风险**——`create` / `edit` 内置同一守卫，有 `error` 会直接拒绝写入（见 [spreadsheet_parity.md](spreadsheet_parity.md)）
4. `spreadsheet.py create --name "名称" --folder-name "目标文件夹" --file spec.json`
5. （迭代）调整规格后 `spreadsheet.py edit --id <ID> --session-created --file spec_v2.json`
6. 用户确认内容后 `spreadsheet.py publish --id <ID>`

> **生成前必读 [spreadsheet_parity.md](spreadsheet_parity.md)**：它回答「哪些写法界面上有、哪些只在快照里有」。界面无入口的状态，用户既看不到入口也改不回来，交付时必须说明。

**两个视图**：`get`（findById）返回**发布版**——未发布的新改动不在其中；`get-edit`（findEditById）返回**编辑稿**（含全部改动）。校验最近一次编辑结果请用 `get-edit`；发布后两者一致（status: 0 未发布 / 1 已发布 / 2 已保存未发布）。

**本地草稿与版本号（重要）**：编辑器打开表格时，若浏览器本地存在草稿且**草稿版本 == 服务端编辑稿版本**，会用**本地草稿覆盖服务端内容**。因此通过接口修改后，若版本号不变，用户刷新仍可能看到旧草稿。`edit` 会自动把 `version` 加一，使旧草稿失效；人工直接调 `update` 时也须提升 `version`，否则改动可能"看不到"。

---

## 规格 JSON（spec）

顶层结构：

| 键 | 类型 | 说明 |
|----|------|------|
| `theme` | 字符串 | **主题预设（推荐）**：`business` / `finance` / `fresh` / `minimal`，给出整套合规命名样式与色板，见 [spreadsheet_visual.md](spreadsheet_visual.md) |
| `styles` | `{名: 样式}` | 自定义命名样式；与主题同名则覆盖主题项 |
| `sheets` | `数组` | 工作表列表，至少 1 个；顺序即展示顺序 |
| `conditionalFormats` | `数组` | 条件格式 |
| `validations` | `数组` | 数据验证（下拉列表 / 数值范围 / 自定义公式等） |
| `filters` | `数组` | 自动筛选（每表一条：范围 + 各列条件） |
| `notes` | `数组` | 批注（纯文本） |
| `slashCells` | `数组` | 斜线格（二分/三分） |
| `datasetTables` | `数组` | 明细表：把数据集字段绑定到某起始格渲染 |
| `filterComponents` | `数组` | 查询组件：按时间（年/月/日）或文本下拉过滤明细表，至多一条（工作簿级单例） |

**默认值与界面位置**：每一项的**类型、默认值、界面入口、可达性**见 [spreadsheet_defaults.md](spreadsheet_defaults.md)（共 105 项，由 `spreadsheet.py defaults --markdown` 生成）；不确定某项默认值时用 `spreadsheet.py defaults --key <键名>` 查，不要凭印象。

**视觉与版式**：标题区 / 表头 / 数据区 / 合计行 / 辅注的五段式结构、色彩角色、字号阶梯、行分隔与对齐规则见 [spreadsheet_visual.md](spreadsheet_visual.md)。用 `theme` 即可满足大部分规范；`spreadsheet.py template --theme <名>` 直接产出合规样板。

### sheets[] 工作表

| 键 | 说明 |
|----|------|
| `name` | 工作表名（不可重复） |
| `rowCount` / `columnCount` | 行数 / 列数，默认 1000 / 26 |
| `freeze` | 冻结至某格，如 `"A2"` 冻结首行；或 `{xSplit,ySplit,startRow,startColumn}` |
| `hidden` | `true` 隐藏该工作表 |
| `tabColor` | 工作表标签颜色 `#RRGGBB` |
| `showGridlines` | `false` 隐藏网格线（⚠️ 界面无此开关，见 [spreadsheet_parity.md](spreadsheet_parity.md)） |
| `rightToLeft` | `true` 从右到左（⚠️ 界面无此开关，见 [spreadsheet_parity.md](spreadsheet_parity.md)） |
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
| `cells.type` | `"text"` 强制文本（保留前导零）；`"number"` 强制数值。⚠️ **界面无此入口，写入后不可逆**，详见 [spreadsheet_parity.md](spreadsheet_parity.md) |

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
| `list` / `listMultiple` | `values: [选项]` | 下拉菜单（单选 / 多选）。选项用 `values` 数组传入（CLI 生成合规存储格式）；如引用单元格区域，改用 `formula: "=$F$2:$F$5"`。可选 `renderMode`：`arrow`（默认，单元格显示文字 + 下拉箭头）/ `text`（仅文字）/ `chip`（彩色芯片） |
| `decimal` / `whole` | `operator` + `values` | 小数 / 整数范围；operator 同条件格式数值比较 |
| `textLength` | `operator` + `values` | 文本长度限制 |
| `date` / `time` | `operator` + `values` | 日期 / 时间范围 |
| `checkbox` | — | 复选框 |
| `custom` | `formula: "=..."` | 自定义公式校验 |
| `any` | — | 任意值（仅带提示） |

可选：`allowBlank`（默认 true）、`promptTitle`/`prompt`（输入提示）、`errorTitle`/`error`（错误提示）。

> **下拉务必保持默认 `arrow`**：产品对下拉有「芯片/箭头/文本」三种渲染方式，缺省会落到**芯片**样式——单元格会被涂成灰底芯片并跳过常规文字渲染，导致值看不清、看着像空壳。`arrow` 模式显示文字 + 下拉箭头，可读可点。

> 产品对应位置：工具栏「数据」→「规则」→「数据验证」，新建规则后条件类型选「下拉菜单」，选项来源可选「自定义」（逐个录入）或「引用数据」（引用某区域）。

## filters 自动筛选

每表一条：`{"sheet", "range": "A1:E100"}`（range 首行为表头行）。**推荐只给范围**：表头出现筛选按钮，由使用者在界面上勾选条件。

如需预置条件，加 `columns`：`{"col": "C", "values": ["是", "否"]}` 按值筛选；或 `{"col": "B", "custom": [{"val": 100, "operator": "greaterThan"}]}` 自定义条件（operator：equal / notEqual / greaterThan / greaterThanOrEqual / lessThan / lessThanOrEqual）。

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

## filterComponents 查询组件

查询组件按条件过滤**明细表**（须先在 `datasetTables` 绑定数据集）。工作簿级单例，`conditions` 支持多条件：

```json
{
  "sheet": "Sheet1", "startCell": "A1", "visible": true,
  "conditions": [
    {"name": "下单日期", "fieldId": "<日期字段ID>", "fieldName": "下单日期",
     "groupType": "d", "deType": 0, "displayType": "time", "granularity": "date"},
    {"name": "客户名称", "fieldId": "<文本字段ID>", "fieldName": "客户名称",
     "groupType": "d", "deType": 0, "displayType": "textSelect", "multiple": true}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `displayType` | `time` 时间过滤（可按年/月/日选）；`textSelect` 文本下拉；`numberRange` 数值区间等 |
| `granularity` | 时间粒度：`year` / `month` / `date`（日）/ `datetime` |
| `multiple` | 文本下拉是否多选 |
| `linkPlugin` | 可选：仅关联指定 `blockName` 的明细表；缺省关联全部明细表 |

`fieldId/fieldName/groupType/deType` 取自明细表所绑数据集的字段（`dataset.py get` 同源）。可选 `required`。高级样式（配色/按钮/布局微调）请在产品界面调整。

---

## 范围外（请用户在产品界面操作）

超链接（富文本链接）、透视表、单元格图片与浮动图片、明细表/透视表的高级样式（表头/斑马纹/汇总行等）、查询组件的高级样式。

这些能力**界面有入口**，只是本 skill 不生成——如实告诉用户在界面完成即可，不要假装能做到，也不要用近似写法硬凑。其余「界面有 / 界面无」的完整对照见 [spreadsheet_parity.md](spreadsheet_parity.md)。

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
