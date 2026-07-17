# -*- coding: utf-8 -*-
"""
generate_insights.py —— 生成「AI 研判」文本（data.json 顶层 ai_insights）

输出：ai_insights.json
  {
    "generated_at": "2026-07-17T12:00:00",
    "overview":   "总览研判文本",
    "investment": "外商来华投资动态研判",
    "jiangsu":    "外商来苏投资动态研判",
    "exchange":   "来华考察·经贸交流研判",
    "industries": {
        "人工智能(软件)": "产业研判…",
        "机器人": "产业研判…",
        "生物医药": "产业研判…",
        "新一代信息通信": "产业研判…"
    }
  }

两种生成模式：
  A) 规则/模板模式（默认，纯标准库、零外部依赖、零密钥，GitHub Actions 离线可跑）
  B) 大模型模式（设置环境变量 AI_INSIGHTS_LLM=1 并提供 AI_INSIGHTS_API_KEY）

大模型模式对接「OpenAI 兼容」接口（DeepSeek / OpenAI / 通义 / 自建 等均可），
通过环境变量配置，调用失败时自动回退到规则模式，保证管线永不中断：
  AI_INSIGHTS_LLM        = "1" 时启用大模型（否则用规则）
  AI_INSIGHTS_API_KEY    = 你的 API Key（必填）
  AI_INSIGHTS_BASE_URL   = 接口地址，默认 https://api.deepseek.com/v1
  AI_INSIGHTS_MODEL      = 模型名，默认 deepseek-chat
  AI_INSIGHTS_TEMPERATURE= 采样温度，默认 0.5
  AI_INSIGHTS_TIMEOUT    = 请求超时(秒)，默认 120
  AI_INSIGHTS_MAX_TOKENS = 最大输出 token，默认 2400

随后由 build_data.py 读取该文件并入 data.json / data.js，供前端「AI 研判」窗口展示。
（调用方式：先 `python generate_insights.py` 生成 ai_insights.json，再 `python build_data.py` 并入。）
"""
import json, os, re, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_EVENTS = ['进博会', '服贸会', '投洽会', '中国发展高层论坛', '博鳌',
              '世界智能产业博览会', '中外知名企业', '跨国公司助力', '投资浙里',
              '相约春天', '辽宁行', '海客圆桌会', '世界制造业大会', 'MWC',
              '海客圆桌', '跨国企业地方行', '投洽会']

# 四大攻坚产业（用于生成 industries 研判）
INDUSTRIES = ['人工智能(软件)', '机器人', '生物医药', '新一代信息通信']
IND_REF = {
    '人工智能(软件)': ['英伟达', '微软', '亚马逊'],
    '机器人': ['ABB', '库卡', '发那科', '安川'],
    '生物医药': ['阿斯利康', '诺华', '礼来', '罗氏', '赛诺菲'],
    '新一代信息通信': ['高通', '爱立信', '诺基亚', '三星'],
}


def is_key(it):
    t = (it.get('title', '') + it.get('summary', ''))
    if any(k in t for k in KEY_EVENTS):
        return True
    if it.get('category') == 'investment' and \
       re.search(r'亿|万美元|万欧元|亿欧元', t) and \
       re.search(r'投资|投产|落地|签约|基地|开工|增资|破土|动工', t):
        return True
    return False


def topn(items, key, n=5):
    c = Counter(i.get(key) for i in items if i.get(key))
    return c.most_common(n)


def month_trend(items, k=6):
    m = {}
    for it in items:
        mm = (it.get('date') or '')[:7]
        if mm:
            m[mm] = m.get(mm, 0) + 1
    keys = sorted(m)[-k:]
    return [(k, m[k]) for k in keys]


def join_labels(pairs, n=3):
    return '、'.join(f"{v}（{c}条）" for v, c in pairs[:n]) if pairs else '—'


def clean_title(t, n=18):
    t = re.sub(r'——.*$', '', t or '').strip(' ———')
    return (t[:n] + '…') if len(t) > n else t


def latest_keys(items, n=3):
    return sorted([i for i in items if is_key(i)],
                 key=lambda x: x.get('date', ''), reverse=True)[:n]


