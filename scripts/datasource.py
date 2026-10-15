#!/usr/bin/env python3
"""DataEase V3 数据源 CLI —— 查询 / 新建 / 校验 / 更新 / 删除。

环境变量:
  DE_BASE_URL     例如 https://de.example.com
  DE_ACCESS_KEY
  DE_SECRET_KEY
  DE_ALLOWED_WRITE_SCOPE  可选，逗号分隔的允许写入组织根/文件夹 ID；
                          增删改目标必须落在这些节点或其子树内

危险操作（update/delete）必须显式传入确认参数，且会先打印风险提示。
新建/建文件夹必须显式传入 --pid（禁止静默落到根目录）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Set

from de_client import DataEaseClient, DataEaseClientError, decode_configuration, encode_configuration

# references/datasource.md 支持的 type
SUPPORTED_TYPES = {
    "mysql",
    "mariadb",
    "TiDB",
    "doris",
    "StarRocks",
    "impala",
    "pg",
    "kingbase",
    "gaussdb",
    "oracle",
    "sqlServer",
    "db2",
    "mongo",
    "ck",
    "redshift",
    "es",
    "API",
    "Excel",
    "ExcelRemote",
    "folder",
}

SCHEMA_REQUIRED = {"oracle", "sqlServer", "pg", "kingbase", "gaussdb", "redshift", "db2"}

DEFAULT_EXTRA_PARAMS = {
    "mysql": "characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true",
    "TiDB": "characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true",
    "mariadb": "characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true",
    "doris": "characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true",
    "StarRocks": "characterEncoding=UTF-8&connectTimeout=5000&useSSL=false&allowPublicKeyRetrieval=true",
    "impala": "AuthMech=0",
    "mongo": "rebuildschema=true&authSource=admin",
}

ADMIN_WARNING = """\
⚠️⚠️⚠️ 高风险：当前为 admin 账号 ⚠️⚠️⚠️
admin 权限过大，误操作可能影响全站数据与配置。
强烈建议：改用「数据分析师」等业务角色账号执行本 skill 操作。
操作前请务必做好备份（数据源/相关数据集与仪表板）。
确认已知晓风险并仍要继续后，再进行新建/更新/删除。
"""

BACKUP_REMINDER = """\
【备份提醒】请先备份相关数据源及依赖的数据集/仪表板；确认已有备份或可接受数据损失后再继续删改。
"""

UPDATE_RISK = """\
【更新风险】
- 请先做好备份（见上方备份提醒）。
- 会覆盖数据源连接配置，可能导致依赖该数据源的数据集/仪表板查询失败。
- 密码留空通常表示「保持原密码」仅在你先 get 再改的场景下才安全；否则请明确传入 password。
- 请确认仅修改参考文档列出的配置字段，并确认目标无误。
"""

DELETE_RISK = """\
【删除风险】
- 请先做好备份（见上方备份提醒）。
- 删除不可自动恢复。
- 若仍有数据集引用此数据源，删除将破坏相关数据集与图表。
- 文件夹删除会影响其下资源（需确认）。
"""

# 数据源删除唯一口令：用户须完整输入方可删除，禁止自动删除
DS_DELETE_PHRASE = "我确认删除此数据源，并已知风险、不会影响业务"



def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _fetch_person(client: DataEaseClient) -> dict:
    data = client.get("/user/personInfo")
    return data if isinstance(data, dict) else {}


def _is_admin_account(person: dict) -> bool:
    account = str(person.get("account") or "").strip().lower()
    return account == "admin"


def _warn_if_admin(client: DataEaseClient) -> dict:
    """若账号为 admin，向 stderr 打印显眼警告；返回 personInfo。"""
    person = _fetch_person(client)
    if _is_admin_account(person):
        print(ADMIN_WARNING, file=sys.stderr)
    return person


def _remind_backup_and_admin(client: DataEaseClient, *, mutating: bool = True) -> None:
    _warn_if_admin(client)
    if mutating:
        print(BACKUP_REMINDER, file=sys.stderr)


def cmd_whoami(client: DataEaseClient, _args: argparse.Namespace) -> None:
    person = _warn_if_admin(client)
    try:
        org_admin = client.get("/user/orgAdmin")
    except DataEaseClientError:
        org_admin = None
    try:
        default_org_admin = client.get("/user/defaultOrgAdmin")
    except DataEaseClientError:
        default_org_admin = None
    _print_json(
        {
            "id": person.get("id"),
            "account": person.get("account"),
            "name": person.get("name"),
            "isAdminAccount": _is_admin_account(person),
            "orgAdmin": org_admin,
            "defaultOrgAdmin": default_org_admin,
            "adminWarningShown": _is_admin_account(person),
        }
    )


def _allowed_write_scope() -> Optional[Set[str]]:
    raw = os.environ.get("DE_ALLOWED_WRITE_SCOPE", "").strip()
    if not raw:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def _is_folder_like(node: dict) -> bool:
    """目录/组织节点（非叶子，或组织根）。"""
    if bool(node.get("orgRoot")):
        return True
    if node.get("leaf") is False:
        return True
    t = node.get("type")
    if t in (None, "", "folder"):
        return node.get("leaf") is not True
    return False


def _walk_tree_index(
    nodes: Any,
    parent_id: Optional[str] = None,
    index: Optional[dict] = None,
    path_names: Optional[list] = None,
) -> dict:
    """构建 id -> {parent, name, orgRoot, path, folderLike} 索引。"""
    if index is None:
        index = {}
    if path_names is None:
        path_names = []
    if not nodes:
        return index
    if isinstance(nodes, dict):
        nodes = [nodes]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id"))
        name = node.get("name")
        cur_path = path_names + ([name] if name is not None else [])
        index[nid] = {
            "parent": parent_id,
            "name": name,
            "orgRoot": bool(node.get("orgRoot")),
            "leaf": node.get("leaf"),
            "type": node.get("type"),
            "folderLike": _is_folder_like(node),
            "path": "/".join(str(x) for x in cur_path if x is not None),
        }
        children = node.get("children")
        if children:
            _walk_tree_index(children, nid, index, cur_path)
    return index


def _tree_endpoint(kind: str) -> tuple[str, str]:
    """返回 (path, busiFlag)。kind: datasource | dataset | dataV | dashboard。"""
    k = (kind or "datasource").strip().lower()
    if k == "dataset":
        return "/datasetTree/tree", "dataset"
    if k == "datasource":
        return "/datasource/tree", "datasource"
    if k in ("datav", "data_v", "screen"):
        return "/dataVisualization/tree", "dataV"
    if k in ("dashboard", "panel", "db"):
        return "/dataVisualization/tree", "dashboard"
    raise DataEaseClientError(
        f"未知资源树 kind={kind}，仅支持 datasource / dataset / dataV / dashboard"
    )


def _load_tree_index(client: DataEaseClient, *, kind: str = "datasource") -> dict:
    path, busi = _tree_endpoint(kind)
    tree = client.post(path, {"busiFlag": busi})
    return _walk_tree_index(tree)


def _folder_matches(info: dict, name: str) -> bool:
    if not info.get("folderLike"):
        return False
    return str(info.get("name") or "") == name


def _resolve_folder(
    client: DataEaseClient,
    *,
    folder_id: Any = None,
    folder_name: Optional[str] = None,
    kind: str = "datasource",
) -> str:
    """
    用 id 或名称解析唯一文件夹 ID。
    名称命中 0 个 → 报错；命中多个 → 抛出候选列表，须用户确认后改用 id。
    kind=datasource 查数据源树；kind=dataset 查数据集树（组织根 id 通常不同）。
    """
    if folder_id is not None and folder_id != "" and folder_name:
        raise DataEaseClientError("请只使用 --pid/--folder-id 或 --folder-name 之一，不要同时指定")
    if (folder_id is None or folder_id == "") and not folder_name:
        raise DataEaseClientError(
            "必须指定父文件夹：--pid（id）或 --folder-name（名称）。"
            "名称不唯一时请 resolve-folder 列出候选并请用户确认。"
        )

    index = _load_tree_index(client, kind=kind)

    if folder_id is not None and folder_id != "":
        fid = str(folder_id)
        if fid not in index:
            # 允许 scope 内的 id 即使树未展开：仍返回，交给后续 scope 校验
            return fid
        info = index[fid]
        if not info.get("folderLike"):
            raise DataEaseClientError(
                f"id={fid}（{info.get('path')}）不是文件夹/组织目录，不能作为父目录"
            )
        return fid

    name = folder_name or ""
    hits = [
        {"id": nid, "name": info.get("name"), "path": info.get("path"), "orgRoot": info.get("orgRoot")}
        for nid, info in index.items()
        if _folder_matches(info, name)
    ]
    # 再按写入范围过滤（若配置了）
    scope = _allowed_write_scope()
    if scope is not None:
        filtered = []
        for h in hits:
            chain = _ancestors(h["id"], index)
            if any(x in scope for x in chain) or h["id"] in scope:
                filtered.append(h)
        hits = filtered

    if len(hits) == 0:
        raise DataEaseClientError(
            f"未找到名称为「{name}」的文件夹"
            + ("（在 DE_ALLOWED_WRITE_SCOPE 内）" if scope else "")
            + "。请核对名称或改用 --pid。"
        )
    if len(hits) > 1:
        raise DataEaseClientError(
            "文件夹名称不唯一，请向用户确认后使用明确 id（--pid）。候选：\n"
            + json.dumps(hits, ensure_ascii=False, indent=2)
        )
    return str(hits[0]["id"])


def cmd_resolve_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    kind = getattr(args, "kind", None) or "datasource"
    if args.id:
        fid = _resolve_folder(client, folder_id=args.id, kind=kind)
        index = _load_tree_index(client, kind=kind)
        info = index.get(fid, {"id": fid})
        _print_json(
            {
                "resolved": True,
                "kind": kind,
                "id": fid,
                **{k: info.get(k) for k in ("name", "path", "orgRoot", "folderLike")},
            }
        )
        return
    if not args.name:
        raise DataEaseClientError("resolve-folder 需要 --id 或 --name")
    try:
        fid = _resolve_folder(client, folder_name=args.name, kind=kind)
        index = _load_tree_index(client, kind=kind)
        info = index.get(fid, {})
        _print_json(
            {
                "resolved": True,
                "kind": kind,
                "unique": True,
                "id": fid,
                "name": info.get("name"),
                "path": info.get("path"),
                "orgRoot": info.get("orgRoot"),
            }
        )
    except DataEaseClientError as e:
        # 若是同名歧义，把候选以 JSON 打印便于 Agent 展示给用户
        msg = str(e)
        if "候选：" in msg:
            _, _, rest = msg.partition("候选：")
            print(msg, file=sys.stderr)
            print(rest.strip())
            raise DataEaseClientError("文件夹名称不唯一，已列出候选，请用户确认后使用 --pid") from e
        raise


def _ancestors(node_id: str, index: dict) -> list:
    chain = []
    cur = str(node_id)
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        info = index.get(cur)
        if not info:
            break
        parent = info.get("parent")
        if parent is None:
            break
        cur = str(parent)
    return chain


def _assert_pid_explicit(payload_or_pid: Any, *, label: str = "pid") -> str:
    if payload_or_pid is None or payload_or_pid == "":
        raise DataEaseClientError(
            f"必须显式指定 {label}（父文件夹/组织目录 ID）。"
            "若有多个候选，请先 tree 并向用户确认后再执行。"
        )
    return str(payload_or_pid)


def _fetch_node_detail_for_scope(
    client: DataEaseClient, tid: str, *, kind: str
) -> Optional[dict]:
    """尽量取节点详情（用于 scope 父链推断）。"""
    if kind == "dataset":
        try:
            detail = client.post(f"/datasetTree/get/{tid}", {})
            return detail if isinstance(detail, dict) else None
        except DataEaseClientError:
            return None
    if kind in ("dataV", "datav", "data_v", "screen"):
        try:
            detail = client.post(
                "/dataVisualization/findById",
                {"id": tid, "busiFlag": "dataV", "resourceTable": "core"},
            )
            return detail if isinstance(detail, dict) else None
        except DataEaseClientError:
            return None
    if kind in ("dashboard", "panel", "db"):
        try:
            detail = client.post(
                "/dataVisualization/findById",
                {"id": tid, "busiFlag": "dashboard", "resourceTable": "core"},
            )
            return detail if isinstance(detail, dict) else None
        except DataEaseClientError:
            return None
    try:
        detail = client.get(f"/datasource/getSimpleDs/{tid}")
        return detail if isinstance(detail, dict) else None
    except DataEaseClientError:
        try:
            detail = client.get(f"/datasource/hidePw/{tid}")
            return detail if isinstance(detail, dict) else None
        except DataEaseClientError:
            return None


def _assert_within_write_scope(
    client: DataEaseClient,
    target_id: Any,
    *,
    role: str,
    kind: str = "datasource",
) -> None:
    """校验目标或其父链落在 DE_ALLOWED_WRITE_SCOPE 内。"""
    scope = _allowed_write_scope()
    if scope is None:
        return
    tid = str(target_id)
    if tid in scope:
        return
    index = _load_tree_index(client, kind=kind)
    if tid not in index:
        # 树未展开到该节点时，用详情的 pid 继续判链
        detail = _fetch_node_detail_for_scope(client, tid, kind=kind)
        if detail is None:
            raise DataEaseClientError(
                f"拒绝{role}：无法定位 id={tid} 是否在允许写入范围内（kind={kind}）"
            )
        if detail.get("pid") is not None:
            pid = str(detail["pid"])
            chain = [tid, pid] + (_ancestors(pid, index) if pid in index else [])
        else:
            chain = [tid]
    else:
        chain = _ancestors(tid, index)
    if not any(x in scope for x in chain):
        raise DataEaseClientError(
            f"拒绝{role}：目标 id={tid} 不在 DE_ALLOWED_WRITE_SCOPE={sorted(scope)} 内。"
            "即使 API Key 对其它组织有权限，也不得越界增删改。"
            "注意：数据源树与数据集树的组织根 id 通常不同，scope 需同时包含对应树的允许节点。"
        )


def _load_json_arg(raw: Optional[str], file_path: Optional[str]) -> Any:
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
    if raw:
        return json.loads(raw)
    return None


def _default_jdbc_configuration(ds_type: str, overrides: dict) -> dict:
    cfg = {
        "dataBase": "",
        "jdbcUrl": "",
        "urlType": "hostName",
        "sshType": "password",
        "extraParams": DEFAULT_EXTRA_PARAMS.get(ds_type, ""),
        "username": "",
        "password": "",
        "host": "",
        "authMethod": "",
        "port": None,
        "sslCA": "",
        "sslCert": "",
        "sslKey": "",
        "initialPoolSize": 5,
        "minPoolSize": 5,
        "maxPoolSize": 100,
        "queryTimeout": 30,
        "useSSH": False,
        "sshHost": "",
        "sshPort": None,
        "sshUserName": "",
        "sshPassword": "",
        "sshKey": "",
        "sshKeyPassword": "",
    }
    if ds_type == "oracle":
        cfg["connectionType"] = "sid"
        cfg["charset"] = "Default"
        cfg["targetCharset"] = "Default"
    if ds_type == "es":
        cfg = {
            "url": "",
            "username": "",
            "password": "",
            "initialPoolSize": 5,
            "minPoolSize": 5,
            "maxPoolSize": 100,
            "queryTimeout": 30,
        }
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg


def _validate_ui_config(ds_type: str, configuration: dict) -> None:
    if ds_type in ("API", "Excel", "ExcelRemote", "folder"):
        return
    if ds_type == "es":
        if not configuration.get("url"):
            raise DataEaseClientError("es 类型必填 configuration.url")
        return

    url_type = configuration.get("urlType") or "hostName"
    if url_type == "jdbcUrl":
        if not configuration.get("jdbcUrl"):
            raise DataEaseClientError("jdbcUrl 模式下必填 configuration.jdbcUrl")
    else:
        for key in ("host", "port", "dataBase"):
            if configuration.get(key) in (None, ""):
                raise DataEaseClientError(f"hostName 模式下必填 configuration.{key}")
    if ds_type in SCHEMA_REQUIRED and not configuration.get("schema"):
        raise DataEaseClientError(
            f"{ds_type} 必填 configuration.schema（可先调用 get-schema 获取列表）"
        )
    if ds_type == "oracle" and url_type != "jdbcUrl" and not configuration.get("connectionType"):
        raise DataEaseClientError("oracle 必填 configuration.connectionType=sid|serviceName")


def cmd_types(client: DataEaseClient, _args: argparse.Namespace) -> None:
    data = client.get("/datasource/types")
    _print_json(data)


def cmd_tree(client: DataEaseClient, args: argparse.Namespace) -> None:
    body = {"busiFlag": "datasource"}
    if args.name:
        body["name"] = args.name
    data = client.post("/datasource/tree", body)
    _print_json(data)


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    path = f"/datasource/hidePw/{args.id}" if args.hide_pw else f"/datasource/get/{args.id}"
    data = client.get(path)
    if isinstance(data, dict) and args.decode and data.get("configuration"):
        data = dict(data)
        data["configurationDecoded"] = decode_configuration(data.get("configuration"))
    _print_json(data)


def cmd_validate(client: DataEaseClient, args: argparse.Namespace) -> None:
    if args.id and not args.file and not args.json:
        data = client.get(f"/datasource/validate/{args.id}")
        _print_json(data)
        return
    payload = _build_save_payload(args, require_id=False)
    data = client.post("/datasource/validate", payload)
    _print_json(data)


def cmd_get_schema(client: DataEaseClient, args: argparse.Namespace) -> None:
    payload = _build_save_payload(args, require_id=False)
    data = client.post("/datasource/getSchema", payload)
    _print_json(data)


def cmd_get_tables(client: DataEaseClient, args: argparse.Namespace) -> None:
    data = client.post("/datasource/getTables", {"datasourceId": args.id})
    _print_json(data)


def cmd_check_repeat(client: DataEaseClient, args: argparse.Namespace) -> None:
    payload = _build_save_payload(args, require_id=False)
    data = client.post("/datasource/checkRepeat", payload)
    _print_json({"repeat": data})


def _build_save_payload(args: argparse.Namespace, require_id: bool) -> dict:
    raw = _load_json_arg(getattr(args, "json", None), getattr(args, "file", None))
    if raw is None:
        if not getattr(args, "type", None) and not getattr(args, "name", None):
            raise DataEaseClientError("请通过 --file/--json 提供完整请求体，或使用快捷参数")
        raw = {}

    payload = dict(raw)
    if getattr(args, "id", None):
        payload["id"] = args.id
    if require_id and not payload.get("id"):
        raise DataEaseClientError("更新必须提供 id（--id 或 JSON 内 id）")

    if getattr(args, "name", None):
        payload["name"] = args.name
    if getattr(args, "pid", None) is not None:
        payload["pid"] = args.pid
    if getattr(args, "type", None):
        payload["type"] = args.type
    if getattr(args, "description", None) is not None:
        payload["description"] = args.description

    ds_type = payload.get("type")
    if ds_type and ds_type not in SUPPORTED_TYPES:
        raise DataEaseClientError(
            f"不支持的类型 {ds_type}。仅支持: {sorted(SUPPORTED_TYPES)}"
        )

    payload.setdefault("nodeType", "folder" if ds_type == "folder" else "datasource")
    payload.setdefault("action", "update" if require_id else "create")
    # 新建必须显式父目录（pid 或后续由 --folder-name 解析）；更新可省略 pid
    folder_name = getattr(args, "folder_name", None)
    if not require_id and not folder_name and (
        "pid" not in payload or payload.get("pid") is None or payload.get("pid") == ""
    ):
        raise DataEaseClientError(
            "新建必须指定父文件夹：--pid（id）或 --folder-name（唯一名称）。"
            "同名不确定时先 resolve-folder 并向用户确认。"
        )

    # configuration 处理
    conf = payload.get("configuration")
    conf_overrides = {}
    for key in (
        "host",
        "port",
        "dataBase",
        "schema",
        "username",
        "password",
        "jdbcUrl",
        "urlType",
        "extraParams",
        "url",
        "connectionType",
        "charset",
        "targetCharset",
        "useSSH",
        "sshHost",
        "sshPort",
        "sshUserName",
        "sshPassword",
        "sshType",
        "sshKey",
        "initialPoolSize",
        "minPoolSize",
        "maxPoolSize",
        "queryTimeout",
    ):
        val = getattr(args, key, None)
        if val is not None:
            conf_overrides[key] = val

    if ds_type and ds_type not in ("API", "Excel", "ExcelRemote", "folder"):
        if conf is None or conf == "" or conf == {}:
            conf = _default_jdbc_configuration(ds_type, conf_overrides)
        elif isinstance(conf, str):
            decoded = decode_configuration(conf)
            if isinstance(decoded, dict):
                decoded.update(conf_overrides)
                conf = decoded
            elif conf_overrides:
                raise DataEaseClientError("无法在已编码 configuration 上叠加快捷参数，请传 JSON 对象")
        elif isinstance(conf, dict):
            conf.update(conf_overrides)
        _validate_ui_config(ds_type, conf)
        payload["configuration"] = encode_configuration(conf)
    elif isinstance(conf, (dict, list)):
        payload["configuration"] = encode_configuration(conf)
    elif conf is None and ds_type not in ("folder",):
        # API/Excel 需完整 JSON
        if ds_type in ("API", "Excel", "ExcelRemote"):
            raise DataEaseClientError(
                f"{ds_type} 请通过 --file 提供完整 configuration（见 references/datasource.md）"
            )

    for readonly_key in ("qrtzInstance", "dsVersion", "createBy", "creator", "updateBy", "taskStatus"):
        payload.pop(readonly_key, None)

    if not payload.get("name"):
        raise DataEaseClientError("name 必填")
    if not payload.get("type"):
        raise DataEaseClientError("type 必填")

    return payload


def cmd_save(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    payload = _build_save_payload(args, require_id=False)
    if getattr(args, "folder_name", None):
        payload["pid"] = _resolve_folder(client, folder_name=args.folder_name)
    else:
        payload["pid"] = _resolve_folder(client, folder_id=payload.get("pid"))
    pid = _assert_pid_explicit(payload.get("pid"))
    _assert_within_write_scope(client, pid, role="写入父目录")
    if args.validate_first:
        client.post("/datasource/validate", payload)
    if args.check_repeat:
        repeated = client.post("/datasource/checkRepeat", payload)
        if repeated:
            raise DataEaseClientError(
                "检测到重复数据源（同 host/库等）。若仍要创建，去掉 --check-repeat 后重试，"
                "并确认与用户意图一致。"
            )
    data = client.post("/datasource/save", payload)
    _print_json(data)


def cmd_update(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    if not args.i_confirm_update:
        print(UPDATE_RISK, file=sys.stderr)
        raise DataEaseClientError(
            "更新需二次确认：请向用户提醒备份与风险，用户确认「已备份且同意更新」后使用 --i-confirm-update"
        )
    print(UPDATE_RISK, file=sys.stderr)
    payload = _build_save_payload(args, require_id=True)
    payload["action"] = "update"
    # 校验目标数据源本身是否在允许范围内；若同时改 pid，新父目录也必须在范围内
    _assert_within_write_scope(client, payload["id"], role="更新目标")
    if payload.get("pid") is not None and payload.get("pid") != "":
        _assert_within_write_scope(client, payload["pid"], role="写入父目录")
    if args.validate_first:
        client.post("/datasource/validate", payload)
    data = client.post("/datasource/update", payload)
    _print_json(data)


def cmd_delete(client: DataEaseClient, args: argparse.Namespace) -> None:
    """删除数据源：强制血缘分析 + 用户完整口令确认；禁止自动删除。"""
    _remind_backup_and_admin(client, mutating=True)
    _assert_within_write_scope(client, args.id, role="删除目标")

    # 1) 强制血缘分析：列出下游数据集与看板（只读）
    from relation import relation_gate

    summary = relation_gate(client, "datasource", args.id)
    print(DELETE_RISK, file=sys.stderr)
    if summary.get("hasVisualUsage"):
        print(
            "警告：仍有仪表板/数据大屏依赖此数据源（清单见上），删除将导致其中图表不可用。",
            file=sys.stderr,
        )

    # 2) 完整口令确认：唯一放行条件
    if (args.confirm_delete or "").strip() != DS_DELETE_PHRASE:
        raise DataEaseClientError(
            "本 skill 禁止自动删除数据源。已向用户展示血缘关系与风险说明，"
            f"仅当用户完整输入口令「{DS_DELETE_PHRASE}」后方可继续，"
            "确认后重试并附加 --confirm-delete <完整口令>"
        )

    # 3) 引用兜底提示后删除
    in_use = client.post(f"/datasource/perDelete/{args.id}", {})
    if in_use:
        print(
            "警告: perDelete 显示仍有数据集引用该数据源，按用户完整口令确认继续删除。",
            file=sys.stderr,
        )
    body = {"id": args.id}
    if args.root_org_node:
        body["rootOrgNode"] = True
    data = client.post("/datasource/delete", body)
    _print_json(data if data is not None else {"deleted": True, "id": args.id})


def cmd_create_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    if args.pid is not None and args.folder_name:
        raise DataEaseClientError("请只使用 --pid 或 --folder-name 之一")
    if args.pid is None and not args.folder_name:
        raise DataEaseClientError(
            "创建文件夹须指定父目录：--pid 或 --folder-name。"
            "同名不确定时先 resolve-folder 请用户确认。"
        )
    if args.folder_name:
        pid = _resolve_folder(client, folder_name=args.folder_name)
    else:
        pid = _resolve_folder(client, folder_id=args.pid)
    pid = _assert_pid_explicit(pid)
    _assert_within_write_scope(client, pid, role="写入父目录")
    payload = {
        "name": args.name,
        "nodeType": "folder",
        "action": "create",
        "pid": pid,
    }
    data = client.post("/datasource/createFolder", payload)
    _print_json(data)


def cmd_template(client: DataEaseClient, args: argparse.Namespace) -> None:
    ds_type = args.type
    if ds_type not in SUPPORTED_TYPES:
        raise DataEaseClientError(f"未知类型: {ds_type}")
    if ds_type == "folder":
        _print_json({"name": "新建文件夹", "nodeType": "folder", "action": "create", "pid": 0})
        return
    if ds_type == "es":
        conf = _default_jdbc_configuration("es", {})
    elif ds_type in ("API", "Excel", "ExcelRemote"):
        conf = {"_comment": f"请按 references/datasource.md 填写完整 {ds_type} configuration"}
    else:
        conf = _default_jdbc_configuration(ds_type, {})
    _print_json(
        {
            "name": f"示例-{ds_type}",
            "pid": 0,
            "nodeType": "datasource",
            "action": "create",
            "type": ds_type,
            "description": "",
            "configuration": conf,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 数据源管理 CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("types", help="列出数据源类型").set_defaults(func=cmd_types)
    sub.add_parser("whoami", help="当前用户；若为 admin 打印高风险警告").set_defaults(func=cmd_whoami)

    t = sub.add_parser("tree", help="数据源树")
    t.add_argument("--name", default=None)
    t.set_defaults(func=cmd_tree)

    rf = sub.add_parser("resolve-folder", help="按 id 或名称解析文件夹（同名则列出候选）")
    rf.add_argument("--id", default=None, help="文件夹 id")
    rf.add_argument("--name", default=None, help="文件夹名称")
    rf.add_argument(
        "--kind",
        default="datasource",
        choices=["datasource", "dataset", "dataV", "dashboard"],
        help="资源树：datasource（默认）/ dataset / dataV / dashboard；各树组织根 id 通常不同",
    )
    rf.set_defaults(func=cmd_resolve_folder)

    g = sub.add_parser("get", help="数据源详情")
    g.add_argument("--id", required=True)
    g.add_argument("--hide-pw", action="store_true", help="使用 hidePw 接口（推荐展示给用户）")
    g.add_argument("--decode", action="store_true", help="解码 configuration")
    g.set_defaults(func=cmd_get)

    def add_payload_args(sp: argparse.ArgumentParser, with_id: bool = False) -> None:
        if with_id:
            sp.add_argument("--id", default=None)
        sp.add_argument("--file", help="请求 JSON 文件路径")
        sp.add_argument("--json", help="请求 JSON 字符串")
        sp.add_argument("--name")
        sp.add_argument("--pid", type=int, default=None, help="父文件夹 id")
        sp.add_argument(
            "--folder-name",
            default=None,
            help="父文件夹名称（须在范围内唯一；同名请先 resolve-folder 确认）",
        )
        sp.add_argument("--type")
        sp.add_argument("--description")
        sp.add_argument("--host")
        sp.add_argument("--port", type=int)
        sp.add_argument("--dataBase")
        sp.add_argument("--schema")
        sp.add_argument("--username")
        sp.add_argument("--password")
        sp.add_argument("--jdbcUrl")
        sp.add_argument("--urlType", choices=["hostName", "jdbcUrl"])
        sp.add_argument("--extraParams")
        sp.add_argument("--url", help="es 或远程相关 URL")
        sp.add_argument("--connectionType", choices=["sid", "serviceName"])
        sp.add_argument("--charset")
        sp.add_argument("--targetCharset")
        sp.add_argument("--useSSH", type=lambda x: str(x).lower() in ("1", "true", "yes"))
        sp.add_argument("--sshHost")
        sp.add_argument("--sshPort", type=int)
        sp.add_argument("--sshUserName")
        sp.add_argument("--sshPassword")
        sp.add_argument("--sshType", choices=["password", "sshkey"])
        sp.add_argument("--sshKey")
        sp.add_argument("--initialPoolSize", type=int)
        sp.add_argument("--minPoolSize", type=int)
        sp.add_argument("--maxPoolSize", type=int)
        sp.add_argument("--queryTimeout", type=int)

    v = sub.add_parser("validate", help="校验连接")
    add_payload_args(v, with_id=True)
    v.set_defaults(func=cmd_validate)

    gs = sub.add_parser("get-schema", help="获取 schema 列表")
    add_payload_args(gs, with_id=True)
    gs.set_defaults(func=cmd_get_schema)

    gt = sub.add_parser("get-tables", help="获取表列表")
    gt.add_argument("--id", required=True)
    gt.set_defaults(func=cmd_get_tables)

    cr = sub.add_parser("check-repeat", help="检查是否重复数据源")
    add_payload_args(cr)
    cr.set_defaults(func=cmd_check_repeat)

    s = sub.add_parser("save", help="新建数据源")
    add_payload_args(s)
    s.add_argument("--validate-first", action="store_true")
    s.add_argument("--check-repeat", action="store_true")
    s.set_defaults(func=cmd_save)

    u = sub.add_parser("update", help="更新数据源（需确认）")
    add_payload_args(u, with_id=True)
    u.add_argument("--validate-first", action="store_true")
    u.add_argument("--i-confirm-update", action="store_true")
    u.set_defaults(func=cmd_update)

    d = sub.add_parser("delete", help="删除数据源（强制血缘分析；须用户完整口令确认，禁止自动删除）")
    d.add_argument("--id", required=True)
    d.add_argument(
        "--confirm-delete",
        default=None,
        help="删除口令：用户须完整输入「我确认删除此数据源，并已知风险、不会影响业务」",
    )
    d.add_argument("--root-org-node", action="store_true")
    d.set_defaults(func=cmd_delete)

    cf = sub.add_parser("create-folder", help="新建文件夹")
    cf.add_argument("--name", required=True)
    cf.add_argument("--pid", type=int, default=None, help="父文件夹 id")
    cf.add_argument("--folder-name", default=None, help="父文件夹名称（须唯一）")
    cf.set_defaults(func=cmd_create_folder)

    tp = sub.add_parser("template", help="打印某类型新建模板 JSON")
    tp.add_argument("--type", required=True)
    tp.set_defaults(func=cmd_template)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        client = DataEaseClient()
        args.func(client, args)
        return 0
    except DataEaseClientError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
