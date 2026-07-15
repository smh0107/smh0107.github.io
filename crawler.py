# -*- coding: utf-8 -*-
"""
crawler.py —— 外商来华投资动态 自动抓取与分类（生产级，免费源）
====================================================================
数据源（均免费、无需密钥）：
  1) Google News RSS ：中文查询直接返回中文标题，覆盖中外媒体，最贴合“全中文”要求
  2) GDELT DOC 2.0 API ：全球新闻事件库，作为国际视角补充（仅保留中文源条目）

输出：
  data.json —— 与 build_data.py 完全相同的结构，前端直接读取
  （item 字段：id/title/summary/url/source/country/industry/event_type/
   category/region/province/city/date/is_jiangsu/is_nanjing/image）

分类：
  国家（country）、行业（南京“1+4+6”攻坚办 10 类）、活动类型
  （投资落地/增资扩产/地区总部/研发中心/考察调研/经贸洽谈/参展参会/论坛活动）、
  江苏与南京标记（is_jiangsu / is_nanjing）。

合并策略：
  每次运行仅刷新“动态”（items）；政策文件（policies）由人工维护，
  爬虫会原样保留旧 data.json 中的 policies，不覆盖。

用法：
  python crawler.py                # 默认每源取 10 条（全国 100+ 检索式，去重后通常 300~500 条）
  python crawler.py --max 15     # 每源取 15 条（更全，但更慢、请求更多）
  python crawler.py --no-gdelt   # 仅用 Google News，不用 GDELT

覆盖范围（确保“全面”）：
  · 全国 34 个省级行政区，每个省分别检索“投资落地”与“考察经贸”两类；
  · 南京“1+4+6”攻坚办 10 类产业全国检索；
  · 主要来源国（美/德/日/韩/法/英/瑞/荷/新/沙特）分别检索；
  · 进博会 / 投洽会 / 服贸会 / 跨国公司地方行 等重大经贸活动。
  每次运行结果会与历史数据合并：保留已有条目的优质摘要，丢弃 120 天前的旧条目，上限 500 条。

【重要】为什么必须在本机/可出网服务器运行（不能在 CloudStudio 沙箱跑）：
  · 本脚本依赖访问 Google News / GDELT，部署用的 CloudStudio 免费沙箱出网受限且会休眠/回收，
    无法稳定执行定时抓取；因此“每 3 小时自动更新”请在你方可出网的服务器（或本机）上部署。
  · 真·每 3 小时更新 = 在本机/服务器放本脚本 + 定时任务，并把生成的 data.json/data.js 同步到网站目录。

定时（每 3 小时，在你方可出网的服务器/本机上）：
  Linux  : (crontab -e)  0 */3 * * *  cd /path/to/site && /usr/bin/python3 crawler.py >>crawl.log 2>&1
  Windows: 任务计划程序，触发器“每隔 3 小时”，操作运行 python crawler.py
  生成后把 data.json / data.js 覆盖到网站目录即可（前端会自动读取最新数据）。
====================================================================
"""
import argparse, datetime, hashlib, json, os, re, ssl, sys, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "data.json")

# 南京“1+4+6”攻坚办 10 类产业（顺序与前端一致）
INDUSTRIES = [
    "人工智能(软件)", "机器人", "生物医药", "新一代信息通信", "智能电网",
    "智能制造装备", "新材料", "智能网联新能源汽车", "集成电路", "低空经济(航空航天)"
]

# 全部 34 个省级行政区（简称，用于构建“全国覆盖”检索式）
PROV_SHORTCUTS = [
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "上海", "江苏",
    "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "广西", "海南",
    "重庆", "四川", "贵州", "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    "台湾", "香港", "澳门",
]

