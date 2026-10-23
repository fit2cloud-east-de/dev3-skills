---
name: dev3-skills
description: >-
  DataEase V3 agent skills via Python API Key for WorkBuddy, Cursor, Codex,
  Claude Code and similar agents. Manages datasource connections, dataset
  creation (tables, fields, preview, calc/group/copy, dimension vs metric), and
  dataV big-screen and dashboard creation (chart catalog, layout, decorations
  including Picture/DeVideo, matrix layouts for dashboards, filters, aggregation).
  Auto-detects local Python3/conda and may install deps only after user confirmation.
  Use when the user mentions DataEase 数据源/数据集/数据大屏/仪表板/电子表格, datasource,
  dataset, dataV, dashboard, spreadsheet, 新建数据源, 新建数据集, 计算字段, 维度指标, 大屏,
  可视化大屏, 看板, 图表排版, 血缘分析, 关联分析, 编辑数据集, 删除数据集, 在线表格,
  单元格公式, 条件格式. Data storytelling is not implemented yet.
---

# DataEase V3 Skills

通过 **Python3 + API Key** 操作 DataEase 3.x。适用于 **WorkBuddy、Cursor、Codex、Claude Code** 等 Agent。脚本在 `scripts/`（先 `cd scripts`）。

**已实现：** 数据源；数据集新建；**数据大屏 dataV**；**仪表板 dashboard**；**电子表格 spreadsheet**  
**未实现：** 数据故事

> **连接制（第一步）：** 任何任务都先确认是否有可用的 DataEase V3 连接配置（部署地址 / Access Key / Secret Key）；**没有就先向用户索取**，拿到并验证连通前不做任何业务操作。详见下方规则 0。

按需阅读（勿一次全读）：

| 场景 | 先读 |
|------|------|
| **连接配置（连接制）/ 环境 / Python 检测 / 认证 / 文件夹 / 风险话术** | [references/common.md](references/common.md) |
| 数据源类型与字段、API | [references/datasource.md](references/datasource.md) |
| 数据集流程、字段操作、编辑/删除与血缘 | [references/dataset.md](references/dataset.md) |
| 数据大屏流程、轴/聚合/过滤、数据集复用规则 | [references/datav.md](references/datav.md) |
| 大屏构图 / 配色 / 组件一致性 | [references/datav_visual.md](references/datav_visual.md) |
| 仪表板流程、矩阵布局、与 dataV 差异 | [references/dashboard.md](references/dashboard.md) |
| 电子表格新建/修改/发布、规格与条件格式 | [references/spreadsheet.md](references/spreadsheet.md) |
| **电子表格界面可达性（哪些界面上有 / 没有）** | [references/spreadsheet_parity.md](references/spreadsheet_parity.md) |
| **电子表格各项默认值全表（105 项）** | [references/spreadsheet_defaults.md](references/spreadsheet_defaults.md)，或 `spreadsheet.py defaults` |
| 电子表格视觉规范（配色/层级/行分隔/对齐） | [references/spreadsheet_visual.md](references/spreadsheet_visual.md) |
| 可复制命令 | [examples/datasource.md](examples/datasource.md)、[examples/dataset.md](examples/dataset.md)、[examples/datav.md](examples/datav.md)、[examples/dashboard.md](examples/dashboard.md)、[examples/spreadsheet.md](examples/spreadsheet.md) |
| 大屏美化示范（居中+底图提示词） | [examples/datav_showcase_center_beautify.md](examples/datav_showcase_center_beautify.md)（效果参考见 `assets/`；运行时生成图放用户工作区） |
| 对外说明 | [README.md](README.md) |

## 强制规则

0. **连接制：第一步就是向用户要连接配置**（详见 [references/common.md](references/common.md)）。本 skill 一切操作都依赖用户的 DataEase V3 连接信息，顺序固定为**先连接、后业务**：
   - **启动动作**：接到任何任务，先确认本地是否已有可用配置 —— `cd scripts && python de_setup.py check`（或 `show` 查看）。
   - **没有配置 → 立刻向用户索取**「部署地址 / Access Key / Secret Key」，这是这一步唯一要做的事：
     ```text
     开始前需要你的 DataEase V3 连接信息（三项缺一不可）：
       1) 部署地址：如 https://de.example.com
       2) Access Key
       3) Secret Key
     可在 DataEase 的「API Key 管理」中创建（Secret Key 仅创建时可见，请一并复制）。
     ```
   - **索取优先于一切**：在拿到这三项并验证连通之前，**不谈需求、不出方案、不做任何业务调用**——缺连接时后续动作都没有意义。
   - **拿到后**保存并验证，再继续业务：
     ```bash
     cd scripts
     python de_setup.py save --base-url <地址> --access-key <AK> --secret-key <SK>
     python de_setup.py check     # 验证连通性 + 自动发现五棵树组织根 + 建议写入范围
     ```
   - **用户暂不提供**：如实说明"没有连接信息无法进行任何操作"，并再次请其提供；**不得臆造、不得跳过、不得拿示例/假地址去试探**。
   - 密钥只存本地（默认 `~/.dataease-de3/config.json`，类 Unix 下收紧为 0600），**不得写入 skill 目录或任何仓库**，向用户回显时一律脱敏。
