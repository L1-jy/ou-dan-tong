"""确定性校验 + 变更比对。"""
import re
import datetime

from prompts import STATUS_RANK

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _meaningful(v):
    s = str(v).strip() if v is not None else ""
    return s != "" and s != "待报价"


def validate_extraction(raw):
    """raw: LLM 返回的 list[dict]。返回 (orders, tasks, skipped)。"""
    orders, tasks, skipped = [], [], []
    for item in raw or []:
        t = item.get("type")
        if t == "order":
            customer = (item.get("customer") or "").strip()
            product = (item.get("product") or "").strip()
            if not customer or not product:
                skipped.append(item)
                continue
            dd = item.get("delivery_date")
            if dd and not DATE_RE.match(str(dd)):
                dd = None
            orders.append({
                "customer": customer,
                "product": product,
                "spec": (item.get("spec") or "").strip(),
                "qty": _to_int(item.get("qty")),
                "unit_price": (item.get("unit_price") or "待报价").strip(),
                "delivery_date": dd,
                "status": item.get("status_hint") or "沟通中",
                "sample_flag": item.get("sample_flag") or "无",
                "source_excerpt": (item.get("source_excerpt") or "").strip()[:100],
            })
        elif t == "task":
            content = (item.get("task_content") or "").strip()
            if not content:
                skipped.append(item)
                continue
            td = item.get("task_deadline")
            if td and not DATE_RE.match(str(td)):
                td = None
            tasks.append({
                "content": content,
                "owner": (item.get("owner") or "").strip(),
                "deadline": td,
                "status": "待办",
            })
        else:
            skipped.append(item)
    return orders, tasks, skipped


def apply_change(existing: dict, extracted: dict, now: str = None):
    """返回 (patch, change|None)。仅覆盖本次有值字段，并记录变更履历。"""
    now = now or datetime.datetime.now().isoformat(timespec="seconds")
    patch, changes = {}, []
    for field in ["spec", "qty", "unit_price", "delivery_date", "sample_flag"]:
        new = extracted.get(field)
        if _meaningful(new) and str(new) != str(existing.get(field)):
            changes.append((field, existing.get(field), new))
            patch[field] = new
    old_rank = STATUS_RANK.get(existing.get("status"), 0)
    new_rank = STATUS_RANK.get(extracted.get("status"), 0)
    if new_rank > old_rank:
        changes.append(("status", existing.get("status"), extracted["status"]))
        patch["status"] = extracted["status"]
    if changes:
        change = {
            "time": now,
            "field": ",".join(f for f, _, _ in changes),
            "old": " | ".join(str(o) for _, o, _ in changes),
            "new": " | ".join(str(n) for _, _, n in changes),
            "source": extracted.get("source_excerpt", ""),
        }
        return patch, change
    return patch, None