# Google News RSS 中文查询（全国各省 × 投资/考察 + 10 行业 + 主要来源国 + 重大经贸活动）
# 目标：每次运行都能覆盖到全国各省份、各行业、各来源国，避免“偏江苏/偏少数城市”。
def _build_google_queries():
    q = []
    # 1) 每个省份：投资落地类 + 考察经贸类 各一条
    for p in PROV_SHORTCUTS:
        q.append(f"{p} 外资 投资 项目 签约 落地")
        q.append(f"{p} 外商 考察 经贸 交流 活动")
    # 2) 每个行业（南京“1+4+6”攻坚办 10 类）全国检索
    for ind in INDUSTRIES:
        q.append(f"{ind} 外资 中国 投资 项目 落地")
    # 3) 主要来源国（与前端“来源”维度一致）
    for c in ["美国", "德国", "日本", "韩国", "法国", "英国", "瑞士", "荷兰", "新加坡", "沙特"]:
        q.append(f"{c} 企业 中国 投资 项目 落地")
    # 4) 重大经贸活动（全国级，常年有增量）
    q += [
        "进博会 外资 参展 签约 项目",
        "投洽会 外资 签约 项目 落地",
        "服贸会 外资 合作 项目",
        "跨国公司 地方行 外资 考察 签约",
    ]
    return q

GOOGLE_QUERIES = _build_google_queries()

GDELT_QUERIES = [
    '(foreign investment China)',
    '("invest" China multinational)',
    '(China International Import Expo foreign)',
    '(foreign company invest Sichuan OR Chongqing OR Hubei OR Henan)',
    '(German OR Japanese OR Korean firm invest China factory)',
]

# 国家/地区关键词
COUNTRY_KW = {
    "美国": ["美国", "美企", "华盛顿", "苹果", "特斯拉", "礼来", "微软", "谷歌", "亚马逊"],
    "德国": ["德国", "德企", "宝马", "大众", "巴斯夫", "西门子", "博世", "舍弗勒", "采埃孚", "默克"],
    "法国": ["法国", "法企", "施耐德", "圣戈班", "埃顿", "赛诺菲"],
    "英国": ["英国", "英企", "阿斯利康", "渣打", "汇丰"],
    "日本": ["日本", "日企", "松下", "丰田", "软银", "三菱"],
    "韩国": ["韩国", "韩企", "三星", "SK", "STI", "现代"],
    "荷兰": ["荷兰", "飞利浦", "阿斯麦", "壳牌"],
    "瑞士": ["瑞士", "ABB", "罗氏", "诺华", "雀巢", "海克斯康"],
    "瑞典": ["瑞典", "宜家", "海克斯康", "爱立信"],
    "比利时": ["比利时", "迈来芯", "J&K", "嘉顿"],
    "意大利": ["意大利", "布雷博", "普拉达"],
    "丹麦": ["丹麦", "诺和诺德", "马士基", "嘉士伯"],
    "加拿大": ["加拿大", "姚氏", "庞巴迪"],
    "波兰": ["波兰"],
    "西班牙": ["西班牙", "桑坦德"],
    "新加坡": ["新加坡", "淡马锡"],
    "中国台湾": ["台资", "台湾", "沪士", "台积电", "富士康"],
    "中国香港": ["港资", "香港"],
}

# 行业关键词 -> 10 类
INDUSTRY_KW = {
    "人工智能(软件)": ["人工智能", "AI", "软件", "算法", "大模型", "数据中心", "算力", "信息技术", "智能体"],
    "机器人": ["机器人", "具身智能", "人形机器人", "工业机器人", "智能装备机器人"],
    "生物医药": ["生物", "医药", "制药", "药品", "医疗", "健康", "基因", "疫苗", "创新药", "诊断", "康护", "生命科学", "医疗器械"],
    "新一代信息通信": ["通信", "5G", "6G", "半导体材料", "光通信", "基板", "PCB", "芯片配套", "信息通信", "服务器"],
    "智能电网": ["智能电网", "电网", "光储", "储能", "电力", "零碳", "新能源电力"],
    "智能制造装备": ["智能制造", "装备制造", "装备", "工厂", "制造基地", "产线", "自动化", "生产基", "产业园"],
    "新材料": ["新材料", "化工", "材料", "陶瓷", "基板材料", "涂层"],
    "智能网联新能源汽车": ["汽车", "新能源", "电动车", "整车", "电池", "智能网联", "车规", "车载"],
    "集成电路": ["集成电路", "芯片", "半导体", "晶圆", "封测", "功率半导体", "微电子", "真空泵"],
    "低空经济(航空航天)": ["低空", "无人机", "航空航天", "飞行器", "航空"],
}

# 投资类 / 交流类 关键词
INVEST_KW = ["签约", "投产", "开工", "落地", "投资", "建设", "设立", "总部", "研发中心", "基地", "扩产", "增资", "新设", "入驻", "启用", "竣工"]
EXCHANGE_KW = ["考察", "调研", "访问", "访华", "论坛", "洽谈", "参展", "参会", "博览会", "对接", "交流", "地方行", "行", "见面", "会见"]

