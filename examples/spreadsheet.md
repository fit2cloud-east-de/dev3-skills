# 电子表格示例

文件夹须在**电子表格树**上解析（第五棵树，组织根 id 与其它树不同）：

```bash
python spreadsheet.py resolve-folder --name "目标文件夹"
# 同名则列出候选，确认后再用 --pid
```

## 生成规格模板（推荐起点）

```bash
python spreadsheet.py template > spec.json
```

## 新建（多 sheet + 公式 + 样式 + 条件格式）

```json
{
  "styles": {
    "title": {"bold": true, "fontSize": 14, "align": "center", "valign": "middle", "bg": "#FFF2CC", "border": "all"},
    "num2": {"numberFormat": "#,##0.00"}
  },
  "sheets": [
    {
      "name": "销售明细",
      "columnWidths": {"A": 120, "B:E": 100},
      "merges": ["A1:E1"],
      "cells": {
        "A1": {"v": "2026年Q3 销售汇总", "style": "title"},
        "A3": {"v": "智能手表"}, "B3": {"v": 128000.5, "style": "num2"},
        "A5": {"v": "合计"}, "B5": {"f": "=SUM(B3:B4)", "style": "num2"},
        "E3": {"v": "00120", "type": "text"}
      }
    },
    {"name": "说明", "cells": {"A1": {"v": "附注页"}}}
  ],
  "conditionalFormats": [
    {
      "sheet": "销售明细",
      "range": "B3:B5",
      "rule": {
        "type": "highlightCell", "subType": "number",
        "operator": "greaterThan", "value": 90000,
        "style": {"bg": "#FFE0E0", "color": "#CC0000", "bold": true}
      }
    }
  ]
}
```

```bash
python spreadsheet.py create --name "季度销售表格" --folder-name "目标文件夹" --file spec.json
```

## 修改本次创建的（必须 --session-created）

调整 spec 后整表替换（如 B5 公式改为含新行）：

```bash
python spreadsheet.py edit --id <ID> --session-created --file spec_v2.json
# 缺少 --session-created 会被拒绝：不支持修改已存在的电子表格
```

## 查询 / 发布

```bash
python spreadsheet.py get --id <ID>        # 发布视图
python spreadsheet.py get-edit --id <ID>   # 编辑稿（含未发布改动）
python spreadsheet.py publish --id <ID>     # 发布，status 0 -> 1
```
