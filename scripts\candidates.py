"""
候选人处理模块

- 候选人格式校验
- 候选人名称解析
- 手工候选人处理（用户直接提供搜索信息）
- 称呼判断
"""


def is_valid_candidate(name: str) -> bool:
    """
    判断联系人名称是否符合候选人格式。
    合格格式：姓名/昵称-当前公司-岗位-地址
    需要至少包含 3 个 `-` 分隔符。
    """
    parts = name.split("-")
    if len(parts) < 4:
        return False
    return all(p.strip() for p in parts[:4])


def parse_candidate(name: str) -> dict:
    """
    解析候选人名称，返回各字段。
    """
    parts = name.split("-")
    return {
        "full_name": name,
        "name_part": parts[0].strip(),
        "company": parts[1].strip() if len(parts) > 1 else "",
        "position": parts[2].strip() if len(parts) > 2 else "",
        "location": parts[3].strip() if len(parts) > 3 else "",
    }


def determine_appellation(name_part: str) -> str:
    """
    根据姓名/昵称判断称呼方式。

    规则：
    1. 三字中文姓名 → 取后两字（如 "刘德华" → "德华"）
    2. 两字中文姓名 → 直接用名字
    3. 英文名/昵称 → 直接用原名
    4. 四字及以上 → 直接用原名（可能复姓）

    原则：宁可用原名，也不要用错称呼。
    """
    name = name_part.strip()

    if _is_pure_chinese(name):
        if len(name) == 3:
            common_compound_surnames = [
                "诸葛",
                "欧阳",
                "司马",
                "上官",
                "东方",
                "独孤",
                "南宫",
                "万俟",
                "闻人",
                "夏侯",
                "端木",
                "公孙",
                "慕容",
                "尉迟",
                "长孙",
                "宇文",
                "轩辕",
                "令狐",
                "皇甫",
                "百里",
            ]
            if name[:2] in common_compound_surnames:
                return name
            return name[1:]
        else:
            return name
    else:
        return name


def _is_pure_chinese(text: str) -> bool:
    """判断字符串是否全部为中文字符"""
    return bool(text) and all("\u4e00" <= c <= "\u9fff" for c in text)


def process_manual_candidates(manual_list: list[dict]) -> list[dict]:
    """
    处理手工提供的候选人列表。

    输入格式（每个 dict）：
    {
        "name": "刘德华",           # 必填：候选人姓名/称呼
        "search_key": "13800138000", # 可选：微信搜索关键词（省略则用 name 搜索）
        "appellation": "德华"        # 可选：称呼（省略则自动判断）
    }
    """
    candidates = []
    seen = set()

    for item in manual_list:
        name = item.get("name", "").strip()
        search_key = item.get("search_key", "").strip()
        if not name:
            continue
        if not search_key:
            search_key = name

        dedup_key = f"{name}|{search_key}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        appellation = item.get("appellation", "").strip()
        if not appellation:
            appellation = determine_appellation(name)

        candidates.append(
            {
                "name": name,
                "search_key": search_key,
                "appellation": appellation,
            }
        )

    return candidates