# 省市地理映射（覆盖全部 34 个省级行政区，南京优先；用于把抓取到的动态归属到省/市）
PROVINCE_CITY = [
    ("南京市", "江苏省", ["南京", "建邺", "江宁", "高淳", "江北", "玄武", "鼓楼"]),
    ("苏州市", "江苏省", ["苏州", "昆山", "太仓", "吴中", "工业园区"]),
    ("无锡市", "江苏省", ["无锡"]),
    ("常州市", "江苏省", ["常州"]),
    ("南通市", "江苏省", ["南通"]),
    ("镇江市", "江苏省", ["镇江", "扬中"]),
    ("徐州市", "江苏省", ["徐州"]),
    ("扬州市", "江苏省", ["扬州"]),
    ("盐城市", "江苏省", ["盐城"]),
    ("泰州市", "江苏省", ["泰州"]),
    ("连云港市", "江苏省", ["连云港"]),
    ("淮安市", "江苏省", ["淮安"]),
    ("宿迁市", "江苏省", ["宿迁"]),
    ("上海市", "上海市", ["上海"]),
    ("北京市", "北京市", ["北京"]),
    ("天津市", "天津市", ["天津"]),
    ("重庆市", "重庆市", ["重庆"]),
    ("广州市", "广东省", ["广州", "黄埔", "白云"]),
    ("深圳市", "广东省", ["深圳"]),
    ("珠海市", "广东省", ["珠海", "佛山", "东莞", "中山"]),
    ("东莞市", "广东省", ["东莞"]),
    ("杭州市", "浙江省", ["杭州"]),
    ("宁波市", "浙江省", ["宁波"]),
    ("嘉兴市", "浙江省", ["嘉兴"]),
    ("温州市", "浙江省", ["温州"]),
    ("绍兴市", "浙江省", ["绍兴"]),
    ("合肥市", "安徽省", ["合肥"]),
    ("芜湖市", "安徽省", ["芜湖"]),
    ("厦门市", "福建省", ["厦门"]),
    ("福州市", "福建省", ["福州"]),
    ("泉州市", "福建省", ["泉州"]),
    ("南昌市", "江西省", ["南昌"]),
    ("赣州市", "江西省", ["赣州", "江西"]),
    ("济南市", "山东省", ["济南"]),
    ("青岛市", "山东省", ["青岛"]),
    ("烟台市", "山东省", ["烟台"]),
    ("郑州市", "河南省", ["郑州", "河南"]),
    ("武汉市", "湖北省", ["武汉", "湖北"]),
    ("长沙市", "湖南省", ["长沙", "湖南"]),
    ("成都市", "四川省", ["成都", "四川"]),
    ("西安市", "陕西省", ["西安", "陕西"]),
    ("沈阳市", "辽宁省", ["沈阳", "辽宁"]),
    ("大连市", "辽宁省", ["大连"]),
    ("盘锦市", "辽宁省", ["盘锦"]),
    ("长春市", "吉林省", ["长春", "吉林"]),
    ("哈尔滨市", "黑龙江省", ["哈尔滨", "黑龙江"]),
    ("石家庄市", "河北省", ["石家庄", "河北"]),
    ("太原市", "山西省", ["太原", "山西"]),
    ("呼和浩特市", "内蒙古自治区", ["内蒙古", "呼和浩特"]),
    ("南宁市", "广西壮族自治区", ["南宁", "广西"]),
    ("海口市", "海南省", ["海口", "海南"]),
    ("贵阳市", "贵州省", ["贵阳", "贵州"]),
    ("昆明市", "云南省", ["昆明", "云南"]),
    ("兰州市", "甘肃省", ["兰州", "甘肃"]),
    ("西宁市", "青海省", ["西宁", "青海"]),
    ("银川市", "宁夏回族自治区", ["银川", "宁夏"]),
    ("乌鲁木齐市", "新疆维吾尔自治区", ["乌鲁木齐", "新疆"]),
    ("拉萨市", "西藏自治区", ["拉萨", "西藏"]),
    ("台北市", "中国台湾", ["台湾", "台北", "台资", "台商"]),
    ("香港", "中国香港", ["香港", "港资"]),
    ("澳门", "中国澳门", ["澳门"]),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FDI-Crawler/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def has_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


def resolve_redirect(url, timeout=10):
    """跟随 Google News 中转链接，拿到原文真实地址。

    用户要求“每一条都能链接到原文”，Google News 的 RSS 链接是中转页，
    点开会跳转到真实报道；这里主动解析出真实 url，既满足“原文链接”，
    也为头图(og:image)提取提供可用地址。解析失败则回退原链接（仍可达原文）。
    """
    if not url or "news.google.com" not in url:
        return url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FDI-Crawler/1.0)"})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.geturl()
    except Exception:
        return url


