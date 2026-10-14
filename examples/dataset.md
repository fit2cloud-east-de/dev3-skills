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
