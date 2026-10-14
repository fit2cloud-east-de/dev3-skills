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

1. `catalog` — 当前支持的图表类型与装饰组件  
2. `resolve-folder` — 在 **数据大屏树** 上定位文件夹（组织根 id 与数据源/数据集树通常不同）  
3. `datasets` + `fields --simplify` — 选型与字段  
4. 按需求拆解：选图类型、轴字段、聚合、过滤、布局与点缀  
5. `plan-example` 作模板 → 写 plan JSON → `apply`（可先 `preview-chart`）  
6. `get --resource-table snapshot`（默认）核对编辑稿；`publish --i-confirm-publish` 同步到正式预览（`core`）

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
  "folderName": "目标文件夹",
  "datasetId": "可选默认数据集",
  "canvas": { "backgroundColor": "#020408" },
  "decorations": [
    { "kind": "ScrollText", "text": "标题", "layout": { "left": 60, "top": 24, "width": 800, "height": 64 } }
  ],
  "charts": [
    {
      "type": "bar",
      "title": "各省销量",
      "datasetId": "<ID>",
      "xAxis": ["省份"],
      "yAxis": [{ "name": "销售量", "summary": "sum" }],
      "layout": { "left": 40, "top": 120, "width": 900, "height": 400 },
      "customFilter": {}
    }
  ]
}
```

`apply` 默认整页替换组件；`--append` 在已有大屏上追加。

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
