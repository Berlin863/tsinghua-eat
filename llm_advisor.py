# -*- coding: utf-8 -*-
"""
大模型研判(可选功能): 把用户画像和候选推荐交给 Claude, 生成一段
"懂吃朋友"口吻的点评 + 个性化追问。

- 凭证: 读环境变量 ANTHROPIC_API_KEY (没有就静默降级, 不影响主流程)
- 依赖: pip install anthropic (可选依赖, 没装也静默降级)
- 模型: 默认 claude-opus-4-8, 可用 EAT_MODEL 环境变量换(如 claude-haiku-4-5)
- 网页版的等价实现在 docs/app.js(浏览器直连, key 存 localStorage)
"""

import json
import os

DEFAULT_MODEL = "claude-opus-4-8"


def get_client():
    """有 key 且装了 SDK 才返回 client, 否则 None(功能静默关闭)。"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()


def _model():
    return os.environ.get("EAT_MODEL", DEFAULT_MODEL)


def _extract_text(resp):
    for block in resp.content:
        if getattr(block, "type", "") == "text":
            return block.text.strip()
    return ""


def _summary_text(prefs, pset, hard):
    """把偏好向量压成给模型看的自然语言画像。"""
    from recommender import KEY_LABELS
    parts = []
    keys = sorted(prefs, key=lambda k: abs(prefs[k]), reverse=True)[:8]
    for k in keys:
        if abs(prefs[k]) < 0.3:
            continue
        label = KEY_LABELS.get(k, k)
        parts.append(f"{'想' if prefs[k] > 0 else '不想要'}{label}"
                     f"({prefs[k]:+.1f})" if abs(prefs[k]) >= 0.3 else "")
    if pset.get("zone"):
        parts.append(f"人在{pset['zone']}")
    parts.append(f"预算档{pset['budget_level']}/5")
    if pset.get("meal_kind") and pset["meal_kind"] != "混合":
        parts.append(f"今天想吃{pset['meal_kind']}")
    if hard.get("halal"):
        parts.append("需要清真")
    return "; ".join(p for p in parts if p) or "口味不明, 全看随机"


def _candidates_text(sections):
    lines = []
    for sec, items in sections.items():
        if not items:
            continue
        names = "、".join(
            f"{it[1]['canteen'] or '任意食堂'}的{it[1]['dish']}"
            f"({it[0]:.0f}分)" for it in items[:4])
        lines.append(f"[{sec}] {names}")
    return "\n".join(lines) or "无候选"


INSIGHT_PROMPT = """你是"今天吃什么"的干饭顾问, 主持人是清华大学的学生.
根据 TA 今天的画像和算法候选, 给出一段研判。

画像: {summary}
{extra}候选(栏目+算法分数):
{candidates}

要求:
1. 先用一句话点出 TA 今天的状态(结合画像, 语气像懂吃的朋友, 活泼接地气)
2. 从候选里选出你最推的一个, 说清为什么(结合画像, 别泛泛而谈)
3. 顺手提一个备选或提醒(比如下雨天配碗汤)
4. 总共 3 句话以内, 不要用列表, 不要重复候选分数"""

FOLLOWUP_PROMPT = """你是"今天吃什么"的干饭顾问. 用户刚答完一轮口味问卷, 画像是: {summary}

请基于画像追问一个问卷没覆盖到的、能帮 TA 决定今天吃什么的个性化问题。
只输出 JSON, 格式: {{"q": "问题(口语化,15字内)", "options": ["选项A", "选项B", "选项C"]}}
不要输出其他内容。"""


def insight(prefs, pset, hard, sections, extra=""):
    """生成研判文本; 失败/无 key 返回 None。"""
    client = get_client()
    if not client:
        return None
    try:
        resp = client.messages.create(
            model=_model(), max_tokens=400,
            messages=[{"role": "user", "content": INSIGHT_PROMPT.format(
                summary=_summary_text(prefs, pset, hard),
                extra=extra, candidates=_candidates_text(sections))}],
        )
        text = _extract_text(resp)
        return text or None
    except Exception as e:
        return f"(研判生成失败: {type(e).__name__}: {str(e)[:80]})"


def followup_question(prefs, pset, hard):
    """让模型生成一个个性化追问; 返回 {q, options} 或 None。"""
    client = get_client()
    if not client:
        return None
    try:
        resp = client.messages.create(
            model=_model(), max_tokens=300,
            messages=[{"role": "user", "content": FOLLOWUP_PROMPT.format(
                summary=_summary_text(prefs, pset, hard))}],
        )
        text = _extract_text(resp)
        m = text[text.find("{"):text.rfind("}") + 1]
        data = json.loads(m)
        if data.get("q") and isinstance(data.get("options"), list) \
                and 2 <= len(data["options"]) <= 4:
            return data
    except Exception:
        pass
    return None


if __name__ == "__main__":
    print("设置 ANTHROPIC_API_KEY 后由 recommender 调用, 本模块不单独运行")
