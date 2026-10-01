# -*- coding: utf-8 -*-
"""
种子数据：清华大学食堂基础信息 + 通用菜品属性词典。

食堂信息来源(清华大学饮食服务中心官网, 2026-09 查询):
  学生食堂: https://www.tsinghua.edu.cn/ysfwzx/info/1004/1007.htm
  教工餐厅: https://www.tsinghua.edu.cn/ysfwzx/info/1004/1008.htm
  特色餐厅: https://www.tsinghua.edu.cn/ysfwzx/info/1004/1009.htm

字段说明:
  zone   校园片区(用于"就近"软匹配, 不精确到米, 供参考)
  price  价位 1(便宜)~4(较贵)
  speed  出餐速度 1(慢)~5(快)
  seats  官方公布的容纳人数(人流量提示), 未知为 None
  halal  是否清真
  note   一句话介绍(官方页面摘要)

菜品 attrs: 正数代表该属性强度(0.5~2), 与问卷里的同名偏好权重做内积;
真实的"哪个食堂哪个窗口有什么"以爬取的小红书帖子为准, 种子只做冷启动兜底。
"""

# ---------------------------------------------------------------- 食堂

CANTEENS = {
    "紫荆园": dict(
        aliases=["紫荆园食堂", "紫荆食堂", "紫荆"], zone="紫荆公寓区", price=1, speed=3,
        seats=3500, halal=False,
        note="紫荆公寓区内, 共5层(含地下一层), 清青披萨在B1"),
    "桃李园": dict(
        aliases=["桃李园食堂", "桃李"], zone="紫荆公寓区", price=1, speed=3,
        seats=None, halal=False,
        note="紫荆公寓区, 共4层(含地下一层), 清青休闲在B1"),
    "芝兰园": dict(
        aliases=["芝兰园餐厅", "芝兰"], zone="紫荆公寓区", price=2, speed=2,
        seats=800, halal=True,
        note="紫荆公寓东北侧, 清真餐厅, 共两层; 清青小火锅在二层南侧"),
    "玉树园": dict(
        aliases=["玉树园餐厅", "玉树"], zone="紫荆公寓区", price=3, speed=2,
        seats=None, halal=False,
        note="紫荆公寓18/19号楼之间, 环境优雅, 传闻烤鸭是招牌(博客评价)"),
    "清芬园": dict(
        aliases=["清芬园食堂", "清芬"], zone="学堂路沿线", price=1, speed=4,
        seats=1900, halal=False,
        note="学堂路×至善路交叉口东南侧, 上下课必经之路, 共4层; 清青快餐在B1"),
    "听涛园": dict(
        aliases=["听涛园食堂", "听涛"], zone="学堂路沿线", price=1, speed=3,
        seats=1000, halal=False,
        note="学堂路×至善路交汇处, 万泉河东, 共两层; 清青牛拉在二层"),
    "丁香园": dict(
        aliases=["丁香园食堂", "丁香"], zone="其他区域", price=1, speed=3,
        seats=580, halal=False,
        note="原名十四食堂, 小巧精致, 饭菜朴素淡雅"),
    "观畴园": dict(
        aliases=["观畴园食堂", "观畴"], zone="西区", price=2, speed=3,
        seats=3000, halal=False,
        note="西大操场北侧三层综合大食堂, 中西+风味小吃; 清青永和/清青咖啡在一层"),
    "闻馨园": dict(
        aliases=["闻馨园食堂", "闻馨"], zone="西区", price=1, speed=3,
        seats=100, halal=True,
        note="观畴园西南角, 清真小食堂"),
    "寓园": dict(
        aliases=["寓园食堂", "寓园"], zone="西区", price=2, speed=3,
        seats=None, halal=False,
        note="西区家属区, 老牌'二员工', 面包坊在其东侧"),
    "荷园": dict(
        aliases=["荷园食堂", "荷园"], zone="校园中部", price=3, speed=2,
        seats=None, halal=False,
        note="荷花池畔, 毗邻工字厅和古月堂, 老牌'一员工'"),
    "熙春园": dict(
        aliases=["熙春园餐厅", "熙春"], zone="校园中部", price=3, speed=2,
        seats=210, halal=False,
        note="原招待餐厅, 工字厅西侧约100米, 徽派建筑"),
    "澜园": dict(
        aliases=["澜园食堂", "澜园"], zone="照澜院一带", price=2, speed=3,
        seats=None, halal=False,
        note="照澜院商业区(社区购物中心二、三层)"),
    "南园": dict(
        aliases=["南园食堂", "南园"], zone="照澜院一带", price=2, speed=3,
        seats=None, halal=False,
        note="南楼小区, 洁华幼儿园南侧, 原南楼餐厅"),
    "家园": dict(
        aliases=["家园食堂", "家园"], zone="照澜院一带", price=2, speed=3,
        seats=120, halal=False,
        note="西南小区, 清华附小南侧"),
    "北园": dict(
        aliases=["北园食堂", "北园"], zone="其他区域", price=2, speed=3,
        seats=100, halal=False,
        note="西北小区西北角, 毗邻圆明园"),
    "融园": dict(
        aliases=["融园食堂", "融园"], zone="其他区域", price=2, speed=3,
        seats=None, halal=False,
        note="五道口金融学院院内, 共两层"),
    "双清园": dict(
        aliases=["双清园食堂", "双清"], zone="其他区域", price=1, speed=3,
        seats=None, halal=False,
        note="2021年开业, 校外双清公寓周边"),
}

