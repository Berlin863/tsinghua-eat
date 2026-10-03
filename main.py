# -*- coding: utf-8 -*-
"""
今天吃什么 —— 小红书清华美食帖驱动的食堂决策器

用法:
  python main.py scrape   [--keywords "清华食堂,清华美食"] [--max-per-kw 15] [--headless]
                          # 打开浏览器采集小红书帖子(首次需扫码登录)
  python main.py build    # 把帖子解析成 data/food_db.json
  python main.py          # 直接开始问问卷并出 Top5 推荐(默认命令)
  python main.py recommend [--questions 12] [--top 5] [--auto]
  python main.py update   # build + recommend 一步到位
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_utf8_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main():
    ensure_utf8_console()
    parser = argparse.ArgumentParser(
        description="今天吃什么: 小红书清华美食帖 + 随机问卷 -> 食堂/菜品 Top5")
    sub = parser.add_subparsers(dest="cmd")

    p_scrape = sub.add_parser("scrape", help="用 Playwright 采集小红书帖子")
    p_scrape.add_argument("--keywords", type=str, default=None,
                          help="逗号分隔的搜索关键词")
    p_scrape.add_argument("--max-per-kw", type=int, default=15)
    p_scrape.add_argument("--max-total", type=int, default=60)
    p_scrape.add_argument("--backfill-comments", action="store_true",
                          help="不采新帖, 只给缺评论的旧帖补采评论")
    p_scrape.add_argument("--headless", action="store_true",
                          help="无头模式(不建议, 登录和验证码都不方便)")

    sub.add_parser("build", help="解析帖子生成 food_db.json")

    p_rec = sub.add_parser("recommend", help="问问卷并推荐(分栏目)")
    p_rec.add_argument("--questions", type=int, default=9, help="抽题数量")
    p_rec.add_argument("--llm", action="store_true",
                       help="启用大模型研判(需 ANTHROPIC_API_KEY + pip install anthropic)")
    p_rec.add_argument("--auto", action="store_true",
                       help="随机自动作答(测试/手滑模式)")

    sub.add_parser("update", help="build 之后立刻 recommend")

    p_exp = sub.add_parser("export", help="导出静态网页数据 docs/data.js")
    p_exp.add_argument("--public", action="store_true",
                       help="公开版: 去掉帖子标题/链接/ID(发布公网前用)")

    args = parser.parse_args()
    cmd = args.cmd or "recommend"

    if cmd == "scrape":
        import xhs_scraper
        if getattr(args, "backfill_comments", False):
            xhs_scraper.backfill_comments(headless=args.headless)
        else:
            kws = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
            xhs_scraper.scrape(keywords=kws, max_per_kw=args.max_per_kw,
                               max_total=args.max_total, headless=args.headless)
    elif cmd == "build":
        import food_parser
        food_parser.build()
    elif cmd == "export":
        import export_web
        export_web.export(public=getattr(args, "public", False))
    elif cmd in ("recommend", "update"):
        if cmd == "update":
            import food_parser
            food_parser.build(verbose=False)
            print("[OK] food_db.json 已更新")
        import recommender
        recommender.run(n_questions=getattr(args, "questions", 9) or 9,
                        use_llm=getattr(args, "llm", False),
                        auto=getattr(args, "auto", False))


if __name__ == "__main__":
    main()
