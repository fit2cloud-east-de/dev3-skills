"""面板级「图表联动」与「图表跳转」配置（数据大屏 / 仪表板共用）。

两套能力都不在画布 JSON 里，而是独立接口写入编辑稿（snapshot）：
- 联动：POST /linkage/saveLinkage、/linkage/updateLinkageActive、/linkage/removeLinkage
- 跳转：POST /linkJump/updateJumpSet、/linkJump/updateJumpSetActive、/linkJump/removeJumpSet

运行时生效条件（缺一不生效，写错不报错但点了没反应，务必自检）：
- 联动：源图表 linkage_active=true，且联动关系 linkage_active=true，且关联字段有 id
- 跳转：源图表 jump_active=true，且字段级 checked=true（inner 还需 target_dv_id）

字段一律用「数据集字段 id」对齐；本模块负责把「图表字段名」翻译成 id，
避免调用方手抄 id 出错。
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from typing import Any, Optional

from de_client import DataEaseClient, DataEaseClientError

RESOURCE_TABLE = "snapshot"

LINK_TYPES = ("outer", "inner")
JUMP_TYPES = ("_self", "_blank", "newPop")
WINDOW_SIZES = ("large", "middle", "small")
TARGET_TYPES = ("view", "filter", "outParams")

CONTENT_MAX = 4000

# 图表里「已使用字段」所在的位置：跳转源字段必须落在其中之一
USED_FIELD_KEYS = ("xAxis", "xAxisExt", "extStack", "yAxis", "yAxisExt", "drillFields")


# ------------------------------------------------------------------ 基础工具


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def get_panel_views(client: DataEaseClient, dv_id: str, *, busi_flag: str = "dataV") -> dict[str, dict]:
    """读取编辑稿里的全部图表视图（canvasViewInfo）。"""
    data = client.post(
        "/dataVisualization/findById",
        {
            "id": str(dv_id),
            "busiFlag": busi_flag,
            "resourceTable": RESOURCE_TABLE,
            "source": "main-edit",
        },
    )
    if not isinstance(data, dict):
        raise DataEaseClientError(f"找不到面板 id={dv_id}")
    views = data.get("canvasViewInfo") or {}
    if not isinstance(views, dict):
        raise DataEaseClientError(f"面板 id={dv_id} 的 canvasViewInfo 结构异常")
    return {str(k): v for k, v in views.items() if isinstance(v, dict)}


def field_label(field: dict) -> str:
    return str(field.get("name") or field.get("originName") or field.get("id"))


def used_fields(view: dict) -> list[dict]:
    """图表实际参与绘制的字段（跳转可选字段来源）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for key in USED_FIELD_KEYS:
        for f in view.get(key) or []:
            if not isinstance(f, dict) or f.get("id") in (None, "", -1):
                continue
            fid = str(f.get("id"))
            if fid in seen:
                continue
            seen.add(fid)
            out.append(f)
    return out


def _title_of(view: dict) -> str:
    return str(view.get("title") or view.get("id"))


def resolve_view(views: dict[str, dict], spec: Any, *, role: str = "图表") -> str:
    """把图表标题或组件 id 解析成 view id；歧义/找不到都明确报错。"""
    if spec is None or str(spec).strip() == "":
        raise DataEaseClientError(f"{role}不能为空")
    s = str(spec).strip()
    if s in views:
        return s
    by_title = [vid for vid, v in views.items() if _title_of(v) == s]
    if len(by_title) == 1:
        return by_title[0]
    if len(by_title) > 1:
        raise DataEaseClientError(
            f"{role}「{s}」重名，无法确定目标。请改用组件 id：{', '.join(by_title)}"
        )
    low = s.lower()
    fuzzy = [vid for vid, v in views.items() if _title_of(v).lower() == low]
    if len(fuzzy) == 1:
        return fuzzy[0]
    catalog = ", ".join(f"{_title_of(v)}({vid})" for vid, v in views.items()) or "（空）"
    raise DataEaseClientError(f"找不到{role}「{s}」。当前面板可选：{catalog}")


