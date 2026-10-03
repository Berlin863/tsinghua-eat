"use strict";
/* 推荐逻辑 v3(与 recommender.py 同源):
   栏目化问卷(心情/天气/感受/个人) -> 偏好估计 -> 分栏目推荐
   (正餐/甜品小吃/饮品, 各栏目内加权随机抽样) + 可选大模型研判。
   依赖 data.js: QUESTIONS / SECTIONS / FOOD_DB / ZONES_DESC */

const SET_KEYS = new Set(["budget_level", "zone", "random_boost", "meal_kind"]);
const STAPLE_IDS = ["meal_kind", "budget"];
const BIG_CANTEEN_SEATS = 1900;
const SECTION_TITLES = { "正餐": "🍚 正餐", "甜品小吃": "🍰 甜品·小吃", "饮品": "🥤 饮品" };

const KEY_LABELS = {
  spicy: "辣", numbing: "麻", sour: "酸", sweet: "甜", savory: "咸鲜",
  rich: "重口", light: "清淡", oily: "油香", fried: "酥脆", soup: "喝汤",
  hot: "热乎", cold: "清凉", crunch: "脆口", soft: "软糯",
  rice: "米饭", noodle: "面食", powder: "粉类", dimsum: "面点", bing: "饼类",
  porridge: "粥品", bread: "面包", salad: "轻食", setmeal: "套餐盖饭",
  mallow: "麻辣烫香锅", teppan: "铁板石锅", hotpot: "小火锅", bbq: "烧烤烤肉",
  sichuan: "川湘", cantonese: "粤式", northwest: "西北", northeast: "东北",
  yunnan: "云贵", xinjiang: "新疆", halal: "清真", japanese: "日式",
  korean: "韩式", western: "西式", vegetarian: "素食", home: "家常",
  quick: "快手", breakfast: "早餐", night_snack: "夜宵", solo: "一人食",
  group: "聚餐", comfort: "碳水安慰", healthy: "健康低脂", protein: "高蛋白",
  veggies: "蔬菜", indulgent: "高热量快乐", meat: "肉食", egg: "加蛋",
  splurge: "愿意奢侈", value_first: "性价比", big_appetite: "大分量",
  novelty: "尝鲜", quiet: "图清净", queue_ok: "不怕排队", near_only: "就近优先",
  dessert: "甜品", drink: "配饮品",
};
const PRICE_DESC = { 1: "约6-12元", 2: "约10-18元", 3: "约15-25元", 4: "约20元+" };

/* ---------------- 抽题与偏好 ---------------- */

