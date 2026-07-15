'use strict';
/* ============================================================
   南京市外商投资动态监测平台 —— 前端逻辑
   数据来自 data.json（由 build_data.py / crawler.py 生成）
   配置与内容分离：模块、产业口径、分页大小均在此可调
   ============================================================ */

const PAGE_SIZE = 10;
let DATA = null;

const state = {
  module: 'overview',
  page: 1,
  filters: {},          // 各模块筛选条件
  industry: '人工智能(软件)' // 四大产业专题当前选中
};

/* —— 可维护配置 —— */
const TITLES = {
  overview: '总览',
  investment: '外商来华投资动态',
  jiangsu: '外商来苏投资动态',
  exchange: '外商来华考察·经贸交流动态',
  industry: '我市四大攻坚产业动态',
  policy: '各级外商投资政策文件'
};
const FOUR = ['人工智能(软件)', '机器人', '生物医药', '新一代信息通信'];
const LV_CLASS = { '国家级': 'gj', '省级': 'sj', '市级': 'shi', '区级': 'qu' };

/* 江苏省 13 个地级市（来苏模块城市筛选固定列出，确保覆盖全省） */
const JIANGSU_CITIES = [
  '南京市', '无锡市', '徐州市', '常州市', '苏州市', '南通市', '连云港市',
  '淮安市', '盐城市', '扬州市', '镇江市', '泰州市', '宿迁市'
];

/* 统一“来源”维度：覆盖来华投资 / 来苏投资 / 考察经贸 三个模块
   结构：港澳台 + 主要投资国别 + 其他国别（兜底“多国/跨国企业/零散国别”） */
const HK_MO_TW = ['中国台湾', '中国香港', '中国澳门'];
const MAJOR_COUNTRIES = ['美国', '德国', '日本', '韩国', '法国', '英国', '瑞士', '瑞典',
  '意大利', '比利时', '丹麦', '波兰', '荷兰', '新加坡', '加拿大', '西班牙',
  '芬兰', '墨西哥', '卢森堡', '白俄罗斯', '沙特', '挪威', '巴西', '阿联酋'];
const OTHER_SOURCE = '__other__';
const SOURCE_OPTIONS = HK_MO_TW.concat(MAJOR_COUNTRIES);

/* 全局翻页函数（供内联 onclick 调用） */
window.gotoPage = function (p) {
  state.page = p;
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

/* ============ 启动 ============ */
/* 导航始终先绑定：即便数据异常，左侧模块切换也不会“失灵” */
wireNav();
wireRefresh();

/* 优先使用 data.js（本地双击 file:// 即可加载）；否则回退到 fetch data.json（服务器部署） */
if (window.DATA && Array.isArray(window.DATA.items)) {
  DATA = window.DATA;
  boot();
} else {
  fetch('data.json')
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(d => { DATA = d; boot(); })
    .catch(e => {
      document.getElementById('content').innerHTML =
        '<div class="loading">⚠ 数据加载失败。<br>本页面需通过本地/云端 HTTP 服务器访问（例如：<code>python -m http.server</code>），' +
        '直接双击打开会因浏览器安全策略无法读取 data.json。<br><br><small>' + e + '</small></div>';
    });
}

/* 左侧导航点击：无条件绑定，数据未就绪时也能切换（显示提示而非“死”页） */
function wireNav() {
  document.querySelectorAll('.nav-item').forEach(a => {
    a.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
      a.classList.add('active');
      state.module = a.dataset.module;
      state.page = 1; state.filters = {};
      if (DATA) {
        render();
      } else {
        document.getElementById('module-title').textContent = TITLES[state.module];
        document.getElementById('content').innerHTML =
          '<div class="loading">数据尚未加载，请刷新页面，或确认同目录下 data.js / data.json 是否存在。</div>';
      }
    });
  });
}

function boot() {
  document.getElementById('updated-at').textContent = (DATA.updated_at || '').replace('T', ' ');
  render();
}

/* ============ 手动“检查更新” ============
   任何访客点击即重新拉取服务器上最新的 data.json（绕过浏览器缓存），
   并用新数据重渲染当前模块、刷新左下角“数据更新”时间。
   说明：浏览器无法自行全网采集，此按钮拉取的是“最近一次已部署的最新数据”。 */
