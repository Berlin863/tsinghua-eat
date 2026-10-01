# -*- coding: utf-8 -*-
"""
帖子解析器: 把 data/posts.json 里的小红书帖子解析成 food_db.json。

做什么:
  1. 在帖子文本里识别食堂(含别名)和菜品(含别名), 都做"最长匹配"避免重复计数
  2. 同一段话里同时出现的 食堂+菜品 视为一对推荐; 整篇只提到一个食堂时,
     篇内所有菜品也弱关联到它(帖子通常是"某某食堂探店"结构)
  3. 统计提及次数/点赞总数/发帖时间新鲜度 -> 热度
  4. 从文本里"发现"种子库之外的高频食堂名
  5. 合并 seed_data 的种子词条, 保证冷启动也能推荐
"""

import json
import math
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import seed_data

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
POSTS_FILE = DATA_DIR / "posts.json"
MANUAL_FILE = DATA_DIR / "manual_posts.json"   # 手动补充的语料
FOOD_DB_FILE = DATA_DIR / "food_db.json"


def load_all_posts():
    """爬取帖子 + 手动补充语料(格式同 posts.json, source=manual)。"""
    posts = json.loads(POSTS_FILE.read_text(encoding="utf-8")) \
        if POSTS_FILE.exists() else []
    for m in (json.loads(MANUAL_FILE.read_text(encoding="utf-8"))
              if MANUAL_FILE.exists() else []):
        m.setdefault("source", "manual")
        m.setdefault("note_id", f"manual-{len(posts) + 1}")
        posts.append(m)
    return posts

SEG_SPLIT = re.compile(r"[。！？!?；;\n]")
# 发现新食堂用: 1~4 个汉字 + 食堂/餐厅
DISCOVER_RE = re.compile(r"([一-龥]{1,4}(?:食堂|餐厅))")
GENERIC_NAMES = {
    "学生食堂", "教工食堂", "教师餐厅", "清真食堂", "万人食堂", "大食堂",
    "新食堂", "老食堂", "美食广场", "饮食广场", "第二食堂", "快餐部",
    # 泛称/指代词, 不是具体食堂名
    "清华食堂", "大学食堂", "学校食堂", "这个食堂", "那个食堂", "哪个食堂",
    "什么食堂", "有啥食堂", "楼下食堂", "隔壁食堂",
}


