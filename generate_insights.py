# -*- coding: utf-8 -*-
"""
generate_insights.py —— 生成「AI 研判」文本（data.json 顶层 ai_insights）

数据驱动的规则化研判生成器（纯标准库，零外部依赖，可在 GitHub Actions 离线运行）。
按周由 .github/workflows/insights.yml 调用，刷新四大范围的研判文本与生成时间。

输出：ai_insights.json
  {
    "generated_at": "2026-07-17T12:00:00",
    "overview":   "总览研判文本",
    "investment": "外商来华投资动态研判",
    "jiangsu":    "外商来苏投资动态研判",
    "exchange":   "来华考察·经贸交流研判"
  }

随后由 build_data.py 读取该文件并入 data.json / data.js，供前端「AI 研判」窗口展示。
（调用方式：先 `python generate_insights.py` 生成 ai_insights.json，再 `python build_data.py` 并入。）

升级为真正大模型生成的路径（可选，需自备 API Key）：
  将下方 heuristic_* 改为调用 LLM 接口、把 stats 作为上下文传入即可。
  例如设置环境变量 AI_INSIGHTS_LLM=1 并在 llm_generate() 中填入你的 API 调用。
"""
import json, os, re, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_EVENTS = ['进博会', '服贸会', '投洽会', '中国发展高层论坛', '博鳌',
               '世界智能产业博览会', '中外知名企业', '跨国公司助力', '投资浙里',
               '相约春天', '辽宁行', '海客圆桌会', '世界制造业大会', 'MWC',
               '海客圆桌', '跨国企业地方行', '投洽会']


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


def compose_overview(stats):
    tr = stats['trend']
    if tr:
        months = [m for m, _ in tr]
        total6 = sum(c for _, c in tr)
        peak_m, peak_v = max(tr, key=lambda x: x[1])
        trend_desc = f"近半年（{months[0]}–{months[-1]}）累计 {total6} 条，其中 {peak_m} 最为集中（{peak_v} 条）"
    else:
        trend_desc = "时间序列数据尚不充分"
    keys = stats['latest']
    key_txt = '；'.join(f"{k['country']}《{clean_title(k['title'])}》" for k in keys[:2]) or '—'
    return (
        f"截至生成时，平台累计收录外商来华动态 {stats['total']} 条（投资 {stats['inv']} / 考察经贸 {stats['ex']}），"
        f"覆盖来源国家与地区 {stats['countries']} 个；其中江苏相关 {stats['js']} 条、南京相关 {stats['nj']} 条。\n"
        f"来源结构上，{join_labels(stats['top_countries'])} 为外资主力；行业上 {join_labels(stats['top_industries'])} 热度居前。"
        f"{trend_desc}。\n"
        f"重点动向：{key_txt}。\n"
        f"研判建议：南京应紧盯头部跨国企业在 {stats['hot_ind']} 领域的增资扩产节奏，借力进博会、投洽会等高能级平台开展精准招商，"
        f"并关注 {stats['top_countries'][0][0] if stats['top_countries'] else '欧美'} 资本在产业链关键环节的布局。"
    )


def compose_investment(stats):
    keys = stats['latest']
    proj = '；'.join(f"{k['country']}《{clean_title(k['title'], 22)}》" for k in keys[:3]) or '—'
    return (
        f"外商来华投资类动态 {stats['inv']} 条，来源以 {join_labels(stats['top_countries'])} 为主，"
        f"{join_labels(stats['top_industries'])} 为最活跃赛道。\n"
        f"近期标志性项目：{proj}。\n"
        f"研判建议：南京宜聚焦 {stats['top_industries'][0][0] if stats['top_industries'] else '人工智能(软件)'}、"
        f"{stats['top_industries'][1][0] if len(stats['top_industries']) > 1 else '生物医药'} 两条主攻赛道，"
        f"围绕已在华布局的头部企业推动其在宁设立研发或区域总部；对龙头采取“链主+配套”组合招商，提升项目体量与技术能级。"
    )


def compose_jiangsu(stats):
    return (
        f"江苏相关外资动态 {stats['js']} 条，覆盖 {len(stats['js_cities'])} 个设区市，南京 {stats['nj']} 条；"
        f"苏州以 {stats['sz']} 条领跑，南京在 {join_labels(stats['js_industries'], 2)} 上形成特色。\n"
        f"研判建议：南京应立足 {stats['js_industries'][0][0] if stats['js_industries'] else '智能制造装备'} 既有基础，"
        f"对标苏州在智能制造装备、生物医药的集群效应，补强薄弱环节；同时用好省级“塑造开放型经济新优势”等政策，争取外资研发中心落地。"
    )


def compose_exchange(stats):
    keys = stats['latest']
    ev = '；'.join(f"《{clean_title(k['title'])}》" for k in keys[:2]) or '—'
    return (
        f"来华考察·经贸交流 {stats['ex']} 条，以 {join_labels(stats['ex_countries'])} 来访为主，"
        f"活动类型集中于 {join_labels(stats['ex_types'], 2)}。\n"
        f"近期高规格活动：{ev}。\n"
        f"研判建议：南京应主动承接进博会、世界制造业大会等溢出效应，办好自有经贸活动提升国际能见度；"
        f"针对重点国别商会、驻华机构开展点对点邀约，把“考察热度”转化为“落地项目”。"
    )


INDUSTRIES = ['人工智能(软件)', '机器人', '生物医药', '新一代信息通信']
IND_REF = {
    '人工智能(软件)': ['英伟达', '微软', '亚马逊'],
    '机器人': ['ABB', '库卡', '发那科', '安川'],
    '生物医药': ['阿斯利康', '诺华', '礼来', '罗氏', '赛诺菲'],
    '新一代信息通信': ['高通', '爱立信', '诺基亚', '三星'],
}


def industry_stats(d, name):
    items = [i for i in d.get('items', []) if i.get('industry') == name]
    inv = sum(1 for i in items if i.get('category') == 'investment')
    js = [i for i in items if i.get('is_jiangsu')]
    return {
        'n': len(items), 'inv': inv, 'ex': len(items) - inv,
        'countries': topn(items, 'country', 3),
        'js_cities': topn(js, 'city', 3),
    }


def compose_industry(name, st):
    mncs = '、'.join(IND_REF.get(name, []))
    return (
        f"{name}方向累计收录相关外资动态 {st['n']} 条（投资 {st['inv']} / 考察经贸 {st['ex']}），"
        f"来源以{join_labels(st['countries'])}为主。头部企业 {mncs} 持续在华布局研发与产能。\n"
        f"研判建议：南京应围绕 {name} 产业链关键环节，依托紫金山实验室、麒麟科创园等载体，"
        f"争取上述头部企业在宁设立研发中心或联合创新平台；聚焦“强链补链”，把跨国公司的技术溢出"
        f"转化为本地配套与产业生态，提升南京在 {name} 全国版图中的显示度。"
    )


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


def main():
    with open(os.path.join(HERE, 'data.json'), encoding='utf-8') as f:
        d = json.load(f)
    s = build_stats(d)
    out = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'overview': compose_overview(s),
        'investment': compose_investment(s),
        'jiangsu': compose_jiangsu(s),
        'exchange': compose_exchange(s),
    }
    industries = {}
    for name in INDUSTRIES:
        industries[name] = compose_industry(name, industry_stats(d, name))
    out['industries'] = industries
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