function gauss() {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function sampleQuestions(n = 9) {
  const bySec = {};
  for (const q of QUESTIONS) (bySec[q.sec] = bySec[q.sec] || []).push(q);
  const staples = bySec.personal.filter(q => STAPLE_IDS.includes(q.id));
  const personalPool = bySec.personal.filter(q => !STAPLE_IDS.includes(q.id));

  const scale = Math.max(0.4, n / 9);
  const quota = {
    mood: Math.max(1, Math.round(2 * scale)),
    weather: Math.max(1, Math.round(1 * scale)),
    craving: Math.max(2, Math.round(3 * scale)),
    personal: Math.max(0, Math.round(1 * scale)),
  };
  let picked = [];
  for (const sec of ["mood", "weather", "craving"])
    picked.push(...shuffle([...bySec[sec]]).slice(0, quota[sec]));
  picked.push(...shuffle([...personalPool]).slice(0, quota.personal));

  let total = picked.length + staples.length;
  const rest = shuffle(QUESTIONS.filter(q => !picked.includes(q) && !staples.includes(q)));
  while (total < n && rest.length) { picked.push(rest.pop()); total++; }
  while (total > n && picked.length > quota.craving) {
    picked.splice(Math.floor(Math.random() * picked.length), 1); total--;
  }
  const order = { mood: 0, weather: 1, craving: 2, personal: 3 };
  picked.sort((a, b) => order[a.sec] - order[b.sec]);
  return [...picked, ...staples];
}

function accumulate(answers) {
  const sums = {}, counts = {}, pset = {}, hard = {};
  for (const { q, choice } of answers) {
    if (choice < 0) continue;
    const opt = q.options[choice];
    if (opt.length > 2 && opt[2] === "require_halal") hard.halal = true;
    for (const [k, v] of Object.entries(opt[1] || {})) {
      if (SET_KEYS.has(k)) pset[k] = v;
      else { sums[k] = (sums[k] || 0) + v; counts[k] = (counts[k] || 0) + 1; }
    }
  }
  const prefs = {};
  for (const k in sums)
    prefs[k] = Math.max(-2, Math.min(2, sums[k] / counts[k]));
  if (pset.budget_level === undefined) pset.budget_level = 3;
  if (pset.random_boost === undefined) pset.random_boost = 0;
  return { prefs, pset, hard };
}

/* ---------------- 候选与打分 ---------------- */

function buildCandidates(db) {
  const canteens = db.canteens;
  const cPop = {};
  for (const [c, v] of Object.entries(canteens))
    cPop[c] = Math.log10(1 + (v.xhs_likes || 0)) + 0.8 * (v.xhs_mentions || 0);
  const avgCPop = Object.values(cPop).reduce((a, b) => a + b, 0) /
    Math.max(1, Object.keys(cPop).length);

  const out = [];
  for (const d of db.dishes) {
    const cells = Object.assign({}, d.canteens);
    if (d.seed_canteen && !cells[d.seed_canteen])
      cells[d.seed_canteen] = { mentions: 0, likes: 0, seed: true };
    const common = {
      dish: d.name, attrs: d.attrs, price: d.price, kind: d.kind || "正餐",
      sourceNote: d.source_note || "",
      xhsMentions: d.xhs_mentions || 0, recency: d.recency || 0,
      posts: d.xhs_posts || [],
    };
    if (Object.keys(cells).length) {
      for (const [cname, cell] of Object.entries(cells)) {
        const info = canteens[cname];
        if (!info) continue;
        out.push(Object.assign({}, common, {
          canteen: cname, cinfo: info,
          cpop: cPop[cname] !== undefined ? cPop[cname] : avgCPop,
          dpop: cell.mentions || 0, dlikes: cell.likes || 0,
          seedCell: !!cell.seed,
        }));
      }
    } else {
      out.push(Object.assign({}, common, {
        canteen: null, cinfo: null, cpop: avgCPop,
        dpop: 0, dlikes: 0, seedCell: false,
      }));
    }
  }
  return out;
}

function tasteMatch(attrs, prefs) {
  let raw = 0;
  const contrib = [];
  for (const [k, v] of Object.entries(attrs)) {
    const pv = prefs[k];
    if (pv) { raw += pv * v; contrib.push([k, pv * v]); }
  }
  return [0.5 + 0.5 * Math.tanh(raw / 5), contrib];
}

function popularityRaw(c) {
  const m = c.dpop;
  const mlog = m > 0 ? Math.log1p(m) : (m < 0 ? -Math.log1p(-m) : 0);
  return 1 + Math.log10(1 + c.dlikes) + 0.8 * mlog + 0.7 * c.recency;
}

function sceneMult(c, prefs, pset) {
  const attrs = c.attrs, info = c.cinfo;
  let mult = 1;
  const kind = c.kind || "正餐";

  const mk = pset.meal_kind || "混合";
  if (mk === "正餐") {
    if (kind === "小吃" || kind === "甜品") mult *= 0.35;
    else if (kind === "配菜") mult *= 0.55;
  } else if (mk === "小吃") {
    if (kind === "正餐") mult *= 0.55;
    else if (kind === "配菜") mult *= 0.70;
  }

  if (kind === "甜品" && prefs.dessert) mult *= 1 + 0.25 * prefs.dessert;
  if (kind === "饮品" && prefs.drink) mult *= 1 + 0.25 * prefs.drink;

  if ((prefs.breakfast || 0) > 0.4) mult *= attrs.breakfast ? 1.35 : 0.45;
  if ((prefs.night_snack || 0) > 0.4) mult *= attrs.night_snack ? 1.30 : 0.85;

  const q = prefs.quick || 0;
  if (q > 0.3) {
    let slowness = Math.max(attrs.hotpot || 0, 0.6 * (attrs.teppan || 0),
      0.6 * (attrs.mallow || 0));
    if (info && (info.speed || 3) <= 2) slowness = Math.max(slowness, 0.5);
    mult *= 1 - 0.3 * Math.min(1, q) * Math.min(1, slowness);
  }
  if ((prefs.group || 0) > 0.4 && (attrs.hotpot || attrs.bbq)) mult *= 1.10;
  if ((prefs.solo || 0) > 0.4 && attrs.hotpot) mult *= 0.92;

  const b = pset.budget_level, p = c.price;
  if (p > b) mult *= Math.max(0.55, 1 - 0.18 * (p - b));
  else if (b < 3 && p <= b) mult *= 1.05;

  if (pset.zone && info) {
    const near = prefs.near_only || 0;
    mult *= info.zone === pset.zone ? 1.08 : 1 - (near > 0.5 ? 0.12 : 0.05);
  }
  if ((prefs.quiet || 0) > 0.5 && info && (info.seats || 0) >= BIG_CANTEEN_SEATS)
    mult *= 0.93;
  if ((prefs.halal || 0) > 0.5 && (attrs.halal || (info && info.halal)))
    mult *= 1.12;

  const n = prefs.novelty || 0;
  const known = Math.min(1, c.xhsMentions / 6);
  if (n > 0) mult *= 1 + 0.12 * n * (1 - known);
  else if (n < 0) mult *= 1 + 0.10 * n * (1 - known);

  return mult;
}

function scoreAll(db, prefs, pset, hard) {
  let cands = buildCandidates(db);
  if (hard.halal)
    cands = cands.filter(c => c.attrs.halal || (c.cinfo && c.cinfo.halal));
  const pops = cands.map(popularityRaw);
  const lo = Math.min(...pops), hi = Math.max(...pops);
  const sigma = 0.08 + 0.12 * (pset.random_boost || 0);

  return cands.map((c, i) => {
    const pop = 0.15 + 0.85 * (hi > lo ? (pops[i] - lo) / (hi - lo) : 0.5);
    const [match, contrib] = tasteMatch(c.attrs, prefs);
    const mult = sceneMult(c, prefs, pset);
    return { score: 100 * (0.58 * match + 0.42 * pop) * mult * (1 + gauss() * sigma), c, contrib };
  }).sort((a, b) => b.score - a.score);
}

function pick(scored, kinds, n, temp = 3.0, sideCap = 1, canteenCap = 2) {
  if (n <= 0) return [];
  const pool = scored.filter(s => kinds.has(s.c.kind));
  const picked = [], seenDish = new Set();
  let sideCnt = 0;
  const canteenCnt = {};
  while (picked.length < n && pool.length) {
    const ws = pool.map(s => Math.max(1e-6, s.score) ** temp);
    let sum = ws.reduce((a, b) => a + b, 0);
    let r = Math.random() * sum;
    let idx = pool.length - 1;
    for (let i = 0; i < pool.length; i++) {
      r -= ws[i];
      if (r <= 0) { idx = i; break; }
    }
    const s = pool.splice(idx, 1)[0];
    const c = s.c;
    if (seenDish.has(c.dish)) continue;
    if (c.kind === "配菜" && sideCnt >= sideCap) continue;
    if (c.canteen && (canteenCnt[c.canteen] || 0) >= canteenCap) continue;
    picked.push(s);
    seenDish.add(c.dish);
    if (c.kind === "配菜") sideCnt++;
    if (c.canteen) canteenCnt[c.canteen] = (canteenCnt[c.canteen] || 0) + 1;
  }
  return picked;
}

function rankSections(db, prefs, pset, hard, temp = 3.0) {
  const scored = scoreAll(db, prefs, pset, hard);
  const mk = pset.meal_kind || "混合";
  const counts = {
    "正餐": { "正餐": 4, "甜品小吃": 1, "饮品": 1 },
    "小吃": { "正餐": 1, "甜品小吃": 3, "饮品": 2 },
    "混合": { "正餐": 3, "甜品小吃": 2, "饮品": 2 },
  }[mk];
  if ((prefs.drink || 0) < -0.5) counts["饮品"] = Math.max(0, counts["饮品"] - 1);
  if ((prefs.dessert || 0) < -0.5) counts["甜品小吃"] = Math.max(0, counts["甜品小吃"] - 1);

  return {
    "正餐": pick(scored, new Set(["正餐", "配菜"]), counts["正餐"], temp),
    "甜品小吃": pick(scored, new Set(["小吃", "甜品"]), counts["甜品小吃"], temp),
    "饮品": pick(scored, new Set(["饮品"]), counts["饮品"], temp),
  };
}

/* ---------------- 大模型研判(可选, key 存本地) ---------------- */

function llmAvailable() { return !!localStorage.getItem("eat_llm_key"); }

async function callLLM(prompt, maxTokens = 500) {
  const key = localStorage.getItem("eat_llm_key");
  const model = localStorage.getItem("eat_llm_model") || "claude-opus-4-8";
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model, max_tokens: maxTokens,
      messages: [{ role: "user", content: prompt }],
    }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  const data = await res.json();
  return (data.content || []).filter(b => b.type === "text")
    .map(b => b.text).join("").trim();
}

