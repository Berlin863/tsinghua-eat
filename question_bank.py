# -*- coding: utf-8 -*-
"""
偏好问题库(78 题, 8 个维度)。

每次推荐会按维度分层随机抽取一部分问题(默认 12 题)来估计你的偏好向量:
  - 每个维度至少抽 1 题, 剩余名额从全库随机抽 -> 每次被问到的问题都不同
  - 回车 = 跳过(该题不影响偏好)

选项格式: (文案, 权重字典)。权重键与 seed_data.DISHES 的 attrs 键同名,
推荐时做内积。少数"设置型"键(budget_level / zone / random_boost)不参与平均,
而是直接覆盖取值。options 里带 True 第四个元素的选项会触发硬过滤(清真)。
"""

# 维度列表(分层抽样用), 顺序即重要度
DIMS = ["口味", "主食", "菜系", "场景", "预算", "健康", "随心", "位置"]

QUESTIONS = [
    # ------------------------------------------------ 口味 (12)
    dict(id="spicy", dim="口味", q="你有多能吃辣?", options=[
        ("无辣不欢, 微辣等于没放", {"spicy": 2, "rich": .5}),
        ("中辣刚好", {"spicy": 1}),
        ("微辣意思一下", {"spicy": .4}),
        ("基本不吃辣", {"spicy": -1.5, "light": .5}),
    ]),
    dict(id="numbing", dim="口味", q="花椒的'麻'你能接受吗?", options=[
        ("麻和辣是灵魂", {"numbing": 1.5, "spicy": .5}),
        ("可以接受一点", {"numbing": .5}),
        ("不要麻", {"numbing": -1}),
    ]),
    dict(id="sour", dim="口味", q="对'酸'的态度?", options=[
        ("越酸越开胃", {"sour": 1.5}),
        ("适量就好", {"sour": .5}),
        ("不喜欢酸", {"sour": -1}),
    ]),
    dict(id="sweet", dim="口味", q="甜口菜(糖醋/红烧那一挂)喜欢吗?", options=[
        ("甜甜的菜是我的菜", {"sweet": 1.5}),
        ("还行, 偶尔吃", {"sweet": .5}),
        ("甜口菜达咩", {"sweet": -1}),
    ]),
    dict(id="savory", dim="口味", q="浓郁下饭 vs 清爽原味?", options=[
        ("浓油赤酱才下饭", {"savory": 1.5, "rich": 1}),
        ("咸鲜适中", {"savory": .7}),
        ("原味清淡养生", {"light": 1.2}),
    ]),
    dict(id="rich", dim="口味", q="你对自己的'重口程度'评价?", options=[
        ("重口星人, 越香越爽", {"rich": 1.5, "oily": .8}),
        ("中等", {"rich": .5}),
        ("口味清淡", {"light": 1.2, "oily": -.8}),
    ]),
    dict(id="fried", dim="口味", q="油炸食品?", options=[
        ("酥脆的声音是享受", {"fried": 1.5, "indulgent": .8}),
        ("偶尔解馋", {"fried": .5}),
        ("最近忌口油炸", {"fried": -1.2, "healthy": .5}),
    ]),
    dict(id="soup_pref", dim="口味", q="吃饭必须配汤吗?", options=[
        ("不喝汤等于没吃", {"soup": 1.2}),
        ("有则更好", {"soup": .4}),
        ("基本不喝", {"soup": -.5}),
    ]),
    dict(id="hot_meal", dim="口味", q="现在想吃热乎的还是偏凉的?", options=[
        ("滚烫热食, 冒烟那种", {"hot": 1.2, "soup": .3}),
        ("都行", {}),
        ("凉的也爽(凉皮/沙拉)", {"cold": .8, "hot": -.5}),
    ]),
    dict(id="texture", dim="口味", q="口感偏好?", options=[
        ("咔嚓脆的", {"crunch": 1}),
        ("软糯入味的", {"soft": 1}),
        ("不挑", {}),
    ]),
    dict(id="soup_or_dry", dim="口味", q="汤面还是干拌?", options=[
        ("汤汤水水连汤带面", {"soup": .8, "noodle": .3}),
        ("干拌才够味", {"soup": -.5, "rich": .4}),
        ("不常吃面", {"noodle": -.6}),
    ]),
    dict(id="craving_now", dim="口味", q="此刻脑子里先浮现哪种味道?", options=[
        ("麻辣鲜香", {"spicy": 1, "numbing": .8}),
        ("酸辣过瘾", {"sour": .8, "spicy": .8}),
        ("甜滋滋", {"sweet": 1}),
        ("咸香浓郁", {"savory": 1}),
    ]),

    # ------------------------------------------------ 主食 (10)
    dict(id="staple", dim="主食", q="米饭还是面食?", options=[
        ("米饭永远的神", {"rice": 1.5}),
        ("面食党", {"rice": -.8, "noodle": 1.5}),
        ("换着来, 看菜", {}),
    ]),
    dict(id="noodle_style", dim="主食", q="面条怎么吃?", options=[
        ("汤面暖胃", {"noodle": 1, "soup": .8}),
        ("拌面/炒面够锅气", {"noodle": 1, "rich": .5}),
        ("不太吃面", {"noodle": -.8}),
    ]),
    dict(id="powder", dim="主食", q="粉类(螺蛳粉/米粉/酸辣粉)?", options=[
        ("闻着臭吃着香的都爱", {"powder": 1.3, "sour": .3}),
        ("一般般", {"powder": .3}),
        ("不吃粉", {"powder": -1}),
    ]),
    dict(id="dimsum", dim="主食", q="面点(包子/饺子/锅贴)?", options=[
        ("碳水快乐源泉", {"dimsum": 1}),
        ("一般", {}),
        ("不喜欢", {"dimsum": -.8}),
    ]),
    dict(id="bing", dim="主食", q="饼类(手抓饼/煎饼/酱香饼)?", options=[
        ("路边摊之魂, 爱吃", {"bing": 1, "quick": .3}),
        ("偶尔", {"bing": .3}),
        ("少吃", {"bing": -.6}),
    ]),
    dict(id="porridge", dim="主食", q="喝粥吗?", options=[
        ("胃被粥拿捏", {"porridge": 1, "light": .5}),
        ("早餐会喝", {"porridge": .4}),
        ("不喝", {"porridge": -.6}),
    ]),
    dict(id="bread", dim="主食", q="面包/轻食当正餐?", options=[
        ("可以接受", {"bread": .8, "salad": .6}),
        ("正餐必须热菜热饭", {"bread": -.5, "hot": .4}),
        ("看心情", {}),
    ]),
    dict(id="setmeal", dim="主食", q="一勺盖浇/套餐 vs 自选几个菜?", options=[
        ("一勺盖上去, 方便", {"setmeal": 1, "quick": .4}),
        ("打两三个菜更香", {"home": .6, "veggies": .3}),
        ("无所谓", {}),
    ]),
    dict(id="mallow", dim="主食", q="麻辣烫/香锅/冒菜这一挂?", options=[
        ("戒不掉, 一周三次", {"mallow": 1.3, "spicy": .6}),
        ("偶尔吃", {"mallow": .4}),
        ("容易上火, 不吃", {"mallow": -1, "light": .4}),
    ]),
    dict(id="teppan", dim="主食", q="铁板/石锅滋滋响的那种?", options=[
        ("馋那一口锅气", {"teppan": .9, "rich": .4}),
        ("一般", {}),
        ("太油了", {"teppan": -.6, "oily": -.3}),
    ]),

    # ------------------------------------------------ 菜系 (12)
    dict(id="sichuan", dim="菜系", q="川湘菜?", options=[
        ("川菜之魂", {"sichuan": 1.5, "spicy": .8}),
        ("偶尔点", {"sichuan": .4}),
        ("吃不了辣, 不太行", {"spicy": -.6}),
    ]),
    dict(id="cantonese", dim="菜系", q="粤式(烧腊/肠粉/靓汤)?", options=[
        ("烧腊 yyds", {"cantonese": 1.2}),
        ("还行", {"cantonese": .3}),
        ("不感冒", {"cantonese": -.6}),
    ]),
    dict(id="northwest", dim="菜系", q="西北风味(拉面/泡馍/油泼面)?", options=[
        ("面食天堂", {"northwest": 1.2, "noodle": .4}),
        ("一般", {}),
        ("不常吃", {"northwest": -.5}),
    ]),
    dict(id="northeast", dim="菜系", q="东北菜(分量大)?", options=[
        ("锅包肉地三鲜, 爱了", {"northeast": 1.1}),
        ("一般", {}),
        ("不太吃", {"northeast": -.5}),
    ]),
    dict(id="yunnan", dim="菜系", q="云贵风味(米线/酸汤)?", options=[
        ("米线酸汤冲冲冲", {"yunnan": 1, "sour": .3}),
        ("一般", {}),
        ("不常吃", {"yunnan": -.5}),
    ]),
    dict(id="xinjiang", dim="菜系", q="新疆菜(烤肉/抓饭/大盘鸡)?", options=[
        ("孜然一撒就投降", {"xinjiang": 1, "bbq": .4}),
        ("一般", {}),
        ("不常吃", {"xinjiang": -.5}),
    ]),
    dict(id="halal_req", dim="菜系", q="需要清真餐吗?", options=[
        ("必须清真", {"halal": 1}, "require_halal"),
        ("不需要", {}),
    ]),
    dict(id="japanese", dim="菜系", q="日式(咖喱/定食)?", options=[
        ("咖喱猪排来一份", {"japanese": 1}),
        ("一般", {}),
        ("不吃", {"japanese": -.5}),
    ]),
    dict(id="korean", dim="菜系", q="韩式(拌饭/部队锅/炸鸡)?", options=[
        ("韩式辣酱很上头", {"korean": 1}),
        ("一般", {}),
        ("不吃", {"korean": -.5}),
    ]),
    dict(id="western", dim="菜系", q="西式(披萨/意面/汉堡)?", options=[
        ("芝士就是力量", {"western": 1}),
        ("一般", {}),
        ("不吃", {"western": -.5}),
    ]),
    dict(id="vegetarian", dim="菜系", q="这顿想吃素吗?", options=[
        ("想全素", {"vegetarian": 1.5, "veggies": 1}),
        ("素多一点", {"veggies": .7}),
        ("无肉不欢", {"meat": 1.2, "vegetarian": -1}),
    ]),
    dict(id="home_vs_special", dim="菜系", q="家常小炒还是风味特色?", options=[
        ("想吃家里那口", {"home": 1.1, "light": .3}),
        ("食堂特色风味窗口", {"rich": .3}),
        ("都行", {}),
    ]),

    # ------------------------------------------------ 场景 (10)
    dict(id="meal_kind", dim="场景", q="这顿要正经吃一顿, 还是垫垫/解馋?", options=[
        ("正经吃一顿, 要管饱的正餐", {"meal_kind": "正餐"}),
        ("想吃点心/小吃/甜品, 解馋为主", {"meal_kind": "小吃"}),
        ("都可以, 混着来", {"meal_kind": "混合"}),
    ]),
    dict(id="meal_time", dim="场景", q="这顿是?", options=[
        ("早餐", {"breakfast": 1.2, "porridge": .3, "dimsum": .3}),
        ("午餐", {}),
        ("晚餐", {}),
        ("夜宵", {"night_snack": 1.5}),
    ]),
    dict(id="rush", dim="场景", q="赶时间吗?", options=[
        ("非常赶, 10分钟内解决", {"quick": 1.5}),
        ("有点赶", {"quick": .6}),
        ("不赶, 慢慢吃", {"quick": -.5, "comfort": .3}),
    ]),
    dict(id="solo_group", dim="场景", q="一人食还是聚餐?", options=[
        ("一人食, 快进快出", {"solo": .6, "quick": .2}),
        ("和朋友一起, 边吃边聊", {"group": .8, "hotpot": .3, "bbq": .2}),
        ("都行", {}),
    ]),
    dict(id="weather", dim="场景", q="今天天气给你的暗示是?", options=[
        ("冷/下雨, 想喝热汤", {"soup": 1.2, "hot": 1}),
        ("想吃干香下饭的", {"rich": .6}),
        ("热, 想吃凉的", {"cold": .8, "light": .4}),
    ]),
    dict(id="mood", dim="场景", q="心情有点低落时, 吃什么治愈?", options=[
        ("碳水炸弹轰炸", {"comfort": 1.2, "indulgent": .8, "sweet": .4}),
        ("麻辣解压", {"spicy": .8, "comfort": .5}),
        ("清淡温润抚慰", {"light": .8, "porridge": .3}),
        ("我心情很好", {}),
    ]),
    dict(id="treat_self", dim="场景", q="要犒劳自己吗(考完试/交完作业)?", options=[
        ("必须大吃一顿", {"indulgent": 1, "splurge": .8}),
        ("平平淡淡才是真", {}),
    ]),
    dict(id="queue", dim="场景", q="排队容忍度?", options=[
        ("为好吃的排15分钟也值", {"queue_ok": 1}),
        ("5分钟是极限", {"queue_ok": -.5, "quick": .4}),
        ("人少清净最重要", {"quiet": 1, "queue_ok": -.8}),
    ]),
    dict(id="post_workout", dim="场景", q="刚运动完?", options=[
        ("是, 要补蛋白质", {"protein": 1.2, "meat": .5}),
        ("是, 先补碳水", {"comfort": .6, "rice": .4}),
        ("没有", {}),
    ]),
    dict(id="shareable", dim="场景", q="想多买几样拼着吃吗?", options=[
        ("对, 什么都想尝", {"group": .5, "bbq": .3}),
        ("一份套餐就好", {"setmeal": .3}),
    ]),
    dict(id="adventure", dim="场景", q="今天胆子大吗(尝试没吃过的窗口)?", options=[
        ("试试没吃过的", {"novelty": 1.3}),
        ("只吃熟悉的老窗口", {"novelty": -1}),
        ("随缘", {"novelty": .3, "random_boost": .6}),
    ]),

    # ------------------------------------------------ 预算 (8)
    dict(id="budget", dim="预算", q="这顿的预算?", options=[
        ("8元以内, 极致性价比", {"budget_level": 1, "value_first": 1}),
        ("8-12元", {"budget_level": 2}),
        ("12-18元", {"budget_level": 3}),
        ("18-25元", {"budget_level": 4}),
        ("25+, 不设限", {"budget_level": 5}),
    ]),
    dict(id="value_vs_good", dim="预算", q="性价比 vs 好吃优先?", options=[
        ("性价比优先", {"value_first": 1}),
        ("好吃最重要, 贵一点没事", {"value_first": -.5, "splurge": .5}),
    ]),
    dict(id="splurge_now", dim="预算", q="今天愿意奢侈一把吗?", options=[
        ("愿意, 特殊日子", {"splurge": 1}),
        ("不了, 老老实实吃饭", {"value_first": .5}),
    ]),
    dict(id="add_egg", dim="预算", q="加蛋/加肉要花钱, 加吗?", options=[
        ("必须加, 一碗才完整", {"egg": .6, "meat": .4}),
        ("看价格再定", {"value_first": .3}),
        ("不加", {}),
    ]),
    dict(id="portion", dim="预算", q="分量要求?", options=[
        ("大份/加量, 吃不饱难受", {"big_appetite": 1}),
        ("正常", {}),
        ("小份就好", {"big_appetite": -.8}),
    ]),
    dict(id="milk_tea", dim="预算", q="配杯奶茶/饮料?", options=[
        ("干饭必须配快乐水", {"splurge": .3}),
        ("白开水/食堂免费汤", {"value_first": .4, "soup": .2}),
    ]),
    dict(id="treat_guest", dim="预算", q="请同学吃饭的场面?", options=[
        ("要体面一点", {"splurge": .8, "group": .4}),
        ("AA 随意吃", {"value_first": .4}),
    ]),
    dict(id="cheap_mode", dim="预算", q="月底了钱包的状态?", options=[
        ("吃土模式, 越便宜越好", {"value_first": .8, "budget_level": 1}),
        ("正常", {}),
        ("刚生活费到账, 富裕", {"splurge": .5}),
    ]),

    # ------------------------------------------------ 健康 (8)
    dict(id="dieting", dim="健康", q="减脂期吗?", options=[
        ("是, 严格控油", {"healthy": 1.5, "fried": -1, "oily": -1, "light": 1}),
        ("佛系控制", {"healthy": .5}),
        ("不是, 该吃吃", {"indulgent": .5}),
    ]),
    dict(id="protein", dim="健康", q="蛋白质需求?", options=[
        ("增肌, 高蛋白", {"protein": 1.3, "meat": .6, "egg": .4}),
        ("正常", {}),
        ("不太在意", {}),
    ]),
    dict(id="veggies", dim="健康", q="想吃蔬菜吗?", options=[
        ("绿叶菜必须有", {"veggies": 1.1, "healthy": .5}),
        ("一般", {"veggies": .3}),
        ("肉食动物", {"meat": .8, "veggies": -.5}),
    ]),
    dict(id="indulgent_now", dim="健康", q="想'犯罪'吗(高热量快乐)?", options=[
        ("放开了吃, 今天不装了", {"indulgent": 1.3, "fried": .6, "oily": .5}),
        ("适度快乐", {}),
        ("克制住", {"healthy": .8, "indulgent": -1}),
    ]),
    dict(id="sugar", dim="健康", q="控糖吗?", options=[
        ("控, 甜的少吃", {"sweet": -1, "healthy": .4}),
        ("不控", {"sweet": .3}),
    ]),
    dict(id="coarse", dim="健康", q="粗粮杂粮?", options=[
        ("喜欢, 健康", {"healthy": .6, "porridge": .3}),
        ("一般", {}),
        ("吃不惯", {}),
    ]),
    dict(id="taboo", dim="健康", q="最近有忌口吗?", options=[
        ("忌油炸", {"fried": -1.2, "oily": -.8, "healthy": .5}),
        ("忌辣", {"spicy": -1.2}),
        ("没有忌口", {}),
    ]),
    dict(id="light_dinner", dim="健康", q="晚上想吃少点?", options=[
        ("是, 晚上吃清淡", {"light": .9, "soup": .4, "porridge": .3}),
        ("正常吃", {}),
    ]),

    # ------------------------------------------------ 随心 (10)
    dict(id="fate", dim="随心", q="把决定权交给命运?", options=[
        ("全随机, 给我惊喜", {"random_boost": 1}),
        ("半随机就好", {"random_boost": .5}),
        ("不要乱来, 按我口味", {"novelty": -.8}),
    ]),
    dict(id="nostalgic", dim="随心", q="想念家里的味道吗?", options=[
        ("想, 胃想回家", {"home": 1, "comfort": .5}),
        ("还好", {}),
    ]),
    dict(id="dark_food", dim="随心", q="猎奇接受度(奇怪搭配/新菜)?", options=[
        ("可以试试, 万一好吃呢", {"novelty": .8}),
        ("不敢, 保命要紧", {"novelty": -.4}),
    ]),
    dict(id="carb_or_meat", dim="随心", q="此刻更馋哪个?", options=[
        ("碳水快乐(面/饼/饭)", {"comfort": .8, "bing": .4, "noodle": .3}),
        ("大口吃肉", {"meat": 1}),
        ("都要!", {"comfort": .4, "meat": .4, "indulgent": .5}),
    ]),
    dict(id="image_now", dim="随心", q="闭上眼, 脑海里浮现的画面是?", options=[
        ("热气腾腾的一碗", {"hot": .8, "soup": .5}),
        ("红亮亮的辣椒", {"spicy": .8, "rich": .5}),
        ("绿油油的清爽", {"light": .7, "veggies": .3}),
        ("奶呼呼的甜", {"sweet": .7, "comfort": .4}),
    ]),
    dict(id="spicy_now", dim="随心", q="现在! 立刻! 想吃辣吗?", options=[
        ("超想, 辣到冒汗", {"spicy": 1.5}),
        ("一点点就好", {"spicy": .5}),
        ("完全不想", {"spicy": -1.2}),
    ]),
    dict(id="drink_pref", dim="随心", q="干饭配什么喝的?", options=[
        ("食堂免费汤就很香", {"soup": .5, "value_first": .3}),
        ("饮料/奶茶", {"splurge": .3}),
        ("啥都不配", {}),
    ]),
    dict(id="fruit_after", dim="随心", q="饭后水果?", options=[
        ("要, 收尾仪式感", {"healthy": .4}),
        ("不要", {}),
    ]),
    dict(id="egg_lover", dim="随心", q="蛋料理?", options=[
        ("煎蛋荷包蛋茶叶蛋, 加加加", {"egg": 1}),
        ("一般", {}),
    ]),
    dict(id="explore_mode", dim="随心", q="新学期/新一周的干饭策略?", options=[
        ("把没吃过的都试一遍", {"novelty": 1.2}),
        ("守护我的固定窗口", {"novelty": -1.2}),
        ("随心情", {}),
    ]),

    # ------------------------------------------------ 位置 (8)
    dict(id="walk", dim="位置", q="走路意愿?", options=[
        ("就近解决, 5分钟内", {"near_only": 1, "quick": .4}),
        ("愿意走10分钟", {"near_only": .3}),
        ("为好吃的走遍全校", {"near_only": -.8}),
    ]),
    dict(id="zone", dim="位置", q="现在人大概在哪片?", options=[
        ("紫荆公寓区", {"zone": "紫荆公寓区"}),
        ("学堂路/教学楼一带", {"zone": "学堂路沿线"}),
        ("西大操场/西区", {"zone": "西区"}),
        ("工字厅/荷花池核心区", {"zone": "校园中部"}),
        ("照澜院/南门一带", {"zone": "照澜院一带"}),
        ("其他/不确定", {}),
    ]),
    dict(id="indoor", dim="位置", q="天气差的话, 要室内/地下食堂吗?", options=[
        ("要, 不想淋雨吹风", {"quick": .2}),
        ("无所谓", {}),
    ]),
    dict(id="lazy_floor", dim="位置", q="找窗口的耐心?", options=[
        ("越简单直接越好", {"quick": .4, "quiet": .3}),
        ("愿意翻楼层探索", {"novelty": .4}),
    ]),
    dict(id="crowd", dim="位置", q="人多热闹 vs 人少安静?", options=[
        ("热闹有人气", {"quiet": -.5}),
        ("安静人少, 吃饭要清净", {"quiet": 1}),
        ("无所谓", {}),
    ]),
    dict(id="size_pref", dim="位置", q="大食堂 vs 小食堂?", options=[
        ("大而全, 品类多", {"novelty": .3}),
        ("小而美, 人少快取", {"quiet": .4}),
        ("都行", {}),
    ]),
    dict(id="takeout", dim="位置", q="堂食还是打包?", options=[
        ("打包带走回宿舍吃", {"quick": .6}),
        ("堂食, 坐下慢慢吃", {"comfort": .3, "solo": .2}),
    ]),
    dict(id="with_roomie", dim="位置", q="和室友/同学一起吗?", options=[
        ("一起拼单多点几样", {"group": .6}),
        ("各吃各的", {"solo": .4}),
    ]),
]

# 设置型权重键(不平均, 直接覆盖)
SET_KEYS = {"budget_level", "zone", "random_boost", "meal_kind"}

assert len(QUESTIONS) == 79, f"题库数量变化: {len(QUESTIONS)}"


def sample_questions(n=12, rng=None):
    """分层抽样: 每个维度保底 1 题, 其余从全库随机补足。"""
    import random
    rng = rng or random
    by_dim = {}
    for q in QUESTIONS:
        by_dim.setdefault(q["dim"], []).append(q)
    picked = [rng.choice(by_dim[d]) for d in DIMS]
    rest = [q for q in QUESTIONS if q not in picked]
    rng.shuffle(rest)
    while len(picked) < n and rest:
        picked.append(rest.pop())
    return picked[:n]