def compose_overview(s):
    tr = s['trend']
    if tr:
        months = [m for m, _ in tr]
        total6 = sum(c for _, c in tr)
        peak_m, peak_v = max(tr, key=lambda x: x[1])
        trend_desc = f"近半年（{months[0]}–{months[-1]}）累计 {total6} 条，其中 {peak_m} 最为集中（{peak_v} 条）"
    else:
        trend_desc = "时间序列数据尚不充分"
    keys = s['latest']
    key_txt = '；'.join(f"{k['country']}《{clean_title(k['title'])}》" for k in keys[:2]) or '—'
    return (
        f"截至生成时，平台累计收录外商来华动态 {s['total']} 条（投资 {s['inv']} / 考察经贸 {s['ex']}），"
        f"覆盖来源国家与地区 {s['countries']} 个；其中江苏相关 {s['js']} 条、南京相关 {s['nj']} 条。\n"
        f"来源结构上，{join_labels(s['top_countries'])} 为外资主力；行业上 {join_labels(s['top_industries'])} 热度居前。"
        f"{trend_desc}。\n"
        f"重点动向：{key_txt}。\n"
        f"研判建议：南京应紧盯头部跨国企业在 {s['hot_ind']} 领域的增资扩产节奏，借力进博会、投洽会等高能级平台开展精准招商，"
        f"并关注 {s['top_countries'][0][0] if s['top_countries'] else '欧美'} 资本在产业链关键环节的布局。"
    )


def compose_investment(s):
    keys = s['latest']
    proj = '；'.join(f"{k['country']}《{clean_title(k['title'], 22)}》" for k in keys[:3]) or '—'
    return (
        f"外商来华投资类动态 {s['inv']} 条，来源以 {join_labels(s['top_countries'])} 为主，"
        f"{join_labels(s['top_industries'])} 为最活跃赛道。\n"
        f"近期标志性项目：{proj}。\n"
        f"研判建议：南京宜聚焦 {s['top_industries'][0][0] if s['top_industries'] else '人工智能(软件)'}、"
        f"{s['top_industries'][1][0] if len(s['top_industries']) > 1 else '生物医药'} 两条主攻赛道，"
        f"围绕已在华布局的头部企业推动其在宁设立研发或区域总部；对龙头采取“链主+配套”组合招商，提升项目体量与技术能级。"
    )


def compose_jiangsu(s):
    return (
        f"江苏相关外资动态 {s['js']} 条，覆盖 {len(s['js_cities'])} 个设区市，南京 {s['nj']} 条；"
        f"苏州以 {s['sz']} 条领跑，南京在 {join_labels(s['js_industries'], 2)} 上形成特色。\n"
        f"研判建议：南京应立足 {s['js_industries'][0][0] if s['js_industries'] else '智能制造装备'} 既有基础，"
        f"对标苏州在智能制造装备、生物医药的集群效应，补强薄弱环节；同时用好省级“塑造开放型经济新优势”等政策，争取外资研发中心落地。"
    )


def compose_exchange(s):
    keys = s['latest']
    ev = '；'.join(f"《{clean_title(k['title'])}》" for k in keys[:2]) or '—'
    return (
        f"来华考察·经贸交流 {s['ex']} 条，以 {join_labels(s['ex_countries'])} 来访为主，"
        f"活动类型集中于 {join_labels(s['ex_types'], 2)}。\n"
        f"近期高规格活动：{ev}。\n"
        f"研判建议：南京应主动承接进博会、世界制造业大会等溢出效应，办好自有经贸活动提升国际能见度；"
        f"针对重点国别商会、驻华机构开展点对点邀约，把“考察热度”转化为“落地项目”。"
    )


def compose_industry(name, st):
    mncs = '、'.join(IND_REF.get(name, []))
    return (
        f"{name}方向累计收录相关外资动态 {st['n']} 条（投资 {st['inv']} / 考察经贸 {st['ex']}），"
        f"来源以{join_labels(st['countries'])}为主。头部企业 {mncs} 持续在华布局研发与产能。\n"
        f"研判建议：南京应围绕 {name} 产业链关键环节，依托紫金山实验室、麒麟科创园等载体，"
        f"争取上述头部企业在宁设立研发中心或联合创新平台；聚焦“强链补链”，把跨国公司的技术溢出"
        f"转化为本地配套与产业生态，提升南京在 {name} 全国版图中的显示度。"
    )


def industry_stats(d, name):
    items = [i for i in d.get('items', []) if i.get('industry') == name]
    inv = sum(1 for i in items if i.get('category') == 'investment')
    js = [i for i in items if i.get('is_jiangsu')]
    return {
        'n': len(items), 'inv': inv, 'ex': len(items) - inv,
        'countries': topn(items, 'country', 3),
        'js_cities': topn(js, 'city', 3),
    }