def extract_image(url, timeout=8):
    """尽力提取文章头图（og:image / twitter:image），用于前端轮播；失败返回空字符串。"""
    if not url or "news.google.com" in url:
        return ""  # Google News 跳转链接无法直接取到原文图
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FDI-Crawler/1.0)"})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            html = r.read(200000).decode("utf-8", "replace")
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def parse_google_news(query, max_n):
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    try:
        xml = fetch(url)
    except Exception as e:
        print(f"  [Google] 查询失败 {query!r}: {e}")
        return []
    out = []
    try:
        root = ET.fromstring(xml)
    except Exception:
        return []
    for it in root.findall(".//item")[:max_n]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src_el = it.find("{*}source") or it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        pub = (it.findtext("pubDate") or "").strip()
        date = ""
        if pub:
            try:
                date = datetime.datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d")
            except Exception:
                pass
        if title and link:
            # Google News 标题常为“正文 - 来源”，拆出更干净的标题与来源
            clean_title, clean_src = title, source
            if " - " in title:
                head, _, tail = title.rpartition(" - ")
                if 0 < len(tail) <= 30 and not head.endswith("]"):
                    clean_title, clean_src = head.strip(), (tail.strip() or source)
            out.append({"title": clean_title, "url": link, "source": clean_src or "网络媒体", "date": date})
    return out


def parse_gdelt(query, max_n):
    params = urllib.parse.urlencode({
        "query": query, "mode": "ArtList", "maxrecords": str(max_n),
        "format": "json", "sort": "datedesc"
    })
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + params
    try:
        raw = fetch(url)
        data = json.loads(raw)
    except Exception as e:
        print(f"  [GDELT] 查询失败 {query!r}: {e}")
        return []
    out = []
    for a in data.get("articles", [])[:max_n]:
        title = (a.get("title") or "").strip()
        link = (a.get("url") or "").strip()
        domain = (a.get("domain") or "").strip()
        seendate = a.get("seendate") or ""
        date = seendate[:10] if len(seendate) >= 10 else ""
        # 仅保留中文源（标题含中文），保证“全中文”呈现
        if title and link and has_cjk(title):
            out.append({"title": title, "url": link, "source": domain or "GDELT", "date": date})
    return out


def classify(title, summary):
    text = f"{title} {summary}"

    # 国家
    country = "跨国企业"
    for c, kws in COUNTRY_KW.items():
        if any(k in text for k in kws):
            country = c
            break

    # 行业（取首个匹配；生物医药优先级略高以便医药类归位）
    industry = ""
    for ind in INDUSTRIES:
        kws = INDUSTRY_KW.get(ind, [])
        if any(k in text for k in kws):
            industry = ind
            break

    # 活动类型 + 大类
    is_inv = any(k in text for k in INVEST_KW)
    is_ex = any(k in text for k in EXCHANGE_KW)
    if is_inv and not is_ex:
        # 细分类型
        if any(k in text for k in ["研发中心", "研发机构", "研究院"]):
            event_type, category = "研发中心", "investment"
        elif any(k in text for k in ["总部"]):
            event_type, category = "地区总部", "investment"
        elif any(k in text for k in ["增资", "扩产", "利润再投资"]):
            event_type, category = "增资扩产", "investment"
        else:
            event_type, category = "投资落地", "investment"
    elif is_ex and not is_inv:
        if any(k in text for k in ["考察", "调研", "访问", "访华", "地方行"]):
            event_type, category = "考察调研", "exchange"
        elif any(k in text for k in ["论坛", "会见", "会"]):
            event_type, category = "论坛活动", "exchange"
        elif any(k in text for k in ["参展", "参会", "博览会", "对接"]):
            event_type, category = "参展参会", "exchange"
        else:
            event_type, category = "经贸洽谈", "exchange"
    else:
        # 两者皆有或都无，按是否有“投资/落地”倾向
        event_type, category = ("投资落地", "investment") if is_inv else ("经贸洽谈", "exchange")

    # 地区
    city, province, region = "", "", "全国"
    for c, p, kws in PROVINCE_CITY:
        if any(k in text for k in kws):
            city, province, region = c, p, p
            break

    is_jiangsu = province == "江苏省"
    is_nanjing = city == "南京市"
    return {
        "country": country, "industry": industry, "event_type": event_type,
        "category": category, "region": region, "province": province,
        "city": city, "is_jiangsu": is_jiangsu, "is_nanjing": is_nanjing
    }