def parse_count(s):
    if s is None:
        return 0
    s = str(s).strip().replace("+", "")
    m = re.search(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


def days_ago(time_field, now=None):
    """帖子时间 -> 距今天数(解析失败返回 None)。"""
    now = now or datetime.now()
    t = str(time_field or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d{13}", t):
        return max(0, (now - datetime.fromtimestamp(int(t) / 1000)).days)
    if re.fullmatch(r"\d{10}", t):
        return max(0, (now - datetime.fromtimestamp(int(t))).days)
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return max(0, (now - d).days)
        except ValueError:
            return None
    if "今天" in t:
        return 0
    if "昨天" in t:
        return 1
    m = re.search(r"(\d+)\s*天前", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*周前", t)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*个月前", t)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*年前", t)
    if m:
        return int(m.group(1)) * 365
    return None


def recency_weight(days):
    """越新的帖子权重越高, 半年衰减到 0.5 左右, 下限 0.2。"""
    if days is None:
        return 0.5
    return max(0.2, math.exp(-days / 345.0))


def match_terms(text, pairs):
    """最长优先的非重叠匹配。pairs: [(canonical, alias), ...] 已按长度降序。"""
    hits = []          # (start, end, canonical)
    for canon, alias in pairs:
        start = 0
        while True:
            i = text.find(alias, start)
            if i < 0:
                break
            span = (i, i + len(alias))
            if not any(s < span[1] and span[0] < e for s, e, _ in hits):
                hits.append((span[0], span[1], canon))
            start = i + len(alias)
    return hits


def build_alias_pairs():
    c_pairs = seed_data.canteen_aliases()
    d_pairs = [(name, alias)
               for name, alias, _ in seed_data.dish_names_sorted()]
    return c_pairs, d_pairs


def discover_canteens(posts):
    """从帖子文本里发现种子库没有的高频"X食堂/X餐厅"。"""
    counter = {}
    for p in posts:
        text = (f"{p.get('title', '')}。{p.get('desc', '')}。"
                + "。".join(c.get("content", "") for c in p.get("comments") or []))
        found = set()
        for m in DISCOVER_RE.finditer(text):
            name = m.group(1)
            if name in GENERIC_NAMES:
                continue
            found.add(name)
        for name in found:
            counter.setdefault(name, set()).add(p["note_id"])
    known = set()
    for name, info in seed_data.CANTEENS.items():
        known.add(name)
        known.update(info.get("aliases", []))
    discovered = {}
    for name, post_ids in counter.items():
        # 与已知名互为包含关系的跳过(如 "紫荆园食堂" 已被 "紫荆园" 覆盖)
        if any(k in name or name in k for k in known):
            continue
        if len(post_ids) >= 3:
            discovered[name] = len(post_ids)
    return discovered


def parse_posts(posts, verbose=True):
    c_pairs, d_pairs = build_alias_pairs()
    now = datetime.now()

    canteen_stat = {}   # canonical -> {mentions, likes_sum, posts:set}
    dish_stat = {}      # dish -> {canteens:{c:[mentions,likes]}, posts:set, recency_best}
    discovered = discover_canteens(posts)

    for p in posts:
        liked = max(1, parse_count(p.get("liked")))
        rec = recency_weight(days_ago(p.get("time"), now))
        # 语料 = (文本, 权重): 正文 1.0, 评论 0.5 —— 评论区说"桃李的麻辣香锅"算半票
        body = (f"{p.get('title', '')}。{p.get('desc', '')}。"
                f"{'、'.join(p.get('tags') or [])}")
        sources = [(body, 1.0)]
        for c in p.get("comments") or []:
            if c.get("content"):
                sources.append((c["content"], 0.5))
        if p.get("negative_desc"):      # 避雷/差评: 负权重(手动语料专用, 比路人评论更有分量)
            sources.append((p["negative_desc"], -1.5))

        seg_sources = []
        post_canteens_w = {}   # canteen -> 权重(正负都可能)
        for text, w in sources:
            for seg in SEG_SPLIT.split(text):
                if not seg.strip():
                    continue
                c_hits = match_terms(seg, c_pairs)
                d_hits = match_terms(seg, d_pairs)
                seg_sources.append((c_hits, d_hits, w))
                for _, _, c in c_hits:
                    if c in post_canteens_w:
                        post_canteens_w[c] = max(post_canteens_w[c], w)
                    else:
                        post_canteens_w[c] = w

        # 整篇只提到一个食堂 => 篇内菜品都弱关联到它(探店帖结构)
        solo_canteen, solo_w = (None, 0)
        if len(post_canteens_w) == 1:
            solo_canteen, solo_w = next(iter(post_canteens_w.items()))

        pair_weight = {}       # (dish, canteen|None) -> 权重(正负, 取最大)
        for c_hits, d_hits, w in seg_sources:
            for ds, de, dish in d_hits:
                if c_hits:
                    # 就近配对: "桃李的米线、听涛的拉面" 各归各的食堂,
                    # 不再把整段里所有食堂都配一遍
                    c = min(c_hits, key=lambda ch: min(abs(ch[0] - ds),
                                                       abs(ch[0] - de)))[2]
                    key = (dish, c)
                elif solo_canteen:
                    key = (dish, solo_canteen)
                    w = min(w, solo_w)
                else:
                    key = (dish, None)
                pair_weight[key] = max(pair_weight[key], w) \
                    if key in pair_weight else w

        # 聚合
        for c, w in post_canteens_w.items():
            st = canteen_stat.setdefault(
                c, {"mentions": 0, "likes_sum": 0, "posts": set()})
            st["mentions"] += w
            if w > 0:
                st["likes_sum"] += liked
            st["posts"].add(p["note_id"])
        for (dish, c), w in pair_weight.items():
            st = dish_stat.setdefault(
                dish, {"canteens": {}, "posts": set(), "recency": 0})
            if c:
                cell = st["canteens"].setdefault(c, [0, 0])
                cell[0] += w
                if w > 0:
                    cell[1] += liked
            st["posts"].add(p["note_id"])
            st["recency"] = max(st["recency"], rec)

    # ---------------- 组装 food_db ----------------
    canteens_out = {}
    for name, info in seed_data.CANTEENS.items():
        st = canteen_stat.get(name, {"mentions": 0, "likes_sum": 0, "posts": set()})
        canteens_out[name] = {
            "zone": info["zone"], "price": info["price"], "speed": info["speed"],
            "seats": info["seats"], "halal": info["halal"], "note": info["note"],
            "xhs_mentions": st["mentions"], "xhs_likes": st["likes_sum"],
            "xhs_posts": sorted(st["posts"]),
        }
    for name, n_posts in discovered.items():
        canteens_out[name] = {
            "zone": "其他区域", "price": 2, "speed": 3, "seats": None,
            "halal": False, "note": "从小红书帖子中发现(种子库之外)",
            "xhs_mentions": n_posts, "xhs_likes": 0, "xhs_posts": [],
            "discovered": True,
        }

    dishes_out = []
    for name, d in seed_data.DISHES.items():
        st = dish_stat.get(name, {"canteens": {}, "posts": set(), "recency": 0})
        dishes_out.append({
            "name": name,
            "attrs": d["attrs"],
            "price": d["price"],
            "kind": d.get("kind", "正餐"),
            "seed_canteen": d.get("canteen"),
            "source_note": d.get("source", ""),
            "canteens": {c: {"mentions": v[0], "likes": v[1]}
                         for c, v in st["canteens"].items()},
            "xhs_mentions": len(st["posts"]),
            "xhs_likes": sum(v[1] for v in st["canteens"].values()),
            "recency": st["recency"],
            "xhs_posts": sorted(st["posts"]),
        })

    db = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "n_posts": len(posts),
        "posts_index": [
            {"note_id": p["note_id"], "title": (p.get("title") or "(无标题)")[:60],
             "url": p.get("url", ""), "liked": parse_count(p.get("liked"))}
            for p in posts[:300]
        ],
        "canteens": canteens_out,
        "dishes": dishes_out,
    }
    return db


def build(verbose=True):
    posts = load_all_posts()
    db = parse_posts(posts, verbose)
    db["n_manual"] = sum(1 for p in posts if p.get("source") == "manual")
    db["n_posts"] = len(posts) - db["n_manual"]   # n_posts 只算爬取的
    DATA_DIR.mkdir(exist_ok=True)
    FOOD_DB_FILE.write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    scraped = [d for d in db["dishes"] if d["xhs_mentions"] > 0]
    if verbose:
        print(f"解析完成: {len(posts)} 条语料(爬取 {db['n_posts']} + 手动 {db['n_manual']})"
              f" -> {FOOD_DB_FILE}")
        print(f"食堂 {len(db['canteens'])} 个(种子 {len(seed_data.CANTEENS)} 个), "
              f"被帖子提到的菜品 {len(scraped)} 种, 种子菜品共 {len(db['dishes'])} 种")
        hot = sorted(db["canteens"].items(),
                     key=lambda kv: kv[1]["xhs_mentions"], reverse=True)[:8]
        for name, st in hot:
            if st["xhs_mentions"]:
                print(f"  热门食堂: {name}  提及 {st['xhs_mentions']:g} 帖  "
                      f"赞 {st['xhs_likes']}")
        top = sorted(scraped, key=lambda d: d["xhs_mentions"], reverse=True)[:10]
        for d in top:
            where = "/".join(f"{c}x{v['mentions']}" for c, v in d["canteens"].items()) or "?"
            print(f"  热门菜品: {d['name']}  {d['xhs_mentions']} 帖  [{where}]")
        if not posts:
            print("(还没有帖子数据, 当前只有种子库; 先运行: python main.py scrape)")
    return db


if __name__ == "__main__":
    build()
