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
python datasource.py delete --id <ID> --i-confirm-delete
```

## 文件夹

```bash
python datasource.py create-folder --name "项目A" --pid <父文件夹ID>
# 或
python datasource.py create-folder --name "项目A" --folder-name "唯一父目录名"
```