function summaryText(prefs, pset, hard) {
  const parts = [];
  const keys = Object.keys(prefs)
    .sort((a, b) => Math.abs(prefs[b]) - Math.abs(prefs[a])).slice(0, 8);
  for (const k of keys) {
    if (Math.abs(prefs[k]) < 0.3) continue;
    parts.push(`${prefs[k] > 0 ? "想" : "不想要"}${KEY_LABELS[k] || k}`);
  }
  if (pset.zone) parts.push(`人在${pset.zone}`);
  parts.push(`预算档${pset.budget_level}/5`);
  if (pset.meal_kind && pset.meal_kind !== "混合") parts.push(`想吃${pset.meal_kind}`);
  if (hard.halal) parts.push("需要清真");
  return parts.join("; ") || "口味不明, 全看随机";
}

function candidatesText(sections) {
  const lines = [];
  for (const [sec, items] of Object.entries(sections)) {
    if (!items.length) continue;
    lines.push(`[${sec}] ` + items.slice(0, 4)
      .map(s => `${s.c.canteen || "任意食堂"}的${s.c.dish}(${s.score.toFixed(0)}分)`).join("、"));
  }
  return lines.join("\n") || "无候选";
}

async function followupQuestion(prefs, pset, hard) {
  const prompt = `你是"今天吃什么"的干饭顾问. 用户刚答完一轮口味问卷, 画像是: ${summaryText(prefs, pset, hard)}\n\n` +
    `请基于画像追问一个问卷没覆盖到的、能帮 TA 决定今天吃什么的个性化问题。\n` +
    `只输出 JSON, 格式: {"q": "问题(口语化,15字内)", "options": ["选项A", "选项B", "选项C"]}\n不要输出其他内容。`;
  const text = await callLLM(prompt, 300);
  const data = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
  if (data.q && Array.isArray(data.options) && data.options.length >= 2) return data;
  return null;
}