function wireRefresh() {
  const btn = document.getElementById('refresh-btn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (btn.classList.contains('loading')) return;
    btn.classList.add('loading');
    const txt = btn.querySelector('.refresh-txt');
    const prevLabel = txt ? txt.textContent : '';
    if (txt) txt.textContent = '正在更新…';
    const prevUpdated = DATA && DATA.updated_at;
    const prevCount = DATA && DATA.items ? DATA.items.length : 0;

    fetch('data.json?t=' + Date.now(), { cache: 'no-store' })
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(d => {
        if (!d || !Array.isArray(d.items)) throw new Error('数据格式异常');
        DATA = d; window.DATA = d;
        const at = document.getElementById('updated-at');
        if (at) at.textContent = (d.updated_at || '').replace('T', ' ');
        render();
        const changed = (d.updated_at && d.updated_at !== prevUpdated) || d.items.length !== prevCount;
        toast(changed
          ? '✓ 已更新到最新数据（共 ' + d.items.length + ' 条，更新于 ' + (d.updated_at || '').replace('T', ' ') + '）'
          : '✓ 当前已是最新（共 ' + d.items.length + ' 条）');
      })
      .catch(e => {
        toast('✗ 刷新失败：' + e.message + '。若为本地双击打开，请改用公网地址访问后再刷新。');
      })
      .finally(() => {
        btn.classList.remove('loading');
        if (txt) txt.textContent = prevLabel || '检查更新';
      });
  });
}

/* 轻量 toast 提示 */
function toast(msg) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => t.classList.remove('show'), 3600);
}

function render() {
  if (window.__carouselTimer) { clearInterval(window.__carouselTimer); window.__carouselTimer = null; }
  document.getElementById('module-title').textContent = TITLES[state.module];
  const c = document.getElementById('content');
  c.innerHTML = '';
  switch (state.module) {
    case 'overview': renderOverview(c); break;
    case 'investment': renderList(c, { category: 'investment' }); break;
    case 'jiangsu': renderList(c, { category: 'investment', jiangsu: true, citySelect: true }); break;
    case 'exchange': renderList(c, { category: 'exchange' }); break;
    case 'industry': renderIndustry(c); break;
    case 'policy': renderPolicy(c); break;
  }
}

/* ============ 工具 ============ */
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function uniq(arr) { return [...new Set(arr.filter(Boolean))]; }
function byDateDesc(a, b) { return (b.date || '').localeCompare(a.date || ''); }

/* 纯 CSS 条形图 */
function barChart(rows, red) {
  if (!rows.length) return '<div class="empty"><p>暂无数据</p></div>';
  const max = Math.max(...rows.map(r => r.value), 1);
  return '<div class="bars">' + rows.map(r =>
    '<div class="bar-item"><div class="bl">' + esc(r.label) + '</div>' +
    '<div class="bar-track"><div class="bar-fill' + (red ? ' red' : '') +
    '" style="width:' + Math.round(r.value / max * 100) + '%"></div></div>' +
    '<div class="bv">' + r.value + '</div></div>'
  ).join('') + '</div>';
}

/* 圆环图（conic-gradient） */
function donut(segments) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  let acc = 0; const stops = [];
  segments.forEach(s => {
    const pct = acc / total * 100;
    const pct2 = (acc + s.value) / total * 100;
    stops.push(s.color + ' ' + pct.toFixed(1) + '% ' + pct2.toFixed(1) + '%');
    acc += s.value;
  });
  const legend = segments.map(s =>
    '<div class="lg"><span class="dot" style="background:' + s.color + '"></span>' +
    esc(s.label) + ' ' + s.value + ' 条</div>').join('');
  return '<div class="donut-wrap"><div style="width:120px;height:120px;border-radius:50%;' +
    'background:conic-gradient(' + stops.join(',') + ');position:relative"></div>' +
    '<div class="legend">' + legend + '</div></div>';
}

