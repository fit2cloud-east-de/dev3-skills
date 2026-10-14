# 数据大屏（dataV）

通过 API 创建/更新 **数据大屏**（`type=dataV`）。仪表板（dashboard）本 skill 暂不实现。

## Agent 强制流程（数据集）

1. **先列数据集**：`datav.py datasets --flat`（或 `dataset.py tree`），对照用户需求选型。  
2. **优先用本次会话为该大屏新建的数据集**；没有合适的再评估是否新建。  
3. **禁止擅自删改已有数据集**。若确需改字段/计算逻辑：  
   - 说明风险：其它看板/大屏可能引用该集，修改会导致其数据变化；  
   - 自查是否冲突；有冲突则 **自己新建数据集**，不得改共用集；  
   - 须用户明确同意后才改已有集。  
4. **禁止擅自复用「非本次创建」的已有数据集**。用户明确确认「可以用某某数据集」后方可绑定。  
5. 图表保存前必须 **取数预览成功**（`preview-chart` / `apply` 内置预览）；失败则中止并修正轴/过滤/聚合。

## 工作流

1. `catalog` / `layouts` — 图表类型、装饰与**排版模板**  
2. `resolve-folder` — 在 **数据大屏树** 上定位文件夹（组织根 id 与数据源/数据集树通常不同）  
3. `datasets` + `fields --simplify` — 选型与字段  
4. 按需求拆解：选布局模板 → 选图类型、轴字段、聚合、过滤 → 填入各内容槽  
5. `plan-example --layout grid_3x4|center_v2` → 写 plan → `apply`（可先 `preview-chart`）  
6. `get --resource-table snapshot`（默认）核对；`publish --i-confirm-publish` 发布  

## 排版模板（优先使用）

默认画布 1920×1080。plan 中设 `layout`（或 `layoutTemplate`）后，未手写像素的图表按槽位自动排版；内容槽可放**任意图表 / 表格 / 指标卡**等。

| id | 名称 | 结构 |
|----|------|------|
| `grid_3x4` | 平均分布 3×4 | 顶栏大标题 + **3 行 × 4 列** 共 12 个等大内容格（`c0`…`c11`） |
| `center_v2` | 居中结构-形式二 | 顶栏大标题 + **中央主内容** `main` + 左右各 2 次要 + 主内容下方 1 次要 |

- `title` / `name`：自动生成标题槽 **富文本**（与界面一致：`render=custom`、`propValue.textValue` 含居中 HTML、`verticalAlign=center-align`）；可用 `decorations` 里 `slot:"title"` 覆盖  
- 图表 `render` 必须与界面 `getViewConfig` 一致：`rich-text` / `indicator` / `picture-group` → `custom`，其余常见图 → `antv`（错误 render 会导致组件不挂载、不可见且无法双击编辑）
- 勿用滚动文字做大标题居中：产品把对齐存在 `style.textAlign`，但滚动文字渲染不按该字段水平居中  
- `charts[].slot`：指定落入哪一格；省略则按模板 `contentSlots` 顺序填充  
- 仍可手写 `layout:{left,top,width,height}` 覆盖单格  
- 图表 **提示（tooltip）** 默认白底黑字（`color:#000000`），勿改成白字  
- 查看像素：`python datav.py layouts --id grid_3x4`

## 画布与组件

| 概念 | 说明 |
|------|------|
| 画布 | 默认 1920×1080 暗色；`canvasStyleData` 为 JSON **字符串** |
| `componentData` | 组件数组的 JSON **字符串**；大屏位置用 `style.left/top/width/height`（像素） |
| `canvasViewInfo` | **对象**：仅 `UserView` / `VQuery` 需要；key = 组件 `id` |
| 装饰 | `ScrollText` / `Picture` / `RectShape` / `CanvasBoard` / `DeDecoration` / `CanvasIcon` 等，**不**进 `canvasViewInfo` |

## 图表轴与聚合（不得出错）

| 图类型 | 轴规则 |
|--------|--------|
| bar / line / area 等 | `xAxis`=维度 `d`；`yAxis`=指标 `q` |
| pie / 环形 | `xAxis`=维度；`yAxis`=**仅 1 个**指标 |
| indicator | **仅** `yAxis`（1 个数值指标）；`xAxis` 空 |
| table-info | 列放 `xAxis`（d/q 均可）；无 yAxis |
| bar-stack 等 | 另配 `extStack` 堆叠维 |
| bar-group / line 分组 | 另配 `xAxisExt` |

- **聚合 `summary`**：写在 **指标字段** 上：`sum` / `avg` / `max` / `min` / `count` / `count_distinct` 等。  
- 文本/时间类指标默认倾向 `count`；数值默认 `sum`。用户指定优先。  
- **图表内过滤** `customFilter`：`{ "logic":"and", "items":[ { "type":"item", "fieldId", "term", "value", ... } ] }`。`term`：`eq/not_eq/lt/le/gt/ge/in/like/null/not_null/between` 等。无过滤用 `{}`。  
- **查询组件 VQuery**：条件在组件 `propValue`，运行时注入图表；结构复杂，须按产品配置核对 `checkedFields` / `checkedFieldsMap`，勿与 `customFilter` 混用错位。

## plan JSON 要点

```json
{
  "name": "销售运营大屏",
  "title": "大标题文案",
  "folderName": "目标文件夹",
  "layout": "grid_3x4",
  "datasetId": "可选默认数据集",
  "canvas": { "backgroundColor": "#020408" },
  "charts": [
    {
      "slot": "c0",
      "type": "bar",
      "title": "各省销量",
      "xAxis": ["省份"],
      "yAxis": [{ "name": "销售量", "summary": "sum" }]
    },
    {
      "slot": "main",
      "type": "map",
      "title": "主视觉（居中结构时用）"
    }
  ]
}
```

`layout: "center_v2"` 时内容槽为 `main`、`secondary_left_top` 等（见 `layouts`）。`apply` 默认整页替换；`--append` 追加。

## 主要 API

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | /de2api/dataVisualization/tree | `{ busiFlag:"dataV" }` |
| POST | /de2api/dataVisualization/saveCanvas | 新建 |
| POST | /de2api/dataVisualization/updateCanvas | 更新画布 |
| POST | /de2api/dataVisualization/findById | 详情（**编辑稿**用 `resourceTable:snapshot`；未发布时 `core` 可能为空） |
| POST | /de2api/dataVisualization/updatePublishStatus | 发布 `status=1` / 取消 `0`（需 `activeViewIds`） |
| POST | /de2api/chart/listByDQ/{datasetId}/{chartId} | 维度/指标字段 |
| POST | /de2api/chartData/getData | 图表取数预览 |

文件夹定位须在 **dataV 树**；写入范围受 `DE_ALLOWED_WRITE_SCOPE` 约束（须含大屏侧允许节点）。