# 校园片区 -> 俗称提示(用于推荐理由展示)
ZONES_DESC = {
    "紫荆公寓区": "东北角紫荆公寓区",
    "学堂路沿线": "学堂路/至善路一带(上下课顺路)",
    "西区": "西大操场/西区家属区一带",
    "校园中部": "工字厅/荷花池核心区",
    "照澜院一带": "照澜院/南小区一带",
    "其他区域": "校园其他位置",
}

# ---------------------------------------------------------------- 菜品
# attrs 键与问卷偏好键一致; price 1~4; aka 是帖子文本里的常见别名。
# canteen/source 字段: 有明确官方或公开来源的才填。

DISHES = {
    # ---- 官方特色窗口(来源: 饮食服务中心官网) ----
    "清青牛拉": dict(aka=["牛肉拉面", "兰州拉面", "牛拉"], canteen="听涛园",
        price=1, source="官网:听涛园二层", attrs={"noodle": 2, "northwest": 1.5, "halal": 1, "soup": 1, "quick": 0.5}),
    "清青披萨": dict(aka=["披萨", "比萨"], canteen="紫荆园",
        price=2, source="官网:紫荆园B1", attrs={"western": 2, "bread": 1.5, "indulgent": 1}),
    "清青快餐": dict(aka=["汉堡", "炸鸡汉堡"], canteen="清芬园",
        price=2, source="官网:清芬园B1", attrs={"western": 2, "quick": 1.5, "fried": 1, "indulgent": 1}),
    "清青小火锅": dict(aka=["小火锅"], canteen="芝兰园",
        price=2, source="官网:芝兰园二层南侧", attrs={"hotpot": 2, "soup": 1, "spicy": 0.5, "group": 1}),
    "清青永和": dict(aka=["永和豆浆"], canteen="观畴园",
        price=2, source="官网:观畴园一层北侧", attrs={"dimsum": 1.5, "porridge": 1, "breakfast": 1.5}),
    "面包坊面包": dict(aka=["面包"], canteen="寓园",
        price=1, source="官网:寓园东侧", attrs={"bread": 2, "quick": 1, "breakfast": 1}),

    # ---- 招牌(公开来源, 置信度中) ----
    "北京烤鸭": dict(aka=["烤鸭"], canteen="玉树园",
        price=3, source="博客评价:玉树园", attrs={"bbq": 1.5, "savory": 1.5, "meat": 1.5, "home": 0.5}),

    # ---- 川湘 ----
    "麻辣香锅": dict(price=2, attrs={"spicy": 2, "numbing": 1, "mallow": 2, "rice": 0.5, "rich": 1.5, "indulgent": 0.5}),
    "麻辣烫": dict(price=1, attrs={"spicy": 1.5, "mallow": 1.5, "soup": 0.5, "veggies": 0.5}),
    "冒菜": dict(price=1, attrs={"spicy": 2, "mallow": 1.5, "soup": 1, "rich": 1}),
    "水煮肉片": dict(price=2, attrs={"spicy": 2, "sichuan": 1.5, "rich": 1.5, "meat": 1, "rice": 0.5}),
    "水煮鱼": dict(price=2, attrs={"spicy": 2, "sichuan": 1.5, "soup": 1, "meat": 1, "rice": 0.5}),
    "酸菜鱼": dict(price=2, attrs={"sour": 1.5, "spicy": 1, "sichuan": 1.5, "soup": 1.5, "meat": 1}),
    "麻婆豆腐": dict(price=1, attrs={"spicy": 1.5, "numbing": 1, "sichuan": 1.5, "rice": 1}),
    "宫保鸡丁": dict(price=1, attrs={"spicy": 1, "sweet": 0.5, "sichuan": 1.5, "meat": 1, "rice": 1}),
    "鱼香肉丝": dict(price=1, attrs={"sour": 1, "sweet": 1, "spicy": 0.5, "sichuan": 1, "rice": 1}),
    "回锅肉": dict(price=1, attrs={"spicy": 1, "sichuan": 1, "rich": 1, "meat": 1, "rice": 1}),
    "辣子鸡": dict(price=2, attrs={"spicy": 2, "sichuan": 1.5, "meat": 1, "crunch": 0.5}),
    "小炒肉": dict(aka=["农家小炒肉", "湘菜小炒肉"], price=1, attrs={"spicy": 1.5, "home": 1, "meat": 1, "rice": 1}),
    "重庆小面": dict(price=1, attrs={"spicy": 2, "numbing": 1, "noodle": 2, "sichuan": 1}),
    "酸汤肥牛": dict(price=2, attrs={"sour": 1.5, "spicy": 1, "soup": 1.5, "meat": 1, "yunnan": 0.5}),

    # ---- 家常/鲁 ----
    "红烧肉": dict(price=2, attrs={"sweet": 1, "savory": 2, "rich": 2, "meat": 1.5, "home": 1.5, "indulgent": 0.5, "soft": 1}),
    "糖醋里脊": dict(price=2, attrs={"sweet": 1, "sour": 1, "fried": 1, "crunch": 1, "meat": 1, "rice": 0.5}),
    "番茄炒蛋": dict(price=1, attrs={"sour": 0.5, "home": 1.5, "veggies": 0.5, "rice": 1, "light": 0.5}),
    "青椒肉丝": dict(price=1, attrs={"spicy": 0.5, "home": 1.2, "meat": 1, "rice": 1}),
    "木须肉": dict(price=1, attrs={"home": 1.2, "egg": 0.5, "meat": 0.5, "rice": 1}),
    "清炒时蔬": dict(aka=["绿叶菜", "青菜"], price=1, attrs={"veggies": 2, "light": 1.5, "healthy": 1.5}),
    "鸡蛋羹": dict(aka=["蒸蛋"], price=1, attrs={"egg": 2, "light": 1.2, "soft": 1.5, "healthy": 1}),

    # ---- 粤 ----
    "烧腊饭": dict(aka=["叉烧饭", "烧鸭饭"], price=2, attrs={"cantonese": 2, "rice": 1.5, "meat": 1.5, "savory": 1}),
    "煲仔饭": dict(price=2, attrs={"cantonese": 1.5, "rice": 1.5, "savory": 1, "rich": 0.5}),
    "肠粉": dict(price=1, attrs={"cantonese": 2, "dimsum": 1, "light": 1, "breakfast": 1}),
    "虾饺": dict(price=2, attrs={"cantonese": 2, "dimsum": 1.5, "breakfast": 1}),
    "例汤": dict(aka=["老火靓汤"], price=1, attrs={"soup": 2, "cantonese": 1, "light": 1, "healthy": 1}),

    # ---- 西北/新疆/清真 ----
    "大盘鸡": dict(price=2, attrs={"spicy": 1.5, "xinjiang": 1.5, "northwest": 1.5, "noodle": 1, "meat": 1.5, "group": 0.5}),
    "羊肉泡馍": dict(price=2, attrs={"northwest": 2, "soup": 1.5, "savory": 1.5, "halal": 1}),
    "油泼面": dict(price=1, attrs={"northwest": 2, "noodle": 2, "spicy": 1, "oily": 1}),
    "裤带面": dict(aka=["biangbiang面"], price=1, attrs={"northwest": 2, "noodle": 2}),
    "肉夹馍": dict(price=1, attrs={"northwest": 1.5, "quick": 1, "meat": 1, "night_snack": 0.5}),
    "凉皮": dict(price=1, attrs={"northwest": 1.5, "cold": 1.5, "sour": 1, "light": 0.5}),
    "烤羊肉串": dict(aka=["羊肉串", "烤串"], price=2, attrs={"bbq": 2, "xinjiang": 1.5, "halal": 1, "night_snack": 1.5, "spicy": 0.5}),
    "手抓饭": dict(price=2, attrs={"xinjiang": 2, "halal": 1, "rice": 1.5, "meat": 1}),
    "新疆炒米粉": dict(price=1, attrs={"spicy": 2, "powder": 2, "xinjiang": 1.5}),
    "羊杂汤": dict(price=1, attrs={"soup": 2, "halal": 1.5, "savory": 1, "hot": 1}),

    # ---- 东北 ----
    "锅包肉": dict(price=2, attrs={"sweet": 1.2, "sour": 1, "northeast": 2, "fried": 1.5, "crunch": 1.5, "meat": 1}),
    "地三鲜": dict(price=1, attrs={"northeast": 2, "veggies": 1.5, "rich": 1, "rice": 1}),
    "东北大拉皮": dict(price=1, attrs={"northeast": 2, "cold": 1.2, "sour": 0.8, "soft": 1}),

    # ---- 云贵/粉 ----
    "过桥米线": dict(aka=["米线"], price=2, attrs={"yunnan": 2, "powder": 2, "soup": 1.5}),
    "小锅米线": dict(price=1, attrs={"yunnan": 2, "powder": 2, "soup": 1, "spicy": 0.8}),
    "螺蛳粉": dict(price=2, attrs={"spicy": 2, "sour": 2, "powder": 2, "rich": 1.5, "night_snack": 1, "indulgent": 0.8}),
    "酸辣粉": dict(price=1, attrs={"spicy": 1.5, "sour": 1.5, "powder": 2}),
    "桂林米粉": dict(price=1, attrs={"powder": 2, "sour": 0.5}),

    # ---- 面点/早餐 ----
    "包子": dict(price=1, attrs={"dimsum": 2, "breakfast": 1.5, "quick": 1}),
    "小笼包": dict(price=1, attrs={"dimsum": 2, "breakfast": 1, "soft": 1}),
    "锅贴": dict(aka=["生煎"], price=1, attrs={"dimsum": 1.5, "fried": 1, "breakfast": 1, "crunch": 1}),
    "饺子": dict(price=1, attrs={"dimsum": 2, "savory": 1, "soft": 1}),
    "煎饼果子": dict(price=1, attrs={"bing": 2, "breakfast": 1.5, "quick": 1.5, "night_snack": 0.5}),
    "手抓饼": dict(price=1, attrs={"bing": 2, "fried": 1, "quick": 1}),
    "酱香饼": dict(price=1, attrs={"bing": 2, "quick": 1.2, "breakfast": 1}),
    "葱油饼": dict(price=1, attrs={"bing": 2, "fried": 1, "breakfast": 1}),
    "油条": dict(price=1, attrs={"fried": 2, "breakfast": 1.5}),
    "豆腐脑": dict(price=1, attrs={"breakfast": 1.5, "soft": 2, "light": 1, "savory": 0.5}),
    "胡辣汤": dict(price=1, attrs={"breakfast": 1.5, "soup": 1.5, "spicy": 1, "savory": 1}),
    "粥": dict(aka=["小米粥", "白粥", "南瓜粥", "八宝粥"], price=1, attrs={"porridge": 2, "breakfast": 1.5, "light": 1.5, "soft": 1.5}),
    "茶叶蛋": dict(price=1, attrs={"egg": 2, "breakfast": 1, "quick": 1}),
    "豆浆": dict(price=1, attrs={"breakfast": 1.5, "porridge": 0.5}),

    # ---- 米饭/套餐 ----
    "盖浇饭": dict(price=1, attrs={"setmeal": 2, "rice": 1.5, "quick": 1}),
    "黄焖鸡米饭": dict(aka=["黄焖鸡"], price=2, attrs={"setmeal": 1.5, "rice": 1, "savory": 1.5, "spicy": 0.5, "meat": 1}),
    "猪脚饭": dict(aka=["猪脚"], price=2, attrs={"setmeal": 1.5, "rice": 1, "savory": 1.5, "meat": 1.5, "soft": 1}),
    "木桶饭": dict(price=2, attrs={"setmeal": 1.5, "rice": 1.5}),
    "铁板饭": dict(aka=["铁板烧"], price=2, attrs={"teppan": 2, "rice": 1, "rich": 1, "oily": 0.5}),
    "咖喱饭": dict(price=2, attrs={"japanese": 1.5, "rice": 1.5, "sweet": 0.5, "savory": 1}),
    "日式定食": dict(price=2, attrs={"japanese": 2, "setmeal": 1.5, "light": 1, "healthy": 0.5}),
    "石锅拌饭": dict(price=2, attrs={"korean": 2, "rice": 1.5, "egg": 0.5, "veggies": 0.5}),
    "部队锅": dict(price=2, attrs={"korean": 2, "hotpot": 1.5, "soup": 1, "spicy": 1, "group": 1}),
    "韩式炸鸡": dict(price=2, attrs={"korean": 1.5, "fried": 2, "indulgent": 1, "night_snack": 1}),
    "意面": dict(aka=["意大利面"], price=2, attrs={"western": 2, "noodle": 1.5}),

    # ---- 轻食/其他 ----
    "沙拉": dict(aka=["轻食"], price=2, attrs={"salad": 2, "veggies": 1.5, "healthy": 2, "light": 1.5, "cold": 1}),
    "三明治": dict(price=2, attrs={"bread": 2, "quick": 1.5, "breakfast": 1, "light": 1}),
    "炸鸡": dict(aka=["炸鸡腿"], price=2, attrs={"fried": 2, "western": 1, "indulgent": 1.5, "night_snack": 1, "crunch": 1}),
    "关东煮": dict(price=1, attrs={"japanese": 1, "soup": 1.5, "night_snack": 1, "light": 1}),
    "麻辣拌": dict(price=1, attrs={"spicy": 1.5, "mallow": 1.5}),
    "酸菜白肉": dict(price=2, attrs={"northeast": 1.5, "soup": 1.5, "sour": 1, "meat": 1}),
    "粗粮饭": dict(aka=["杂粮饭"], price=1, attrs={"healthy": 1.5, "rice": 1}),
    "烤红薯": dict(price=1, attrs={"hot": 1.5, "soft": 1.5, "healthy": 1, "comfort": 1}),

    # ---- 手动语料扩充(2026-10, 用户实测的清华各食堂窗口) ----
    "糖醋鸡": dict(price=1, attrs={"sweet": 1, "sour": .5, "rice": .5}),
    "菠萝咕噜肉": dict(price=2, attrs={"sweet": 1.5, "sour": .5, "fried": 1, "meat": 1, "cantonese": 1}),
    "叉烧小排": dict(price=2, attrs={"sweet": .8, "savory": 1.5, "meat": 1.2, "cantonese": 1}),
    "糖醋小排": dict(price=2, attrs={"sweet": 1.5, "sour": 1, "soft": 1, "meat": 1}),
    "带鱼": dict(aka=["酥带鱼", "烧带鱼"], price=2, attrs={"savory": 1.5, "meat": 1, "rich": .5}),
    "蛋卷": dict(aka=["虎皮蛋卷", "肉松蛋卷"], price=1, attrs={"dimsum": 1, "breakfast": 1, "soft": 1}),
    "担担面": dict(price=1, attrs={"noodle": 2, "sichuan": 1.5, "spicy": 1.2, "numbing": .5}),
    "甜水面": dict(price=1, attrs={"noodle": 2, "sichuan": 1.2, "sweet": 1, "spicy": .8}),
    "黑鸭煲": dict(price=2, attrs={"savory": 1.5, "rich": 1.5, "spicy": .8, "meat": 1, "soup": .5}),
    "山东炒鸡": dict(price=2, attrs={"home": 1.5, "savory": 1.5, "meat": 1.5, "rich": .8}),
    "金钱蛋": dict(price=1, attrs={"egg": 2, "fried": 1, "home": 1}),
    "荤豆花": dict(price=1, attrs={"sichuan": 1, "soft": 1.5, "soup": 1, "light": .5}),
    "干拌荤豆花": dict(price=1, attrs={"sichuan": 1.2, "spicy": 1, "rich": 1, "soft": 1}),
    "腊汁肉拌面": dict(price=2, attrs={"northwest": 1.5, "noodle": 2, "meat": 1.2, "savory": 1}),
    "肥牛蘸水面": dict(price=2, attrs={"northwest": 1.5, "noodle": 2, "meat": 1, "sour": .5}),
    "炸蔬菜": dict(price=1, attrs={"veggies": 1.5, "fried": 1.5, "crunch": 1}),
    "豌杂小面": dict(price=1, attrs={"sichuan": 1.5, "noodle": 2, "spicy": 1, "home": .5}),
    "江西小炒": dict(price=1, attrs={"spicy": 2, "home": 1.2, "rich": .8, "meat": .8}),
    "尖椒干豆腐": dict(price=1, attrs={"home": 1.5, "veggies": .8, "spicy": .5, "light": .5}),
    "瓦罐汤": dict(price=1, attrs={"soup": 2, "light": 1, "healthy": .8}),
    "扁肉": dict(price=1, attrs={"dimsum": 1.5, "soup": .8, "light": .8}),
    "芋泥": dict(price=1, attrs={"sweet": 1.5, "soft": 1.5, "comfort": .8}),
    "牛肉米粉": dict(price=1, attrs={"powder": 2, "meat": 1, "soup": .8}),
    "小龙虾": dict(price=2, attrs={"spicy": 1.5, "night_snack": 1.5, "meat": 1, "indulgent": .8}),
    "煎蛋": dict(aka=["现煎荷包蛋", "荷包蛋"], price=1, attrs={"egg": 2, "quick": 1}),
    "冒烤鸭": dict(price=2, attrs={"spicy": 1.2, "mallow": 1, "meat": 1.2, "rich": 1}),
    "鸡里蹦": dict(price=2, attrs={"meat": 1.5, "protein": 1, "savory": 1, "rich": .5}),
    "白煮鸡腿": dict(price=2, attrs={"protein": 2, "healthy": 1.5, "light": 1.2, "meat": 1.5}),
    "跷脚牛肉": dict(price=2, attrs={"soup": 1.5, "savory": 1.2, "meat": 1, "sichuan": .8}),
    "烤鱼": dict(price=2, attrs={"spicy": 1.5, "rich": 1.5, "meat": 1.2, "group": .8}),
    "砂锅土豆粉": dict(price=1, attrs={"powder": 2, "soup": 1, "soft": 1, "hot": 1}),
    "叉烧包": dict(aka=["叉烧馅包子"], price=1, attrs={"dimsum": 1.5, "cantonese": 1, "sweet": .5, "breakfast": 1}),
    "叻沙米粉": dict(price=2, attrs={"powder": 2, "soup": 1, "spicy": .8, "sweet": .5}),
    "白切鸡": dict(price=2, attrs={"cantonese": 1.5, "light": 1.2, "meat": 1.5, "healthy": .5}),
    "虾膏豆腐": dict(price=2, attrs={"savory": 1.5, "soft": 1, "rich": .8}),
    "海南鸡饭": dict(price=2, attrs={"rice": 1.5, "light": 1.2, "meat": 1.2, "healthy": .5}),
    "椰子鸡饭": dict(price=2, attrs={"rice": 1.5, "sweet": .5, "light": 1, "meat": 1}),
    "炙子烤肉": dict(price=2, attrs={"bbq": 1.5, "meat": 1.5, "savory": 1, "rich": .8}),
    "醋溜木须": dict(price=1, attrs={"sour": 1.2, "home": 1, "egg": .8, "light": .5}),
    "啤酒鸡": dict(price=2, attrs={"home": 1, "savory": 1.2, "meat": 1.2, "rich": .5}),
    "麻辣牛肉干": dict(price=2, attrs={"spicy": 1.5, "meat": 2, "savory": 1, "night_snack": .5}),
    "胡萝卜牛肉": dict(price=1, attrs={"home": 1.2, "veggies": .8, "meat": 1, "light": .5}),
    "豚骨拉面": dict(price=2, attrs={"japanese": 1.5, "noodle": 2, "soup": 1}),
    "烧鸟": dict(price=2, attrs={"japanese": 1.2, "bbq": 1.2, "night_snack": 1}),
    "沙茶面": dict(price=1, attrs={"noodle": 2, "soup": 1, "savory": 1}),
    "打抛饭": dict(price=2, attrs={"rice": 1.5, "spicy": 1, "savory": 1}),
}

