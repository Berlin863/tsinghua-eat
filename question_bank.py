# -*- coding: utf-8 -*-
"""
偏好问题库 v2 —— 按栏目组织的口语化问卷。

四个栏目(答题时按栏目分组展示, 每次随机抽一部分):
  mood      心情: 情绪/能量/压力/社交状态
  weather   天气: 体感/晴雨/季节食欲
  craving   感受: 味道直觉(辣酸甜咸/素肉/汤干/米面/口感/甜品饮品馋度)
  personal  个人: 餐段/正餐还是解馋/预算/位置/时间/清真等实际约束

机制与 v1 一致: 选项 -> 权重字典, 与 seed_data.DISHES 的 attrs 键同名做内积。
设置型键(budget_level/zone/random_boost/meal_kind)直接覆盖。
新键: dessert=想吃甜品的程度, drink=想配饮品的程度(-1..1)。
"""

# 栏目定义: 展示标题 + 每次默认抽取数量
SECTIONS = {
    "mood": {"title": "先聊聊心情", "emoji": "💬", "pick": 2},
    "weather": {"title": "今天天气", "emoji": "🌤", "pick": 1},
    "craving": {"title": "舌头的直觉", "emoji": "👅", "pick": 3},
    "personal": {"title": "你的情况", "emoji": "🧭", "pick": 2},
}

# personal 栏目里每次必问的题(不参与随机)
STAPLE_IDS = ["meal_kind", "budget"]

