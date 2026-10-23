# 数据大屏示例

```bash
cd scripts
export DE_BASE_URL=... DE_ACCESS_KEY=... DE_SECRET_KEY=...
export DE_ALLOWED_WRITE_SCOPE=<数据源组织根>,<数据集组织根>,<大屏组织根>
```

## 选型、布局与字段

```bash
python datav.py catalog
python datav.py layouts
python datav.py layouts --id center_v2
python datav.py datasets --flat
python datav.py fields --dataset-id <DATASET_ID> --simplify
python datav.py resolve-folder --name "目标文件夹"
```

布局模板：`grid_3x4`（平均分布 3×4）、`center_v2`（居中结构-形式二）。内容槽可放任意图表。

**美化示范（居中 + 底图/外框图，提示词配方）：** 见 [datav_showcase_center_beautify.md](datav_showcase_center_beautify.md)（含效果参考图）。运行时生成的美化素材放用户工作区；文档参考图在 `assets/`。

## 单图预览（保存前）

```bash
python datav.py preview-chart \
  --dataset-id <DATASET_ID> --type bar --title "各省销售量" \
  --x-axis '["省份"]' \
  --y-axis '[{"name":"销售量","summary":"sum"}]'
```

## 一键按 plan 新建（推荐带布局模板）

```bash
python datav.py plan-example --layout grid_3x4 > plan.json
# 或：python datav.py plan-example --layout center_v2 > plan.json
# 编辑：folderName、datasetId、各槽 type/轴字段；可不写像素
python datav.py apply --file plan.json
python datav.py get --id <返回的大屏ID> --summary
python datav.py publish --id <DV_ID> --i-confirm-publish
```


## 空屏 + 追加

```bash
python datav.py create-empty --name "示例大屏" --folder-name "目标文件夹"
python datav.py apply --id <DV_ID> --file plan_charts.json --append
```

## 图片 / 视频组件

在 plan 的 `decorations` 中声明（字段与界面媒体栏保存一致）：

```json
{
  "name": "媒体大屏示例",
  "folderName": "目标文件夹",
  "layout": "grid_3x4",
  "datasetId": "<DATASET_ID>",
  "charts": [],
  "decorations": [
    {
      "kind": "Picture",
      "url": "https://example.com/banner.png",
      "adaptation": "adaptation",
      "layout": { "left": 40, "top": 900, "width": 400, "height": 140 }
    },
    {
      "kind": "DeVideo",
      "url": "https://example.com/demo.mp4",
      "autoplay": true,
      "loop": true,
      "muted": true,
      "layout": { "left": 1400, "top": 780, "width": 480, "height": 270 }
    }
  ]
}
```

- 图片 → `propValue.url`；视频 → `videoLinks.web.src`（不要把视频地址写进 `propValue`）  
- `python datav.py catalog` 可查看 `Picture` / `DeVideo` 说明  


## 数据集规则提醒

- 未获用户确认，不要绑定「别人已经建好」的数据集。  
- 不要改共用数据集；有冲突就新建。  
- 需要改已有集时，先讲清「其它看板可能一起变」的风险并取得同意。