1. **首次跑脚本前做 Python 环境检测**（详见 [references/common.md](references/common.md)）：查找 `python3` / `python` / Conda 环境（≥3.9）及 `requirements.txt` 依赖。缺失时可提议自动安装，但必须向用户说明将执行的命令与影响，**获得明确确认后再安装**；禁止静默安装。  
2. **配置以对应 reference 为准**；不要传入未列出的 type / 字段 / 图表类型。  
3. **插件数据源**：产品可能可见；本 skill 暂不支持其新建/改配置（查询仍可用）。  
4. **文件夹用 id 或唯一名称**；同名（含子目录）必须列出候选并请用户确认。数据源 / 数据集 / **数据大屏** / **仪表板** / **电子表格** 是五棵独立树，组织根 id 通常不同，勿混用。  
5. **组织写入边界**：即使 Key 能访问其它组织，也不得在用户未允许的范围内增删改；推荐 `DE_ALLOWED_WRITE_SCOPE`（写大屏/仪表板时须含对应树允许节点）。  
6. **Admin**：`whoami` 若账号为 `admin`，须先展示下方警告；建议改用数据分析师角色并先备份。  
7. **删/改**：先提醒备份 → 说明风险与目标 → 用户明确确认后再执行（CLI 需确认开关）。**数据源删除为最严档：禁止自动删除**，须先列出其血缘引用，且**仅当用户完整输入口令「我确认删除此数据源，并已知风险、不会影响业务」**方可执行（`datasource.py delete --confirm-delete <完整口令>`），否则一律拒绝。    
8. **数据集维度/指标**：按业务判定（可度量聚合 → 指标 `q`；切片分组 → 维度 `d`）；歧义先问。  
9. **数据大屏 / 仪表板 · 数据集纪律**（详见 [references/datav.md](references/datav.md)、[references/dashboard.md](references/dashboard.md)）：  
   - 先 `datasets` 选型；无合适则按需求评估新建，**禁止随意删改已有数据集**；  
   - **未获用户明确确认，禁止复用非本次创建的已有数据集**；  
   - 若提议修改已有集：必须说明「其它看板/大屏可能引用、数据会跟着变」的风险，自查冲突，冲突则自建新集；  
   - 图表轴、聚合 `summary`、`customFilter`、布局必须与 `catalog`/字段清单一致；**预览取数失败不得保存**；  
   - **大屏视觉**：构图层级、淡彩/渐变、外框色系统一，见 [references/datav_visual.md](references/datav_visual.md)；  
   - **仪表板**：亮色矩阵布局（`x/y/sizeX/sizeY`），勿用大屏像素坐标或暗色大屏主题。  
