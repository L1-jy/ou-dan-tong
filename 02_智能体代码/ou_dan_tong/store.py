"""本地 JSON 存储，对应订单 / 任务两张台账。"""
import json
import os
import datetime

from config import DATA_DIR


class Store:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.orders_file = os.path.join(data_dir, "orders.json")
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.orders = self._load(self.orders_file)
        self.tasks = self._load(self.tasks_file)

    def _load(self, path):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def save(self):
        with open(self.orders_file, "w", encoding="utf-8") as f:
            json.dump(self.orders, f, ensure_ascii=False, indent=2)
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    def reset(self):
        self.orders, self.tasks = [], []
        self.save()

    def next_order_id(self, date: str = None):
        date = date or datetime.date.today().strftime("%Y%m%d")
        n = sum(1 for o in self.orders if date in o["order_id"]) + 1
        return f"ORD-{date}-{n:02d}"

    def next_task_id(self, date: str = None):
        date = date or datetime.date.today().strftime("%Y%m%d")
        n = sum(1 for t in self.tasks if date in t["task_id"]) + 1
        return f"TSK-{date}-{n:02d}"

    def find_active(self, customer: str, product: str):
        for o in self.orders:
            if o["customer"] == customer and o["product"] == product and o["status"] != "已交付":
                return o
        return None

    def add_order(self, order: dict):
        self.orders.append(order)
        self.save()

    def update_order(self, order_id: str, patch: dict, change: dict = None):
        for o in self.orders:
            if o["order_id"] == order_id:
                o.update({k: v for k, v in patch.items() if v is not None})
                if change:
                    o.setdefault("changes", []).append(change)
                o["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
                self.save()
                return o
        return None

    def add_task(self, task: dict):
        self.tasks.append(task)
        self.save()
        return task

    def query_orders(self, customer=None, status=None, due_before=None, created_on=None):
        res = self.orders
        if customer:
            res = [o for o in res if customer in o["customer"]]
        if status:
            res = [o for o in res if o["status"] == status]
        if due_before:
            res = [o for o in res if o.get("delivery_date") and o["delivery_date"] <= due_before and o["status"] != "已交付"]
        if created_on:
            res = [o for o in res if o.get("created_at", "").startswith(created_on)]
        return res

    def query_tasks(self, status: str = "待办", overdue_before=None):
        res = [t for t in self.tasks if t["status"] == status]
        if overdue_before:
            res = [t for t in res if t.get("deadline") and t["deadline"] < overdue_before]
        return res
