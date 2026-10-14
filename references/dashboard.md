# 仪表板（dashboard）

通过 API 创建/更新 **仪表板**（`type=dashboard`，`busiFlag=dashboard`）。与数据大屏共用图表取数与数据集纪律，但 **资源树、布局坐标系、主题** 不同。

## 与 dataV 的关键差异

| 项 | 仪表板 | 数据大屏 |
|----|--------|----------|
| type / busiFlag | `dashboard` | `dataV` |
| 资源树 | 独立，组织根 id 通常不同 | 独立 |
| 定位 | 矩阵 `x/y/sizeX/sizeY`（72×36，1-based） | 像素 `style.left/top/width/height` |
| 主题 | 亮色 `#f5f6f7`，白卡片 | 暗色大屏 |
| 发布 type | `dashboard` | `dataV` |

**禁止**把大屏文件夹 id 当作仪表板 `pid`，反之亦然。写 scope 须包含 **仪表板树** 允许节点。

## Agent 强制流程（数据集）

与 [datav.md](datav.md) 相同：先选型 → 禁止擅自删改/复用他人数据集 → 保存前取数预览必须成功。

## 工作流

1. `catalog` / `layouts` — 图表与**矩阵布局模板**  
2. `resolve-folder` — 在 **仪表板树** 定位文件夹  
3. `datasets` + `fields --simplify` — 选型与字段  
4. 选布局 → 填图种/轴/聚合 → `plan-example` → 写 plan → `apply`  
5. `get --summary` 核对；确认后 `publish --i-confirm-publish`

## 矩阵布局模板

画布参考 1920×1080；**真实位置以矩阵为准**（编辑器打开后按容器重算像素）。plan 设 `layout` 后，未手写矩阵坐标的项按槽位填充。

| id | 名称 | 结构 |
|----|------|------|
| `grid_2x2` | 平均分布 2×2 | 顶栏标题 + 4 个等大内容格 |
| `grid_3x2` | 平均分布 3×2 | 顶栏标题 + 6 格（3 列 × 2 行） |
| `kpi_charts` | 指标卡 + 双图 | 顶栏 + 一行 4 指标（`k0`…`k3`）+ 底栏左右大图（`c0`/`c1`） |

- 标题槽自动生成 **富文本**（`render=custom`、居中 `textValue`、亮色字）  
- 手写覆盖：`layout: { "x": 1, "y": 5, "sizeX": 36, "sizeY": 16 }`  
- 查看槽位：`python dashboard.py layouts --id grid_2x2`

## 画布与组件

| 概念 | 说明 |
|------|------|
| 画布 | `DEFAULT_CANVAS_STYLE_DATA_LIGHT`；`canvasStyleData` 为 JSON **字符串** |
| `componentData` | 组件数组 JSON **字符串**；须含矩阵 `x/y/sizeX/sizeY` |
| `canvasViewInfo` | 对象；`UserView` / `VQuery` 的 key = 组件 `id` |
| 组件背景 | 默认白卡片 `commonBackground`（`COMMON_COMPONENT_BACKGROUND_LIGHT`） |
| 图表配色 | 亮色轴/图例/标题；可用 `extraView` 微调 |

## CLI 速查

```bash
cd scripts
python dashboard.py catalog
python dashboard.py layouts --id kpi_charts
python dashboard.py resolve-folder --name "AI专用组织"
python dashboard.py apply --file plan.json
python dashboard.py get --id <ID> --summary
python dashboard.py publish --id <ID> --i-confirm-publish
```

也可：`datasource.py resolve-folder --kind dashboard --name ...`

## Plan 最小示例

```json
{
  "name": "经营概览",
  "title": "经营概览",
  "folderName": "AI专用组织",
  "layout": "kpi_charts",
  "datasetId": "<DATASET_ID>",
  "charts": [
    { "slot": "k0", "type": "indicator", "title": "销量合计", "yAxis": [{"name": "销售量", "summary": "sum"}] },
    { "slot": "c0", "type": "bar", "title": "分省销量", "xAxis": ["省份"], "yAxis": [{"name": "销售量", "summary": "sum"}] },
    { "slot": "c1", "type": "pie", "title": "占比", "xAxis": ["省份"], "yAxis": [{"name": "销售量", "summary": "sum"}] }
  ]
}
```

完整命令见 [examples/dashboard.md](../examples/dashboard.md)。
