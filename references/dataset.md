# 数据集：类型、字段与接口

## 流程（单表新建）

1. `POST /de2api/datasource/getTables` — `{ datasourceId }` 取表  
2. `POST /de2api/datasetData/tableField` — 取字段  
3. 判定每个字段 **维度 `d` / 指标 `q`**（见下）  
4. 按需追加计算字段 / 分组字段 / 复制字段  
5. `POST /de2api/datasetData/previewData` — 预览无误  
6. `POST /de2api/datasetTree/create` — 保存到目标文件夹（`pid` 或唯一文件夹名）

名称未指定时可用 `{表名}_数据集`。

---

## tableField 请求

```json
{
  "datasourceId": "<数据源ID>",
  "id": "<节点临时ID>",
  "tableName": "<表名>",
  "type": "db",
  "info": "{\"table\":\"<表名>\",\"sql\":\"\"}",
  "isCross": false
}
```

Excel / 本地文件类数据源：`type` 仍常用 `db`，`tableName` 为 `getTables` 返回的表名。

---

## 维度 / 指标（groupType）

| deType | 含义 | 默认 groupType |
|--------|------|----------------|
| 0 | 文本 | d 维度 |
| 1 | 时间 | d 维度 |
| 2 | 整型数值 | q 指标 |
| 3 | 浮点数值 | q 指标 |
| 4 | 布尔 | q 指标 |
| 5 | 地理 | d 维度 |
| 7 | URL | d 维度 |

**按需求判定（优先于死板类型）：**

- **指标**：可度量、可聚合——销量、金额、次数、比率、价格等  
- **维度**：用于切片/分组——日期、省份、类型、人名、部门、状态、名称等  
- 用户明确指定时以用户为准；可用 CLI `--dq-map '{"销售额":"q","省份":"d"}'` 强制

---

## 保存体（create）要点

| 字段 | 说明 |
|------|------|
| name | 数据集名称 |
| pid | 目标文件夹 ID（须在允许写入范围内） |
| nodeType | `dataset` |
| type | `union` |
| mode | `0` 直连；`1` 同步（Excel/API 等常用 1） |
| union | 表关联树（单表一条） |
| allFields | 全部字段（含计算/分组/复制） |
| isCross | 通常 `false` |

### union 单表结构

```json
[{
  "currentDs": {
    "id": "<节点ID>",
    "datasourceId": "<数据源ID>",
    "tableName": "<表名>",
    "type": "db",
    "info": "{\"table\":\"<表名>\",\"sql\":\"\"}",
    "sqlVariableDetails": null
  },
  "currentDsFields": [ /* 仅原始字段 extField=0 */ ],
  "childrenDs": [],
  "unionToParent": { "unionType": "left", "unionFields": [] }
}]
```

### 字段 extField

| 值 | 含义 |
|----|------|
| 0 | 原始字段 |
| 2 | 计算字段或复制字段（提交时 `originName` 需 Base64） |
| 3 | 分组字段 |

**复制字段**：`extField=2`，`originName` 为 `[源字段id]`，名称默认加 `_copy`。  
**计算字段**：`extField=2`，`originName` 为表达式（可用 `{{字段显示名}}`，CLI 会换成 `[id]`）。  
**分组字段**：`extField=3`，`originName` 为源字段 id，`groupList` 为分组规则，结果为维度。

---

## 字段操作 JSON（`--ops-file` / `--ops-json`）

```json
[
  { "op": "copy", "from": "省份", "name": "省份_copy" },
  { "op": "calc", "name": "销量加一", "expression": "{{销售量}}+1", "deType": 2, "groupType": "q" },
  {
    "op": "group",
    "name": "省份分区",
    "from": "省份",
    "groupList": [{ "name": "华东", "text": ["上海", "江苏"], "minTerm": "lt", "maxTerm": "lt" }],
    "otherGroup": "其他"
  },
  { "op": "set-group-type", "field": "销售量", "groupType": "q" }
]
```

---

## 其它接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /de2api/datasetTree/tree | `{ busiFlag: "dataset" }` |
| POST | /de2api/datasetTree/get/{id} | 详情 |
| POST | /de2api/datasetTree/create | 新建 |
| POST | /de2api/datasetTree/save | 更新保存 |
| POST | /de2api/datasetData/previewData | 预览 |

文件夹定位：**必须在数据集树**上解析（`dataset.py resolve-folder`），规则同数据源（id 或唯一名称；同名须确认）。**不要**使用数据源树的组织/文件夹 id 作为 `pid`。写入范围受 `DE_ALLOWED_WRITE_SCOPE` 约束（须包含数据集侧允许节点）。

`dataset.py move`：目标若落在**虚拟组织根**（`orgRoot`）或其下、父链含虚拟节点时，部分环境 `checkMove` 会 NPE；误放资源优先**删除后按正确 pid 重建**。
