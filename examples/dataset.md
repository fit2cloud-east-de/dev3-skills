# 数据集示例

文件夹须在**数据集树**上解析（与数据源组织根 id 通常不同）：

```bash
python dataset.py resolve-folder --name "目标文件夹"
# 同名则列出候选，确认后再用 --pid
```

## 单表新建

```bash
python dataset.py tables --datasource-id <DS_ID>
python dataset.py classify --datasource-id <DS_ID> --table <表名>
python dataset.py fields --datasource-id <DS_ID> --table <表名> --infer-dq
python dataset.py preview --datasource-id <DS_ID> --table <表名>

python dataset.py create \
  --datasource-id <DS_ID> \
  --table <表名> \
  --folder-name "目标文件夹" \
  --name "业务分析集" \
  --dq-map '{"销售量":"q","省份":"d","统计日期":"d"}' \
  --ops-json '[{"op":"copy","from":"省份"},{"op":"calc","name":"销量加一","expression":"{{销售量}}+1","deType":2,"groupType":"q"}]'
```

## 字段操作 ops.json

```json
[
  { "op": "copy", "from": "省份", "name": "省份_copy" },
  { "op": "calc", "name": "销量加一", "expression": "{{销售量}}+1", "deType": 2, "groupType": "q" },
  {
    "op": "group",
    "name": "区域",
    "from": "省份",
    "groupList": [{ "name": "华东", "text": ["上海", "江苏"], "minTerm": "lt", "maxTerm": "lt" }],
    "otherGroup": "其他"
  },
  { "op": "set-group-type", "field": "销售量", "groupType": "q" }
]
```

```bash
python dataset.py create --datasource-id <DS_ID> --table <表名> \
  --pid <文件夹ID> --name "带计算字段的数据集" --ops-file ops.json
```

## 查询 / 移动

```bash
python dataset.py tree
python dataset.py get --id <数据集ID>
python dataset.py move --id <数据集ID> --folder-name "目标文件夹"
```

## 预览已保存数据集

```bash
python dataset.py preview --id <数据集ID>
```

## 血缘分析（编辑/删除已有资源前）

```bash
python relation.py get --kind dataset --id <数据集ID> --brief
# summary.hasVisualUsage=true 表示有仪表板/大屏引用，改动会导致其中图表不可用
```

## 编辑已保存数据集（自动血缘分析 + 分级确认）

```bash
python dataset.py get --id <数据集ID> > dataset_detail.json   # 导出详情，修改后提交

# 情形1：被看板引用 —— 须由用户输入「确认修改」四字
python dataset.py edit --id <数据集ID> --file dataset_detail.json --confirm-modify 确认修改

# 情形2：无下游引用 —— 普通确认
python dataset.py edit --id <数据集ID> --name "新名称" --yes

# 情形3：当前任务新建且无外部操作 —— 免提示
python dataset.py edit --id <数据集ID> --ops-json '[{"op":"calc","name":"销量加一","expression":"{{销售量}}+1","deType":2,"groupType":"q"}]' --session-created
```

## 删除数据集（自动血缘分析 + 分级确认）

```bash
python dataset.py delete --id <数据集ID>
# 被看板引用时，须用户确认后：
python dataset.py delete --id <数据集ID> --confirm-modify 确认删除
# 无下游引用时：
python dataset.py delete --id <数据集ID> --yes
```
