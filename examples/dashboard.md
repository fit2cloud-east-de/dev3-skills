# 仪表板 CLI 示例

先 `cd scripts`，并设置 `DE_BASE_URL` / `DE_ACCESS_KEY` / `DE_SECRET_KEY` / `DE_ALLOWED_WRITE_SCOPE`（scope 须含 **仪表板树** 组织根或文件夹 id）。

## 目录与选型

```bash
python dashboard.py tree
python dashboard.py resolve-folder --name "AI专用组织"
python dashboard.py datasets --flat
python dashboard.py fields --dataset-id <DATASET_ID> --simplify
python dashboard.py catalog
python dashboard.py layouts --id grid_2x2
```

## 打印 plan 骨架

```bash
python dashboard.py plan-example --layout kpi_charts
python dashboard.py plan-example --layout grid_3x2
python dashboard.py plan-example --layout free
```

## 创建并应用

将 `plan-example` 输出保存为 `plan.json`，填入真实 `datasetId` / 字段名 / `folderName`（或 `pid`）：

```bash
python dashboard.py apply --file plan.json
python dashboard.py get --id <DASHBOARD_ID> --summary
python dashboard.py publish --id <DASHBOARD_ID> --i-confirm-publish
```

更新已有板（整页替换）：

```bash
python dashboard.py apply --id <DASHBOARD_ID> --file plan.json
```

追加组件：

```bash
python dashboard.py apply --id <DASHBOARD_ID> --file plan_append.json --append
```

## 空板

```bash
python dashboard.py create-empty --name "空白仪表板" --folder-name "AI专用组织"
```

## 手写矩阵坐标

```json
{
  "name": "自定义矩阵板",
  "folderName": "AI专用组织",
  "datasetId": "<DATASET_ID>",
  "charts": [
    {
      "type": "bar",
      "title": "柱图",
      "xAxis": ["省份"],
      "yAxis": [{"name": "销售量", "summary": "sum"}],
      "layout": { "x": 1, "y": 1, "sizeX": 36, "sizeY": 18 }
    },
    {
      "type": "pie",
      "title": "饼图",
      "xAxis": ["省份"],
      "yAxis": [{"name": "销售量", "summary": "sum"}],
      "layout": { "x": 37, "y": 1, "sizeX": 36, "sizeY": 18 }
    }
  ]
}
```

说明见 [references/dashboard.md](../references/dashboard.md)。
