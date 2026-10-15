# 电子表格示例

文件夹须在**电子表格树**上解析（第五棵树，组织根 id 与其它树不同）：

```bash
python spreadsheet.py resolve-folder --name "目标文件夹"
# 同名则列出候选，确认后再用 --pid
```

## 生成规格模板（覆盖全部特性，推荐起点）

```bash
python spreadsheet.py template > spec.json
```

## 新建（多 sheet + 公式 + 样式 + 富文本 + 冻结 + 条件格式 + 验证 + 筛选 + 批注 + 斜线格）

```json
{
  "styles": {
    "title": {"bold": true, "fontSize": 14, "align": "center", "valign": "middle", "bg": "#FFF2CC", "border": "all"},
    "num2": {"numberFormat": "#,##0.00"}
  },
  "sheets": [
    {
      "name": "销售明细", "freeze": "A2", "tabColor": "#4472C4",
      "columnWidths": {"A": 120, "B:E": 100}, "merges": ["A1:E1"],
      "cells": {
        "A1": {"richText": [
          {"text": "重点", "style": {"color": "#CC0000", "bold": true}},
          {"text": "：2026年Q3 销售汇总"}
        ]},
        "A3": {"v": "智能手表"}, "B3": {"v": 128000.5, "style": "num2"},
        "A5": {"v": "合计"}, "B5": {"f": "=SUM(B3:B4)", "style": "num2"},
        "E3": {"v": "00120", "type": "text"}
      }
    },
    {"name": "说明", "hidden": true, "cells": {"A1": {"v": "内部附注页"}}}
  ],
  "conditionalFormats": [
    {"sheet": "销售明细", "range": "B3:B5",
     "rule": {"type": "highlightCell", "subType": "number", "operator": "greaterThan",
              "value": 90000, "style": {"bg": "#FFE0E0", "color": "#CC0000", "bold": true}}}
  ],
  "validations": [
    {"sheet": "销售明细", "range": "D3:D50", "type": "list", "values": ["已审核", "待审核"],
     "promptTitle": "状态", "prompt": "从下拉选择"},
    {"sheet": "销售明细", "range": "B3:B100", "type": "decimal", "operator": "greaterThanOrEqual",
     "values": [0], "errorTitle": "非法输入", "error": "销售额须 ≥ 0"}
  ],
  "filters": [
    {"sheet": "销售明细", "range": "A2:E100", "columns": [{"col": "D", "values": ["已审核"]}]}
  ],
  "notes": [{"sheet": "销售明细", "cell": "A1", "text": "表头行已冻结"}],
  "slashCells": [{"sheet": "销售明细", "cell": "F1", "type": "two"}],
  "datasetTables": [
    {"sheet": "销售明细", "startCell": "A7", "datasetId": "<数据集ID>", "resultLimit": 100,
     "blockName": "明细数据", "fields": [{"id": "<字段ID>", "name": "<字段名>",
       "dataeaseName": "<f_xxxx>", "groupType": "d", "deType": 0, "extField": 0}]}
  ],
  "filterComponents": [
    {"sheet": "销售明细", "startCell": "A1", "conditions": [
      {"name": "下单日期", "fieldId": "<日期字段ID>", "fieldName": "下单日期",
       "groupType": "d", "deType": 0, "displayType": "time", "granularity": "date"},
      {"name": "客户名称", "fieldId": "<文本字段ID>", "fieldName": "客户名称",
       "groupType": "d", "deType": 0, "displayType": "textSelect", "multiple": true}
    ]}
  ]
}
```

```bash
python spreadsheet.py create --name "季度销售表格" --folder-name "目标文件夹" --file spec.json
```

## 修改本次创建的（必须 --session-created）

调整 spec 后整表替换：

```bash
python spreadsheet.py edit --id <ID> --session-created --file spec_v2.json
# 缺少 --session-created 会被拒绝：不支持修改已存在的电子表格
```

## 查询 / 发布（注意两个视图的区别）

```bash
python spreadsheet.py get --id <ID>        # 发布视图（未发布的新改动不在此）
python spreadsheet.py get-edit --id <ID>   # 编辑稿（含未发布改动，校验编辑结果用这个）
python spreadsheet.py publish --id <ID>     # 发布，status 0/2 -> 1
```
