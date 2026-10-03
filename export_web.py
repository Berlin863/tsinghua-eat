# -*- coding: utf-8 -*-
"""
把问题库 + food_db 导出成 docs/data.js, 供纯静态网页(GitHub Pages)使用。
目录用 docs/ 是为了 GitHub Pages "Deploy from branch" 能直接选 /(docs) 根路径。

用法:
  python main.py export            # 完整版(本地用, 推荐里能引用原帖标题)
  python main.py export --public   # 公开版: 去掉帖子标题/链接/ID, 只留聚合数字
                                  # 发布到公网仓库前用这个, 避免搬运小红书内容
"""

import json
from pathlib import Path

import seed_data
from question_bank import QUESTIONS, SECTIONS

ROOT = Path(__file__).resolve().parent
FOOD_DB_FILE = ROOT / "data" / "food_db.json"
WEB_DIR = ROOT / "docs"
DATA_JS = WEB_DIR / "data.js"


def export(public=False):
    if not FOOD_DB_FILE.exists():
        raise SystemExit("缺少 data/food_db.json, 先运行: python main.py build")
    db = json.loads(FOOD_DB_FILE.read_text(encoding="utf-8"))

    questions = [
        {"id": q["id"], "sec": q["sec"], "q": q["q"],
         "options": [[o[0], o[1]] + ([o[2]] if len(o) > 2 else [])
                     for o in q["options"]]}
        for q in QUESTIONS
    ]

    if public:
        db = json.loads(json.dumps(db))     # deep copy
        db["posts_index"] = []
        db["public_mode"] = True
        for c in db["canteens"].values():
            c.pop("xhs_posts", None)
        for d in db["dishes"]:
            d.pop("xhs_posts", None)

    WEB_DIR.mkdir(exist_ok=True)
    payload = ("// 自动生成: python main.py export"
               + (" --public" if public else "")
               + f"  |  {len(questions)} 题, {db['n_posts']} 帖语料\n"
               + "const QUESTIONS = " + json.dumps(questions, ensure_ascii=False,
                                                    separators=(",", ":")) + ";\n"
               + "const SECTIONS = " + json.dumps(SECTIONS, ensure_ascii=False) + ";\n"
               + "const FOOD_DB = " + json.dumps(db, ensure_ascii=False,
                                                 separators=(",", ":")) + ";\n"
               + "const ZONES_DESC = " + json.dumps(seed_data.ZONES_DESC,
                                                    ensure_ascii=False) + ";\n")
    DATA_JS.write_text(payload, encoding="utf-8")
    mode = "公开版(已去除帖子标题/链接/ID)" if public else "完整版"
    print(f"[OK] {DATA_JS}  ({mode})")
    print("     本地双击 docs/index.html 即可用; 提交前如要公开请用 --public 重导出")


if __name__ == "__main__":
    export()