def norm_title(t):
    return re.sub(r"\s+", "", t or "").lower()


def run(max_n, use_gdelt):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 开始抓取…")
    raw = []
    for q in GOOGLE_QUERIES:
        items = parse_google_news(q, max_n)
        print(f"  Google << {q!r}: {len(items)} 条")
        raw.extend(items)
        time.sleep(0.2)  # 礼貌延时，避免被源站限流
    if use_gdelt:
        for q in GDELT_QUERIES:
            items = parse_gdelt(q, max_n)
            print(f"  GDELT << {q!r}: {len(items)} 条")
            raw.extend(items)
            time.sleep(0.2)

    # 去重（按标题归一）
    seen = {}
    unique = []
    for it in raw:
        k = norm_title(it["title"])
        if not k or k in seen:
            continue
        seen[k] = True
        unique.append(it)

    # 分类 + 解析原文真实 url + 头图（前 60 条尽力取真实地址与头图）
    fresh = []
    for i, it in enumerate(unique, 1):
        meta = classify(it["title"], "")
        real_url = it["url"]
        image = ""
        if i <= 60:
            real_url = resolve_redirect(it["url"])
            image = extract_image(real_url)
        fresh.append({
            "id": "auto_" + hashlib.md5(real_url.encode("utf-8")).hexdigest()[:10],
            "title": it["title"],
            "summary": it["title"],   # RSS 不提供摘要时以标题兜底（真实、可链接原文）
            "url": real_url,
            "source": it["source"] or "网络媒体",
            "date": it["date"] or datetime.datetime.now().strftime("%Y-%m-%d"),
            "image": image,
            **meta
        })

    # 与历史数据合并：保留旧条目中更丰富的摘要；丢弃 120 天前的旧条目以保持“新鲜”；上限 500 条。
    # 这样既能叠加本次全国级广度，又不丢失此前人工/历史整理的高质量条目。
    policies = []
    old_items = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_items = old.get("items", [])
            policies = old.get("policies", [])
            print(f"  保留政策文件 {len(policies)} 条（人工维护，不覆盖）")
        except Exception:
            pass

    seen_urls = {n["url"] for n in fresh}
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
    merged = list(fresh)
    kept_old = 0
    for o in old_items:
        if o.get("url") in seen_urls:
            continue  # 本次已抓到同链接，用新的（带真实 url/图）
        if (o.get("date") or "") < cutoff:
            continue  # 过期旧条目丢弃
        merged.append(o)
        seen_urls.add(o["url"])
        kept_old += 1
    print(f"  合并历史条目 {kept_old} 条（保留优质摘要），本次新增 {len(fresh)} 条")

    merged.sort(key=lambda x: x["date"], reverse=True)
    if len(merged) > 500:
        merged = merged[:500]

    data = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "industries": INDUSTRIES,
        "items": merged,
        "policies": policies,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 同时生成 data.js，供本地双击打开(file://)时正常加载
    js_path = os.path.join(HERE, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("/* 自动生成，请勿手改。由 crawler.py 生成。*/\n")
        f.write("window.DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"  已生成 data.js（本地双击打开可用）")
    print(f"  完成：动态 {len(merged)} 条（投资 {sum(1 for x in merged if x['category']=='investment')} / "
          f"考察经贸 {sum(1 for x in merged if x['category']=='exchange')}），"
          f"江苏相关 {sum(1 for x in merged if x['is_jiangsu'])} 条 → {DATA_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10, help="每个查询抓取条数")
    ap.add_argument("--no-gdelt", action="store_true", help="不使用 GDELT 源")
    args = ap.parse_args()
    run(args.max, not args.no_gdelt)
