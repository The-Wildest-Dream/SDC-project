"""Demonstration roles only; these are not real authentication or production permissions."""
ACTORS = {"销售甲": "销售人员", "销售乙": "销售人员", "经理": "经理"}


def require(actor, role):
    if ACTORS.get(actor) != role:
        raise ValueError(f"当前模拟角色不能执行此操作，需要{role}。")


def own(actor, owner):
    require(actor, "销售人员")
    if actor != owner:
        raise ValueError("只能修改或提交自己的草稿。")
