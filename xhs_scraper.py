# -*- coding: utf-8 -*-
"""
小红书"清华美食"帖子采集器 (Playwright)

策略: 不硬刚反爬, 而是"当一个安静的真人用户":
  1. 用本机真实 Edge/Chrome 浏览器 + 持久化用户目录, 首次手动扫码登录, 之后复用登录态
  2. 所有操作之间随机停顿(几秒级), 滚动按真人节奏小步滑, 鼠标偶尔随机移动
  3. 每个关键词/每次运行都设上限, 帖子数量克制, 数据只留在本地
  4. 遇到滑块/验证码不绕过 —— 停下来等你在浏览器窗口里手动完成

用法:
  python main.py scrape                     # 默认关键词
  python main.py scrape --keywords "清华食堂,清华干饭"
"""

import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("缺少依赖, 请先执行: pip install playwright")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
POSTS_FILE = DATA_DIR / "posts.json"
PROFILE_DIR = ROOT / "browser_profile"   # 持久化浏览器配置(保存登录态)

DEFAULT_KEYWORDS = [
    "清华食堂", "清华美食", "清华干饭", "清华必吃",
    "清华食堂推荐", "清华食堂攻略", "清华大学食堂", "清华好吃的窗口",
]

# ---- 礼貌上限(求稳, 别调高; 想采更多就多跑几次, 间隔几小时) ----
MAX_NOTES_PER_KEYWORD = 15   # 每个关键词最多打开的帖子数
MAX_TOTAL_PER_RUN = 60       # 单次运行总上限
MAX_SCROLL_ROUNDS = 30       # 搜索页每轮关键词最多滚动次数
NOTE_SLEEP = (3.5, 9.0)      # 帖子之间的随机停顿(秒)
KEYWORD_SLEEP = (8, 18)      # 关键词切换之间的停顿(秒)
LONG_REST_CHANCE = 0.15      # 每篇帖子后小概率多歇一会儿
LONG_REST = (20, 45)

NOTE_ID_RE = re.compile(r"/(?:explore|search_result|notes?)/([0-9a-zA-Z]{20,40})")
VERIFY_HINTS = ("扫码登录", "访问异常", "拖动滑块", "安全验证", "请完成验证")


def rs(a, b):
    time.sleep(random.uniform(a, b))


