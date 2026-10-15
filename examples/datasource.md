# 数据源示例

## 环境

```bash
export DE_BASE_URL=https://de.example.com
export DE_ACCESS_KEY=your_access_key
export DE_SECRET_KEY=your_secret_key
export DE_ALLOWED_WRITE_SCOPE=<允许写入的组织根或文件夹ID>
cd scripts
pip install -r requirements.txt
```

```bash
python datasource.py whoami
python datasource.py resolve-folder --name "目标文件夹"
# 同名则列出候选，请用户确认后再用 --pid
```

## 查询

```bash
python datasource.py types
python datasource.py tree
python datasource.py get --id <ID> --hide-pw --decode
python datasource.py get-tables --id <ID>
python datasource.py validate --id <ID>
```

## 新建 MySQL

```bash
python datasource.py save \
  --type mysql \
  --name "demo-mysql" \
  --pid <已确认的文件夹ID> \
  --host 127.0.0.1 \
  --port 3306 \
  --dataBase demo \
  --username root \
  --password 'secret' \
  --validate-first \
  --check-repeat
```

也可用 `--folder-name "唯一文件夹名"` 代替 `--pid`。

## 新建 PostgreSQL

```bash
python datasource.py get-schema --type pg --name tmp --host 127.0.0.1 --port 5432 \
  --dataBase postgres --username postgres --password 'secret'

python datasource.py save --type pg --name "demo-pg" --pid <已确认的文件夹ID> \
  --host 127.0.0.1 --port 5432 --dataBase postgres \
  --username postgres --password 'secret' --schema public --validate-first
```

## JSON 新建 Oracle

见 `references/datasource.md` 字段说明；`--file oracle.json` 提交，`configuration` 可为对象（CLI 会 Base64）。

```bash
python datasource.py save --file oracle.json --validate-first
```

## 更新 / 删除（须确认）

```bash
python datasource.py get --id <ID> --hide-pw --decode
python datasource.py update --i-confirm-update --id <ID> --file oracle.json --validate-first
```

删除数据源为最严档：自动血缘分析并列出引用，**禁止自动删除**，仅当用户完整输入口令后放行：

```bash
python datasource.py delete --id <ID>
# 会先列出下游数据集/看板并要求口令，用户确认后：
python datasource.py delete --id <ID> \
  --confirm-delete "我确认删除此数据源，并已知风险、不会影响业务"
```

## 文件夹

```bash
python datasource.py create-folder --name "项目A" --pid <父文件夹ID>
# 或
python datasource.py create-folder --name "项目A" --folder-name "唯一父目录名"
```

## 本地 Excel

```bash
# 1) 上传并生成 save 载荷
python datasource.py upload-excel --file 报表.xlsx --name "销售报表" --out excel_payload.json
# 2) 保存为数据源（目标文件夹须在数据源树解析）
python datasource.py save --file excel_payload.json --folder-name "目标文件夹"
# 3) 自测：取表
python datasource.py get-tables --id <新建数据源ID>
```