/* 信息卡片（投资/考察通用，带原文链接） */
function itemCard(it) {
  const tags = [];
  tags.push('<span class="tag country">' + esc(it.country) + '</span>');
  if (it.industry) tags.push('<span class="tag ind">' + esc(it.industry) + '</span>');
  tags.push('<span class="tag type">' + esc(it.event_type) + '</span>');
  if (it.is_jiangsu) tags.push('<span class="tag js">江苏</span>');
  if (it.is_jiangsu && it.city) tags.push('<span class="tag city">' + esc(it.city.replace('市', '')) + '</span>');
  if (it.is_nanjing) tags.push('<span class="tag nj">南京</span>');
  tags.push('<span class="tag">' + esc(it.source) + '</span>');
  return '<div class="card"><div class="c-head"><div class="c-title">' +
    '<a href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></div>' +
    '<div class="c-meta">' + esc(it.date) + '</div></div>' +
    '<div class="c-summary">' + esc(it.summary) + '</div>' +
    '<div class="tags">' + tags.join('') + '</div>' +
    '<a class="open-link" href="' + esc(it.url) + '" target="_blank" rel="noopener">查看原文</a></div>';
}

/* 分页控件 */
function pager(total) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (state.page > pages) state.page = pages;
  if (state.page < 1) state.page = 1;
  let btns = '';
  const start = Math.max(1, state.page - 2), end = Math.min(pages, state.page + 2);
  for (let i = start; i <= end; i++) {
    btns += '<button class="' + (i === state.page ? 'active' : '') + '" onclick="gotoPage(' + i + ')">' + i + '</button>';
  }
  return '<div class="pager"><button ' + (state.page <= 1 ? 'disabled' : '') +
    ' onclick="gotoPage(' + (state.page - 1) + ')">上一页</button>' + btns +
    '<button ' + (state.page >= pages ? 'disabled' : '') + ' onclick="gotoPage(' + (state.page + 1) + ')">下一页</button>' +
    '<span class="info">共 ' + total + ' 条 · 第 ' + state.page + '/' + pages + ' 页 · 每页 ' + PAGE_SIZE + ' 条</span></div>';
}

/* 通用筛选条 */
function filterBar(opts) {
  const base = opts.base || DATA.items;
  const f = state.filters;
  let html = '<div class="filterbar">';
  if (opts.industry !== false) {
    html += '<span class="f-label">行业</span><select id="f-ind"><option value="">全部行业</option>' +
      DATA.industries.map(x => '<option value="' + esc(x) + '"' + (f.ind === x ? ' selected' : '') + '>' + esc(x) + '</option>').join('') +
      '</select>';
  }
  if (opts.country !== false) {
    // 统一来源：港澳台 + 主要投资国别（分组）+ 其他国别（兜底）
    let srcOpts = '<option value="">全部来源</option>' +
      '<optgroup label="港澳台">' + HK_MO_TW.map(x =>
        '<option value="' + esc(x) + '"' + (f.cty === x ? ' selected' : '') + '>' + esc(x) + '</option>').join('') + '</optgroup>' +
      '<optgroup label="主要投资国别">' + MAJOR_COUNTRIES.map(x =>
        '<option value="' + esc(x) + '"' + (f.cty === x ? ' selected' : '') + '>' + esc(x) + '</option>').join('') + '</optgroup>' +
      '<option value="' + OTHER_SOURCE + '"' + (f.cty === OTHER_SOURCE ? ' selected' : '') + '>其他国别</option>';
    html += '<span class="f-label">来源</span><select id="f-cty">' + srcOpts + '</select>';
  }
  if (opts.citySelect) {
    // 固定列出江苏 13 个地级市，确保覆盖全省（即便某市暂无数据也可筛选）
    const cities = JIANGSU_CITIES.slice().sort();
    html += '<span class="f-label">城市</span><select id="f-city"><option value="">江苏全部城市</option>' +
      cities.map(x => '<option value="' + esc(x) + '"' + (f.city === x ? ' selected' : '') + '>' + esc(x) + '</option>').join('') +
      '</select>';
  }
  if (opts.month !== false) {
    // 时间：按月日历选择（input type=month），可选具体月份，留空为全部
    html += '<span class="f-label">时间</span>' +
      '<input type="month" id="f-month" class="f-month" value="' + esc(f.month || '') + '" title="选择具体月份">' +
      '<span class="month-clear" id="f-month-clear">全部</span>';
  }
  html += '<span class="f-label">关键词</span><input type="text" id="f-kw" placeholder="标题/摘要/来源…" value="' + esc(f.kw || '') + '">' +
    '<span class="spacer"></span><span class="reset" id="f-reset">重置</span></div>';
  return html;
}