10. **编辑/删除已有资源前必须血缘分析**（详见 [references/common.md](references/common.md)）：改动非本任务创建的数据集等资源前，先查下游引用（`relation.py get`；`dataset.py edit/delete` 已内置强制执行）。**有仪表板/数据大屏引用**：须向用户展示引用清单与风险（相关图表将不可用），**用户输入「确认修改」四字**后方可继续（`--confirm-modify 确认修改`），否则拒绝；**无下游引用**：仍须用户确认（`--yes`）；**当前任务新建且无外部操作**：可免提示继续（`--session-created`，仅限 Agent 能确认时）。
11. 展示详情优先藏密码；JDBC 建议先 `validate`，需 schema 的类型先 `get-schema`。
12. **电子表格边界**（详见 [references/spreadsheet.md](references/spreadsheet.md)、[references/spreadsheet_parity.md](references/spreadsheet_parity.md)）：支持新建与发布；**仅可修改当前任务内创建的电子表格**（`edit` 须 `--session-created`，否则拒绝）；**不支持修改已存在的电子表格**、不提供删除。规格（sheet / 单元格 / 公式 / 样式 / 条件格式）以 reference 为准，勿凭空编造字段。**视觉与版式必须遵循 [references/spreadsheet_visual.md](references/spreadsheet_visual.md)**：默认套用 `theme` 预设，按五段式组织（标题区/表头/数据区/合计/辅注），一套色系、统一字号阶梯与数字对齐。**`create` / `edit` 已内置自检守卫**：规格里若出现界面不会产生的状态（合并区残留值、重叠合并等）会**直接拒绝写入**；写入前可用 `spreadsheet.py lint --file <spec>` 预览全部 `error` / `warn`；确需绕过加 `--allow-lint-errors`（不推荐）。对「界面无入口」的写法（强制值类型、从右到左、关闭网格线等）须按 [spreadsheet_parity.md](references/spreadsheet_parity.md) 向用户说明「以后只能在 skill 里改」。**任何字段的默认值不确定时，先 `spreadsheet.py defaults --key <键名>` 查询，不要凭印象填**（全量表见 [spreadsheet_defaults.md](references/spreadsheet_defaults.md)）。

## 【ADMIN 警告】（原样展示）

```text
⚠️⚠️⚠️ 高风险：当前为 admin 账号 ⚠️⚠️⚠️
admin 权限过大，误操作可能影响全站数据与配置。
强烈建议：改用「数据分析师」等业务角色账号执行本 skill 操作。
操作前请务必做好备份（数据源/相关数据集与仪表板）。
确认已知晓风险并仍要继续后，再进行新建/更新/删除。
```

## 工作流提纲

**连接（永远的第一步）：** 先查本地配置（`de_setup.py check` / `show`）；**没有就首先向用户索取「部署地址 / Access Key / Secret Key」**——在拿到并验证连通之前，不进入需求讨论与任何业务步骤 → `de_setup.py save` 保存 → 检测 Python / Conda →（缺依赖则说明并确认后安装）→ `de_setup.py check` 验证连通性并获取五棵树组织根与写入范围 → `whoami`。  

**数据源：** 确认文件夹 → 查/建/校验 → 更新删除须备份+确认；**删除须先列血缘引用，且用户完整输入口令「我确认删除此数据源，并已知风险、不会影响业务」**，禁止自动删除。    

**数据集：** 确认数据源与文件夹 → `tables` → `fields`/`classify` →（可选 ops）→ `preview` → `create`；**编辑/删除已有集：先血缘分析（内置），按分级确认（确认修改 / --yes / --session-created）执行**。  

**数据大屏：** 理解需求 → `datasets`/`fields`（遵守复用规则）→ `catalog`/`layouts` 选图与排版 → 按 [datav_visual.md](references/datav_visual.md) 定主视觉/色板/外框 → 写 plan → `preview-chart` 或 `apply` → `get` → 确认后 `publish`。见 [references/datav.md](references/datav.md)、[examples/datav.md](examples/datav.md)。

**仪表板：** 理解需求 → 在 **仪表板树** `resolve-folder` → `datasets`/`fields` → `catalog`/`layouts`（矩阵模板）→ 写 plan → `apply` → `get` → 确认后 `publish`。见 [references/dashboard.md](references/dashboard.md)、[examples/dashboard.md](examples/dashboard.md)。  

**电子表格：** 在**电子表格树** `resolve-folder` → `template --theme <名>` 取样板并按需求写规格（sheet / 公式 / 样式 / 条件格式 / 明细表 / 查询组件）→ `lint` 预览风险（`create`/`edit` 内置同一守卫，有 error 会拒绝写入）→ `create` →（迭代 `edit --session-created`）→ 用户确认后 `publish`；**版式遵循 [references/spreadsheet_visual.md](references/spreadsheet_visual.md)**，**界面可达性遵循 [references/spreadsheet_parity.md](references/spreadsheet_parity.md)**。见 [references/spreadsheet.md](references/spreadsheet.md)、[examples/spreadsheet.md](examples/spreadsheet.md)。

## 范围外

数据故事；插件数据源新建/改配置；无确认的删改与数据集复用；未经完整口令的数据源删除；修改已存在的电子表格（仅可改本任务所建）；未授权组织/文件夹内的写入；未经用户确认的 Python/依赖安装；地图等强依赖地理资源配置的复杂项须用户提供必要配置后再做。