async function llmInsight(prefs, pset, hard, sections, extra = "") {
  const prompt = `你是"今天吃什么"的干饭顾问, 主持人是清华大学的学生.\n` +
    `根据 TA 今天的画像和算法候选, 给出一段研判。\n\n画像: ${summaryText(prefs, pset, hard)}\n` +
    (extra ? `${extra}\n` : "") +
    `候选(栏目+算法分数):\n${candidatesText(sections)}\n\n要求:\n` +
    `1. 先用一句话点出 TA 今天的状态(结合画像, 语气像懂吃的朋友, 活泼接地气)\n` +
    `2. 从候选里选出你最推的一个, 说清为什么(结合画像, 别泛泛而谈)\n` +
    `3. 顺手提一个备选或提醒(比如下雨天配碗汤)\n` +
    `4. 总共 3 句话以内, 不要用列表, 不要重复候选分数`;
  return callLLM(prompt, 400);
}

/* ---------------- UI ---------------- */

function esc(s) {
  return String(s).replace(/[&<>"']/g,
    m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

function profileChips(prefs, pset, hard) {
  const chips = [];
  if (hard.halal) chips.push(["清真", true]);
  if (pset.zone) chips.push(["位置·" + pset.zone, false]);
  if (pset.meal_kind && pset.meal_kind !== "混合")
    chips.push([pset.meal_kind === "小吃" ? "解馋模式" : "正餐模式", true]);
  chips.push(["预算档 " + pset.budget_level, false]);
  const keys = Object.keys(prefs)
    .sort((a, b) => Math.abs(prefs[b]) - Math.abs(prefs[a])).slice(0, 8);
  for (const k of keys) {
    if (Math.abs(prefs[k]) < 0.3) continue;
    chips.push([`${KEY_LABELS[k] || k} ${prefs[k] >= 0 ? "+" : ""}${prefs[k].toFixed(1)}`,
      Math.abs(prefs[k]) >= 1.2]);
  }
  return chips;
}

function resultCardHtml(rankNo, { score, c, contrib }) {
  const cname = c.canteen || "任意食堂(就近找窗口)";
  const hits = contrib.filter(([, v]) => v > 0.25).sort((a, b) => b[1] - a[1])
    .slice(0, 3).map(([k]) => KEY_LABELS[k] || k);
  const lines = [];
  if (hits.length) lines.push(`命中偏好: <b>${hits.join("、")}</b>`);
  if (c.dpop || c.dlikes)
    lines.push(`小红书热度: <b>${c.dpop.toFixed(c.dpop % 1 ? 1 : 0)} 次提及</b> · 约 ${Math.round(c.dlikes)} 赞`);
  else if (c.sourceNote) lines.push(`来源: ${esc(c.sourceNote)}`);
  lines.push(`价位 ${PRICE_DESC[c.price] || ""}` +
    (c.cinfo ? ` | ${esc(c.cinfo.zone)}` : ""));
  if (c.posts.length && (FOOD_DB.posts_index || []).length) {
    const idx = Object.fromEntries(FOOD_DB.posts_index.map(p => [p.note_id, p]));
    const titles = c.posts.slice(0, 2)
      .map(id => idx[id] && idx[id].title).filter(Boolean)
      .map(t => `《${esc(t.slice(0, 22))}》`);
    if (titles.length) lines.push("帖子: " + titles.join(" "));
  }
  const kindTag = (c.kind && c.kind !== "正餐") ? `〔${c.kind}〕` : "";
  return `<div class="card result-card">
    <div class="result-head">
      <span class="rank-no">${rankNo}</span>
      <span class="canteen">【${esc(cname)}】</span>
      <span class="dish">${esc(c.dish)}${kindTag}</span>
      <span class="score">综合 ${score.toFixed(1)}</span>
    </div>
    <ul class="reasons">${lines.map(l => `<li>- ${l}</li>`).join("")}</ul>
  </div>`;
}

function initUI() {
  const $ = id => document.getElementById(id);
  const screens = ["start", "quiz", "followup", "result"].map(s => $("screen-" + s));
  const show = name => screens.forEach(el => el.hidden = el.id !== "screen-" + name);

  $("db-desc").textContent =
    `小红书 ${FOOD_DB.n_posts} 帖语料` +
    (FOOD_DB.n_manual ? ` + 手动补充 ${FOOD_DB.n_manual} 条` : "") +
    ` + ${QUESTIONS.length} 题栏目问卷 → 分栏目推荐`;

  // 设置(key 只存 localStorage, 请求直接从你的浏览器发给 Anthropic)
  $("llm-key").value = localStorage.getItem("eat_llm_key") || "";
  $("llm-model").value = localStorage.getItem("eat_llm_model") || "claude-opus-4-8";
  $("llm-key").oninput = e => localStorage.setItem("eat_llm_key", e.target.value.trim());
  $("llm-model").onchange = e => localStorage.setItem("eat_llm_model", e.target.value);

  let session = null;

  function startQuiz() {
    const n = +$("n-questions").value;
    session = { questions: sampleQuestions(n), answers: [], i: 0, temp: 3.0, llmExtra: "" };
    show("quiz");
    renderQuestion();
  }

  function renderQuestion() {
    const { questions, answers, i } = session;
    if (i >= questions.length) return afterQuiz();
    const q = questions[i];
    const meta = SECTIONS[q.sec] || { emoji: "👉", title: q.sec };
    $("q-section").textContent = `${meta.emoji} ${meta.title}`;
    $("progress-bar").style.width = `${(i / questions.length) * 100}%`;
    $("q-meta").textContent = `[${i + 1}/${questions.length}]`;
    $("q-text").textContent = q.q;
    $("q-options").innerHTML = q.options
      .map((o, j) => `<button data-j="${j}">${esc(o[0])}</button>`).join("");
    for (const btn of $("q-options").children)
      btn.onclick = () => choose(+btn.dataset.j);
  }

  function choose(j) {
    session.answers.push({ q: session.questions[session.i], choice: j });
    session.i++;
    renderQuestion();
  }
  $("btn-skip").onclick = () => choose(-1);

  async function afterQuiz() {
    $("progress-bar").style.width = "100%";
    const acc = accumulate(session.answers);
    Object.assign(session, acc);
    // 有 key 时让 AI 追问一句(失败静默跳过)
    if (llmAvailable()) {
      try {
        const fq = await followupQuestion(session.prefs, session.pset, session.hard);
        if (fq) return renderFollowup(fq);
      } catch (e) { /* 网络/解析失败 -> 直接出结果 */ }
    }
    renderResults();
  }

  function renderFollowup(fq) {
    show("followup");
    $("followup-q").textContent = "✨ " + fq.q;
    $("followup-options").innerHTML = fq.options
      .map((o, j) => `<button data-j="${j}">${esc(o)}</button>`).join("");
    for (const btn of $("followup-options").children)
      btn.onclick = () => {
        session.llmExtra = `个性化追问[${fq.q}]回答: ${fq.options[+btn.dataset.j]}。`;
        renderResults();
      };
    $("btn-followup-skip").onclick = () => renderResults();
  }

  function renderResults() {
    show("result");
    $("result-desc").textContent =
      `(语料: 小红书 ${FOOD_DB.n_posts} 帖 + 手动 ${FOOD_DB.n_manual || 0} 条, ` +
      `抖动 σ=${(0.08 + 0.12 * (session.pset.random_boost || 0)).toFixed(2)})`;
    $("profile").innerHTML = profileChips(session.prefs, session.pset, session.hard)
      .map(([t, hot]) => `<span class="chip${hot ? " hot" : ""}">${esc(t)}</span>`).join("");

    const sections = rankSections(FOOD_DB, session.prefs, session.pset, session.hard,
      session.temp);
    let html = "";
    const hints = {
      "饮品": "饮品数据还很少 —— 欢迎补充常喝的窗口(奶茶/酸梅汤/柠檬水...)",
      "甜品小吃": "甜品小吃不多, 欢迎补充语料",
    };
    for (const [sec, items] of Object.entries(sections)) {
      html += `<h2 class="section-title">${SECTION_TITLES[sec]}</h2>`;
      if (!items.length) {
        html += `<p class="muted">${hints[sec] || "暂无推荐"}</p>`;
        continue;
      }
      html += items.map((s, i) => resultCardHtml(i + 1, s)).join("");
    }
    $("sections").innerHTML = html;
    $("insight").hidden = true;
    $("insight-text").textContent = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function runInsight() {
    const btn = $("btn-insight");
    if (!llmAvailable()) {
      $("insight").hidden = false;
      $("insight-text").innerHTML =
        `先在首页 <b>⚙️ AI 研判设置</b> 里填入你自己的 Anthropic API Key(只存在本浏览器)。` +
        `没有 key 也能正常用推荐, 只是少一段点评。`;
      return;
    }
    btn.disabled = true; btn.textContent = "✨ AI 研判中…";
    try {
      const sections = rankSections(FOOD_DB, session.prefs, session.pset,
        session.hard, session.temp);
      const text = await llmInsight(session.prefs, session.pset, session.hard,
        sections, session.llmExtra);
      $("insight").hidden = false;
      $("insight-text").textContent = text || "(生成失败, 再试一次)";
    } catch (e) {
      $("insight").hidden = false;
      $("insight-text").textContent = `研判失败: ${e.message} (检查 key/网络/余额)`;
    } finally {
      btn.disabled = false; btn.textContent = "✨ AI 研判";
    }
  }

  $("btn-start").onclick = startQuiz;
  $("btn-reroll").onclick = () => {
    session.temp = Math.max(1.0, (session.temp ?? 3.0) * 0.65);
    renderResults();
  };
  $("btn-reask").onclick = startQuiz;
  $("btn-insight").onclick = runInsight;
}

if (typeof document !== "undefined"
  && document.getElementById("screen-start")) {
  initUI();
}
