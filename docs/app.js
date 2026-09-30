"use strict";
/* 推荐逻辑(与 Python 版 recommender.py 同源):
   抽题 -> 估计偏好 -> (菜品×食堂)打分(口味匹配+热度+场景修正) -> 随机抖动 -> Top5
   依赖 data.js 提供的全局: QUESTIONS / FOOD_DB / ZONES_DESC */

const SET_KEYS = new Set(["budget_level", "zone", "random_boost"]);
const BIG_CANTEEN_SEATS = 1900;
const DIMS = ["口味", "主食", "菜系", "场景", "预算", "健康", "随心", "位置"];

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
};
const PRICE_DESC = { 1: "约6-12元", 2: "约10-18元", 3: "约15-25元", 4: "约20元+" };

/* ---------------- 工具 ---------------- */

function gauss() {  // Box-Muller
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function sampleQuestions(n) {
  const byDim = {};
  for (const q of QUESTIONS) (byDim[q.dim] = byDim[q.dim] || []).push(q);
  const picked = DIMS.map(d =>
    byDim[d][Math.floor(Math.random() * byDim[d].length)]);
  const rest = QUESTIONS.filter(q => !picked.includes(q));
  for (let i = rest.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [rest[i], rest[j]] = [rest[j], rest[i]];
  }
  while (picked.length < n && rest.length) picked.push(rest.pop());
  return picked.slice(0, n);
}

function accumulate(answers) {
  // answers: [{q, choice}]  choice 为 -1 表示跳过
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
    if (Object.keys(cells).length) {
      for (const [cname, cell] of Object.entries(cells)) {
        const info = canteens[cname];
        if (!info) continue;
        out.push({
          dish: d.name, attrs: d.attrs, price: d.price, canteen: cname, cinfo: info,
          cpop: cPop[cname] !== undefined ? cPop[cname] : avgCPop,
          dpop: cell.mentions || 0, dlikes: cell.likes || 0,
          seedCell: !!cell.seed, sourceNote: d.source_note || "",
          xhsMentions: d.xhs_mentions || 0, recency: d.recency || 0,
          posts: d.xhs_posts || [],
        });
      }
    } else {
      out.push({
        dish: d.name, attrs: d.attrs, price: d.price, canteen: null, cinfo: null,
        cpop: avgCPop, dpop: 0, dlikes: 0, seedCell: false, sourceNote: "",
        xhsMentions: 0, recency: d.recency || 0, posts: [],
      });
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
  return [0.5 + 0.5 * Math.tanh(raw / 6), contrib];
}

function popularityRaw(c) {
  return 1 + Math.log10(1 + c.dlikes) + 0.9 * c.dpop + 0.7 * c.recency;
}

function sceneMult(c, prefs, pset) {
  const attrs = c.attrs, info = c.cinfo;
  let mult = 1;

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
    if (info.zone === pset.zone) mult *= 1.08;
    else mult *= 1 - (near > 0.5 ? 0.12 : 0.05);
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

function rank(db, prefs, pset, hard, topN = 5) {
  let cands = buildCandidates(db);
  if (hard.halal)
    cands = cands.filter(c =>
      c.attrs.halal || (c.cinfo && c.cinfo.halal));

  const pops = cands.map(popularityRaw);
  const lo = Math.min(...pops), hi = Math.max(...pops);
  const sigma = 0.05 + 0.10 * pset.random_boost;

  const scored = cands.map((c, i) => {
    const pop = 0.15 + 0.85 * (hi > lo ? (pops[i] - lo) / (hi - lo) : 0.5);
    const [match, contrib] = tasteMatch(c.attrs, prefs);
    const mult = sceneMult(c, prefs, pset);
    const score = 100 * (0.55 * match + 0.45 * pop) * mult * (1 + gauss() * sigma);
    return { score, c, contrib };
  }).sort((a, b) => b.score - a.score);

  const picked = [], seenDish = new Set(), canteenCnt = {};
  for (const s of scored) {
    if (seenDish.has(s.c.dish)) continue;
    if (s.c.canteen && (canteenCnt[s.c.canteen] || 0) >= 2) continue;
    picked.push(s);
    seenDish.add(s.c.dish);
    if (s.c.canteen) canteenCnt[s.c.canteen] = (canteenCnt[s.c.canteen] || 0) + 1;
    if (picked.length >= topN) break;
  }
  return picked;
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
  chips.push(["预算档 " + pset.budget_level, false]);
  const keys = Object.keys(prefs)
    .sort((a, b) => Math.abs(prefs[b]) - Math.abs(prefs[a])).slice(0, 8);
  for (const k of keys)
    chips.push([`${KEY_LABELS[k] || k} ${prefs[k] >= 0 ? "+" : ""}${prefs[k].toFixed(1)}`,
      Math.abs(prefs[k]) >= 1.2]);
  return chips;
}

function resultCardHtml(rankNo, { score, c, contrib }) {
  const cname = c.canteen || "任意食堂(就近找窗口)";
  const hits = contrib.filter(([, v]) => v > 0.25).sort((a, b) => b[1] - a[1])
    .slice(0, 3).map(([k]) => KEY_LABELS[k] || k);
  const lines = [];
  if (hits.length) lines.push(`命中偏好: <b>${hits.join("、")}</b>`);
  if (c.dpop || c.dlikes)
    lines.push(`小红书热度: <b>${(+c.dpop).toFixed(c.dpop % 1 ? 1 : 0)} 次提及</b> · 约 ${Math.round(c.dlikes)} 赞`);
  else if (c.sourceNote) lines.push(`来源: ${esc(c.sourceNote)}`);
  if (c.seedCell) lines.push("(官方特色窗口)");
  const zoneTxt = c.cinfo
    ? `${c.cinfo.zone}(${ZONES_DESC[c.cinfo.zone] || ""})` : "";
  lines.push(`价位 ${PRICE_DESC[c.price] || ""}` + (zoneTxt ? ` | ${zoneTxt}` : ""));
  if (c.cinfo && c.cinfo.note) lines.push(esc(c.cinfo.note));
  if (!c.canteen)
    lines.push("种子菜品未关联具体食堂, 大食堂基础窗口常见");
  if (c.posts.length && (FOOD_DB.posts_index || []).length) {
    const idx = Object.fromEntries(FOOD_DB.posts_index.map(p => [p.note_id, p]));
    const titles = c.posts.slice(0, 2)
      .map(id => idx[id] && idx[id].title).filter(Boolean)
      .map(t => `《${esc(t.slice(0, 22))}》`);
    if (titles.length) lines.push("帖子: " + titles.join(" "));
  }
  return `<div class="card result-card">
    <div class="result-head">
      <span class="rank-no">${rankNo}</span>
      <span class="canteen">【${esc(cname)}】</span>
      <span class="dish">${esc(c.dish)}</span>
      <span class="score">综合 ${score.toFixed(1)}</span>
    </div>
    <ul class="reasons">${lines.map(l => `<li>- ${l}</li>`).join("")}</ul>
  </div>`;
}

function initUI() {
  const $ = id => document.getElementById(id);
  const screens = ["start", "quiz", "result"].map(s => $("screen-" + s));
  const show = name => screens.forEach(el =>
    el.hidden = el.id !== "screen-" + name);

  $("db-desc").textContent =
    `小红书 ${FOOD_DB.n_posts} 帖语料 + ${QUESTIONS.length} 题随机问卷 → 食堂/菜品 Top5`;

  let session = null;   // {answers, questions, prefs, pset, hard}

  function startQuiz() {
    const n = +$("n-questions").value;
    session = { questions: sampleQuestions(n), answers: [], i: 0 };
    show("quiz");
    renderQuestion();
  }

  function renderQuestion() {
    const { questions, answers, i } = session;
    if (i >= questions.length) return finishQuiz();
    const q = questions[i];
    $("progress-bar").style.width = `${(i / questions.length) * 100}%`;
    $("q-meta").textContent = `[${i + 1}/${questions.length}] ${q.dim}`;
    $("q-text").textContent = q.q;
    $("q-options").innerHTML = q.options
      .map((o, j) => `<button data-j="${j}">${esc(o[0])}</button>`).join("");
    for (const btn of $("q-options").children)
      btn.onclick = () => choose(+btn.dataset.j);
  }

  function choose(j) { session.answers.push({ q: session.questions[session.i], choice: j }); session.i++; renderQuestion(); }
  $("btn-skip").onclick = () => choose(-1);

  function finishQuiz() {
    $("progress-bar").style.width = "100%";
    const acc = accumulate(session.answers);
    Object.assign(session, acc);
    renderResults();
  }

  function renderResults() {
    show("result");
    $("result-desc").textContent =
      `(语料: 小红书 ${FOOD_DB.n_posts} 帖 + 官方种子库, 抖动 σ=${(0.05 + 0.1 * session.pset.random_boost).toFixed(2)})`;
    $("profile").innerHTML = profileChips(session.prefs, session.pset, session.hard)
      .map(([t, hot]) => `<span class="chip${hot ? " hot" : ""}">${esc(t)}</span>`).join("");
    const picked = rank(FOOD_DB, session.prefs, session.pset, session.hard, 5);
    $("cards").innerHTML = picked.map((s, i) => resultCardHtml(i + 1, s)).join("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  $("btn-start").onclick = startQuiz;
  $("btn-reroll").onclick = renderResults;          // 同一偏好重新掷骰
  $("btn-reask").onclick = startQuiz;               // 重新问一轮
}

if (typeof document !== "undefined"
  && document.getElementById("screen-start")) {
  initUI();
}