function bindFilters(onChange) {
  const map = { 'f-ind': 'ind', 'f-cty': 'cty', 'f-city': 'city', 'f-month': 'month' };
  Object.keys(map).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => { state.filters[map[id]] = el.value; state.page = 1; onChange(); });
  });
  const mc = document.getElementById('f-month-clear');
  if (mc) mc.addEventListener('click', () => {
    const mi = document.getElementById('f-month'); if (mi) mi.value = '';
    state.filters.month = ''; state.page = 1; onChange();
  });
  const kw = document.getElementById('f-kw');
  if (kw) kw.addEventListener('input', () => { state.filters.kw = kw.value.trim(); state.page = 1; onChange(); });
  const rs = document.getElementById('f-reset');
  if (rs) rs.addEventListener('click', () => { state.filters = {}; state.page = 1; onChange(); });
}

function applyFilters(items) {
  const f = state.filters;
  return items.filter(i => {
    if (f.ind && i.industry !== f.ind) return false;
    if (f.cty) {
      // 选中“其他国别”→ 过滤掉所有已知来源（港澳台+主要国别），保留多国/跨国企业/零散国别
      if (f.cty === OTHER_SOURCE) { if (SOURCE_OPTIONS.includes(i.country)) return false; }
      else if (i.country !== f.cty) return false;
    }
    if (f.city && i.city !== f.city) return false;
    if (f.month && (i.date || '').slice(0, 7) !== f.month) return false;
    if (f.kw) {
      const hay = (i.title + i.summary + i.source + i.country + (i.industry || '')).toLowerCase();
      if (!hay.includes(f.kw.toLowerCase())) return false;
    }
    return true;
  });
}

/* ============ 总览 ============ */
function renderOverview(c) {
  const items = DATA.items.slice().sort(byDateDesc);
  const countries = uniq(items.map(i => i.country)).length;
  const jsCount = items.filter(i => i.is_jiangsu).length;
  const exCount = items.filter(i => i.category === 'exchange').length;

  c.innerHTML =
    '<div class="kpi-row">' +
    kpi(items.length, '动态总数', false) +
    kpi(countries, '来源国家/地区', false) +
    kpi(jsCount, '江苏相关动态', true) +
    kpi(exCount, '考察·经贸活动', false) +
    '</div>' +
    buildCarousel(items.slice(0, 6)) +
    '<div class="grid-2"><div class="panel"><h3>活动类型分布</h3>' +
    donut([
      { label: '投资落地/增资/总部/研发', value: items.filter(i => i.category === 'investment').length, color: '#15395f' },
      { label: '考察/经贸/参会/论坛', value: exCount, color: '#c8102e' }
    ]) + '</div>' +
    '<div class="panel"><h3>来源国家/地区 TOP</h3>' +
    barChart(sourceCounts(items).slice(0, 8)) + '</div></div>' +
    '<div class="grid-2" style="margin-top:18px"><div class="panel"><h3>行业分布 TOP</h3>' +
    barChart(topCount(items.filter(i => i.industry), 'industry', 8)) + '</div>' +
    '<div class="panel"><h3>江苏相关动态 · 城市 TOP</h3>' +
    barChart(topCount(items.filter(i => i.is_jiangsu), 'city', 8)) + '</div></div>' +
    '<div class="section-title"><span class="bar"></span>最新动态</div>' +
    '<div class="feed">' + items.slice(0, PAGE_SIZE).map(itemCard).join('') + '</div>' +
    pager(items.length);

  initCarousel();
}