def _field_index(fields: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for f in fields:
        for key in (str(f.get("id")), f.get("name"), f.get("originName")):
            if key:
                idx[str(key)] = f
    return idx


def resolve_field(fields: list[dict], spec: Any, *, role: str = "字段") -> dict:
    s = str(spec or "").strip().strip("[]")
    if not s:
        raise DataEaseClientError(f"{role}不能为空")
    idx = _field_index(fields)
    hit = idx.get(s) or idx.get(s.lower())
    if hit:
        return hit
    names = ", ".join(field_label(f) for f in fields) or "（空）"
    raise DataEaseClientError(f"找不到{role}「{s}」。可用字段：{names}")


# ------------------------------------------------------------------ 联动


def linkage_candidates(
    client: DataEaseClient, dv_id: str, source_view_id: str, view_ids: list[str]
) -> list[dict]:
    """联动候选：一次拿到所有目标图表、其数据集字段、以及已有联动配置。"""
    data = client.post(
        "/linkage/getViewLinkageGatherArray",
        {
            "dvId": str(dv_id),
            "sourceViewId": str(source_view_id),
            "targetViewIds": [str(v) for v in view_ids],
            "resourceTable": RESOURCE_TABLE,
        },
    )
    return [x for x in (data or []) if isinstance(x, dict)]


def _pair_linkage_fields(
    source_fields: list[dict],
    target_fields: list[dict],
    pairs: Optional[list],
    *,
    source_used: Optional[list[dict]] = None,
) -> list[dict]:
    if pairs:
        out = []
        for pair in pairs:
            if isinstance(pair, dict):
                sf = pair.get("source") or pair.get("from")
                tf = pair.get("target") or pair.get("to")
            elif isinstance(pair, (list, tuple)) and len(pair) == 2:
                sf, tf = pair
            else:
                raise DataEaseClientError(f"联动字段映射格式无法识别: {pair}")
            s = resolve_field(source_fields, sf, role="源字段")
            t = resolve_field(target_fields, tf, role="目标字段")
            out.append({"sourceField": str(s.get("id")), "targetField": str(t.get("id"))})
        return out
    # 未指定 → 只取源图表真正用到的字段，按同名自动配对（避免把整张表字段全挂上）
    t_idx = {str(f.get("name") or f.get("originName")): f for f in target_fields}
    pool = source_used if source_used else source_fields
    out = []
    for f in pool:
        name = str(f.get("name") or f.get("originName"))
        hit = t_idx.get(name)
        if hit:
            out.append({"sourceField": str(f.get("id")), "targetField": str(hit.get("id"))})
    return out


def apply_linkage(
    client: DataEaseClient,
    dv_id: str,
    views: dict[str, dict],
    items: list[dict],
    *,
    replace: bool = False,
) -> list[dict]:
    """按 plan 里的 linkage 列表写入联动关系；默认合并（只增改，不删已有目标）。"""
    report: list[dict] = []
    view_ids = list(views.keys())
    for i, item in enumerate(items or []):
        if not isinstance(item, dict):
            raise DataEaseClientError(f"linkage[{i}] 必须是对象")
        source_id = resolve_view(views, item.get("source") or item.get("sourceView"), role="联动源图表")
        targets = item.get("targets") or item.get("targetViews") or item.get("target")
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            raise DataEaseClientError(f"linkage[{i}] 缺少 targets（联动目标图表）")

        candidates = linkage_candidates(client, dv_id, source_id, view_ids)
        if not candidates:
            raise DataEaseClientError(
                f"联动源「{_title_of(views[source_id])}」没有可用目标图表；"
                "面板里至少要有两个可联动图表"
            )
        cand_by_id = {str(c.get("targetViewId")): c for c in candidates}
        src_cand = cand_by_id.get(str(source_id)) or {}
        source_fields = src_cand.get("targetViewFields") or used_fields(views[source_id])
        # 自动配对只认源图表用到的字段，避免把整张数据集字段全挂上
        source_used = used_fields(views[source_id])
        if not source_fields:
            raise DataEaseClientError(f"联动源「{_title_of(views[source_id])}」无法取到数据集字段")

        # 合并模式：先保留目标之外的已有配置
        keep: list[dict] = []
        if not replace:
            for c in candidates:
                tid = str(c.get("targetViewId"))
                if tid == str(source_id):
                    continue
                if c.get("linkageActive") and c.get("linkageFields"):
                    keep.append(
                        {
                            "targetViewId": tid,
                            "linkageActive": True,
                            "linkageFields": [
                                {
                                    "sourceField": str(f.get("sourceField")),
                                    "targetField": str(f.get("targetField")),
                                }
                                for f in c["linkageFields"]
                                if f.get("sourceField") and f.get("targetField")
                            ],
                        }
                    )

        built: list[dict] = []
        for tspec in targets:
            tid = resolve_view(views, tspec, role="联动目标图表")
            if tid == str(source_id):
                raise DataEaseClientError("联动目标不能是源图表自身")
            cand = cand_by_id.get(tid)
            if not cand:
                raise DataEaseClientError(f"目标图表 {tid} 不在联动候选中，请确认其已保存且非查询组件")
            target_fields = cand.get("targetViewFields") or used_fields(views[tid])
            if not target_fields:
                raise DataEaseClientError(
                    f"目标图表「{_title_of(views[tid])}」无法取到数据集字段，无法建立联动"
                )
            active = item.get("active")
            active = True if active is None else bool(active)
            pairs = _pair_linkage_fields(
                source_fields, target_fields, item.get("fields"), source_used=source_used
            )
            if active and not pairs:
                raise DataEaseClientError(
                    f"「{_title_of(views[source_id])}」→「{_title_of(views[tid])}」"
                    "找不到可配对的同名字段，请在 fields 里显式写 {source, target}"
                )
            built.append(
                {
                    "targetViewId": tid,
                    "targetViewName": cand.get("targetViewName") or _title_of(views[tid]),
                    "targetViewType": cand.get("targetViewType") or views[tid].get("type"),
                    "tableId": cand.get("tableId"),
                    "linkageActive": active,
                    "linkageFields": pairs,
                }
            )

        merged = {str(x["targetViewId"]): x for x in keep}
        for x in built:
            merged[str(x["targetViewId"])] = x
        payload_list = list(merged.values())

        client.post(
            "/linkage/saveLinkage",
            {
                "dvId": str(dv_id),
                "sourceViewId": str(source_id),
                "resourceTable": RESOURCE_TABLE,
                "linkageInfo": payload_list,
            },
        )
        client.post(
            "/linkage/updateLinkageActive",
            {
                "dvId": str(dv_id),
                "sourceViewId": str(source_id),
                "activeStatus": bool(item.get("linkageActive", True)),
            },
        )
        report.append(
            {
                "source": _title_of(views[source_id]),
                "sourceViewId": source_id,
                "mode": "replace" if replace else "merge",
                "targets": [
                    {
                        "target": x.get("targetViewName"),
                        "targetViewId": x["targetViewId"],
                        "active": x["linkageActive"],
                        "fields": [
                            {"sourceField": f["sourceField"], "targetField": f["targetField"]}
                            for f in x["linkageFields"]
                        ],
                    }
                    for x in payload_list
                ],
            }
        )
    return report


def list_linkage(client: DataEaseClient, dv_id: str, views: dict[str, dict]) -> dict:
    """面板联动全貌。后端返回 {sourceViewId#sourceFieldId: [targetViewId#targetFieldId,...]}。"""
    raw = client.get(f"/linkage/getVisualizationAllLinkageInfo/{dv_id}/{RESOURCE_TABLE}") or {}
    by_source: dict[str, dict] = {}
    for key, targets in (raw or {}).items():
        vid, _, fid = str(key).partition("#")
        src = views.get(vid) or {}
        entry = by_source.setdefault(
            vid,
            {
                "sourceViewId": vid,
                "source": _title_of(src) if src else None,
                "pairs": [],
            },
        )
        for t in targets or []:
            tvid, _, tfid = str(t).partition("#")
            t_view = views.get(tvid) or {}
            entry["pairs"].append(
                {
                    "targetViewId": tvid,
                    "target": _title_of(t_view) if t_view else None,
                    "sourceFieldId": fid or None,
                    "targetFieldId": tfid or None,
                }
            )
    return {"dvId": str(dv_id), "linkage": list(by_source.values())}


def remove_linkage(client: DataEaseClient, dv_id: str, views: dict[str, dict], source: str) -> dict:
    source_id = resolve_view(views, source, role="联动源图表")
    client.post(
        "/linkage/removeLinkage",
        {"dvId": str(dv_id), "sourceViewId": source_id, "resourceTable": RESOURCE_TABLE},
    )
    return {"source": _title_of(views[source_id]), "sourceViewId": source_id, "removed": True}


def set_linkage_active(
    client: DataEaseClient, dv_id: str, views: dict[str, dict], source: str, active: bool
) -> dict:
    source_id = resolve_view(views, source, role="联动源图表")
    client.post(
        "/linkage/updateLinkageActive",
        {"dvId": str(dv_id), "sourceViewId": source_id, "activeStatus": bool(active)},
    )
    return {"source": _title_of(views[source_id]), "sourceViewId": source_id, "linkageActive": bool(active)}


# ------------------------------------------------------------------ 跳转


def query_jump_of_view(client: DataEaseClient, dv_id: str, view_id: str) -> dict:
    data = client.get(f"/linkJump/queryWithViewId/{dv_id}/{view_id}")
    return data if isinstance(data, dict) else {}


def jump_target_views(client: DataEaseClient, target_dv_id: str) -> dict[str, dict]:
    """目标面板可跳转的图表 + 过滤组件 + 外部参数。"""
    data = client.get(f"/linkJump/viewTableDetailList/{target_dv_id}") or {}
    views = {}
    for v in data.get("visualizationViewTables") or []:
        views[str(v.get("id"))] = {
            "id": str(v.get("id")),
            "title": v.get("title"),
            "type": v.get("type"),
            "tableId": v.get("tableId"),
            "fields": v.get("tableFields") or [],
            "targetType": "view",
        }
    bash = data.get("bashComponentData")
    if bash:
        try:
            comps = json.loads(bash)
        except (TypeError, json.JSONDecodeError):
            comps = []
        for c in comps if isinstance(comps, list) else []:
            if c.get("component") == "VQuery" and isinstance(c.get("propValue"), list):
                for f in c["propValue"]:
                    views[str(f.get("id"))] = {
                        "id": str(f.get("id")),
                        "title": f.get("name"),
                        "type": "filter",
                        "tableId": None,
                        "fields": [{"id": "1000001", "name": "过滤组件参数"}],
                        "targetType": "filter",
                    }
    for o in data.get("outParamsJumpInfo") or []:
        views[str(o.get("id"))] = {
            "id": str(o.get("id")),
            "title": o.get("name") or o.get("title"),
            "type": "outerParams",
            "tableId": None,
            "fields": [{"id": "1000001", "name": "外部参数"}],
            "targetType": "outParams",
        }
    if not views:
        views = _fallback_target_views(client, target_dv_id)
    return views


def _fallback_target_views(client: DataEaseClient, target_dv_id: str) -> dict[str, dict]:
    """目标面板还没发布过时，跳转明细接口查不到图表；退回读编辑稿的 canvasViewInfo。

    代价：只能匹配该图表「已用到」的字段，字段范围比发布后略窄。
    """
    for flag in ("dataV", "dashboard"):
        try:
            panel = get_panel_views(client, target_dv_id, busi_flag=flag)
        except DataEaseClientError:
            continue
        out: dict[str, dict] = {}
        for vid, v in panel.items():
            if str(v.get("type")) == "VQuery":
                continue
            fields = used_fields(v)
            if not fields:
                continue
            out[vid] = {
                "id": vid,
                "title": _title_of(v),
                "type": v.get("type"),
                "tableId": v.get("tableId"),
                "fields": fields,
                "targetType": "view",
            }
        if out:
            warn(
                f"目标面板 {target_dv_id} 尚未发布，跳转目标改用编辑稿解析，"
                "只能匹配各图表已使用的字段；发布后再配可放宽到整表字段"
            )
            return out
    return {}


def _content_to_ids(content: str, name_to_id: dict[str, str]) -> str:
    """界面里写 [字段名]，保存时必须转成 [字段id]。"""
    import re

    def repl(m: re.Match) -> str:
        token = m.group(1)
        fid = name_to_id.get(token)
        if fid is None:
            # 允许直接写 id
            if token.isdigit():
                return f"[{token}]"
            raise DataEaseClientError(
                f"链接内容里的占位符 [{token}] 不是该图表的字段。可用：{', '.join(name_to_id) or '（无）'}"
            )
        return f"[{fid}]"

    return re.sub(r"\[([^\]]+)\]", repl, content)


def _build_target_view_infos(
    client: DataEaseClient,
    *,
    target_dv_id: str,
    source_field: dict,
    source_fields: list[dict],
    targets: list,
) -> list[dict]:
    if not targets:
        raise DataEaseClientError(
            "内部跳转必须提供 targets（目标图表及其字段映射），例如 "
            '[{"view": "目标图表", "fields": [{"source": "省份", "target": "省份"}]}]'
        )
    tv = jump_target_views(client, target_dv_id)
    if not tv:
        raise DataEaseClientError(f"目标面板 {target_dv_id} 没有可跳转的图表/过滤组件")
    sf_id = str(source_field.get("id"))
    sf_name = field_label(source_field)
    out: list[dict] = []
    for spec in targets:
        if not isinstance(spec, dict):
            raise DataEaseClientError(f"跳转目标格式无法识别: {spec}")
        key = spec.get("view") or spec.get("targetView") or spec.get("name") or spec.get("id")
        hit = tv.get(str(key))
        if not hit:
            if not key:
                raise DataEaseClientError("跳转目标缺少 view（目标图表标题或 id）")
            by_title = [v for v in tv.values() if str(v.get("title")) == str(key)]
            hit = by_title[0] if len(by_title) == 1 else None
        if not hit:
            names = [f"{v.get('title')}({k})" for k, v in tv.items()]
            raise DataEaseClientError(f"目标面板里找不到「{key}」。可选：{', '.join(names)}")
        ttype = spec.get("type") or hit.get("targetType") or "view"
        if ttype not in TARGET_TYPES:
            raise DataEaseClientError(f"targetType 只能是 {TARGET_TYPES}，收到 {ttype}")
        pairs = spec.get("fields")
        if not pairs:
            # 未给映射：先按同名匹配，再按同 id 匹配
            cand = [f for f in hit["fields"] if str(f.get("name") or f.get("originName")) == sf_name]
            if not cand:
                cand = [f for f in hit["fields"] if str(f.get("id")) == sf_id]
            if not cand:
                avail = ", ".join(field_label(f) for f in hit["fields"]) or "（空）"
                raise DataEaseClientError(
                    f"目标「{hit.get('title')}」里找不到与源字段「{sf_name}」对应的字段（可选：{avail}），"
                    "请显式写 fields: [{\"source\": ..., \"target\": ...}]"
                )
            pairs = [{"source": sf_id, "target": field_label(cand[0])}]
        if isinstance(pairs, dict):
            pairs = [pairs]
        for pair in pairs:
            if isinstance(pair, dict):
                sf = pair.get("source")
                tf = pair.get("target")
            else:
                sf, tf = sf_id, pair
            s_field = source_field if sf in (None, "", sf_id) else resolve_field(source_fields, sf, role="源字段")
            t_field = resolve_field(hit["fields"], tf, role="目标字段")
            out.append(
                {
                    "targetViewId": str(hit["id"]),
                    "targetType": ttype,
                    "sourceFieldActiveId": str(s_field.get("id")),
                    "targetFieldId": str(t_field.get("id")),
                }
            )
    return out


def apply_jump(
    client: DataEaseClient,
    dv_id: str,
    views: dict[str, dict],
    items: list[dict],
    *,
    replace: bool = False,
) -> list[dict]:
    """按 plan 里的 jump 列表写入跳转；默认合并（保留其它字段已有跳转）。"""
    report: list[dict] = []
    for i, item in enumerate(items or []):
        if not isinstance(item, dict):
            raise DataEaseClientError(f"jump[{i}] 必须是对象")
        source_id = resolve_view(views, item.get("source") or item.get("sourceView"), role="跳转源图表")
        view = views[source_id]
        title = _title_of(view)

        existing = query_jump_of_view(client, dv_id, source_id)
        existing_array = [x for x in (existing.get("linkJumpInfoArray") or []) if isinstance(x, dict)]
        name_to_id = {
            str(x.get("sourceFieldName")): str(x.get("sourceFieldId"))
            for x in existing_array
            if x.get("sourceFieldName") and x.get("sourceFieldId")
        }
        allowed = used_fields(view)
        if not allowed and not name_to_id:
            raise DataEaseClientError(f"图表「{title}」没有可用字段（可能不是数据集图表），无法配置跳转")

        fields_spec = item.get("fields") or item.get("field")
        if isinstance(fields_spec, (str, dict)):
            fields_spec = [fields_spec]
        if not fields_spec:
            raise DataEaseClientError(f"jump[{i}] 缺少 field（触发字段）")

        resolved: list[tuple[dict, Optional[dict]]] = []
        for fspec in fields_spec:
            fname = (fspec.get("name") or fspec.get("field")) if isinstance(fspec, dict) else fspec
            resolved.append((resolve_field(allowed, fname, role="触发字段"), fspec if isinstance(fspec, dict) else None))
        built_ids = {str(f.get("id")) for f, _ in resolved}

        # 合并模式：保留本次未涉及字段的已有跳转
        keep: list[dict] = []
        if not replace:
            for x in existing_array:
                if x.get("checked") and str(x.get("sourceFieldId")) not in built_ids:
                    keep.append(x)

        def pick(key: str, fspec: Optional[dict], default: Any = None) -> Any:
            if fspec is not None and fspec.get(key) is not None:
                return fspec[key]
            if item.get(key) is not None:
                return item[key]
            return default

        built: list[dict] = []
        for field, fspec in resolved:
            fid = str(field.get("id"))
            link_type = str(pick("linkType", fspec, "outer"))
            if link_type not in LINK_TYPES:
                raise DataEaseClientError(f"linkType 只能是 {LINK_TYPES}，收到 {link_type}")
            jump_type = str(pick("jumpType", fspec, "_blank"))
            if jump_type not in JUMP_TYPES:
                raise DataEaseClientError(f"jumpType 只能是 {JUMP_TYPES}，收到 {jump_type}")
            window = str(pick("windowSize", fspec, "middle"))
            if window not in WINDOW_SIZES:
                raise DataEaseClientError(f"windowSize 只能是 {WINDOW_SIZES}，收到 {window}")

            entry: dict[str, Any] = {
                "sourceFieldId": fid,
                "sourceFieldName": field_label(field),
                "linkType": link_type,
                "jumpType": jump_type,
                "windowSize": window,
                "targetDvId": None,
                "content": None,
                "checked": bool(pick("checked", fspec, True)),
                "attachParams": bool(pick("attachParams", fspec, False)),
                "targetViewInfoList": [],
            }

            if link_type == "inner":
                target_dv_id = pick("targetDvId", fspec) or pick("targetDv", fspec)
                if not target_dv_id:
                    raise DataEaseClientError(
                        f"字段「{field_label(field)}」为内部跳转，必须给 targetDvId（目标仪表板/大屏 id）"
                    )
                entry["targetDvId"] = str(target_dv_id)
                entry["targetViewInfoList"] = _build_target_view_infos(
                    client,
                    target_dv_id=str(target_dv_id),
                    source_field=field,
                    source_fields=allowed,
                    targets=pick("targets", fspec),
                )
            else:
                content = pick("content", fspec)
                if not content:
                    raise DataEaseClientError(
                        f"字段「{field_label(field)}」为外部链接，必须给 content"
                        '（如 "https://example.com/detail?prov=[省份]"）'
                    )
                if len(str(content)) > CONTENT_MAX:
                    raise DataEaseClientError(f"content 超过 {CONTENT_MAX} 字符上限")
                entry["content"] = _content_to_ids(str(content), name_to_id)

            built.append(entry)

        merged = [x for x in keep if str(x.get("sourceFieldId")) not in built_ids] + built

        client.post(
            "/linkJump/updateJumpSet",
            {
                "sourceDvId": str(dv_id),
                "sourceViewId": source_id,
                "resourceTable": RESOURCE_TABLE,
                "checked": bool(item.get("checked", True)),
                "linkJumpInfo": None,
                "linkJumpInfoArray": merged,
            },
        )
        client.post(
            "/linkJump/updateJumpSetActive",
            {
                "sourceDvId": str(dv_id),
                "sourceViewId": source_id,
                "activeStatus": bool(item.get("jumpActive", True)),
                "resourceTable": RESOURCE_TABLE,
            },
        )
        report.append(
            {
                "source": title,
                "sourceViewId": source_id,
                "mode": "replace" if replace else "merge",
                "jumpActive": bool(item.get("jumpActive", True)),
                "fields": [
                    {
                        "field": x.get("sourceFieldName"),
                        "sourceFieldId": x["sourceFieldId"],
                        "linkType": x["linkType"],
                        "jumpType": x["jumpType"],
                        "targetDvId": x.get("targetDvId"),
                        "content": (x.get("content") or "")[:120] or None,
                        "targets": len(x.get("targetViewInfoList") or []),
                    }
                    for x in built
                ],
            }
        )
    return report


def list_jump(client: DataEaseClient, dv_id: str, views: dict[str, dict]) -> dict:
    raw = client.get(f"/linkJump/queryVisualizationJumpInfo/{dv_id}/{RESOURCE_TABLE}") or {}
    base = raw.get("baseJumpInfoMap") or {}
    out = []
    for key, info in (base or {}).items():
        vid = str(key).split("#")[0]
        out.append(
            {
                "sourceViewId": vid,
                "source": _title_of(views[vid]) if vid in views else None,
                "sourceField": info.get("sourceFieldName"),
                "linkType": info.get("linkType"),
                "jumpType": info.get("jumpType"),
                "windowSize": info.get("windowSize"),
                "targetDvId": info.get("targetDvId"),
                "targetDvType": info.get("targetDvType"),
                "content": info.get("content"),
                "attachParams": info.get("attachParams"),
            }
        )
    return {"dvId": str(dv_id), "activeJumpCount": len(out), "jump": out}


def jump_fields(client: DataEaseClient, dv_id: str, views: dict[str, dict], source: str) -> dict:
    source_id = resolve_view(views, source, role="跳转源图表")
    view = views[source_id]
    allowed = used_fields(view)
    existing = query_jump_of_view(client, dv_id, source_id)
    configured = {
        str(x.get("sourceFieldId")): x for x in (existing.get("linkJumpInfoArray") or []) if x.get("checked")
    }
    return {
        "source": _title_of(view),
        "sourceViewId": source_id,
        "jumpActive": bool(view.get("jumpActive")),
        "fields": [
            {
                "id": str(f.get("id")),
                "name": field_label(f),
                "deType": f.get("deType"),
                "groupType": f.get("groupType"),
                "configured": str(f.get("id")) in configured,
            }
            for f in allowed
        ],
    }


def remove_jump(client: DataEaseClient, dv_id: str, views: dict[str, dict], source: str) -> dict:
    source_id = resolve_view(views, source, role="跳转源图表")
    client.post(
        "/linkJump/removeJumpSet",
        {"sourceDvId": str(dv_id), "sourceViewId": source_id, "resourceTable": RESOURCE_TABLE},
    )
    return {"source": _title_of(views[source_id]), "sourceViewId": source_id, "removed": True}


def set_jump_active(
    client: DataEaseClient, dv_id: str, views: dict[str, dict], source: str, active: bool
) -> dict:
    source_id = resolve_view(views, source, role="跳转源图表")
    client.post(
        "/linkJump/updateJumpSetActive",
        {
            "sourceDvId": str(dv_id),
            "sourceViewId": source_id,
            "activeStatus": bool(active),
            "resourceTable": RESOURCE_TABLE,
        },
    )
    return {"source": _title_of(views[source_id]), "sourceViewId": source_id, "jumpActive": bool(active)}


# ------------------------------------------------------------------ 交付自检


def self_check(report: dict) -> list[str]:
    """写入后提醒那些「配置成功但运行时可能不生效」的情况。"""
    tips: list[str] = []
    for item in report.get("linkage") or []:
        if not item.get("targets"):
            tips.append(f"联动「{item.get('source')}」没有任何目标图表，运行时不会触发")
        for t in item.get("targets") or []:
            if t.get("active") and not t.get("fields"):
                tips.append(f"联动「{item.get('source')}」→「{t.get('target')}」未写入关联字段")
    for item in report.get("jump") or []:
        if not item.get("fields"):
            tips.append(f"跳转「{item.get('source')}」没有写入任何字段")
    return tips


def warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


# ------------------------------------------------------------------ CLI 装配


def _load_json(raw: Optional[str], file_path: Optional[str]) -> Any:
    from pathlib import Path

    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8-sig"))
    if raw:
        return json.loads(raw)
    return None


def _load_items(args: Any, key: str) -> Optional[list]:
    payload = _load_json(getattr(args, "json", None), getattr(args, "file", None))
    if payload is None:
        return None
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get(key) or payload.get("items")
        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return items
        # 单个对象即一项
        if key in payload or payload.get("source") or payload.get("sourceView"):
            return [payload]
    raise DataEaseClientError(f"{key} 配置格式无法识别，应为数组或含 {key} 数组的对象")


def _parse_pairs(raw: Optional[list]) -> list:
    out = []
    for pair in raw or []:
        if "=" in str(pair):
            a, b = str(pair).split("=", 1)
            out.append({"source": a.strip(), "target": b.strip()})
        else:
            out.append({"source": str(pair).strip(), "target": str(pair).strip()})
    return out


def _views_of(client: DataEaseClient, args: Any) -> dict[str, dict]:
    return get_panel_views(client, args.id, busi_flag=getattr(args, "busi_flag", "dataV"))


def cmd_linkage_list(client: DataEaseClient, args: Any) -> None:
    _print_json(list_linkage(client, args.id, _views_of(client, args)))


def cmd_linkage_set(client: DataEaseClient, args: Any) -> None:
    items = _load_items(args, "linkage")
    if items is None:
        if not getattr(args, "source", None):
            raise DataEaseClientError("linkage set 需要 --source（源图表标题或 id），或用 --file 提供 linkage 数组")
        items = [
            {
                "source": args.source,
                "targets": getattr(args, "target", None) or [],
                "fields": _parse_pairs(getattr(args, "field", None)),
                "linkageActive": not bool(getattr(args, "no_active", False)),
            }
        ]
    report = apply_linkage(client, args.id, _views_of(client, args), items, replace=bool(getattr(args, "replace", False)))
    tips = self_check({"linkage": report})
    for t in tips:
        warn(t)
    _print_json({"dvId": str(args.id), "linkage": report, "tips": tips})


def cmd_linkage_remove(client: DataEaseClient, args: Any) -> None:
    _print_json(remove_linkage(client, args.id, _views_of(client, args), args.source))


def cmd_linkage_active(client: DataEaseClient, args: Any) -> None:
    _print_json(
        set_linkage_active(client, args.id, _views_of(client, args), args.source, not bool(args.off))
    )


def cmd_jump_list(client: DataEaseClient, args: Any) -> None:
    _print_json(list_jump(client, args.id, _views_of(client, args)))


def cmd_jump_fields(client: DataEaseClient, args: Any) -> None:
    _print_json(jump_fields(client, args.id, _views_of(client, args), args.source))


def cmd_jump_set(client: DataEaseClient, args: Any) -> None:
    items = _load_items(args, "jump")
    if items is None:
        if not getattr(args, "source", None):
            raise DataEaseClientError("jump set 需要 --source（源图表标题或 id），或用 --file 提供 jump 数组")
        if not (getattr(args, "field", None) or getattr(args, "fields", None)):
            raise DataEaseClientError("jump set 需要 --field（触发字段，可重复）")
        targets = None
        if getattr(args, "target", None):
            targets = [{"view": t} for t in args.target]
        item = {
            "source": args.source,
            "fields": [{"name": f} for f in (args.field or args.fields or [])],
            "linkType": getattr(args, "link_type", None) or "outer",
            "jumpType": getattr(args, "jump_type", None) or "_blank",
            "windowSize": getattr(args, "window_size", None) or "middle",
            "content": getattr(args, "content", None),
            "attachParams": bool(getattr(args, "attach_params", False)),
            "targetDvId": getattr(args, "target_dv_id", None),
            "targets": targets,
            "jumpActive": not bool(getattr(args, "no_active", False)),
        }
        items = [item]
    report = apply_jump(client, args.id, _views_of(client, args), items, replace=bool(getattr(args, "replace", False)))
    tips = self_check({"jump": report})
    for t in tips:
        warn(t)
    _print_json({"dvId": str(args.id), "jump": report, "tips": tips})


def cmd_jump_remove(client: DataEaseClient, args: Any) -> None:
    _print_json(remove_jump(client, args.id, _views_of(client, args), args.source))


def cmd_jump_active(client: DataEaseClient, args: Any) -> None:
    _print_json(set_jump_active(client, args.id, _views_of(client, args), args.source, not bool(args.off)))


def add_linkage_parser(sub: Any, *, busi_flag: str, label: str) -> None:
    p = sub.add_parser("linkage", help=f"{label}图表联动：list / set / remove / active")
    act = p.add_subparsers(dest="linkage_action", required=True)

    def base(parser: Any, need_source: bool = False) -> None:
        parser.add_argument("--id", required=True, help=f"{label} ID（dvId）")
        if need_source:
            parser.add_argument("--source", required=True, help="源图表标题或组件 id")
        parser.set_defaults(busi_flag=busi_flag)

    a = act.add_parser("list", help="查看现有联动关系")
    base(a)
    a.set_defaults(func=cmd_linkage_list)

    b = act.add_parser("set", help="写入联动（默认合并，--replace 重建）")
    base(b)
    b.add_argument("--source", default=None, help="源图表标题或组件 id（--file 时可省略）")
    b.add_argument("--target", action="append", help="目标图表标题或 id，可重复")
    b.add_argument("--field", action="append", help="关联字段 A=B（源字段=目标字段），可重复；省略则同名自动配对")
    b.add_argument("--file", help="linkage 数组 JSON 文件")
    b.add_argument("--json", help="linkage 数组 JSON 字符串")
    b.add_argument("--replace", action="store_true", help="清空该源图表已有联动后重建")
    b.add_argument("--no-active", action="store_true", help="写入但不启用（源图表联动开关置 false）")
    b.set_defaults(func=cmd_linkage_set)

    c = act.add_parser("remove", help="删除某源图表的全部联动")
    base(c, need_source=True)
    c.set_defaults(func=cmd_linkage_remove)

    d = act.add_parser("active", help="开关某源图表的联动总开关")
    base(d, need_source=True)
    d.add_argument("--off", action="store_true", help="关闭（默认开启）")
    d.set_defaults(func=cmd_linkage_active)


def add_jump_parser(sub: Any, *, busi_flag: str, label: str) -> None:
    p = sub.add_parser("jump", help=f"{label}图表跳转：list / fields / set / remove / active")
    act = p.add_subparsers(dest="jump_action", required=True)

    def base(parser: Any, need_source: bool = False) -> None:
        parser.add_argument("--id", required=True, help=f"{label} ID（dvId）")
        if need_source:
            parser.add_argument("--source", required=True, help="源图表标题或组件 id")
        parser.set_defaults(busi_flag=busi_flag)

    a = act.add_parser("list", help="查看已启用的跳转")
    base(a)
    a.set_defaults(func=cmd_jump_list)

    b = act.add_parser("fields", help="列出该图表可做跳转触发字段的字段")
    base(b, need_source=True)
    b.set_defaults(func=cmd_jump_fields)

    c = act.add_parser("set", help="写入跳转（默认合并，--replace 重建）")
    base(c)
    c.add_argument("--source", default=None, help="源图表标题或组件 id（--file 时可省略）")
    c.add_argument("--field", action="append", help="触发字段名，可重复")
    c.add_argument("--fields", action="append", help="同 --field")
    c.add_argument("--link-type", choices=list(LINK_TYPES), default=None, help="outer=外部链接 / inner=面板内跳转")
    c.add_argument("--jump-type", choices=list(JUMP_TYPES), default=None, help="_self / _blank / newPop")
    c.add_argument("--window-size", choices=list(WINDOW_SIZES), default=None, help="弹窗大小，仅 newPop 生效")
    c.add_argument("--content", default=None, help='外部链接，字段占位写 [字段名]，如 "https://x?p=[省份]"')
    c.add_argument("--target-dv-id", default=None, help="内部跳转的目标面板 id")
    c.add_argument("--target", action="append", help="目标图表标题或 id，可重复；字段默认同名匹配，精确映射请用 --file")
    c.add_argument("--attach-params", action="store_true", help="把当前过滤条件作为外部参数带过去")
    c.add_argument("--file", help="jump 数组 JSON 文件")
    c.add_argument("--json", help="jump 数组 JSON 字符串")
    c.add_argument("--replace", action="store_true", help="清空该图表已有跳转后重建")
    c.add_argument("--no-active", action="store_true", help="写入但不启用（源图表跳转开关置 false）")
    c.set_defaults(func=cmd_jump_set)

    d = act.add_parser("remove", help="删除某图表全部跳转")
    base(d, need_source=True)
    d.set_defaults(func=cmd_jump_remove)

    e = act.add_parser("active", help="开关某图表的跳转总开关")
    base(e, need_source=True)
    e.add_argument("--off", action="store_true", help="关闭（默认开启）")
    e.set_defaults(func=cmd_jump_active)


__all__ = [
    "RESOURCE_TABLE",
    "LINK_TYPES",
    "JUMP_TYPES",
    "WINDOW_SIZES",
    "TARGET_TYPES",
    "get_panel_views",
    "used_fields",
    "resolve_view",
    "resolve_field",
    "apply_linkage",
    "list_linkage",
    "remove_linkage",
    "set_linkage_active",
    "apply_jump",
    "list_jump",
    "jump_fields",
    "remove_jump",
    "set_jump_active",
    "query_jump_of_view",
    "jump_target_views",
    "self_check",
    "add_linkage_parser",
    "add_jump_parser",
]
