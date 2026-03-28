"""
候选人数据库管理模块

持久化到 data/contacts_cache.json，
支持逐个追加候选人、查询、清除等操作。
"""

import json
import os
from datetime import datetime, timezone, timedelta

CACHE_FILE = os.path.join("greeting", "contacts_cache.json")
CST = timezone(timedelta(hours=8))


def _ensure_dir():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)


def _empty_cache() -> dict:
    return {
        "version": "1.0",
        "scan_time": datetime.now(CST).isoformat(),
        "candidates": [],
    }


def load_cache() -> dict | None:
    """加载候选人数据库。文件不存在或格式错误返回 None。"""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return None


def has_cache() -> bool:
    """是否存在有效的候选人数据"""
    cache = load_cache()
    return cache is not None and len(cache.get("candidates", [])) > 0


def get_cache_summary() -> str:
    """返回数据库摘要信息"""
    cache = load_cache()
    if not cache:
        return "无数据"
    scan_time = cache.get("scan_time", "未知")
    cands = len(cache.get("candidates", []))
    return f"更新时间: {scan_time}, 候选人: {cands}"


def get_cached_candidates() -> list[dict]:
    """获取所有候选人列表"""
    cache = load_cache()
    if not cache:
        return []
    return cache.get("candidates", [])


def clear_cache():
    """清除数据库"""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


def add_candidate_to_cache(candidate: dict):
    """
    将单个候选人追加到数据库（去重）。
    用于手工录入候选人发送成功后自动入库。

    Args:
        candidate: 候选人字典，至少包含 full_name 字段
    """
    _ensure_dir()
    cache = load_cache()
    if cache is None:
        cache = _empty_cache()

    existing_names = {c.get("full_name") for c in cache.get("candidates", [])}
    full_name = candidate.get("full_name", candidate.get("name", ""))
    if full_name and full_name not in existing_names:
        cache["candidates"].append(candidate)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