# ---------------------------------------------------------------- 菜品分类
# 正餐 = 能当一顿饭吃; 小吃 = 点心/甜品/早餐小食/零食; 配菜 = 汤/绿叶菜/小菜(搭配用)。
# 未列出的默认"正餐"。
KIND_SNACK = {
    "清青永和", "面包坊面包", "蛋卷", "芋泥", "烤红薯", "茶叶蛋", "豆浆",
    "油条", "葱油饼", "酱香饼", "手抓饼", "煎饼果子", "小笼包", "包子",
    "锅贴", "豆腐脑", "胡辣汤", "粥", "关东煮", "烤羊肉串", "烧鸟",
    "麻辣牛肉干", "小龙虾", "叉烧包", "煎蛋", "炸蔬菜",
}
KIND_SIDE = {
    "例汤", "瓦罐汤", "清炒时蔬", "鸡蛋羹", "金钱蛋", "醋溜木须",
    "尖椒干豆腐", "粗粮饭", "羊杂汤", "东北大拉皮",
}


def _assign_kinds():
    for name, d in DISHES.items():
        d["kind"] = ("小吃" if name in KIND_SNACK
                     else "配菜" if name in KIND_SIDE else "正餐")


_assign_kinds()


def canteen_aliases():
    """返回 [(canonical, alias), ...], 按别名长度降序, 供解析器做最长匹配。"""
    pairs = []
    for name, info in CANTEENS.items():
        pairs.append((name, name))
        for a in info.get("aliases", []):
            pairs.append((name, a))
    return sorted(pairs, key=lambda x: len(x[1]), reverse=True)


def dish_names_sorted():
    """菜品名+别名, 按长度降序(解析时先匹配长的, 避免'拉面'吃掉'牛肉拉面')。"""
    out = []
    for name, d in DISHES.items():
        out.append((name, name, d))
        for a in d.get("aka", []):
            out.append((name, a, d))
    return sorted(out, key=lambda x: len(x[1]), reverse=True)