/* 轮播：精选动态自动轮动，带左右箭头与圆点；支持 item.image（无图时行业渐变兜底） */
function industryGradient(name) {
  const map = {
    '人工智能(软件)': 'linear-gradient(120deg,#0e2a47,#1d4a7a)',
    '机器人': 'linear-gradient(120deg,#10243f,#2a6f97)',
    '生物医药': 'linear-gradient(120deg,#0e2a47,#0a7d4a)',
    '新一代信息通信': 'linear-gradient(120deg,#15233f,#3a5bd0)',
    '智能电网': 'linear-gradient(120deg,#0e2a47,#1f7a8c)',
    '智能制造装备': 'linear-gradient(120deg,#1a1f3a,#4a4e8c)',
    '新材料': 'linear-gradient(120deg,#0e2a47,#7a5a1f)',
    '智能网联新能源汽车': 'linear-gradient(120deg,#10243f,#c8102e)',
    '集成电路': 'linear-gradient(120deg,#15233f,#5a3a8c)',
    '低空经济(航空航天)': 'linear-gradient(120deg,#0e2a47,#1d6fa5)'
  };
  return map[name] || 'linear-gradient(120deg,#0e2a47,#1d4a7a)';
}

function buildCarousel(featured) {
  if (!featured.length) return '';
  const slides = featured.map((it, idx) => {
    const bg = it.image
      ? "background-image:url('" + esc(it.image) + "');background-size:cover;background-position:center"
      : 'background:' + industryGradient(it.industry);
    const tags = [];
    if (it.country) tags.push('<span class="c-tag-i">' + esc(it.country) + '</span>');
    if (it.industry) tags.push('<span class="c-tag-i">' + esc(it.industry) + '</span>');
    if (it.is_jiangsu) tags.push('<span class="c-tag-i">江苏</span>');
    if (it.is_nanjing) tags.push('<span class="c-tag-i">南京</span>');
    return '<div class="cslide' + (idx === 0 ? ' show' : '') + '" style="' + bg + '">' +
      '<div class="c-shade"></div>' +
      '<div class="c-body">' +
      '<div class="c-tags">' + tags.join('') + '</div>' +
      '<div class="c-title">' + esc(it.title) + '</div>' +
      '<div class="c-summary">' + esc(it.summary) + '</div>' +
      '<a class="c-link" href="' + esc(it.url) + '" target="_blank" rel="noopener">查看原文 ↗</a>' +
      '</div></div>';
  }).join('');
  const dots = featured.map((_, i) => '<span class="c-dot' + (i === 0 ? ' active' : '') + '" data-i="' + i + '"></span>').join('');
  return '<div class="carousel' + (featured.length <= 1 ? ' single' : '') + '" id="carousel">' + slides +
    '<button class="carrow prev" id="cprev" aria-label="上一条">‹</button>' +
    '<button class="carrow next" id="cnext" aria-label="下一条">›</button>' +
    '<div class="cdots" id="cdots">' + dots + '</div></div>';
}

function initCarousel() {
  const car = document.getElementById('carousel');
  if (!car) return;
  const slides = car.querySelectorAll('.cslide');
  const dots = car.querySelectorAll('.c-dot');
  let i = 0;
  function show(n) {
    i = (n + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle('show', k === i));
    dots.forEach((d, k) => d.classList.toggle('active', k === i));
  }
  function restart() {
    if (window.__carouselTimer) clearInterval(window.__carouselTimer);
    if (slides.length <= 1) return;
    window.__carouselTimer = setInterval(() => show(i + 1), 4500);
  }
  const prev = car.querySelector('#cprev'), next = car.querySelector('#cnext');
  if (prev) prev.addEventListener('click', () => { show(i - 1); restart(); });
  if (next) next.addEventListener('click', () => { show(i + 1); restart(); });
  dots.forEach(d => d.addEventListener('click', () => { show(+d.dataset.i); restart(); }));
  restart();
}

function kpi(num, lab, red) {
  return '<div class="kpi' + (red ? ' red' : '') + '"><div class="num">' + num + '</div><div class="lab">' + lab + '</div></div>';
}

function topCount(items, key, n) {
  const m = {};
  items.forEach(i => { const v = i[key]; if (v) m[v] = (m[v] || 0) + 1; });
  return Object.keys(m).map(k => ({ label: k, value: m[k] })).sort((a, b) => b.value - a.value).slice(0, n);
}

/* 来源维度计数：与“来源”下拉(SOURCE_OPTIONS)保持一致，按数量降序，
   仅列出有数据的来源（其他国别/零散来源不在扇区内） */