def build_stats(d):
    items = d.get('items', [])
    inv = sum(1 for i in items if i.get('category') == 'investment')
    ex = sum(1 for i in items if i.get('category') == 'exchange')
    js = sum(1 for i in items if i.get('is_jiangsu'))
    nj = sum(1 for i in items if i.get('is_nanjing'))
    countries = len({i.get('country') for i in items if i.get('country')})
    js_items = [i for i in items if i.get('is_jiangsu')]
    ex_items = [i for i in items if i.get('category') == 'exchange']
    sz = sum(1 for i in js_items if i.get('city') == '苏州市')
    return {
        'total': len(items), 'inv': inv, 'ex': ex, 'js': js, 'nj': nj,
        'countries': countries,
        'top_countries': topn(items, 'country', 3),
        'top_industries': topn(items, 'industry', 3),
        'hot_ind': topn(items, 'industry', 1)[0][0] if topn(items, 'industry', 1) else '人工智能(软件)',
        'trend': month_trend(items),
        'latest': latest_keys(items, 3),
        'js_cities': topn(js_items, 'city', 13),
        'js_industries': topn(js_items, 'industry', 6),
        'sz': sz,
        'ex_countries': topn(ex_items, 'country', 3),
        'ex_types': topn(ex_items, 'event_type', 3),
    }


def rule_generate(s, d, ind_map):
    """规则/模板模式生成完整 ai_insights 结构。"""
    industries = {name: compose_industry(name, ind_map[name]) for name in INDUSTRIES}
    return {
        'overview': compose_overview(s),
        'investment': compose_investment(s),
        'jiangsu': compose_jiangsu(s),
        'exchange': compose_exchange(s),
        'industries': industries,
    }


# ============================ 大模型模式 ============================
SYSTEM_PROMPT = (
    "你是南京市商务局（外国投资管理处）的产业研判助手，服务对象是负责招商引资与外资管理的政府工作人员。"
    "你的研判必须基于提供的真实数据，专业、务实、面向决策、可直接用于内部参考，避免空话套话。"
    "只能输出一个 JSON 对象，不要输出任何解释、前缀或 Markdown 代码块。"
)

USER_INSTRUCTION = (
    "下面是一份外商来华投资/考察经贸动态的真实统计。请据此撰写研判文本。\n"
    "【总体要求】全部用简体中文；每段 150–320 字；必须引用数据中的具体来源国/地区、行业、重点活动、城市、数量，"
    "给出对南京招商与外资管理有操作性的建议；不要编造数据中不存在的事实。\n"
    "【输出 JSON 键说明】\n"
    "  overview   : 总览研判（全局态势 + 趋势 + 重点动向 + 总体建议）\n"
    "  investment : 外商来华投资动态研判（来源国、活跃赛道、标志性项目、招商建议）\n"
    "  jiangsu    : 外商来苏（江苏含南京）投资动态研判，须点出南京在江苏数据中的定位、相对苏州的短板与突破口\n"
    "  exchange   : 来华考察·经贸交流研判（来访国别、活动类型、高规格活动、把考察转化为落地的建议）\n"
    "  industries : 对象，含 4 个键，分别为对应产业的南京攻坚研判（结合头部跨国公司动态，给出南京可落地建议）：\n"
    "               \"人工智能(软件)\"、\"机器人\"、\"生物医药\"、\"新一代信息通信\"\n"
    "只输出 JSON，键名必须严格如上，不要多余字段。\n\n"
    "【数据】\n"
)


def build_prompt(s, ind_map):
    lines = []
    lines.append(f"· 累计动态 {s['total']} 条（投资 {s['inv']} / 考察经贸 {s['ex']}），覆盖来源国家与地区 {s['countries']} 个；江苏相关 {s['js']} 条、南京相关 {s['nj']} 条。")
    lines.append(f"· 来源国家/地区 TOP：{join_labels(s['top_countries'], 5)}")
    lines.append(f"· 行业分布 TOP：{join_labels(s['top_industries'], 5)}")
    tr = '；'.join(f"{m}:{c}" for m, c in s['trend']) or '（不足）'
    lines.append(f"· 近半年月度趋势：{tr}")
    keys = s['latest']
    if keys:
        ktxt = '；'.join(f"{k.get('country','?')}《{clean_title(k.get('title',''),24)}》({k.get('date','?')})" for k in keys)
        lines.append(f"· 近期重点动向：{ktxt}")
    lines.append(f"· 江苏格局：覆盖 {len(s['js_cities'])} 个设区市，苏州 {s['sz']} 条领跑，南京 {s['nj']} 条；南京特色产业：{join_labels(s['js_industries'], 3)}")
    lines.append(f"· 考察交流：{s['ex']} 条，来访国别 {join_labels(s['ex_countries'],3)}，活动类型 {join_labels(s['ex_types'],3)}")
    for name in INDUSTRIES:
        st = ind_map[name]
        lines.append(f"· 产业【{name}】：{st['n']} 条（投资 {st['inv']}/考察 {st['ex']}），来源国 {join_labels(st['countries'],3)}；头部企业参考 {('、'.join(IND_REF.get(name, [])))}")
    return USER_INSTRUCTION + '\n'.join(lines) + '\n'