QUESTIONS = [
    # ------------------------------------------------ 心情 (8)
    dict(id="mood_now", sec="mood", q="今天心情怎么样?", options=[
        ("特别好, 有好事发生", {"splurge": .6, "indulgent": .5}),
        ("还行, 平平常常", {}),
        ("有点累, 被生活榨干", {"light": .4, "quick": .3, "comfort": .3}),
        ("emo 了, 需要被治愈", {"comfort": .9, "sweet": .4}),
    ]),
    dict(id="energy", sec="mood", q="现在的电量还剩多少?", options=[
        ("满血, 能为吃的走遍全校", {"near_only": -.5}),
        ("还剩一半", {}),
        ("红色警告, 只想就近躺平", {"near_only": .8, "quick": .4}),
    ]),
    dict(id="stress", sec="mood", q="最近压力大吗?", options=[
        ("山大, 必须吃点爽的发泄", {"spicy": .6, "indulgent": .6, "rich": .4}),
        ("有点, 但还行", {}),
        ("毫无压力, 轻松愉快", {"healthy": .3, "light": .2}),
    ]),
    dict(id="social", sec="mood", q="这顿是一个人还是搭子一起?", options=[
        ("独自干饭, 快进快出", {"solo": .6, "quick": .3}),
        ("和同学一起, 边吃边聊", {"group": .7, "bbq": .2, "hotpot": .2}),
    ]),
    dict(id="reward", sec="mood", q="有什么值得庆祝的事吗?", options=[
        ("有! 刚干完一件大事", {"splurge": .8, "indulgent": .6}),
        ("没有, 普通的一天", {"value_first": .3}),
    ]),
    dict(id="comfort_style", sec="mood", q="心情不好时你是哪种干饭人?", options=[
        ("碳水炸弹救我", {"comfort": 1, "bing": .4, "noodle": .3}),
        ("麻辣一冲, 烦恼清空", {"spicy": .8, "comfort": .4}),
        ("喝口热汤, 温柔抚慰", {"soup": .9, "light": .5, "hot": .4}),
        ("甜的东西治百病", {"sweet": 1, "dessert": .8, "comfort": .5}),
    ]),
    dict(id="brave", sec="mood", q="今天对新窗口的尝试意愿?", options=[
        ("很勇, 没吃过的都想试", {"novelty": 1.2}),
        ("保守, 只吃熟悉的老地方", {"novelty": -1}),
        ("随缘", {"novelty": .3}),
    ]),
    dict(id="fate", sec="mood", q="今天的决定权交给谁?", options=[
        ("交给命运, 给我惊喜", {"random_boost": 1}),
        ("我自己说了算, 按口味来", {"novelty": -.6}),
    ]),

    # ------------------------------------------------ 天气 (5)
    dict(id="temp_feel", sec="weather", q="现在外面什么体感?", options=[
        ("冷, 想抱个暖水袋", {"hot": 1, "soup": .8}),
        ("凉爽舒适", {}),
        ("热, 走两步就冒汗", {"cold": .9, "light": .3}),
    ]),
    dict(id="rain", sec="weather", q="下雨了吗?", options=[
        ("下雨/阴沉沉的", {"soup": .8, "comfort": .4, "hot": .4}),
        ("晴天", {}),
    ]),
    dict(id="wind", sec="weather", q="风大吗? (北京特色问题)", options=[
        ("妖风肆虐, 想躲在室内", {"hot": .4, "soup": .3, "quick": .2}),
        ("没风 / 不在乎", {}),
    ]),
    dict(id="vibe", sec="weather", q="这种天气你想吃什么气氛的?", options=[
        ("热气腾腾冒烟的锅气", {"hot": .7, "rich": .3}),
        ("清爽冰凉透心", {"cold": .7, "light": .4}),
        ("无所谓, 好吃就行", {}),
    ]),
    dict(id="sweat", sec="weather", q="想吃辣发汗吗?", options=[
        ("想, 出一身汗才舒服", {"spicy": .8, "hot": .3}),
        ("不想, 越吃越热受不了", {"spicy": -.5, "cold": .3}),
    ]),

    # ------------------------------------------------ 感受 (12)
    dict(id="taste_first", sec="craving", q="闭上眼, 脑子里最先浮现哪种味道?", options=[
        ("麻辣鲜香, 越冲越好", {"spicy": 1.3, "numbing": .6}),
        ("酸辣开胃, 一口上头", {"sour": 1, "spicy": .8}),
        ("甜甜的, 治愈系", {"sweet": 1.2, "dessert": .5}),
        ("咸香浓郁, 下饭神器", {"savory": 1.2, "rich": .5}),
    ]),
    dict(id="meat_veg", sec="craving", q="想吃肉还是吃素?", options=[
        ("无肉不欢, 大口吃肉", {"meat": 1.3}),
        ("想吃清淡的蔬菜", {"veggies": 1.1, "light": .6, "healthy": .4}),
        ("荤素搭配, 干活不累", {}),
    ]),
    dict(id="soup_dry", sec="craving", q="想喝汤还是吃干香的?", options=[
        ("连汤带水, 呼噜呼噜", {"soup": 1.1, "hot": .4}),
        ("干香入味, 越嚼越香", {"rich": .7, "savory": .4}),
    ]),
    dict(id="staple", sec="craving", q="主食的灵魂是?", options=[
        ("米饭, 一勺盖上去", {"rice": 1.3}),
        ("面条, 哧溜哧溜", {"noodle": 1.3, "rice": -.5}),
        ("粉/米线, 滑溜溜", {"powder": 1.3}),
        ("饼/面点, 碳水快乐", {"bing": .9, "dimsum": .8}),
    ]),
    dict(id="spicy_now", sec="craving", q="现在这个瞬间, 辣度接受到哪?", options=[
        ("变态辣也行", {"spicy": 1.8}),
        ("中辣刚好", {"spicy": 1}),
        ("微辣意思一下", {"spicy": .4}),
        ("不吃辣, 保护肠胃", {"spicy": -1.3}),
    ]),
    dict(id="rich_light", sec="craving", q="今天的口味浓度?", options=[
        ("重口, 浓油赤酱才过瘾", {"rich": 1.3, "oily": .6}),
        ("中等", {}),
        ("清淡, 吃完不困", {"light": 1.2, "oily": -.6, "healthy": .4}),
    ]),
    dict(id="texture", sec="craving", q="口感上馋哪种?", options=[
        ("咔嚓脆的", {"crunch": 1, "fried": .4}),
        ("软糯入味的", {"soft": 1}),
        ("有嚼劲/弹牙的", {"noodle": .3, "soft": -.3}),
    ]),
    dict(id="cuisine", sec="craving", q="今天是中餐胃还是想换换?", options=[
        ("中餐胃, 家常烟火气", {"home": .9}),
        ("川湘麻辣魂", {"sichuan": 1.1, "spicy": .5}),
        ("西北面食江湖", {"northwest": 1.1, "noodle": .5}),
        ("粤式清淡精致", {"cantonese": 1.1, "light": .3}),
        ("日韩/西式换口味", {"japanese": .7, "korean": .7, "western": .7}),
    ]),
    dict(id="dessert_craving", sec="craving", q="饭后甜点那口, 馋吗?", options=[
        ("馋! 甜点是另一顿饭", {"dessert": 1.2, "sweet": .7}),
        ("偶尔来一点", {"dessert": .4}),
        ("不馋, 甜的少吃", {"dessert": -.8, "sweet": -.4}),
    ]),
    dict(id="drink_craving", sec="craving", q="想配杯喝的吗?", options=[
        ("必须配, 干饭仪式感", {"drink": 1}),
        ("看推荐, 顺路就买", {"drink": .4}),
        ("不用, 白开水/食堂免费汤", {"drink": -1, "soup": .3, "value_first": .3}),
    ]),
    dict(id="fried", sec="craving", q="油炸的东西此刻想吃吗?", options=[
        ("香脆的声音就是快乐", {"fried": 1.3, "indulgent": .5}),
        ("可以但不必", {"fried": .3}),
        ("最近忌口", {"fried": -1.2, "healthy": .4}),
    ]),
    dict(id="wokai", sec="craving", q="想吃现炒锅气还是快捷搞定?", options=[
        ("现炒的菜才有灵魂", {"home": .7, "rich": .3}),
        ("快捷套餐, 效率优先", {"quick": .8, "setmeal": .6}),
    ]),

    # ------------------------------------------------ 个人 (10)
    dict(id="meal_kind", sec="personal", q="这顿要正经吃一顿, 还是垫垫/解馋?", options=[
        ("正经吃一顿, 要管饱的正餐", {"meal_kind": "正餐"}),
        ("点心甜品小吃, 解馋为主", {"meal_kind": "小吃"}),
        ("都可以, 混着来", {"meal_kind": "混合"}),
    ]),
    dict(id="budget", sec="personal", q="这顿的预算?", options=[
        ("8元以内, 极致性价比", {"budget_level": 1, "value_first": 1}),
        ("8-12元", {"budget_level": 2}),
        ("12-18元", {"budget_level": 3}),
        ("18-25元", {"budget_level": 4}),
        ("25以上, 不设限", {"budget_level": 5}),
    ]),
    dict(id="meal_time", sec="personal", q="这顿是?", options=[
        ("早餐", {"breakfast": 1.2, "porridge": .3, "dimsum": .3}),
        ("午餐", {}),
        ("晚餐", {}),
        ("夜宵", {"night_snack": 1.5}),
    ]),
    dict(id="zone", sec="personal", q="现在人大概在哪片?", options=[
        ("紫荆公寓区", {"zone": "紫荆公寓区"}),
        ("学堂路/教学楼一带", {"zone": "学堂路沿线"}),
        ("西大操场/西区", {"zone": "西区"}),
        ("工字厅/荷花池核心区", {"zone": "校园中部"}),
        ("照澜院/南门一带", {"zone": "照澜院一带"}),
        ("其他/不确定", {}),
    ]),
    dict(id="rush", sec="personal", q="赶时间吗?", options=[
        ("非常赶, 10分钟内解决", {"quick": 1.5}),
        ("有点赶", {"quick": .6}),
        ("不赶, 慢慢享受", {"quick": -.5, "comfort": .3}),
    ]),
    dict(id="halal_req", sec="personal", q="需要清真餐吗?", options=[
        ("必须清真", {"halal": 1}, "require_halal"),
        ("不需要", {}),
    ]),
    dict(id="portion", sec="personal", q="食量如何?", options=[
        ("大胃王, 必须管饱", {"big_appetite": 1}),
        ("正常", {}),
        ("小鸟胃, 吃不多", {"big_appetite": -.8}),
    ]),
    dict(id="queue", sec="personal", q="排队的容忍度?", options=[
        ("为好吃的排15分钟也值", {"queue_ok": 1}),
        ("5分钟是极限", {"queue_ok": -.5, "quick": .4}),
        ("人少清净最重要", {"quiet": 1, "queue_ok": -.8}),
    ]),
    dict(id="walk", sec="personal", q="愿意为吃的走多远?", options=[
        ("就近解决, 5分钟内", {"near_only": 1, "quick": .4}),
        ("走10分钟没问题", {"near_only": .3}),
        ("为好吃的走遍全校", {"near_only": -.8}),
    ]),
    dict(id="splurge_q", sec="personal", q="今天愿意奢侈一把吗?", options=[
        ("愿意, 特殊的日子", {"splurge": 1}),
        ("不了, 老老实实吃饭", {"value_first": .5}),
    ]),
]