function sourceCounts(items) {
  const m = {};
  SOURCE_OPTIONS.forEach(s => { m[s] = 0; });
  items.forEach(i => { if (SOURCE_OPTIONS.includes(i.country)) m[i.country] = (m[i.country] || 0) + 1; });
  return SOURCE_OPTIONS.map(s => ({ label: s, value: m[s] }))
    .filter(r => r.value > 0).sort((a, b) => b.value - a.value);
}

/* ============ 通用列表（来华投资 / 来苏投资 / 考察经贸） ============ */
function renderList(c, opts) {
  let base = DATA.items.slice();
  if (opts.category) base = base.filter(i => i.category === opts.category);
  if (opts.jiangsu) base = base.filter(i => i.is_jiangsu);

  const wrap = document.createElement('div');
  wrap.innerHTML = filterBar({ base, citySelect: opts.citySelect }) +
    '<div class="grid-2"><div><div class="feed" id="feed"></div></div>' +
    '<div class="panel"><h3>' + (opts.jiangsu ? '来苏投资' : (opts.category === 'exchange' ? '考察经贸' : '来华投资')) + '统计</h3>' +
    '<div id="stats"></div></div></div>' +
    '<div id="pg"></div>';
  c.appendChild(wrap);

  function refresh() {
    const filtered = applyFilters(base).sort(byDateDesc);
    const pageItems = filtered.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
    document.getElementById('feed').innerHTML = pageItems.length
      ? pageItems.map(itemCard).join('') : '<div class="empty"><p>没有符合条件的条目</p></div>';
    document.getElementById('pg').innerHTML = pager(filtered.length);
    const indRows = topCount(filtered, 'industry', 6);
    const srcRows = sourceCounts(filtered);
    document.getElementById('stats').innerHTML =
      (indRows.length ? barChart(indRows) : barChart([{ label: '（无行业标注）', value: 0 }])) +
      '<div style="margin-top:14px"><h3 style="font-size:13px;color:var(--navy);margin-bottom:8px">来源国家/地区</h3>' +
      (srcRows.length ? barChart(srcRows) : '<div class="empty"><p>暂无来源数据</p></div>') + '</div>';
  }
  bindFilters(refresh);
  refresh();
}

/* ============ 四大攻坚产业专题 ============ */
function renderIndustry(c) {
  c.innerHTML = '';
  const cards = FOUR.map(name => {
    const n = DATA.items.filter(i => i.industry === name).length;
    return '<div class="ind-card' + (state.industry === name ? ' active' : '') + '" data-ind="' + esc(name) + '">' +
      '<div class="ic-name">' + esc(name) + '</div><div class="ic-count">' + n + '</div>' +
      '<div class="ic-lab">相关动态</div></div>';
  }).join('');

  const wrap = document.createElement('div');
  wrap.innerHTML = '<div class="ind-cards">' + cards + '</div>' +
    '<div class="grid-2"><div><div class="feed" id="feed"></div></div>' +
    '<div class="panel"><h3>「' + esc(state.industry) + '」来源分布</h3><div id="stats"></div></div></div>' +
    '<div id="pg"></div>';
  c.appendChild(wrap);

  wrap.querySelectorAll('.ind-card').forEach(el => {
    el.addEventListener('click', () => {
      state.industry = el.dataset.ind; state.page = 1; renderIndustry(c);
    });
  });

  function refresh() {
    const base = DATA.items.filter(i => i.industry === state.industry).sort(byDateDesc);
    const pageItems = base.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
    document.getElementById('feed').innerHTML = pageItems.length
      ? pageItems.map(itemCard).join('') : '<div class="empty"><p>该产业暂无相关动态</p></div>';
    document.getElementById('pg').innerHTML = pager(base.length);
    const srcRows = sourceCounts(base);
    const inv = base.filter(i => i.category === 'investment').length;
    const ex = base.length - inv;
    document.getElementById('stats').innerHTML =
      '<div class="type-stat"><span class="ts red">投资类 ' + inv + ' 条</span><span class="ts blue">考察·经贸类 ' + ex + ' 条</span></div>' +
      '<div style="margin-top:14px"><h3 style="font-size:13px;color:var(--navy);margin-bottom:8px">来源国家/地区</h3>' +
      (srcRows.length ? barChart(srcRows) : '<div class="empty"><p>暂无来源数据</p></div>') + '</div>';
  }
  refresh();
}

