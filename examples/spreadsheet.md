# 电子表格示例

文件夹须在**电子表格树**上解析（第五棵树，组织根 id 与其它树不同）：

```bash
python spreadsheet.py resolve-folder --name "目标文件夹"
# 同名则列出候选，确认后再用 --pid
```

## 生成高质量样板（推荐起点，自动套用主题）

```bash
python spreadsheet.py template --theme business > spec.json   # 可选 finance / fresh / minimal
```

样板已含五段式版式（标题区/表头/数据区/合计/辅注）、公式、斑马纹、下拉、筛选、批注与条件格式，改内容即可用。

## 新建（主题 + 多 sheet + 公式 + 条件格式 + 验证 + 筛选 + 批注）

```json
{
  "theme": "business",
  "sheets": [
    {
      "name": "销售明细", "freeze": "A3", "tabColor": "#1F4E79",
      "columnWidths": {"A": 150, "B": 80, "C": 110, "D": 120},
      "merges": ["A1:D1"],
      "cells": {
        "A1": {"v": "2026年Q3 销售汇总", "style": "title"},
        "A2": {"v": "统计周期：2026-07-01 ~ 2026-09-30　｜　单位：元", "style": "subtitle"},
        "A3": {"v": "产品名称", "style": "headerLeft"},
        "B3": {"v": "数量", "style": "header"},
        "C3": {"v": "单价", "style": "header"},
        "D3": {"v": "金额", "style": "header"},
        "A4": {"v": "智能手表", "style": "cellText"},
        "B4": {"v": 12, "style": "qty"},
        "C4": {"v": 899, "style": "money"},
        "D4": {"f": "=B4*C4", "style": "money"},
        "A5": {"v": "无线耳机", "style": "zebraText"},
        "B5": {"v": 30, "style": "zebra"},
        "D5": {"f": "=B5*C5", "style": "zebra"},
        "A6": {"v": "合计", "style": "total"},
        "D6": {"f": "=SUM(D4:D5)", "style": "totalMoney"}
      }
    }
  ],
  "conditionalFormats": [
    {"sheet": "销售明细", "range": "D4:D5",
     "rule": {"type": "highlightCell", "subType": "number", "operator": "greaterThan",
              "value": 10000, "style": {"bg": "#FDE8E8", "color": "#C0392B", "bold": true}}}
  ],
  "validations": [
    {"sheet": "销售明细", "range": "E4:E100", "type": "list", "values": ["已结算", "待结算"],
     "promptTitle": "状态", "prompt": "从下拉选择"}
  ],
  "filters": [
    {"sheet": "销售明细", "range": "A3:E100", "columns": [{"col": "E", "values": ["已结算"]}]}
  ],
  "notes": [{"sheet": "销售明细", "cell": "D3", "text": "金额 = 数量 × 单价"}],
  "datasetTables": [
    {"sheet": "销售明细", "startCell": "A9", "datasetId": "<数据集ID>", "resultLimit": 100,
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