# 设置型权重键(不平均, 直接覆盖)
SET_KEYS = {"budget_level", "zone", "random_boost", "meal_kind"}


def sample_questions(n=9, rng=None):
    """按栏目分层抽样: 必问题(personal 的 staple) + 各栏目随机抽取。

    n 大致按比例分配到各栏目(必问题不计入 n)。
    返回按栏目顺序排列的问题列表(mood -> weather -> craving -> personal)。
    """
    import random
    rng = rng or random.Random()

    by_sec = {}
    for q in QUESTIONS:
        by_sec.setdefault(q["sec"], []).append(q)

    staples = [q for q in by_sec["personal"] if q["id"] in STAPLE_IDS]
    personal_pool = [q for q in by_sec["personal"] if q["id"] not in STAPLE_IDS]

    # 剩余名额按栏目比例分: mood 2 / weather 1 / craving 3 / personal 1 (n=9 基准)
    scale = max(0.4, n / 9.0)
    quota = {
        "mood": max(1, round(2 * scale)),
        "weather": max(1, round(1 * scale)),
        "craving": max(2, round(3 * scale)),
        "personal": max(0, round(1 * scale)),
    }

    picked = []
    for sec in ["mood", "weather", "craving"]:
        pool = list(by_sec[sec])
        rng.shuffle(pool)
        picked.extend(pool[:quota[sec]])
    rng.shuffle(personal_pool)
    picked.extend(personal_pool[:quota["personal"]])

    total = len(picked) + len(staples)
    # 超出 n 就从非必问里裁掉; 不足就从剩余题里补
    while total > n and len(picked) > quota["craving"]:
        picked.pop(rng.randrange(len(picked)))
        total -= 1
    rest = [q for q in QUESTIONS if q not in picked and q not in staples]
    rng.shuffle(rest)
    while total < n and rest:
        picked.append(rest.pop())
        total += 1

    # 按栏目顺序重排, 答题体验连贯
    order = {"mood": 0, "weather": 1, "craving": 2, "personal": 3}
    picked.sort(key=lambda q: order[q["sec"]])
    return picked + staples


assert len(QUESTIONS) == 35, f"题库数量变化: {len(QUESTIONS)}"