/* ============ 政策文件 ============ */
function renderPolicy(c) {
  c.innerHTML = '';
  const f = state.filters;
  const levels = ['国家级', '省级', '市级'];
  const curLvl = f.lvl && f.lvl !== '全部' ? f.lvl : null;
  const chips = ['全部'].concat(levels).map(l =>
    '<span class="chip' + ((f.lvl || '全部') === l ? ' active' : '') + '" data-lvl="' + esc(l) + '">' + esc(l) + '</span>').join('');

  /* 地区筛选：国家级不显示；省级=有政策的省份，市级=有政策的城市，且支持手动输入检索 */
  let regionCtrl = '';
  if (curLvl && curLvl !== '国家级') {
    const regionList = uniq(DATA.policies.filter(p => p.level === curLvl).map(p => p.region)).sort();
    const opts = regionList.map(r => '<option value="' + esc(r) + '">' + esc(r) + '</option>').join('');
    regionCtrl = '<span class="f-label">地区</span>' +
      '<input type="text" id="p-region" class="f-region" list="p-region-list" placeholder="输入' +
      (curLvl === '省级' ? '省份' : '城市') + '检索…" value="' + esc(f.region || '') + '">' +
      '<datalist id="p-region-list">' + opts + '</datalist>';
  }

  const wrap = document.createElement('div');
  wrap.innerHTML = '<div class="chip-row" id="lvl-chips">' + chips + '</div>' +
    '<div class="filterbar">' + regionCtrl +
    '<span class="f-label">关键词</span><input type="text" id="p-kw" placeholder="标题/发布单位…" value="' + esc(f.kw || '') + '">' +
    '<span class="spacer"></span><span class="reset" id="p-reset">重置</span></div>' +
    '<div class="policy"><div id="plist"></div></div>' +
    '<div id="pg"></div>';
  c.appendChild(wrap);

  wrap.querySelectorAll('.chip').forEach(el => {
    el.addEventListener('click', () => { state.filters.lvl = el.dataset.lvl; state.filters.region = ''; state.page = 1; renderPolicy(c); });
  });

  function refresh() {
    let list = DATA.policies.filter(p => p.level !== '区级');
    if (f.lvl && f.lvl !== '全部') list = list.filter(p => p.level === f.lvl);
    if (f.region) list = list.filter(p => p.region === f.region);
    if (f.kw) {
      const kw = f.kw.toLowerCase();
      list = list.filter(p => (p.title + p.publisher + p.summary).toLowerCase().includes(kw));
    }
    list.sort(byDateDesc);
    const pageItems = list.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
    document.getElementById('plist').innerHTML = pageItems.length ? pageItems.map(policyCard).join('')
      : '<div class="empty"><p>该层级/地区暂无出台的政策文件</p></div>';
    document.getElementById('pg').innerHTML = pager(list.length);
  }

  const rg = document.getElementById('p-region');
  if (rg) rg.addEventListener('input', () => { state.filters.region = rg.value.trim(); state.page = 1; refresh(); });
  const kw = document.getElementById('p-kw');
  kw.addEventListener('input', () => { state.filters.kw = kw.value.trim(); state.page = 1; refresh(); });
  document.getElementById('p-reset').addEventListener('click', () => { state.filters = {}; state.page = 1; renderPolicy(c); });
  refresh();
}

function policyCard(p) {
  return '<div class="card"><div class="c-head"><div class="c-title">' +
    '<a href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + '</a></div>' +
    '<span class="lvl ' + (LV_CLASS[p.level] || 'gj') + '">' + esc(p.level) + '</span></div>' +
    '<div class="c-summary">' + esc(p.summary) + '</div>' +
    '<div class="tags"><span class="tag">' + esc(p.region) + '</span>' +
    '<span class="tag">' + esc(p.publisher) + '</span>' +
    '<span class="tag">' + esc(p.date) + '</span></div>' +
    '<a class="open-link" href="' + esc(p.url) + '" target="_blank" rel="noopener">查看政策原文</a></div>';
}