def _extract_json(text):
    text = text.strip()
    # 去除可能的代码围栏
    if text.startswith('```'):
        text = re.sub(r'^```[a-zA-Z]*\n', '', text)
        text = re.sub(r'\n```$', '', text)
        text = text.strip()
    s = text.find('{')
    e = text.rfind('}')
    if s == -1 or e == -1 or e < s:
        raise ValueError('响应中未找到 JSON')
    return text[s:e + 1]


def llm_generate(s, d, ind_map, rules):
    """调用 OpenAI 兼容接口生成研判；任何异常都抛出，由 main 回退规则。"""
    import requests  # 延迟导入，规则模式下无需该依赖

    api_key = (os.environ.get('AI_INSIGHTS_API_KEY') or '').strip()
    if not api_key:
        raise ValueError('未设置 AI_INSIGHTS_API_KEY')
    base_url = (os.environ.get('AI_INSIGHTS_BASE_URL') or 'https://api.deepseek.com/v1').strip().rstrip('/')
    model = (os.environ.get('AI_INSIGHTS_MODEL') or 'deepseek-chat').strip()
    try:
        temperature = float(os.environ.get('AI_INSIGHTS_TEMPERATURE') or '0.5')
    except ValueError:
        temperature = 0.5
    try:
        timeout = int(os.environ.get('AI_INSIGHTS_TIMEOUT') or '120')
    except ValueError:
        timeout = 120
    try:
        max_tokens = int(os.environ.get('AI_INSIGHTS_MAX_TOKENS') or '2400')
    except ValueError:
        max_tokens = 2400

    url = base_url + '/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': build_prompt(s, ind_map)},
        ],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    # 部分兼容接口支持 json_object，失败不影响（我们仍做健壮解析）
    try:
        payload['response_format'] = {'type': 'json_object'}
    except Exception:
        pass

    print(f"[LLM] 调用 {model} @ {base_url} …")
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
    content = r.json()['choices'][0]['message']['content']
    return parse_insights(content, rules)


def parse_insights(content, rules):
    """解析 LLM 输出，逐字段校验；不合格字段回退到 rules 对应文本。"""
    raw = json.loads(_extract_json(content))
    out = {}
    for k in ('overview', 'investment', 'jiangsu', 'exchange'):
        val = (raw.get(k) or '').strip() if isinstance(raw.get(k), str) else ''
        out[k] = val if len(val) >= 30 else rules[k]
    ind_raw = raw.get('industries') if isinstance(raw.get('industries'), dict) else {}
    out_ind = {}
    for name in INDUSTRIES:
        v = (ind_raw.get(name) or '').strip() if isinstance(ind_raw.get(name), str) else ''
        out_ind[name] = v if len(v) >= 30 else rules['industries'][name]
    out['industries'] = out_ind
    return out


def main():
    with open(os.path.join(HERE, 'data.json'), encoding='utf-8') as f:
        d = json.load(f)
    s = build_stats(d)
    ind_map = {name: industry_stats(d, name) for name in INDUSTRIES}

    # 先算规则版本，作为大模型缺失字段的兜底
    rules = rule_generate(s, d, ind_map)

    use_llm = (os.environ.get('AI_INSIGHTS_LLM') or '').strip() == '1'
    out = None
    if use_llm:
        try:
            out = llm_generate(s, d, ind_map, rules)
            print('[LLM] 大模型研判生成成功')
        except Exception as e:
            print('[LLM] 调用失败，回退规则生成：', repr(e))
            out = None
    if out is None:
        if use_llm:
            print('[模式] 规则兜底')
        else:
            print('[模式] 规则/模板（未启用大模型）')
        out = rules

    out['generated_at'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    path = os.path.join(HERE, 'ai_insights.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('已生成', path)
    for k in ('overview', 'investment', 'jiangsu', 'exchange'):
        print(f'  [{k}] {len(out[k])} 字')
    for k in INDUSTRIES:
        print(f'  [industry:{k}] {len(out["industries"][k])} 字')
    print('  生成于', out['generated_at'])


if __name__ == '__main__':
    main()
