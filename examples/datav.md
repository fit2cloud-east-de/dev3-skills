# 数据大屏示例

```bash
cd scripts
export DE_BASE_URL=... DE_ACCESS_KEY=... DE_SECRET_KEY=...
export DE_ALLOWED_WRITE_SCOPE=<数据源组织根>,<数据集组织根>,<大屏组织根>
```

## 选型与字段

```bash
python datav.py catalog
python datav.py datasets --flat
python datav.py fields --dataset-id <DATASET_ID> --simplify
python datav.py resolve-folder --name "目标文件夹"
```

## 单图预览（保存前）

```bash
python datav.py preview-chart \
  --dataset-id <DATASET_ID> --type bar --title "各省销售量" \
  --x-axis '["省份"]' \
  --y-axis '[{"name":"销售量","summary":"sum"}]'
```

## 一键按 plan 新建

```bash
python datav.py plan-example > /tmp/plan.json
# 编辑 plan：folderName、datasetId、字段名、布局
python datav.py apply --file /tmp/plan.json
python datav.py get --id <返回的大屏ID> --summary
# 未发布时请看 snapshot（get 默认）；发布到正式预览：
python datav.py publish --id <DV_ID> --i-confirm-publish
```


## 空屏 + 追加

```bash
python datav.py create-empty --name "联调大屏" --folder-name "目标文件夹"
python datav.py apply --id <DV_ID> --file plan_charts.json --append
```

## 数据集规则提醒

- 未获用户确认，不要绑定「别人已经建好」的数据集。  
- 不要改共用数据集；有冲突就新建。  
- 需要改已有集时，先讲清「其它看板可能一起变」的风险并取得同意。
