# 通用约定

## 适用客户端

本 skill 可在 **WorkBuddy、Cursor、Codex、Claude Code** 以及其他支持加载 Agent Skills 的工具中使用。加载本目录后，由 Agent 按 [SKILL.md](../SKILL.md) 调用 `scripts/`。

## Python 环境检测与依赖安装

**目标：** Python **3.9+**，并能 `import jwt`、`requests`、`Crypto`（包名 `PyJWT`、`requests`、`pycryptodome`，见 `scripts/requirements.txt`）。

### 检测（自动，无需确认）

按顺序探测，记录第一个可用解释器：

1. 当前已激活的 venv / Conda（直接 `python` / `python3`）  
2. `python3`、`python`；Windows 可试 `py -3`  
3. Conda / Mamba：`conda info --envs`，对候选环境用 `conda run -n <name> python ...`  

对每个候选执行：

```bash
python -c "import sys; assert sys.version_info >= (3, 9); import jwt, requests; from Crypto.Cipher import AES; print(sys.executable, sys.version)"
```

（将 `python` 换成实际候选命令。）

### 安装（必须解释 + 用户确认）

若无合格解释器，或缺依赖：

1. 向用户说明现状（找到了什么 / 缺什么）  
2. 给出拟执行命令，例如：  
   - `python -m pip install -r scripts/requirements.txt`  
   - 或 `conda create -n de-skills python=3.11 -y` 后再 pip/conda 装依赖  
3. **用户明确同意后再执行**；禁止静默安装或改动用户全局环境而不告知  
4. 装完复检；失败则停止并给出手工步骤  

用户拒绝时：只提供手工指引，不继续跑业务脚本。

## 连接配置（连接制）

**本 skill 始终基于连接制：任何业务操作前都要先拿到用户的 DataEase V3 连接信息。**

### 首次使用：先向用户索取

向用户索取三项（缺一不可）：

| 项 | 说明 |
|----|------|
| 部署地址 | 用户 DataEase V3 的访问地址，如 `https://de.example.com`（脚本自动补 `/de2api`） |
| Access Key | 用户在其 DataEase「API Key 管理」中创建的 Access Key |
| Secret Key | 对应 Secret Key（**只在创建时可见，请提醒用户妥善保存**） |

拿到后保存并验证（推荐）：

```bash
cd scripts
python de_setup.py save --base-url https://de.example.com --access-key <AK> --secret-key <SK>
python de_setup.py check
```

`check` 会：验证连通性 → 显示当前账号（admin 会给出高风险提示）→ **自动发现五棵资源树的组织根 id** → 输出可直接保存的写入范围建议。

**若用户暂不提供配置，不要臆造、不要跳过——停下来向用户说明缺什么，等其提供后再继续。**

### 配置来源与优先级

`命令行参数` > `环境变量` > `本地配置文件`

| 来源 | 说明 |
|------|------|
| 环境变量 | `DE_BASE_URL` / `DE_ACCESS_KEY` / `DE_SECRET_KEY` / `DE_ALLOWED_WRITE_SCOPE` |
| 本地配置文件 | 默认 `~/.dataease-de3/config.json`（由 `de_setup.py save` 写入，权限 0600；可用 `DE_CONFIG_FILE` 指定其它路径），字段：`baseUrl` / `accessKey` / `secretKey` / `writeScope` |

`python de_setup.py show` 可查看当前生效配置（**密钥自动脱敏**）。

### 写入范围与组织根

- 推荐配置写入范围：既可在本地配置里保存 `writeScope`，也可用环境变量 `DE_ALLOWED_WRITE_SCOPE`（两者都支持；环境变量优先）。
- **五棵树的组织根 id 通常不同**，`de_setup.py check` 会自动列出，直接照抄其建议值即可，避免手抄错 id。
- 即使 Key 能访问其它组织，也不得在用户允许范围之外增删改。

### 安全约定