def pick_channel():
    """优先本机 Chrome, 其次 Edge(Win11 自带), 都没有就用 Chromium。"""
    candidates = [
        ("chrome", Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe")),
        ("chrome", Path(r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")),
        ("msedge", Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")),
        ("msedge", Path(r"C:/Program Files/Microsoft/Edge/Application/msedge.exe")),
    ]
    for ch, path in candidates:
        if path.exists():
            return ch
    return "chromium"


def load_posts():
    if POSTS_FILE.exists():
        return json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    return []


def save_posts(posts):
    DATA_DIR.mkdir(exist_ok=True)
    POSTS_FILE.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


def is_logged_in(context):
    try:
        for c in context.cookies("https://www.xiaohongshu.com"):
            if c.get("name") == "web_session" and c.get("value"):
                return True
    except Exception:
        pass
    return False


def ensure_login(context, page):
    page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
    rs(2.5, 4.5)
    if is_logged_in(context):
        print("[OK] 已有登录态, 直接开始")
        return
    print("\n" + "=" * 60)
    print("请在弹出的浏览器窗口里登录小红书(建议手机 App 扫码)")
    print("登录成功后本脚本会自动继续; 窗口请保持打开 (最多等 5 分钟)")
    print("=" * 60 + "\n")
    deadline = time.time() + 300
    while time.time() < deadline:
        rs(3, 5)
        if is_logged_in(context):
            print("[OK] 登录成功")
            rs(1.5, 3)
            return
    raise SystemExit("等待登录超时, 请重新运行再试")


def wander_mouse(page):
    """模拟真人随手晃鼠标。"""
    try:
        page.mouse.move(
            random.randint(120, 1300), random.randint(100, 800),
            steps=random.randint(6, 18))
    except Exception:
        pass


def close_login_popup(page):
    """搜索页可能弹出登录引导浮层, 尝试关掉。"""
    for sel in ('[class*="close"]', ".close", '[aria-label="Close"]'):
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                rs(0.8, 1.6)
                return
        except Exception:
            continue


def wait_if_verified(page):
    """检测滑块/验证页: 不绕过, 停下来等人工处理。"""
    try:
        html = page.content()
    except Exception:
        return
    if any(h in html for h in VERIFY_HINTS) and not is_logged_in(page.context):
        return
    if any(h in html for h in VERIFY_HINTS[1:]):  # 访问异常/滑块等
        print("\n[!!] 检测到安全验证/滑块, 请在浏览器窗口手动完成")
        print("     (脚本会在旁边等最多 3 分钟)")
        deadline = time.time() + 180
        while time.time() < deadline:
            rs(4, 7)
            try:
                html = page.content()
            except Exception:
                return
            if not any(h in html for h in VERIFY_HINTS[1:]):
                print("[OK] 验证已通过, 继续")
                return
        raise SystemExit("验证超时, 请稍后重新运行")


def collect_note_ids(page, keyword, limit):
    """搜索并像真人一样滚动收集帖子链接(搜索结果是虚拟列表, 边滚边收)。

    返回 [(note_id, 原始href), ...]; 小红书现在要求带 xsec_token 的完整链接,
    裸开 /explore/<id> 会被拦, 所以优先保留带 token 的那条。
    """
    url = (f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
           f"&source=web_search_result_notes")

    def _try_once():
        # commit 即返回(小红书的 domcontentloaded 有时迟迟不触发), 然后自己等
        page.goto(url, wait_until="commit", timeout=60000)
        try:
            page.bring_to_front()
        except Exception:
            pass
        rs(3, 6)
        try:
            # state=attached: 小红书瀑布流卡片在 DOM 里但常被判定为"不可见",
            # 用默认 visible 状态会白白超时, 我们只需要链接存在
            page.wait_for_selector(
                "a[href*='/search_result/'], a[href*='/explore/']",
                timeout=30000, state="attached")
            return True
        except Exception:
            close_login_popup(page)
            wait_if_verified(page)
            try:
                page.wait_for_selector(
                    "a[href*='/search_result/'], a[href*='/explore/']",
                    timeout=20000, state="attached")
                return True
            except Exception:
                return False

    if not _try_once():
        print("  [等待] 搜索页加载慢, 冷却 45 秒后重试一次…")
        rs(40, 55)
        if not _try_once():
            print("  [跳过] 没有搜到内容")
            return []

    best = {}   # note_id -> href(优先带 xsec_token 的)
    order = []
    stale = 0
    for _ in range(MAX_SCROLL_ROUNDS):
        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))")
        new = 0
        for h in hrefs:
            m = NOTE_ID_RE.search(h or "")
            if not m:
                continue
            nid = m.group(1)
            if nid not in best:
                best[nid] = h
                order.append(nid)
                new += 1
            elif "xsec_token" in (h or "") and "xsec_token" not in (best[nid] or ""):
                best[nid] = h
        stale = stale + 1 if new == 0 else 0
        if len(order) >= limit or stale >= 5:
            break
        # 真人式浏览: 晃一下鼠标, 小步下滑, 偶尔回看一眼
        wander_mouse(page)
        page.mouse.wheel(0, random.randint(450, 1000))
        rs(1.2, 2.8)
        if random.random() < 0.12:
            page.mouse.wheel(0, -random.randint(150, 400))
            rs(0.8, 1.8)
    return [(nid, best[nid]) for nid in order]


def parse_count(s):
    """'1.2万' -> 12000, '358' -> 358"""
    if s is None:
        return 0
    s = str(s).strip().replace("+", "")
    m = re.search(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


def dig_state(html, nid):
    """优先从页面内嵌的 __INITIAL_STATE__ 取结构化数据。"""
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(.+?)</script>", html, re.S)
    if not m:
        return None
    raw = m.group(1).strip().rstrip(";").replace("undefined", "null")
    try:
        state = json.loads(raw)
    except Exception:
        return None
    try:
        note_map = (state.get("note") or {}).get("noteDetailMap") or {}
        node = note_map.get(nid) or next(iter(note_map.values()), {})
        note = node.get("note") or {}
        if not note:
            return None
        inter = note.get("interactInfo") or {}
        return dict(
            title=(note.get("title") or "").strip(),
            desc=(note.get("desc") or "").strip(),
            author=((note.get("user") or {}).get("nickname") or "").strip(),
            liked=parse_count(inter.get("liked") or inter.get("likedCount")),
            collected=parse_count(inter.get("collected")),
            comments=parse_count(inter.get("commentCount")),
            tags=[t.get("name", "") for t in note.get("tagList") or []],
            time=str(note.get("time") or ""),
        )
    except Exception:
        return None


def dig_dom(page):
    """DOM 兜底(小红书样式类名带哈希, 用相对稳定的 id/结构)。"""
    def txt(sel):
        try:
            return page.locator(sel).first.inner_text(timeout=2500).strip()
        except Exception:
            return ""
    title = txt("#detail-title") or txt(".note-content .title")
    desc = txt("#detail-desc") or txt(".note-text") or txt(".desc")
    author = txt(".username .name") or txt(".author .name")
    liked = parse_count(txt(".like-wrapper .count") or txt(".engage-bar .count"))
    if not title and not desc:
        return None
    return dict(title=title, desc=desc, author=author, liked=liked,
                collected=0, comments=0, tags=[], time="")


COMMENT_API_MARKERS = ("/api/sns/web/v2/comment/page", "/api/comment/list")
MAX_COMMENTS = 30
COMMENT_SCROLL_ROUNDS = 6


def _comment_listener(captured):
    """监听浏览器自己发出的评论接口响应(我们不主动调任何接口)。"""
    def on_response(resp):
        if any(m in resp.url for m in COMMENT_API_MARKERS):
            try:
                captured.append(resp.json())
            except Exception:
                pass
    return on_response


def scroll_comments(page, rounds=COMMENT_SCROLL_ROUNDS):
    """在帖子页右侧评论区滚几下, 触发页面自然加载评论。"""
    try:
        page.mouse.move(random.randint(950, 1150), random.randint(450, 650),
                        steps=random.randint(5, 12))
    except Exception:
        pass
    for _ in range(rounds):
        try:
            page.mouse.wheel(0, random.randint(450, 800))
        except Exception:
            pass
        rs(1.0, 2.2)


def extract_comments(captured):
    """从拦截到的评论接口响应里整理评论(含楼中楼, 最多 MAX_COMMENTS 条)。"""
    comments, seen = [], set()

    def add(c, reply=False):
        cid = str(c.get("id") or c.get("comment_id") or len(comments))
        if cid in seen:
            return
        seen.add(cid)
        user = ((c.get("user_info") or {}).get("nickname")
                or (c.get("user") or {}).get("nickname") or "")
        content = (c.get("content") or "").strip()
        if content:
            comments.append(dict(user=user,
                                 content=("└ " if reply else "") + content,
                                 likes=parse_count(c.get("like_count"))))

    for payload in captured:
        data = (payload or {}).get("data") or {}
        for c in data.get("comments") or []:
            add(c)
            for sc in c.get("sub_comments") or []:
                add(sc, reply=True)
    return comments[:MAX_COMMENTS]


def open_note(page, nid, url=None):
    """打开一篇帖子并抽取内容+评论; 返回 None 表示失败。

    url: 搜索结果里带 xsec_token 的完整链接; 缺省用 /explore/<id>。
    """
    url = url or f"https://www.xiaohongshu.com/explore/{nid}"
    captured = []
    listener = _comment_listener(captured)
    page.on("response", listener)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.bring_to_front()
        except Exception:
            pass
        rs(2.5, 5.5)
        try:
            page.wait_for_selector("#detail-title, #detail-desc, .note-text",
                                   timeout=8000, state="attached")
        except Exception:
            pass  # 状态里能挖到就行, 不强求 DOM
        wait_if_verified(page)
        scroll_comments(page)
        html = page.content()
        data = dig_state(html, nid) or dig_dom(page)
    finally:
        try:
            page.remove_listener("response", listener)
        except Exception:
            pass
    if not data or not (data.get("title") or data.get("desc")):
        return None
    data.update(note_id=nid, url=url, scraped_at=int(time.time()),
                comments=extract_comments(captured))
    return data


def scrape(keywords=None, max_per_kw=MAX_NOTES_PER_KEYWORD,
           max_total=MAX_TOTAL_PER_RUN, headless=False):
    keywords = keywords or DEFAULT_KEYWORDS
    posts = load_posts()
    done = {p["note_id"] for p in posts}
    print(f"本地已有 {len(posts)} 篇帖子; 浏览器: {pick_channel()}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel=pick_channel(),
            headless=headless,
            viewport={"width": 1440, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                # 后台/被遮挡窗口防渲染节流: 不加这些, 瀑布流卡片不会加载
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ensure_login(ctx, page)

        total_new = 0
        for kw in keywords:
            if total_new >= max_total:
                print("\n已到单次运行上限, 收工。想采更多请隔几个小时再跑一次。")
                break
            print(f"\n=== 关键词: {kw} ===")
            ids = collect_note_ids(page, kw, limit=max_per_kw * 2)
            print(f"  搜到 {len(ids)} 篇候选帖子")
            kw_new = 0
            for nid, href in ids:
                if nid in done:
                    continue          # 已采过的跳过, 别误伤后面的新帖
                if kw_new >= max_per_kw or total_new >= max_total:
                    break
                note = open_note(page, nid, f"https://www.xiaohongshu.com{href}")
                if note:
                    posts.append(note)
                    done.add(nid)
                    save_posts(posts)          # 增量保存, 中断也不丢
                    total_new += 1
                    kw_new += 1
                    print(f"  [{kw_new}/{max_per_kw}] {note['title'][:38] or '(无标题)'} "
                          f"| 赞 {note['liked']} | 累计 {len(posts)} 篇")
                else:
                    print("  [跳过] 该帖解析失败(可能已删除/是视频合集)")
                rs(*NOTE_SLEEP)
                if random.random() < LONG_REST_CHANCE:
                    rs(*LONG_REST)
            if kw_new == 0:
                print("  本轮没有新帖子")
            rs(*KEYWORD_SLEEP)

        print(f"\n完成: 本次新采 {total_new} 篇, 本地共 {len(posts)} 篇 -> {POSTS_FILE}")
        rs(1, 2)
        ctx.close()


def backfill_comments(headless=False):
    """给评论为空的帖子补采评论(用当初保存的 URL 重新访问一次)。"""
    posts = load_posts()
    todo = [p for p in posts
            if not p.get("comments") and not p.get("comments_checked")]
    if not todo:
        print("所有帖子都已有评论数据, 无需回填")
        return
    print(f"需要补评论的帖子: {len(todo)} 篇")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel=pick_channel(),
            headless=headless,
            viewport={"width": 1440, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        ensure_login(ctx, page)
        for i, note in enumerate(todo, 1):
            fresh = open_note(page, note["note_id"], url=note.get("url"))
            note["comments_checked"] = True   # 试过一次就打标, 不反复重访
            if fresh:
                note["comments"] = fresh.get("comments", [])
                note["liked"] = fresh.get("liked", note.get("liked", 0))
                save_posts(posts)
                print(f"  [{i}/{len(todo)}] {(note.get('title') or '(无标题)')[:32]}"
                      f" -> {len(note['comments'])} 条评论")
            else:
                note["comments"] = []
                save_posts(posts)
                print(f"  [{i}/{len(todo)}] 解析失败, 标记为无评论")
            rs(2.5, 6.0)   # 回填是"第二次访问", 间隔略短但仍保持克制
            if random.random() < LONG_REST_CHANCE:
                rs(*LONG_REST)
        print(f"评论回填完成 -> {POSTS_FILE}")
        rs(1, 2)
        ctx.close()


if __name__ == "__main__":
    scrape()
