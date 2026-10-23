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
4. 选布局 → 填图种/轴/聚合 → 需要时补 `config`（图表样式）与 `canvas`（全局设置）  
5. `plan-example` → 写 plan → **`lint-plan` 自检** → `apply`  
6. 需要联动/跳转时随 plan 写 `linkage` / `jump`，或用子命令在图表保存后维护  
7. `get --summary` 核对；确认后 `publish --i-confirm-publish`

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

## 全局默认配置（面板级）

与数据大屏同一份 `canvasStyleData` 结构，默认值走**亮色**。plan 里写 `canvas`，支持点号路径：

```json
{
  "canvas": {
    "backgroundColor": "#f5f6f7",
    "dashboard.gapSize": 8,
    "dashboard.resultCount": 2000,
    "component.chartTitle.color": "#1f2329",
    "component.chartTitle.fontSize": 14,
    "component.chartCommonStyle.backgroundColor": "rgba(255,255,255,1)",
    "component.filterStyle.labelColor": "#1f2329"
  }
}
```

仪表板与数据大屏默认值不同、需要特别留意的项：

| 配置项 | 仪表板默认 | 数据大屏默认 | 说明 |
|--------|------------|--------------|------|
| `themeId` / `color` | `10001` / `#000000` | `10002` / `#fff` | 亮色 / 暗色主题 |
| `backgroundColor` | `#f5f6f7` | `#020408` | 画布底色 |
| `dashboard.themeColor` | `light` | `dark` | 面板明暗 |
| `scale` | 60 | 100 | 仪表板按缩放比保存，大屏按实际尺寸 |
| `component.chartTitle.color` | `#000000` | `#ffffff` | 统一标题色 |
| `component.chartColor.basicStyle.colors` | 面板统一配色（`#1E90FF` 起） | 无（走图表自身配色） | 仪表板才有面板级配色 |
| `component.filterStyle.*` | 亮色（`#1f2329` / `#FFFFFF`） | 暗色（`#ffffff` / `#131C42`） | 查询组件风格 |

全量 100+ 项与逐项默认值见 [panel_defaults.md](panel_defaults.md)，或：

```bash
python dashboard.py defaults --group canvas          # 全部面板级配置
python dashboard.py defaults --key dashboard.gapSize # 单项
```

## 图表配置

与数据大屏同一套 `charts[].config` 友好键，落在 `customAttr` / `customStyle` / `senior` 三个容器；差别只是**亮色默认值**（标签/轴/图例为 `#333333` 系，指标卡值 `#0C296E`，指标卡名 `#646A73`，提示框底色 `#5A5C62`）。

```json
{
  "type": "bar",
  "title": "分省销量",
  "xAxis": ["省份"],
  "yAxis": [{ "name": "销售量", "summary": "sum" }],
  "config": { "label.show": true, "legend.vPosition": "top", "xAxis.color": "#333333" }
}
```

- 脚本在建图后会自动套用亮色主题（`apply_light_view_theme`），`config` 在其后再覆盖
- 键名写错会立即报错并给出近似项；清单：`python dashboard.py defaults --group chart`
- 需要原样透传产品字段时用 `charts[].extraView`

## 联动与跳转

接口与数据大屏**完全相同**，只是 `dvId` 换成仪表板 id、`busiFlag=dashboard`。详细语义（运行时生效条件、字段可选项、占位符、常见坑）见 [datav.md](datav.md) 的「图表联动」「图表跳转」两节。

```json
{
  "linkage": [{ "source": "分省销量", "targets": ["占比"] }],
  "jump": [
    { "source": "分省销量", "field": "省份", "linkType": "outer",
      "content": "https://bi.example.com/region?p=[省份]" }
  ]
}
```

```bash
python dashboard.py linkage list   --id <ID>
python dashboard.py linkage set    --id <ID> --source "分省销量" --target "占比"
python dashboard.py jump fields    --id <ID> --source "分省销量"
python dashboard.py jump set       --id <ID> --file jump.json
python dashboard.py jump active    --id <ID> --source "分省销量" [--off]
```

## 保存前自检

```bash
python dashboard.py lint-plan --file plan.json
```

`apply` 内置同样的自检，有 error 直接阻断写入。矩阵越界（`x+sizeX-1>72` / `y+sizeY-1>36`）、标题重名、图种轴放错都会被指出；确认强行写入加 `--allow-lint-errors`。

`config` 键名写错（如 `label.shw`）会被拦下并给近似项；把 `jump`/`linkage` 写在 `charts[]` 里不会生效，自检会给警告（应写在 plan 顶层并给 `source`）。

## CLI 速查

```bash
cd scripts
python dashboard.py catalog
python dashboard.py layouts --id kpi_charts
python dashboard.py resolve-folder --name "销售分析"
python dashboard.py defaults --group canvas
python dashboard.py lint-plan --file plan.json
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
  "folderName": "销售分析",
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
