# -*- coding: utf-8 -*-
"""
推荐引擎: 随机抽样问卷估计偏好 -> 对 食堂x菜品 打分 -> 输出 Top5。

偏好模型:
  - 常规键(辣/酸/米面/...)取所有作答的平均并截断到 [-2, 2]
  - 设置键(budget_level/zone/random_boost)直接取最后一次作答
  - 打分 = 0.55*口味匹配 + 0.45*热度, 再乘 场景/预算/位置/新鲜感 等修正
  - 最后加一点高斯抖动 —— 同一个人问两次, 推荐也不完全一样(随机性)
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

import seed_data
from question_bank import SET_KEYS, sample_questions

ROOT = Path(__file__).resolve().parent
FOOD_DB_FILE = ROOT / "data" / "food_db.json"

KEY_LABELS = {
    "spicy": "辣", "numbing": "麻", "sour": "酸", "sweet": "甜",
    "savory": "咸鲜", "rich": "重口", "light": "清淡", "oily": "油香",
    "fried": "酥脆", "soup": "喝汤", "hot": "热乎", "cold": "清凉",
    "crunch": "脆口", "soft": "软糯",
    "rice": "米饭", "noodle": "面食", "powder": "粉类", "dimsum": "面点",
    "bing": "饼类", "porridge": "粥品", "bread": "面包", "salad": "轻食",
    "setmeal": "套餐盖饭", "mallow": "麻辣烫香锅", "teppan": "铁板石锅",
    "hotpot": "小火锅", "bbq": "烧烤烤肉",
    "sichuan": "川湘", "cantonese": "粤式", "northwest": "西北",
    "northeast": "东北", "yunnan": "云贵", "xinjiang": "新疆", "halal": "清真",
    "japanese": "日式", "korean": "韩式", "western": "西式",
    "vegetarian": "素食", "home": "家常",
    "quick": "快手", "breakfast": "早餐", "night_snack": "夜宵",
    "solo": "一人食", "group": "聚餐", "comfort": "碳水安慰",
    "healthy": "健康低脂", "protein": "高蛋白", "veggies": "蔬菜",
    "indulgent": "高热量快乐", "meat": "肉食", "egg": "加蛋",
    "splurge": "愿意奢侈", "value_first": "性价比", "big_appetite": "大分量",
    "novelty": "尝鲜", "quiet": "图清净", "queue_ok": "不怕排队",
    "near_only": "就近优先",
}
PRICE_DESC = {1: "约6-12元", 2: "约10-18元", 3: "约15-25元", 4: "约20元+"}
BIG_CANTEEN_SEATS = 1900   # 超过这个座位数算"人流量大"


# ---------------------------------------------------------------- 问卷

def ask_questions(n=12, auto=False, rng=None):
    """随机抽题并作答, 返回 (prefs, pset, hard)。"""
    rng = rng or random.Random()
    questions = sample_questions(n, rng)
    sums, counts = defaultdict(float), defaultdict(int)
    pset, hard = {}, {}

    print(f"\n随机抽了 {len(questions)} 道题, 估计一下你今天想吃什么(回车=跳过)\n")
    for i, q in enumerate(questions, 1):
        opts = q["options"]
        print(f"[{i}/{len(questions)}] ({q['dim']}) {q['q']}")
        for j, opt in enumerate(opts, 1):
            print(f"    {j}. {opt[0]}")
        if auto:
            choice = rng.randrange(len(opts))
            print(f"    -> 自动选择: {opts[choice][0]}")
        else:
            choice = -1
            for _ in range(3):
                try:
                    s = input("    你的选择(序号): ").strip()
                except EOFError:
                    s = ""
                if s == "":
                    choice = -1
                    break
                if s.isdigit() and 1 <= int(s) <= len(opts):
                    choice = int(s) - 1
                    break
                print("    没看懂, 再输一次(直接回车=跳过)")
            if choice < 0:
                print("    (跳过)")
                continue
        text, w = opts[choice][0], opts[choice][1]
        if len(opts[choice]) > 2 and opts[choice][2] == "require_halal":
            hard["halal"] = True
        for k, v in w.items():
            if k in SET_KEYS:
                pset[k] = v
            else:
                sums[k] += v
                counts[k] += 1

    prefs = {k: max(-2.0, min(2.0, sums[k] / counts[k])) for k in sums}
    pset.setdefault("budget_level", 3)
    pset.setdefault("random_boost", 0.0)
    return prefs, pset, hard


def show_profile(prefs, pset, hard):
    keys = sorted(prefs, key=lambda k: abs(prefs[k]), reverse=True)
    shown = [f"{KEY_LABELS.get(k, k)} {prefs[k]:+.1f}" for k in keys[:8]]
    extra = []
    if hard.get("halal"):
        extra.append("清真")
    if pset.get("zone"):
        extra.append(f"位置[{pset['zone']}]")
    extra.append(f"预算档 {pset['budget_level']}")
    print("  你的干饭画像: " + " · ".join(shown + extra))


# ---------------------------------------------------------------- 候选

def build_candidates(db):
    """每个 (菜品, 食堂) 组合是一个候选; 无食堂关联的菜品挂 None。"""
    canteens = db["canteens"]
    c_pop = {c: math.log10(1 + v.get("xhs_likes", 0)) + 0.8 * v.get("xhs_mentions", 0)
             for c, v in canteens.items()}
    avg_c_pop = sum(c_pop.values()) / max(1, len(c_pop))

    out = []
    for d in db["dishes"]:
        cells = dict(d.get("canteens") or {})
        if d.get("seed_canteen") and d["seed_canteen"] not in cells:
            cells[d["seed_canteen"]] = {"mentions": 0, "likes": 0, "seed": True}
        common = dict(
            dish=d["name"], attrs=d["attrs"], price=d["price"],
            kind=d.get("kind", "正餐"),
            source_note=d.get("source_note", ""),
            xhs_mentions=d["xhs_mentions"], recency=d.get("recency", 0),
            posts=d.get("xhs_posts") or [],
        )
        if cells:
            for cname, cell in cells.items():
                info = canteens.get(cname)
                if not info:
                    continue
                out.append(dict(
                    common, canteen=cname, cinfo=info,
                    cpop=c_pop.get(cname, avg_c_pop),
                    dpop=cell.get("mentions", 0), dlikes=cell.get("likes", 0),
                    seed_cell=bool(cell.get("seed")),
                ))
        else:
            out.append(dict(
                common, canteen=None, cinfo=None, cpop=avg_c_pop,
                dpop=0, dlikes=0, seed_cell=False,
            ))
    return out


# ---------------------------------------------------------------- 打分

def taste_match(attrs, prefs):
    raw, contrib = 0.0, []
    for k, v in attrs.items():
        pv = prefs.get(k)
        if pv:
            raw += pv * v
            contrib.append((k, pv * v))
    return 0.5 + 0.5 * math.tanh(raw / 5.0), contrib


def popularity_raw(c):
    """热度: 点赞取对数, 提及次数取'带符号对数'(负提及=差评压热度)。"""
    m = c["dpop"]
    mlog = math.log1p(m) if m > 0 else (-math.log1p(-m) if m < 0 else 0.0)
    return 1.0 + math.log10(1 + c["dlikes"]) + 0.8 * mlog + 0.7 * c["recency"]


def scene_mult(c, prefs, pset, hard):
    attrs, info = c["attrs"], c["cinfo"]
    mult = 1.0

    # 正餐/小吃/配菜: 按"想吃什么类型"打折(配额在 rank 里再兜一层)
    mk = pset.get("meal_kind", "混合")
    kind = c.get("kind", "正餐")
    if mk == "正餐":
        if kind == "小吃":
            mult *= 0.35
        elif kind == "配菜":
            mult *= 0.55
    elif mk == "小吃":
        if kind == "正餐":
            mult *= 0.55
        elif kind == "配菜":
            mult *= 0.70

    # 餐段
    if prefs.get("breakfast", 0) > 0.4:
        mult *= 1.35 if attrs.get("breakfast") else 0.45
    if prefs.get("night_snack", 0) > 0.4:
        mult *= 1.30 if attrs.get("night_snack") else 0.85

    # 赶时间: 慢菜(火锅/铁板/麻辣烫类)和大食堂排队折扣
    q = prefs.get("quick", 0)
    if q > 0.3:
        slowness = max(attrs.get("hotpot", 0), 0.6 * attrs.get("teppan", 0),
                       0.6 * attrs.get("mallow", 0))
        if info and info.get("speed", 3) <= 2:
            slowness = max(slowness, 0.5)
        mult *= 1 - 0.3 * min(1.0, q) * min(1.0, slowness)

    # 聚餐/一人食
    if prefs.get("group", 0) > 0.4 and (attrs.get("hotpot") or attrs.get("bbq")):
        mult *= 1.10
    if prefs.get("solo", 0) > 0.4 and attrs.get("hotpot"):
        mult *= 0.92

    # 预算
    b, p = pset.get("budget_level", 3), c["price"]
    if p > b:
        mult *= max(0.55, 1 - 0.18 * (p - b))
    elif b < 3 and p <= b:
        mult *= 1.05

    # 位置/远近
    zone = pset.get("zone")
    if zone and info:
        near = prefs.get("near_only", 0)
        if info.get("zone") == zone:
            mult *= 1.08
        else:
            mult *= 1 - (0.12 if near > 0.5 else 0.05)

    # 安静偏好 vs 大食堂
    if prefs.get("quiet", 0) > 0.5 and info and (info.get("seats") or 0) >= BIG_CANTEEN_SEATS:
        mult *= 0.93

    # 清真: 软偏好加成(硬过滤在 build 时做)
    if prefs.get("halal", 0) > 0.5 and (attrs.get("halal") or (info and info.get("halal"))):
        mult *= 1.12

    # 尝鲜 vs 守成
    n = prefs.get("novelty", 0)
    known = min(1.0, c["xhs_mentions"] / 6.0)
    if n > 0:
        mult *= 1 + 0.12 * n * (1 - known)
    elif n < 0:
        mult *= 1 + 0.10 * n * (1 - known)

    return mult


def rank(db, prefs, pset, hard, top_n=5, rng=None):
    """打分后在头部候选池里"加权随机抽样"取 top_n —— 永远合理, 常常不同。"""
    rng = rng or random.Random()
    cands = build_candidates(db)
    if hard.get("halal"):
        cands = [c for c in cands
                 if c["attrs"].get("halal") or (c["cinfo"] and c["cinfo"].get("halal"))]

    pops = [popularity_raw(c) for c in cands]
    lo, hi = min(pops), max(pops)

    scored = []
    for c, pr in zip(cands, pops):
        pop = 0.15 + 0.85 * ((pr - lo) / (hi - lo) if hi > lo else 0.5)
        match, contrib = taste_match(c["attrs"], prefs)
        mult = scene_mult(c, prefs, pset, hard)
        sigma = 0.08 + 0.12 * pset.get("random_boost", 0)
        jitter = 1 + rng.gauss(0, sigma)
        score = 100 * (0.58 * match + 0.42 * pop) * mult * jitter
        scored.append((score, c, contrib))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 各类型配额(由 meal_kind 决定)
    mk = pset.get("meal_kind", "混合")
    caps = {"正餐": {"小吃": 1, "配菜": 1, "正餐": top_n},
            "小吃": {"小吃": top_n, "配菜": 2, "正餐": 1},
            "混合": {"小吃": 2, "配菜": 1, "正餐": top_n}}[mk]

    picked, seen_dish, canteen_cnt, kind_cnt = [], set(), defaultdict(int), defaultdict(int)

    def acceptable(s):
        c = s[1]
        if c["dish"] in seen_dish:
            return False
        if c["canteen"] and canteen_cnt[c["canteen"]] >= 2:
            return False
        if kind_cnt[c.get("kind", "正餐")] >= caps[c.get("kind", "正餐")]:
            return False
        return True

    def take(s):
        picked.append(s)
        c = s[1]
        seen_dish.add(c["dish"])
        if c["canteen"]:
            canteen_cnt[c["canteen"]] += 1
        kind_cnt[c.get("kind", "正餐")] += 1

    # 头部 24 个候选按 分数^温度 加权抽样; "让命运决定"时温度放平, 更野
    temp = 1.2 if pset.get("random_boost", 0) > 0.5 else 3.0
    pool = [s for s in scored[:24]]
    while len(picked) < top_n and pool:
        ws = [max(1e-6, s[0]) ** temp for s in pool]
        i = rng.choices(range(len(pool)), weights=ws, k=1)[0]
        s = pool.pop(i)
        if acceptable(s):
            take(s)

    # 兜底: 候选池耗尽还没凑满 -> 放宽类型配额顺序补齐
    for s in scored:
        if len(picked) >= top_n:
            break
        if s[1]["dish"] not in seen_dish and acceptable(s):
            take(s)
    return picked


# ---------------------------------------------------------------- 输出

def render(db, picked, prefs, pset, hard):
    posts_idx = {p["note_id"]: p for p in db.get("posts_index", [])}

    print("\n" + "=" * 62)
    n = db.get("n_posts", 0)
    print(f"  今日吃什么 · Top{len(picked)}   (语料: 小红书 {n} 帖 + 官方种子库)")
    print("=" * 62)
    for rank_i, (score, c, contrib) in enumerate(picked, 1):
        cname = c["canteen"] or "任意食堂(就近找窗口)"
        info = c["cinfo"]
        if not c["canteen"]:
            c = dict(c)
            c["_hint"] = "种子菜品未关联到具体食堂(爬取帖子后会自动补上), 大食堂基础窗口常见"
        kind_tag = "" if c.get("kind", "正餐") == "正餐" else f"〔{c['kind']}〕"
        print(f"\n {rank_i}. 【{cname}】{c['dish']}{kind_tag}    综合 {score:.1f} 分")
        # 理由: 偏好命中
        hits = sorted(contrib, key=lambda kv: kv[1], reverse=True)
        hit_txt = [KEY_LABELS.get(k, k) for k, v in hits if v > 0.25][:3]
        lines = []
        if hit_txt:
            lines.append("命中偏好: " + "、".join(hit_txt))
        # 热度
        if c["dpop"] or c["dlikes"]:
            lines.append(f"小红书热度: {int(c['dpop'])} 次提及 · 约 {int(c['dlikes'])} 赞")
        elif c["source_note"]:
            lines.append(f"来源: {c['source_note']}")
        if c["seed_cell"]:
            lines.append("(官方特色窗口)")
        # 价格与位置
        price_txt = PRICE_DESC.get(c["price"], "")
        zone_txt = f"{info['zone']}({seed_data.ZONES_DESC.get(info['zone'], '')})" if info else ""
        lines.append(f"价位 {price_txt}" + (f" | {zone_txt}" if zone_txt else ""))
        if info and info.get("note"):
            lines.append(f"{info['note']}")
        if c.get("_hint"):
            lines.append(c["_hint"])
        for ln in lines:
            print(f"    - {ln}")
        # 引用帖子
        titles = []
        for pid in c["posts"][:2]:
            p = posts_idx.get(pid)
            if p and p.get("title"):
                titles.append(p["title"][:22])
        if titles:
            print(f"    - 帖子: 《{'》 《'.join(titles)}》")
    print("\n" + "-" * 62)
    print("  提示: 分数含随机抖动, 再问一次可能换一批; 一切以窗口实物为准 :)")


# ---------------------------------------------------------------- 主入口

def run(n_questions=12, top_n=5, auto=False, db_path=None):
    db_path = Path(db_path) if db_path else FOOD_DB_FILE
    if not db_path.exists():
        print("找不到 data/food_db.json, 先运行: python main.py build")
        return
    db = json.loads(db_path.read_text(encoding="utf-8"))

    rng = random.Random()
    prefs, pset, hard = ask_questions(n_questions, auto=auto, rng=rng)
    print("\n  (偏好估计完成)")
    show_profile(prefs, pset, hard)

    while True:
        picked = rank(db, prefs, pset, hard, top_n=top_n, rng=rng)
        render(db, picked, prefs, pset, hard)
        if auto:
            break
        try:
            cmd = input("\n回车退出 | r=换个手气(重新掷骰) | q=重新问一轮: ").strip().lower()
        except EOFError:
            break
        if cmd == "r":
            continue
        if cmd == "q":
            prefs, pset, hard = ask_questions(n_questions, auto=False, rng=rng)
            show_profile(prefs, pset, hard)
            continue
        break


if __name__ == "__main__":
    run()