- 密钥只写入本地配置文件，**严禁提交进任何代码仓库、不要写进 skill 目录**。
- 展示配置一律脱敏（`de_setup.py show` / `datasource.py whoami`）。
- 与用户确认连接信息属于必要收集，但**不要把它回显到聊天记录里**（除域名外，AK/SK 请只回显脱敏值）。

## 认证

API Key：AES(`accessKey|uuid|timestamp`) + JWT；请求头 `accessKey` / `signature` / `x-de-ask-token`。实现见 `scripts/de_client.py`。

## 文件夹定位

- `--pid`（id）或 `--folder-name`（名称，须在范围内唯一）
- **数据源 / 数据集 / 数据大屏 / 仪表板 / 电子表格是五棵独立树**：同名组织在各侧的 **id 通常不同**。  
  - 数据源：`datasource.py resolve-folder`  
  - 数据集：`dataset.py resolve-folder`  
  - 数据大屏：`datav.py resolve-folder`（或 `datasource.py resolve-folder --kind dataV`）  
  - 仪表板：`dashboard.py resolve-folder`（或 `datasource.py resolve-folder --kind dashboard`）  
  - 电子表格：`spreadsheet.py resolve-folder`（或 `datasource.py resolve-folder --kind spreadsheet`）  
  切勿跨树混用组织根 id。
- 同名 / 子目录同名：先 resolve-folder，把候选交给用户确认后再用 `--pid`
- 写入须落在用户允许范围 + `DE_ALLOWED_WRITE_SCOPE` 内；若同时写多类资源，scope 需包含**各树**允许的组织根/文件夹 id

## 血缘分析（编辑/删除已有资源前必做）

修改或删除**非当前任务创建**的数据集/数据源等资源前，必须先查询其下游引用：若被仪表板、数据大屏使用，改动会导致相关看板中的图表不可用。

```bash
python relation.py get --kind datasource --id <数据源ID> [--brief]
python relation.py get --kind dataset --id <数据集ID> [--brief]
python relation.py get --kind dv --id <大屏/仪表板ID> [--brief]
```

输出 `summary`（`--brief` 仅摘要）关键字段：

| 字段 | 说明 |
|------|------|
| `hasVisualUsage` | 是否有仪表板/数据大屏在使用 |
| `visualUsage` | 看板清单（类型 / id / 名称 / 经由哪个数据集） |
| `upstream` / `downstream` | 上游依赖与下游引用明细 |

`dataset.py edit` / `dataset.py delete` 已**内置强制血缘检查**（自动查询并打印报告），无需手工先跑 relation.py；其它资源的手工改动前建议先用 relation.py 查询。

### 分级确认（改动已存在资源的硬性门槛）

| 情形 | 要求 | CLI 用法 |
|------|------|----------|
| **数据源删除（最严档）** | **禁止自动删除**。先展示血缘引用清单与风险，**用户须完整输入口令「我确认删除此数据源，并已知风险、不会影响业务」**方可继续，否则拒绝 | `--confirm-delete "我确认删除此数据源，并已知风险、不会影响业务"` |
| 被仪表板/数据大屏引用 | 向用户展示引用清单与风险，**必须由用户输入「确认修改」四字**方可继续，否则拒绝 | `--confirm-modify 确认修改`（删除亦接受 `确认删除`） |
| 无任何下游引用 | 仍须向用户说明并确认 | `--yes` |
| 当前任务新建且无外部操作 | 可免提示继续（仅当 Agent 能确认该资源及引用它的看板均为本任务所建） | `--session-created` |

血缘报告始终打印，供用户与 Agent 核对。

## 风险话术（删改时告知用户）

**备份**：请先备份相关数据源及依赖的数据集/仪表板；确认已有备份或可接受数据损失后再继续。  

**更新/编辑**：将覆盖配置，可能导致依赖资源失败；若被仪表板/数据大屏引用，改动后相关图表将不可用。请确认目标与字段无误。  

**删除**：不可自动恢复；有引用时相关看板与图表可能失效。请确认删除。  

**依赖安装**：将修改本机 Python/Conda 环境并下载第三方包；请确认拟用解释器与安装命令后再继续。    
