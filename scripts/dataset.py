#!/usr/bin/env python3
"""DataEase V3 数据集 CLI —— 取表/字段/预览/新建（含计算、分组、复制字段）。

环境变量同 datasource.py：DE_BASE_URL / DE_ACCESS_KEY / DE_SECRET_KEY / DE_ALLOWED_WRITE_SCOPE
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError, encode_configuration  # noqa: F401
from de_ids import snowflake_id
from datasource import (  # 复用组织边界与 admin/备份提醒
    _assert_within_write_scope,
    _load_tree_index,
    _remind_backup_and_admin,
    _resolve_folder,
)

# deType: 0文本 1时间 2整型 3浮点 4布尔 5地理 6二进制 7URL
# groupType: d=维度 q=指标（默认规则与产品一致）
DETYPE_TO_GROUP = {
    0: "d",
    1: "d",
    2: "q",
    3: "q",
    4: "q",
    5: "d",
    6: "d",
    7: "d",
}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load_json(raw: Optional[str], file_path: Optional[str]) -> Any:
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
    if raw:
        return json.loads(raw)
    return None


def _default_group_type(de_type: Any, override: Optional[str] = None) -> str:
    if override in ("d", "q"):
        return override
    try:
        return DETYPE_TO_GROUP.get(int(de_type), "d")
    except (TypeError, ValueError):
        return "d"


def _infer_group_type_by_name(name: str, de_type: Any) -> str:
    """
    在类型默认基础上，按常见业务命名微调维度/指标。
    指标倾向：量、额、数、率、价、金额、数量、次数、占比、score、amount、count、qty、rate…
    维度倾向：名称、类型、状态、省份、城市、日期、人、部门、id、name、type、status…
    """
    base = _default_group_type(de_type)
    n = (name or "").strip().lower()
    metric_keys = (
        "量", "额", "数", "率", "价", "金额", "数量", "次数", "占比", "总和", "合计",
        "amount", "count", "qty", "quantity", "rate", "ratio", "price", "score", "sum", "total",
        "sales", "销售量", "销售额",
    )
    dim_keys = (
        "名称", "类型", "状态", "省份", "城市", "日期", "时间", "人", "部门", "类别", "地区",
        "name", "type", "status", "province", "city", "date", "time", "id", "code", "类别",
        "统计日期", "曝光类型", "统计人", "部门信息", "图像",
    )
    if any(k.lower() in n or k in (name or "") for k in metric_keys):
        # 数值类更信指标；文本叫「类型」等仍维度
        if base == "q" or any(k in (name or "") for k in ("量", "额", "数", "率", "价", "金额", "数量")):
            return "q"
    if any(k.lower() in n or k in (name or "") for k in dim_keys):
        return "d"
    return base


def _encode_calc_fields(fields: list) -> list:
    out = []
    for f in fields:
        item = dict(f)
        if item.get("extField") == 2 and isinstance(item.get("originName"), str):
            # 复制字段 originName 形如 [id]，计算字段为表达式；提交前均 Base64
            raw = item["originName"]
            try:
                base64.b64decode(raw, validate=True)
                # 已是 base64 则不动
            except Exception:
                item["originName"] = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
        out.append(item)
    return out


def _table_info(table_name: str, sql: str = "") -> str:
    return json.dumps({"table": table_name, "sql": sql}, ensure_ascii=False, separators=(",", ":"))


def cmd_tables(client: DataEaseClient, args: argparse.Namespace) -> None:
    data = client.post("/datasource/getTables", {"datasourceId": args.datasource_id})
    _print_json(data)


def cmd_fields(client: DataEaseClient, args: argparse.Namespace) -> None:
    table_name = args.table
    info = _table_info(table_name)
    body = {
        "datasourceId": args.datasource_id,
        "id": args.node_id or snowflake_id(),
        "info": info,
        "tableName": table_name,
        "type": args.table_type,
        "isCross": False,
    }
    fields = client.post("/datasetData/tableField", body)
    if isinstance(fields, list):
        for f in fields:
            if args.infer_dq:
                f["groupType"] = _infer_group_type_by_name(f.get("name") or f.get("originName"), f.get("deType"))
            else:
                f["groupType"] = f.get("groupType") or _default_group_type(f.get("deType"))
    _print_json(fields)


def _build_union_and_fields(
    *,
    datasource_id: str,
    table_name: str,
    table_type: str,
    fields: list,
    extra_fields: Optional[list] = None,
) -> tuple[list, list]:
    node_id = snowflake_id()
    all_fields = []
    current_ds_fields = []
    for f in fields:
        fid = str(f.get("id") or snowflake_id())
        item = {
            "id": fid,
            "datasourceId": str(datasource_id),
            "datasetTableId": node_id,
            "datasetGroupId": None,
            "originName": f.get("originName") or f.get("name"),
            "name": f.get("name") or f.get("originName"),
            "description": f.get("description"),
            "groupType": f.get("groupType") or _infer_group_type_by_name(f.get("name"), f.get("deType")),
            "type": f.get("type") or "VARCHAR",
            "deType": f.get("deType") if f.get("deType") is not None else 0,
            "deExtractType": f.get("deExtractType") if f.get("deExtractType") is not None else f.get("deType", 0),
            "extField": int(f.get("extField") or 0),
            "checked": True if f.get("checked") is None else bool(f.get("checked")),
        }
        if f.get("dateFormat"):
            item["dateFormat"] = f["dateFormat"]
        if f.get("dateFormatType"):
            item["dateFormatType"] = f["dateFormatType"]
        all_fields.append(item)
        if item["extField"] == 0:
            current_ds_fields.append(item)

    for ef in extra_fields or []:
        item = dict(ef)
        item.setdefault("id", snowflake_id())
        item.setdefault("datasourceId", str(datasource_id))
        item.setdefault("datasetTableId", node_id)
        item.setdefault("checked", True)
        item.setdefault("extField", 2)
        if "groupType" not in item:
            item["groupType"] = _infer_group_type_by_name(item.get("name"), item.get("deType"))
        all_fields.append(item)

    union = [
        {
            "currentDs": {
                "id": node_id,
                "datasourceId": str(datasource_id),
                "tableName": table_name,
                "type": table_type,
                "info": _table_info(table_name),
                "sqlVariableDetails": None,
            },
            "currentDsFields": current_ds_fields,
            "childrenDs": [],
            "unionToParent": {"unionType": "left", "unionFields": []},
        }
    ]
    return union, all_fields


def cmd_preview(client: DataEaseClient, args: argparse.Namespace) -> None:
    payload = _load_json(args.json, args.file)
    if payload is None:
        # 快捷：datasource + table
        if not args.datasource_id or not args.table:
            raise DataEaseClientError("preview 需要 --file/--json，或 --datasource-id + --table")
        fields = client.post(
            "/datasetData/tableField",
            {
                "datasourceId": args.datasource_id,
                "id": snowflake_id(),
                "info": _table_info(args.table),
                "tableName": args.table,
                "type": args.table_type,
                "isCross": False,
            },
        )
        if not isinstance(fields, list):
            raise DataEaseClientError(f"tableField 返回异常: {fields}")
        for f in fields:
            f["groupType"] = _infer_group_type_by_name(f.get("name"), f.get("deType"))
        union, all_fields = _build_union_and_fields(
            datasource_id=args.datasource_id,
            table_name=args.table,
            table_type=args.table_type,
            fields=fields,
        )
        payload = {"union": union, "allFields": all_fields, "isCross": False}
    body = dict(payload)
    if body.get("allFields"):
        body["allFields"] = _encode_calc_fields(body["allFields"])
    data = client.post("/datasetData/previewData", body)
    _print_json(data)


def _apply_field_ops(all_fields: list, ops: list) -> list:
    """应用计算/分组/复制等字段操作。"""
    by_name = {f.get("name"): f for f in all_fields}
    by_id = {str(f.get("id")): f for f in all_fields}
    result = list(all_fields)
    for op in ops:
        kind = (op.get("op") or op.get("type") or "").lower()
        if kind in ("copy", "复制"):
            src = op.get("from") or op.get("source") or op.get("field")
            src_f = by_name.get(src) or by_id.get(str(src))
            if not src_f:
                raise DataEaseClientError(f"复制字段找不到源字段: {src}")
            new_id = snowflake_id()
            copied = dict(src_f)
            copied["id"] = new_id
            copied["extField"] = 2
            copied["originName"] = (
                src_f["originName"] if src_f.get("extField") == 2 else f"[{src_f['id']}]"
            )
            copied["name"] = op.get("name") or f"{src_f.get('name')}_copy"
            copied["dataeaseName"] = None
            copied["fieldShortName"] = None
            if op.get("groupType") in ("d", "q"):
                copied["groupType"] = op["groupType"]
            result.append(copied)
            by_name[copied["name"]] = copied
            by_id[new_id] = copied
        elif kind in ("calc", "calculate", "计算"):
            name = op.get("name") or "计算字段"
            expr = op.get("expression") or op.get("originName") or ""
            if not expr:
                raise DataEaseClientError(f"计算字段 {name} 缺少 expression")
            de_type = op.get("deType", 0)
            group_type = op.get("groupType") or _infer_group_type_by_name(name, de_type)
            # 表达式里可用 {{字段名}} 替换为 [fieldId]
            resolved = expr
            for fname, ff in list(by_name.items()):
                resolved = resolved.replace("{{" + fname + "}}", f"[{ff['id']}]")
            item = {
                "id": snowflake_id(),
                "name": name,
                "originName": resolved,
                "groupType": group_type,
                "type": op.get("type") or "VARCHAR",
                "deType": de_type,
                "deExtractType": de_type,
                "extField": 2,
                "checked": True,
                "params": op.get("params") or [],
                "datasourceId": result[0].get("datasourceId") if result else None,
                "datasetTableId": result[0].get("datasetTableId") if result else None,
            }
            result.append(item)
            by_name[name] = item
            by_id[item["id"]] = item
        elif kind in ("group", "分组"):
            name = op.get("name") or "分组字段"
            src = op.get("from") or op.get("source") or op.get("field")
            src_f = by_name.get(src) or by_id.get(str(src))
            if not src_f:
                raise DataEaseClientError(f"分组字段找不到源字段: {src}")
            item = {
                "id": snowflake_id(),
                "name": name,
                "originName": str(src_f["id"]),
                "otherGroup": op.get("otherGroup") or "其他",
                "groupType": "d",
                "deType": 0,
                "type": "ANY",
                "deExtractType": 0,
                "extField": 3,
                "checked": True,
                "groupList": op.get("groupList")
                or [
                    {
                        "name": "分组1",
                        "text": op.get("text") or [],
                        "minTerm": "lt",
                        "maxTerm": "lt",
                        "min": None,
                        "max": None,
                    }
                ],
                "datasourceId": src_f.get("datasourceId"),
                "datasetTableId": src_f.get("datasetTableId"),
            }
            result.append(item)
            by_name[name] = item
            by_id[item["id"]] = item
        elif kind in ("set-group-type", "dq", "维度指标"):
            target = op.get("field") or op.get("name")
            tf = by_name.get(target) or by_id.get(str(target))
            if not tf:
                raise DataEaseClientError(f"设置维度/指标找不到字段: {target}")
            gt = op.get("groupType")
            if gt not in ("d", "q"):
                raise DataEaseClientError("groupType 必须为 d 或 q")
            tf["groupType"] = gt
        else:
            raise DataEaseClientError(f"未知字段操作: {kind}")
    return result


def cmd_resolve_folder(client: DataEaseClient, args: argparse.Namespace) -> None:
    """在数据集树上解析文件夹（勿用数据源组织根 id）。"""
    from datasource import cmd_resolve_folder as _ds_resolve

    args.kind = "dataset"
    _ds_resolve(client, args)


def cmd_move(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)
    if args.folder_name:
        pid = _resolve_folder(client, folder_name=args.folder_name, kind="dataset")
    else:
        if args.pid is None:
            raise DataEaseClientError("移动须指定目标文件夹 --pid 或 --folder-name")
        pid = _resolve_folder(client, folder_id=args.pid, kind="dataset")
    # 只校验目标目录在写入范围内（允许把误放到根/范围外的资源迁回）
    _assert_within_write_scope(client, pid, role="写入父目录", kind="dataset")

    index = _load_tree_index(client, kind="dataset")
    info = index.get(str(pid), {})
    if info.get("orgRoot"):
        raise DataEaseClientError(
            "目标是虚拟组织根（orgRoot），datasetTree/move 可能因父链 NPE 失败。"
            "请删除后用 create --folder-name/--pid 重建到正确位置，"
            "或先建真实子文件夹再试 move（部分环境子文件夹父链仍会失败）。"
        )

    detail = client.post(f"/datasetTree/get/{args.id}", {})
    if not isinstance(detail, dict):
        raise DataEaseClientError(f"无法获取数据集详情: {args.id}")
    name = args.name or detail.get("name")
    body = {
        "id": str(args.id),
        "pid": pid,
        "name": name,
        "nodeType": detail.get("nodeType") or "dataset",
    }
    try:
        data = client.post("/datasetTree/move", body)
    except DataEaseClientError as e:
        raise DataEaseClientError(
            f"{e}；若目标在组织根子树下，服务端 checkMove 可能对虚拟组织节点 NPE。"
            "建议删除后按正确数据集树 pid 重建。"
        ) from e
    _print_json(data)


def cmd_create(client: DataEaseClient, args: argparse.Namespace) -> None:
    _remind_backup_and_admin(client, mutating=True)

    if args.folder_name:
        pid = _resolve_folder(client, folder_name=args.folder_name, kind="dataset")
    else:
        if args.pid is None:
            raise DataEaseClientError("必须指定目标文件夹 --pid 或 --folder-name")
        pid = _resolve_folder(client, folder_id=args.pid, kind="dataset")
    _assert_within_write_scope(client, pid, role="写入父目录", kind="dataset")

    # 完整 payload 文件优先
    payload = _load_json(args.json, args.file)
    if payload and payload.get("union") and payload.get("allFields"):
        body = dict(payload)
        body["pid"] = pid
        body.setdefault("nodeType", "dataset")
        body.setdefault("name", args.name or body.get("name") or "未命名数据集")
        body.setdefault("type", "union")
        body.setdefault("mode", args.mode if args.mode is not None else 0)
        body.setdefault("isCross", False)
        if body.get("allFields"):
            body["allFields"] = _encode_calc_fields(body["allFields"])
        if not args.skip_preview:
            client.post("/datasetData/previewData", {
                "union": body["union"],
                "allFields": body["allFields"],
                "isCross": body.get("isCross", False),
            })
        data = client.post("/datasetTree/create", body)
        _print_json(data)
        return

    if not args.datasource_id or not args.table:
        raise DataEaseClientError("创建数据集需要 --datasource-id 与 --table，或提供完整 --file")

    # 1) fields
    node_probe_id = snowflake_id()
    fields = client.post(
        "/datasetData/tableField",
        {
            "datasourceId": args.datasource_id,
            "id": node_probe_id,
            "info": _table_info(args.table),
            "tableName": args.table,
            "type": args.table_type,
            "isCross": False,
        },
    )
    if not isinstance(fields, list) or not fields:
        raise DataEaseClientError(f"未获取到表字段: {fields}")

    for f in fields:
        f["groupType"] = _infer_group_type_by_name(f.get("name"), f.get("deType"))

    union, all_fields = _build_union_and_fields(
        datasource_id=args.datasource_id,
        table_name=args.table,
        table_type=args.table_type,
        fields=fields,
    )

    ops = _load_json(None, args.ops_file) if args.ops_file else []
    if args.ops_json:
        ops = json.loads(args.ops_json)
    if ops:
        all_fields = _apply_field_ops(all_fields, ops)

    # 用户强制维度/指标映射 JSON: {"销售额":"q","省份":"d"}
    if args.dq_map:
        dq = json.loads(args.dq_map)
        for f in all_fields:
            if f.get("name") in dq and dq[f["name"]] in ("d", "q"):
                f["groupType"] = dq[f["name"]]

    name = args.name or f"{args.table}_数据集"
    mode = args.mode
    if mode is None:
        try:
            ds = client.get(f"/datasource/getSimpleDs/{args.datasource_id}")
            dstype = (ds or {}).get("type") if isinstance(ds, dict) else None
            mode = 1 if dstype in ("Excel", "ExcelRemote", "API") else 0
        except DataEaseClientError:
            mode = 0

    encoded_fields = _encode_calc_fields(all_fields)
    preview_body = {"union": union, "allFields": encoded_fields, "isCross": False}
    if not args.skip_preview:
        preview = client.post("/datasetData/previewData", preview_body)
        # 预览失败会抛错；成功可简要输出字段数
        print(
            f"preview ok fields={len((preview or {}).get('data', {}).get('fields') or [])}",
            file=sys.stderr,
        )

    body = {
        "name": name,
        "pid": pid,
        "nodeType": "dataset",
        "type": "union",
        "mode": mode,
        "union": union,
        "allFields": encoded_fields,
        "isCross": False,
    }
    data = client.post("/datasetTree/create", body)
    _print_json(data)


def cmd_tree(client: DataEaseClient, args: argparse.Namespace) -> None:
    body = {"busiFlag": "dataset"}
    if args.name:
        body["name"] = args.name
    _print_json(client.post("/datasetTree/tree", body))


def cmd_get(client: DataEaseClient, args: argparse.Namespace) -> None:
    _print_json(client.post(f"/datasetTree/get/{args.id}", {}))


def cmd_classify(client: DataEaseClient, args: argparse.Namespace) -> None:
    """仅输出字段维度/指标建议，不保存。"""
    fields = client.post(
        "/datasetData/tableField",
        {
            "datasourceId": args.datasource_id,
            "id": snowflake_id(),
            "info": _table_info(args.table),
            "tableName": args.table,
            "type": args.table_type,
            "isCross": False,
        },
    )
    rows = []
    for f in fields if isinstance(fields, list) else []:
        name = f.get("name") or f.get("originName")
        de_type = f.get("deType")
        default_gt = _default_group_type(de_type)
        inferred = _infer_group_type_by_name(name, de_type)
        rows.append(
            {
                "name": name,
                "deType": de_type,
                "defaultGroupType": default_gt,
                "inferredGroupType": inferred,
                "label": "维度" if inferred == "d" else "指标",
            }
        )
    _print_json(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DataEase V3 数据集管理 CLI")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("tree", help="数据集树")
    t.add_argument("--name", default=None)
    t.set_defaults(func=cmd_tree)

    g = sub.add_parser("get", help="数据集详情")
    g.add_argument("--id", required=True)
    g.set_defaults(func=cmd_get)

    tb = sub.add_parser("tables", help="数据源下表列表")
    tb.add_argument("--datasource-id", required=True)
    tb.set_defaults(func=cmd_tables)

    f = sub.add_parser("fields", help="表字段（含维度/指标建议）")
    f.add_argument("--datasource-id", required=True)
    f.add_argument("--table", required=True)
    f.add_argument("--table-type", default="db")
    f.add_argument("--node-id", default=None)
    f.add_argument("--infer-dq", action="store_true", help="按命名推断维度/指标")
    f.set_defaults(func=cmd_fields)

    c = sub.add_parser("classify", help="输出字段维度/指标判定")
    c.add_argument("--datasource-id", required=True)
    c.add_argument("--table", required=True)
    c.add_argument("--table-type", default="db")
    c.set_defaults(func=cmd_classify)

    pv = sub.add_parser("preview", help="预览数据集数据")
    pv.add_argument("--file")
    pv.add_argument("--json")
    pv.add_argument("--datasource-id")
    pv.add_argument("--table")
    pv.add_argument("--table-type", default="db")
    pv.set_defaults(func=cmd_preview)

    rf = sub.add_parser("resolve-folder", help="在数据集树上按 id/名称解析文件夹")
    rf.add_argument("--id", default=None)
    rf.add_argument("--name", default=None)
    rf.set_defaults(func=cmd_resolve_folder)

    mv = sub.add_parser("move", help="移动数据集到目标文件夹")
    mv.add_argument("--id", required=True)
    mv.add_argument("--pid", type=int, default=None)
    mv.add_argument("--folder-name", default=None)
    mv.add_argument("--name", default=None, help="可选，默认保持原名")
    mv.set_defaults(func=cmd_move)

    cr = sub.add_parser("create", help="新建数据集（预览后保存到目标文件夹）")
    cr.add_argument("--name", default=None, help="数据集名称，默认 表名_数据集")
    cr.add_argument("--pid", type=int, default=None)
    cr.add_argument("--folder-name", default=None)
    cr.add_argument("--datasource-id")
    cr.add_argument("--table")
    cr.add_argument("--table-type", default="db", help="db / sql 等，Excel 物理表通常仍用 db")
    cr.add_argument("--mode", type=int, default=None, help="0直连 1同步；默认按数据源类型")
    cr.add_argument("--file", help="完整 DatasetGroupInfoDTO JSON")
    cr.add_argument("--json")
    cr.add_argument("--ops-file", help="字段操作 JSON 文件（copy/calc/group）")
    cr.add_argument("--ops-json", help="字段操作 JSON 字符串")
    cr.add_argument("--dq-map", help='强制维度指标映射 JSON，如 {"销售额":"q"}')
    cr.add_argument("--skip-preview", action="store_true")
    cr.set_defaults(func=cmd_create)

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
