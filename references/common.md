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

## 环境变量

| 变量 | 说明 |
|------|------|
| `DE_BASE_URL` | 如 `https://your-de-host`（脚本自动加 `/de2api`） |
| `DE_ACCESS_KEY` / `DE_SECRET_KEY` | API Key |
| `DE_ALLOWED_WRITE_SCOPE` | 推荐；逗号分隔的允许写入组织根/文件夹 ID |

```bash
cd scripts
# 仅在用户确认后：python -m pip install -r requirements.txt
```

## 认证

API Key：AES(`accessKey|uuid|timestamp`) + JWT；请求头 `accessKey` / `signature` / `x-de-ask-token`。实现见 `scripts/de_client.py`。

## 文件夹定位

- `--pid`（id）或 `--folder-name`（名称，须在范围内唯一）
- **数据源 / 数据集 / 数据大屏 / 仪表板是四棵独立树**：同名组织在各侧的 **id 通常不同**。  
  - 数据源：`datasource.py resolve-folder`  
  - 数据集：`dataset.py resolve-folder`  
  - 数据大屏：`datav.py resolve-folder`（或 `datasource.py resolve-folder --kind dataV`）  
  - 仪表板：`dashboard.py resolve-folder`（或 `datasource.py resolve-folder --kind dashboard`）  
  切勿跨树混用组织根 id。
- 同名 / 子目录同名：先 resolve-folder，把候选交给用户确认后再用 `--pid`
- 写入须落在用户允许范围 + `DE_ALLOWED_WRITE_SCOPE` 内；若同时写多类资源，scope 需包含**各树**允许的组织根/文件夹 id

## 风险话术（删改时告知用户）

**备份**：请先备份相关数据源及依赖的数据集/仪表板；确认已有备份或可接受数据损失后再继续。  

**更新**：将覆盖配置，可能导致依赖资源失败；请确认目标与字段无误。  

**删除**：不可自动恢复；有引用时相关资源可能失效；请确认删除。  

**依赖安装**：将修改本机 Python/Conda 环境并下载第三方包；请确认拟用解释器与安装命令后再继续。  
