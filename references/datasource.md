# DataEase 数据源类型与配置字段

`configuration` 提交时必须为 **Base64(UTF-8 JSON)**。使用本目录 CLI 的 `save` / `update` 时会自动编码；直接调 HTTP 时需自行编码。

---

## 公共请求字段（save / update / validate）

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 1–64 字符 |
| type | 是 | 下表 type 值 |
| pid | 是* | 父目录 ID。也可用 CLI `--folder-name` 在名称唯一时解析。同名/子目录同名须先确认。受 `DE_ALLOWED_WRITE_SCOPE` 约束 |

\* 新建必填父目录（id 或可唯一解析的名称）。
| nodeType | 是 | 数据源固定 `datasource` |
| action | 是 | 新建 `create`，更新 `update` |
| description | 否 | 描述 |
| configuration | 是* | Base64 JSON；folder 无 |
| syncSetting | API / ExcelRemote | 同步任务；其它 JDBC 类型省略或 null |
| enableDataFill | 否 | 是否启用数据填报 |

\* Excel 需先 `uploadFile`，见下文。

---

## 支持的类型

| type | 显示名 | 分类 | 备注 |
|------|--------|------|------|
| mysql | MySQL | OLTP | |
| mariadb | MariaDB | OLTP | |
| TiDB | TiDB | OLTP | |
| doris | Apache Doris | OLAP | |
| StarRocks | StarRocks | OLAP | |
| impala | Apache Impala | OLAP | |
| pg | PostgreSQL | OLTP | 需 schema |
| kingbase | Kingbase | OLTP | 需 schema |
| gaussdb | GaussDB | OLTP | 需 schema |
| oracle | Oracle | OLTP | 需 schema + connectionType |
| sqlServer | SQL Server | OLTP | 需 schema |
| db2 | Db2 | OLTP | 需 schema |
| mongo | Mongodb-BI | OLTP | |
| ck | ClickHouse | OLAP | 可选 SSL PEM |
| redshift | AWS Redshift | DL | 需 schema |
| es | Elasticsearch | OLAP | 使用 url，不用 host/port |
| API | API | OTHER | 使用完整 JSON 表定义 |
| Excel | 本地 Excel | LOCAL | 需 multipart 上传 |
| ExcelRemote | 远程 Excel | LOCAL | url + 可选账号 + 同步 |
| folder | 文件夹 | — | 使用 `createFolder` |

新建 / 更新请使用上表 `type`。

**插件数据源：** 若环境已安装插件，产品中可能还能看到其它数据源类型。本 skill 暂不支持对插件类型做新建或改配置；需要时请在产品中手动操作。对已存在的数据源，仍可用查询类接口查看。

---

## JDBC 类（hostName 模式）

`urlType=hostName`（默认）。

| 字段 | 必填 | 默认/说明 |
|------|------|-----------|
| host | 是 | 主机 |
| port | 是 | 端口（按目标库填写） |
| dataBase | 是 | 数据库名；oracle 对应 SID/服务名侧标识 |
| username | 建议 | 多数库连接需要 |
| password | 建议 | 多数库连接需要 |
| extraParams | 否 | 见下方默认值 |
| schema | 部分类型必填 | oracle / sqlServer / pg / kingbase / gaussdb / redshift / db2 |
| connectionType | oracle | `sid` 或 `serviceName` |
| charset / targetCharset | oracle 可选 | 如 UTF-8 |
| initialPoolSize | 是 | 默认 5 |
| minPoolSize | 是 | 默认 5 |
| maxPoolSize | 是 | 默认 100 |
| queryTimeout | 是 | 默认 30（秒） |
| useSSH | 否 | 默认 false |
| sshHost / sshPort / sshUserName | useSSH 时 | |
| sshType | useSSH 时 | `password` / `sshkey` |
| sshPassword 或 sshKey | 按 sshType | sshKey 时可有 sshKeyPassword |
| sslCA / sslCert / sslKey | 仅 ck 可选 | PEM 文本 |

### jdbcUrl 模式

`urlType=jdbcUrl`：必填 `jdbcUrl`；不再填 host / port / dataBase / extraParams / SSH。用户名、密码仍可填。

### 默认 extraParams

- mysql / TiDB / mariadb / doris / StarRocks:  
  `characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true`
- impala: `AuthMech=0`
- mongo: `rebuildschema=true&authSource=admin`
- 其它: 空字符串

### schema 获取

对需 schema 的类型：先填好主机与账号等，再调用 `POST /de2api/datasource/getSchema`，将返回值之一写入 `configuration.schema`。

---

## Elasticsearch（es）

| 字段 | 必填 | 说明 |
|------|------|------|
| url | 是 | 数据源 URL |
| username / password | 否 | |
| 连接池字段 | 是 | 同 JDBC 默认 |

不使用 urlType / host / port / SSH。

---

## API

`configuration` 为 **API 表项数组**（可含 params 表）的 Base64，不是 JDBC 对象。另需 `syncSetting`：

```json
{
  "updateType": "all_scope",
  "syncRate": "SIMPLE_CRON",
  "simpleCronValue": "1",
  "simpleCronType": "minute",
  "startTime": 0,
  "endTime": 0,
  "endLimit": "0",
  "cron": "0 0/1 * * * ? *"
}
```

单表项常用字段：`name`, `url`, `method`, `request`（headers / arguments / body / authManager / page）, `fields`, `useJsonPath`, `jsonPath`, `deTableName`。

校验单表：`POST /de2api/datasource/checkApiDatasource`。

可用 `datasource.py template --type API` 生成骨架，补全后用 `--file` 提交。

---

## Excel（本地）

1. `POST /de2api/datasource/uploadFile`（multipart：`file`, `id`, `editType`）解析 sheet  
2. 将返回结构写入 `configuration`（含 sheets / fields）后 Base64  
3. `save` / `update`

必须先上传文件，不能仅凭空 JSON 新建。

---

## ExcelRemote

configuration 对象（编码前）：

| 字段 | 必填 | 说明 |
|------|------|------|
| url | 是 | 远程文件地址 |
| userName / passwd | 否 | 调用 `loadRemoteFile` 时用户名、密码需再 Base64 一次 |
| sheets | 加载后 | 由 `loadRemoteFile` 返回填充 |

另需 `syncSetting`（同 API）。加载：`POST /de2api/datasource/loadRemoteFile`。

---

## 文件夹

`POST /de2api/datasource/createFolder`：`name`, `nodeType=folder`, `action=create`, `pid`。

---

## 查询类接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /de2api/datasource/types | 类型列表 |
| POST | /de2api/datasource/tree | body 含 `busiFlag: datasource` |
| GET | /de2api/datasource/get/{id} | 详情 |
| GET | /de2api/datasource/hidePw/{id} | 详情（隐藏密码，适合展示） |
| POST | /de2api/datasource/validate | body 同 save |
| GET | /de2api/datasource/validate/{id} | 按已存 ID 校验 |
| POST | /de2api/datasource/getSchema | |
| POST | /de2api/datasource/getTables | `{ datasourceId }` |
| POST | /de2api/datasource/checkRepeat | 是否重复连接 |
| POST | /de2api/datasource/perDelete/{id} | 是否有数据集占用 |
| POST | /de2api/datasource/delete | `{ id, rootOrgNode? }` |

---

## 勿提交的字段

不要写入：`qrtzInstance`, `dsVersion`, `createBy`, `creator`, `updateBy`, `taskStatus`, `lastSyncTime`。  
只使用本文件列出的配置字段。
