# -*- coding: utf-8 -*-
"""
build_data.py —— 生成外商来华投资动态数据集 data.json
本脚本把经检索核实的真实新闻/政策条目结构化为规范 JSON。
生产环境下由 crawler.py 自动抓取并生成同样结构的数据（字段一致）。
所有文本均为中文，每条均带可点击的互联网原文 url。
"""
import json, datetime, os, re

def norm_title(s):
    return re.sub(r"\s+", "", (s or "")).lower()

# 南京“1+4+6”攻坚办产业口径（10 类）
INDUSTRIES = [
    "人工智能(软件)", "机器人", "生物医药", "新一代信息通信", "智能电网",
    "智能制造装备", "新材料", "智能网联新能源汽车", "集成电路", "低空经济(航空航天)"
]

# 分类字典：event_type -> 大类的 category
INVEST_TYPES = {"投资落地", "增资扩产", "地区总部", "研发中心"}
EXCHANGE_TYPES = {"考察调研", "经贸洽谈", "参展参会", "论坛活动"}

# 原始条目（不写 is_jiangsu / is_nanjing，由脚本按 city/province 自动补全）
# 字段: title, summary, url, source, country, industry, event_type, region, province, city, date
RAW_ITEMS = [
    # ---------- 投资落地（全国含江苏）----------
    dict(title="巴斯夫（广东）一体化基地正式投产", summary="德国巴斯夫全球最大单笔投资项目、总投资约87亿欧元的湛江一体化基地正式投产，是其在华投资规模最大的独资单体项目。", url="https://www.cs.com.cn/xwzx/01/2026/04/03/detail_2026040310001192.html", source="中国证券报", country="德国", industry="新材料", event_type="投资落地", region="广东省", province="广东省", city="湛江市", date="2026-03-26"),
    dict(title="添康集团亚太区添康康护项目破土动工", summary="总投资2500万美元的添康康护项目在浙江嘉兴经开区破土动工，规划生产车间、研发中心及配套设施，建设周期约15个月。", url="https://www.cs.com.cn/xwzx/01/2026/04/03/detail_2026040310001192.html", source="中国证券报", country="跨国企业", industry="生物医药", event_type="投资落地", region="浙江省", province="浙江省", city="嘉兴市", date="2026-03-20"),
    dict(title="礼来计划未来十年在华投资30亿美元", summary="礼来公司宣布未来十年在华投资30亿美元扩大生产，深度融入中国医药创新生态，彰显跨国药企长期深耕信心。", url="https://www.ciie.org/zbh/bqxwbd/20260408/58821.html", source="中国国际进口博览局", country="美国", industry="生物医药", event_type="投资落地", region="全国", province="", city="", date="2026-04-08"),
    dict(title="诺和诺德宣布扩建广州生产基地", summary="诺和诺德宣布扩建广州生产基地，持续加码中国生物医药与健康管理业务，融入本地创新生态。", url="https://www.ciie.org/zbh/bqxwbd/20260408/58821.html", source="中国国际进口博览局", country="丹麦", industry="生物医药", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-04-08"),
    dict(title="施耐德电气新建厦门、无锡两座工厂并升级北京研发中心", summary="法国施耐德电气宣布新建厦门、无锡两座工厂并升级北京研发中心，深化在华本土制造与研发布局。", url="https://www.ciie.org/zbh/bqxwbd/20260408/58821.html", source="中国国际进口博览局", country="法国", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="无锡市", date="2026-04-08"),
    dict(title="罗氏诊断苏州工业园新建项目投资30亿元", summary="罗氏诊断在苏州工业园新建项目投资30亿元，预计2028年建成投产，是其在华扩大本地化生产的重要布局。", url="https://news.cctv.com/2026/03/19/ARTIsqd3olxNn8Xbd4VmCg0L260319.shtml", source="央视网", country="瑞士", industry="生物医药", event_type="投资落地", region="江苏省", province="江苏省", city="苏州市", date="2026-03-19"),
    dict(title="新一批标志性重大外资项目总投资达134亿美元", summary="国家发改委推出新一批13个标志性重大外资项目，总投资134亿美元，聚焦电子制造、高端化工、新能源汽车等技术密集领域。", url="https://news.cctv.com/2026/03/19/ARTIsqd3olxNn8Xbd4VmCg0L260319.shtml", source="央视网", country="多国", industry="", event_type="投资落地", region="全国", province="", city="", date="2026-03-19"),
    dict(title="阿斯利康在黄埔建设放射性偶联药物（RDC）生产供应基地", summary="阿斯利康宣布在广州黄埔建设RDC生产供应基地，聚焦前列腺癌等恶性肿瘤精准治疗，加码大湾区生物医药布局。", url="https://www.gz.gov.cn/ysgz/xwdt/ysdt/content/post_10788903.html", source="广州市政府", country="英国", industry="生物医药", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-02-01"),
    dict(title="松下机电扩建多层基板材料MEGTRON新生产线", summary="松下机电投资约75亿日元在广州扩建多层基板材料MEGTRON新生产线，服务AI与高速通信需求，计划2027年4月投产。", url="https://www.gz.gov.cn/ysgz/xwdt/ysdt/content/post_10788903.html", source="广州市政府", country="日本", industry="新一代信息通信", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-02-01"),
    dict(title="德国莱茵TÜV投资1.5亿元建设大湾区运营中心", summary="德国莱茵TÜV投资1.5亿元在广州建设大湾区运营中心，规划覆盖新能源汽车、机器人、低空飞行器等领域的20个综合实验室。", url="https://www.gz.gov.cn/ysgz/xwdt/ysdt/content/post_10788903.html", source="广州市政府", country="德国", industry="智能制造装备", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-02-01"),
    dict(title="大众汽车德国以外首个全流程研发测试中心在合肥落成", summary="大众汽车德国以外首个全流程研发测试中心在安徽合肥落成，强化其在中国市场的本土研发与测试能力。", url="https://www.ciie.org/zbh/bqxwbd/20260408/58821.html", source="中国国际进口博览局", country="德国", industry="智能网联新能源汽车", event_type="投资落地", region="安徽省", province="安徽省", city="合肥市", date="2026-04-08"),
    dict(title="埃地沃兹在青岛落地半导体真空泵中国研发中心", summary="全球半导体真空泵领域企业埃地沃兹在青岛高新区落地中国研发中心，未来3年投入约8000万元攻关关键技术。", url="http://bofcom.qingdao.gov.cn/zwgk_59/bmdt_59/202605/t20260529_10620441.shtml", source="青岛市商务局", country="英国", industry="集成电路", event_type="研发中心", region="山东省", province="山东省", city="青岛市", date="2026-05-29"),
    dict(title="海克斯康将青岛总部升级为亚洲产品制造中心", summary="工业测量巨头海克斯康将大中华区总部设在青岛，并规划升级为亚洲产品制造中心，4月以14.5亿美元收购无损检测龙头。", url="http://bofcom.qingdao.gov.cn/zwgk_59/bmdt_59/202605/t20260529_10620441.shtml", source="青岛市商务局", country="瑞典", industry="智能制造装备", event_type="地区总部", region="山东省", province="山东省", city="青岛市", date="2026-04-01"),
    dict(title="阿斯利康连续三年追加投资青岛基地至8.86亿美元", summary="全球制药巨头阿斯利康自2023年落户青岛以来连续三年追加投资，总额从4.5亿美元翻倍至8.86亿美元，二期提前竣工。", url="http://bofcom.qingdao.gov.cn/zwgk_59/bmdt_59/202605/t20260529_10620441.shtml", source="青岛市商务局", country="英国", industry="生物医药", event_type="增资扩产", region="山东省", province="山东省", city="青岛市", date="2026-03-15"),
    dict(title="朗盛启动青岛生产基地扩产升级", summary="德国化工巨头朗盛启动青岛生产基地扩产升级，总产能从每年2.5万吨增至3万吨，为5年来全球最大一笔投资。", url="http://bofcom.qingdao.gov.cn/zwgk_59/bmdt_59/202605/t20260529_10620441.shtml", source="青岛市商务局", country="德国", industry="新材料", event_type="增资扩产", region="山东省", province="山东省", city="青岛市", date="2025-11-01"),
    dict(title="比利时J&K集团高淳亚洲总部项目即将投产", summary="比利时J&K集团在南京高淳投资约4500万美元建设亚洲总部，承担研发、生产、销售、服务全产业链职能，预计7月全面投产。", url="https://www.toutiao.com/article/7639914427483587072/", source="高淳发布", country="比利时", industry="智能制造装备", event_type="地区总部", region="江苏省", province="江苏省", city="南京市", date="2026-05-15"),
    dict(title="波兰食品配料集团江宁亚太总部及研发生产基地破土动工", summary="波兰食品配料集团在南京江宁空港片区建设亚太总部及研发生产基地，打造“研发+生产+亚太总部”三位一体战略支点。", url="https://i.ifeng.com/c/8rjICAfyrN4", source="凤凰网", country="波兰", industry="生物医药", event_type="地区总部", region="江苏省", province="江苏省", city="南京市", date="2026-03-23"),
    dict(title="意大利布雷博南京公司获评省级研发中心并认定为省跨国公司地区总部", summary="制动解决方案供应商布雷博中国区研发中心获评省级研发中心，在宁公司成功认定为江苏省跨国公司地区总部。", url="https://m.sohu.com/a/990067012_121388342", source="搜狐", country="意大利", industry="智能制造装备", event_type="研发中心", region="江苏省", province="江苏省", city="南京市", date="2026-03-01"),
    dict(title="宝马全球信息技术研发中心落地南京建邺", summary="宝马全球信息技术研发中心落地南京建邺，与阿里中心、小米南京科技园等共同构筑河西中央科创区创新桥头堡。", url="https://big5.china.com.cn/gate/big5/bjtime.china.com.cn/2026-01/20/content_43338544.html", source="中国网", country="德国", industry="人工智能(软件)", event_type="研发中心", region="江苏省", province="江苏省", city="南京市", date="2026-01-20"),
    dict(title="ABB与江苏海航电气合作“AI+光储直柔”零碳示范园区在扬中投产", summary="ABB与江苏海航电气合作的“AI+光储直柔”零碳示范园区在江苏扬中投产，融合人工智能与智能电网技术。", url="https://www.ciie.org/zbh/bqxwbd/20260408/58821.html", source="中国国际进口博览局", country="瑞士", industry="智能电网", event_type="投资落地", region="江苏省", province="江苏省", city="镇江市", date="2026-04-08"),
    dict(title="法国埃顿集团两个“总部级”项目落户无锡", summary="法国埃顿集团与无锡高新区签下两份协议：外商独资工业产业园REITs中国总部与城市级物理AI和机器人创新平台双双落子。", url="https://www.sohu.com/a/1036619989_122014422", source="无锡日报", country="法国", industry="机器人", event_type="地区总部", region="江苏省", province="江苏省", city="无锡市", date="2026-06-15"),
    dict(title="西门子Xcelerator中国产业生态中心暨大湾区工业AI创新基地筹建", summary="西门子将在深圳筹建在华首个数字平台产业基地——Xcelerator中国产业生态中心暨大湾区工业AI创新基地，推动机器人生态合作。", url="https://www.toutiao.com/article/7647093926079349298/", source="今日头条", country="德国", industry="人工智能(软件)", event_type="研发中心", region="广东省", province="广东省", city="深圳市", date="2026-04-01"),
    dict(title="博银合创具身智能机器人基地签约落户苏州工业园区", summary="博世旗下博原资本与银河通用合资成立博银合创，投资10亿元在苏州建设企业总部及工业具身智能机器人研发产业化基地。", url="https://www.163.com/dy/article/KPJ4IH7V0519D45U.html", source="网易", country="德国", industry="机器人", event_type="投资落地", region="江苏省", province="江苏省", city="苏州市", date="2026-04-03"),
    dict(title="德国舍弗勒成立具身智能机器人公司落子太仓", summary="德资巨头舍弗勒在太仓成立具身智能机器人公司，专注人形机器人核心零部件与子系统研发生产，融合数字孪生与AI大模型。", url="https://caifuhao.eastmoney.com/news/20260301131828393916560", source="东方财富", country="德国", industry="机器人", event_type="投资落地", region="江苏省", province="江苏省", city="苏州市", date="2026-02-27"),
    dict(title="韩国STI株式会社功率半导体智造基地落地广州白云", summary="韩国STI株式会社在广州白云投资约124亿元建设功率半导体智造基地，生产AMB陶瓷基板等关键材料，预计年底投产。", url="https://www.thepaper.cn/newsDetail_forward_32574968", source="澎湃新闻", country="韩国", industry="集成电路", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-02-10"),
    dict(title="比利时迈来芯集成电路上海独资公司落地黄浦并布局机器人", summary="比利时微电子工程公司迈来芯在上海黄浦成立独资企业，落地中国战略升级，并成立中国机器人团队拓展新兴领域。", url="https://m.jfdaily.com/sgh/detail?id=1719822", source="解放日报", country="比利时", industry="集成电路", event_type="地区总部", region="上海市", province="上海市", city="上海市", date="2026-03-12"),
    dict(title="沪士电子增资101亿元加码江苏昆山AI芯片配套PCB", summary="沪士电子在江苏昆山签约人工智能芯片配套高端印制线路板项目，整体投资101亿元，打造全球领先的高端PCB生产基地。", url="https://cj.sina.com.cn/article/norm_detail?url=https%3A%2F%2Ffinance.sina.com.cn%2Fjjxw%2F2026-04-08%2Fdoc-inhtttai9731161.shtml", source="新浪财经", country="中国台湾", industry="新一代信息通信", event_type="增资扩产", region="江苏省", province="江苏省", city="苏州市", date="2026-04-08"),

    # ---------- 港澳台外资动态（覆盖各模块）----------
    dict(title="台湾群懋昌智能装备3000万美元台资项目奠基昆山千灯", summary="台湾群昌塑胶在昆山千灯镇投资设立群懋昌智能装备科技，项目占地22.7亩，总投资3000万美元，主营高端服务器精密钣金、连接器精密构件及食品自动化包装产线。", url="https://www.ksrmtzx.com/news/detail/290551", source="昆山融媒体", country="中国台湾", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="苏州市", date="2026-07-07"),
    dict(title="台湾富甲电子新能源汽车零部件项目签约落户昆山千灯", summary="台湾Skyrock集团下属富甲电子（昆山）签约新能源汽车零部件电子产品生产基地，总投资3000万美元，主营铝锌镁精密压铸，前瞻布局机器人结构件及AI项目研发。", url="https://www.ks.gov.cn/kss/qzkx/202605/c3c8228642784c75a12e6cb4bbc5676c.shtml", source="昆山市政府", country="中国台湾", industry="智能网联新能源汽车", event_type="投资落地", region="江苏省", province="江苏省", city="苏州市", date="2026-05-06"),
    dict(title="新世界中国90万平方米新世界188號综合体落户深圳龙岗", summary="港资标杆企业新世界中国在大运深港国际科教城门户匠造约90万平方米超级综合体新世界188號，赋能深圳东部高质量发展与大湾区建设。", url="https://www.toutiao.com/article/7615103842119729707", source="今日头条", country="中国香港", industry="新一代信息通信", event_type="投资落地", region="广东省", province="广东省", city="深圳市", date="2026-03-14"),
    dict(title="横琴粤澳深度合作区澳资企业突破8000户", summary="截至2026年6月2日，横琴粤澳深度合作区实有澳资企业数量突破8000户，占合作区企业总数的15.9%，平均每6家企业中就有1家具有澳门基因。", url="https://news.cnr.cn/native/gd/20260604/t20260604_527648283.shtml", source="中国新闻网", country="中国澳门", industry="新一代信息通信", event_type="投资落地", region="广东省", province="广东省", city="珠海市", date="2026-06-04"),
    dict(title="广药国际拟投资10亿元在横琴打造医药智造中心", summary="广药国际拟在横琴投资10亿元打造医药智造中心，构建包括澳门生产基地、出口生产基地在内的六位一体综合平台，助力澳门建设一流医药国际化产业基地。", url="https://www.21jingji.com/article/20260521/herald/7edb8c4523a3f42d0baedf8012871180.html", source="21世纪经济报道", country="中国澳门", industry="生物医药", event_type="投资落地", region="广东省", province="广东省", city="珠海市", date="2026-01-15"),
    dict(title="香港投资推广署2026年上半年引资逾530亿港元", summary="香港投资推广署公布2026年上半年招商引资成绩，吸引投资超过530亿港元，行政长官李家超表示香港背靠祖国、联通世界优势持续吸引全球企业来港发展。", url="https://www.investhk.gov.hk/zh-cn/news/chief-executive-welcomes-enterprises-to-develop-in-hong-kong-as-investhk-attracts-over-53-billion-in-first-half-of-2026/", source="香港投资推广署", country="中国香港", industry="人工智能(软件)", event_type="投资落地", region="中国香港", province="中国香港", city="中国香港", date="2026-06-25"),
    dict(title="22家重点企业落户香港或扩展在港业务", summary="香港引进重点企业办公室举行签署仪式，欢迎22家重点企业落户香港或扩展业务，涵盖AI、智慧出行、生命健康科技、低空经济等领域，预计带来约730亿港元投资。", url="https://it.sohu.com/a/1012147116_115362", source="搜狐", country="中国香港", industry="人工智能(软件)", event_type="投资落地", region="中国香港", province="中国香港", city="中国香港", date="2026-04-20"),

    # ---------- 考察·经贸交流（全国含江苏）----------
    dict(title="跨国公司高管密集访华 项目扎根落地", summary="中国发展高层论坛、博鳌亚洲论坛上，苹果、礼来、巴斯夫、大众、博世等跨国公司全球负责人悉数到场，表达长期深耕信心。", url="https://www.toutiao.com/article/7622856650256351796", source="新华网", country="多国", industry="", event_type="论坛活动", region="全国", province="", city="", date="2026-03-30"),
    dict(title="外国政商界组团访华 拥抱开放创新的中国", summary="“十五五”开局之年全球政商界掀起密集访华热潮，30多位美企高管、大众CEO四周两度访华、韩国政府代表团试乘无人驾驶。", url="https://big5.china.com.cn/opinion2020/2026-03/25/content_118401627.shtml", source="中国网", country="多国", industry="", event_type="考察调研", region="全国", province="", city="", date="2026-03-25"),
    dict(title="“跨国公司助力高质量发展地方行——湘聚湖南”活动举办", summary="松下、花旗、陶氏化学、赛默飞世尔等跨国公司中国区负责人赴湘，与三一集团、广汽埃安等本地企业共话合作前景。", url="https://www.cpaffc.org.cn/index/news/detail/id/11057/lang/1.html", source="中国人民对外友好协会", country="多国", industry="", event_type="经贸洽谈", region="湖南省", province="湖南省", city="长沙市", date="2026-05-20"),
    dict(title="外资企业“江西行”在赣州对接成效显著", summary="中国贸促会率外资企业代表团来赣，通用电气、阿斯利康、百胜中国、施耐德等围绕原创新药、稀土钨材料达成合作共识。", url="http://www.ganxian.gov.cn/gxqxxgk/c111379/202604/23c78f265b0c48c390462686eb14188f.shtml", source="赣县区政府", country="多国", industry="", event_type="考察调研", region="江西省", province="江西省", city="赣州市", date="2026-04-14"),
    dict(title="跨国公司高管看好中国市场 多国实际对华投资增长", summary="今年前2个月加拿大、瑞士、法国实际对华投资分别增长210%、41.3%、3%，多家外国商会数据印证外资持续布局态度。", url="https://paper.people.com.cn/rmrbhwb/pc/attachement/202604/07/4605ad8a-c9c8-4eb3-b355-9f72c2867538.pdf", source="人民日报海外版", country="多国", industry="", event_type="论坛活动", region="全国", province="", city="", date="2026-04-07"),
    dict(title="近800家全球企业签约参展第九届进博会", summary="已有来自70多个国家和地区的近800家全球企业签约参展第九届进博会企业商业展，签约展览面积近28万平方米。", url="https://www.ciie.org/zbh/cn/2024/medium-item1/xinhua/20260423/58935.html", source="新华网", country="多国", industry="", event_type="参展参会", region="上海市", province="上海市", city="上海市", date="2026-04-23"),
    dict(title="2026年服贸会开幕倒计时60天 首批活动确定", summary="2026年服贸会将于9月9日至13日在首钢园举办，首批41场论坛会议、33场洽谈推介、23项配套活动已确定。", url="https://k.sina.com.cn/article_5953189932_162d6782c06704mfya.html?loc=39", source="新浪财经", country="多国", industry="", event_type="参展参会", region="北京市", province="北京市", city="北京市", date="2026-07-11"),
    dict(title="第26届中国国际投资贸易洽谈会将于2026年举办", summary="商务部明确2026年举办第26届投洽会，并与地方共同举办第14届中部博览会，打造中部崛起有效平台。", url="https://www.163.com/dy/article/KJPD87CU05199NPP.html", source="网易", country="多国", industry="", event_type="参展参会", region="福建省", province="福建省", city="厦门市", date="2026-06-20"),
    dict(title="第九届中国国际进口博览会将于2026年11月在上海举办", summary="第九届进博会将于11月5日至10日在上海国家会展中心举行，设六大展区及创新孵化专区，总展览面积超36万平方米。", url="https://belfast.china-consulate.gov.cn/sgdt/202604/t20260417_11894394.htm", source="中国驻贝尔法斯特总领馆", country="多国", industry="", event_type="参展参会", region="上海市", province="上海市", city="上海市", date="2026-04-17"),

    # ---------- 港澳台考察·经贸交流动态 ----------
    dict(title="第十七届津台投资合作洽谈会在天津开幕", summary="第十七届津台投资合作洽谈会开幕，两岸企业家峰会、国共两党及工商界代表出席，围绕产业链协同、新赛道培育等议题深化津台产业对接。", url="https://www.toutiao.com/article/7660434226629624355/", source="网信宁河", country="中国台湾", industry="", event_type="经贸洽谈", region="天津市", province="天津市", city="天津市", date="2026-07-08"),
    dict(title="2026年重点台企进贵州投资促进活动走进铜仁", summary="20余名台企代表赴贵州铜仁实地考察中医药、茶业、朱砂、特色食品等产业，共商合作路径，推动黔台产业深度融合。", url="https://szb.tongren.gov.cn/trrb/content/202604/13/content_75277.html", source="铜仁日报", country="中国台湾", industry="", event_type="考察调研", region="贵州省", province="贵州省", city="铜仁市", date="2026-04-09"),
    dict(title="港澳台侨企业与上海企业合作交流会在沪举行", summary="相聚上海·共创未来——港澳台侨企业与上海企业合作交流会在东方枢纽国际商务合作区举行，近百位港澳台侨企业代表与上海企业对接合作机遇。", url="https://www.ciie.org/zbh/cn/2024/medium-item1/other/20260316/57425.html", source="中国新闻网", country="中国台湾", industry="", event_type="经贸洽谈", region="上海市", province="上海市", city="上海市", date="2026-03-14"),
    dict(title="九八智汇·厦台科技创新与高端制造对接交流活动在厦门举办", summary="投洽会系列活动之厦台科技创新与高端制造对接交流在厦门举办，近百位台资企业及产业园区代表围绕半导体、智能制造、电子信息等寻求合作。", url="https://dzb.sunnews.cn/page/2026-04/09/A02/hxcb20260409A02.pdf", source="海峡导报", country="中国台湾", industry="", event_type="经贸洽谈", region="福建省", province="福建省", city="厦门市", date="2026-04-08"),

    # ---------- 江苏省其余地级市外资动态（补齐 13 市全覆盖）----------
    dict(title="莫朗绿色算力智能设备制造基地项目落子徐州云龙区", summary="外资项目莫朗（江苏）数字能源技术有限公司绿色算力智能设备制造基地落户徐州云龙区，总投资约21亿元，计划2026年四季度开工，建设厂房及办公楼。", url="https://dinggc.cbi360.net/project/4578312961839394816.html", source="采招网", country="跨国企业", industry="人工智能(软件)", event_type="投资落地", region="江苏省", province="江苏省", city="徐州市", date="2026-05-27"),
    dict(title="江苏艾思孚动力有限公司在邳州成立", summary="外商投资（非独资）企业江苏艾思孚动力有限公司在徐州邳州经济开发区注册成立，注册资本1000万元，主营液力及气压动力机械与元件制造。", url="https://mnews.tianyancha.com/ll_cbxbj7avwe.html", source="天眼查", country="跨国企业", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="徐州市", date="2026-02-13"),
    dict(title="日本TAKAKO在常州武进高新区设立全资运营总部", summary="全球液压精密零部件领军企业日本株式会社TAKAKO落子武进国家高新区，注册成立全资外资子公司高弘精密液压（常州）有限公司，打造中国区研发运营总部。", url="https://finance.sina.com.cn/wm/2026-06-24/doc-inieniee6359773.shtml", source="新浪财经", country="日本", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="常州市", date="2026-06-24"),
    dict(title="德国Cyber Technologies半导体3D检测设备项目签约常州高新区", summary="德国半导体精密检测知名企业Cyber Technologies投资超1亿元在常州高新区签约，设立中国首个生产基地，承接亚太市场业务，达产年销售额可达1500万欧元以上。", url="https://kczg.org.cn/zt530activity/newsDetail?id=6363792", source="常观", country="德国", industry="集成电路", event_type="投资落地", region="江苏省", province="江苏省", city="常州市", date="2026-04-01"),
    dict(title="德国德采实集团中国首个生产基地在常州高新区投产", summary="全球实验室离心机领域“隐形冠军”德国德采实集团将其中国首个生产基地落户常州高新区中瑞产业园二期并竣工投产，主攻Sigma系列实验室离心机本土化生产。", url="https://i.ifeng.com/c/8tpLzs0y4fo", source="凤凰网", country="德国", industry="生物医药", event_type="投资落地", region="江苏省", province="江苏省", city="常州市", date="2026-06-10"),
    dict(title="斯堪尼亚纯电重卡项目签约落户南通如皋", summary="瑞典商用车巨头斯堪尼亚纯电重卡项目签约落户如皋经济技术开发区，在南通绿色低碳发展方向下深化在华生产基地布局。", url="https://www.nantong.gov.cn/ntsrmzf/zwyw/content/8c1fea39-763d-42d6-ba9e-ebde742ae084.html", source="南通市政府", country="瑞典", industry="智能网联新能源汽车", event_type="投资落地", region="江苏省", province="江苏省", city="南通市", date="2026-05-20"),
    dict(title="意大利OMB高端阀门制造项目落户南通高新区", summary="全球石油天然气行业锻钢阀门制造商意大利OMB阀门集团高端阀门制造项目签约南通高新区，通过本地化生产销售至全球市场，预计10月投产。", url="https://www.tongzhou.gov.cn/tzzt/yshjgzdt/content/1aeb7dc6-4c66-4fcd-ae61-774e105e447a.html", source="通州日报", country="意大利", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="南通市", date="2026-06-18"),
    dict(title="中韩英日“四国五方”赣榆LNG接收站项目加速建设", summary="总投资约64亿元、由华电江苏、连云港港口集团与韩国SK、英国BP、日本JERA“四国五方”联合建设的赣榆液化天然气接收站项目稳步推进，外资占比约29%。", url="https://news.10jqka.com.cn/20260629/c677784494.shtml", source="同花顺", country="多国", industry="智能电网", event_type="投资落地", region="江苏省", province="江苏省", city="连云港市", date="2026-06-29"),
    dict(title="庆鼎精密电子在淮安投建110亿元高端PCB项目", summary="鹏鼎控股全资子公司庆鼎精密电子（淮安）有限公司与淮安经济技术开发区签署协议，投资110亿元建设高端PCB项目生产基地，完善区域电子信息产业链。", url="https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid=002938&id=12000776", source="新浪财经", country="中国台湾", industry="新一代信息通信", event_type="投资落地", region="江苏省", province="江苏省", city="淮安市", date="2026-03-17"),
    dict(title="韩国科伊塔5G应急电源项目落户盐城黄尖镇", summary="韩国科伊塔股份有限公司5G基站应急电源项目签约落户盐城亭湖区黄尖镇，由高意泰新能源投资建设，外资占比100万美元，主要为LG代工生产5G应急电源。", url="http://www.dldanuo.cn/kuaixun/202601/20422.html", source="新华网", country="韩国", industry="新一代信息通信", event_type="投资落地", region="江苏省", province="江苏省", city="盐城市", date="2026-01-01"),
    dict(title="德国KNUTH机床项目签约落户扬州高新区", summary="德国KNUTH机床项目正式签约落户扬州高新区，专攻精密切削机床，与园区金属成形机床产业形成互补，补齐高端精切机床细分领域空白。", url="https://hj.yangzhou.gov.cn/xwzx/jcdt/art/2026/art_e8fe5e79ad2e466dbd256ba2cbd449c2.html", source="扬州高新区", country="德国", industry="智能制造装备", event_type="投资落地", region="江苏省", province="江苏省", city="扬州市", date="2026-07-09"),
    dict(title="德国洛克威全球铣挖机隐形冠军在扬州设立中国区总部", summary="全球铣挖机领域隐形冠军德国洛克威公司在扬州高新区中德（欧）世界隐形冠军专精特新产业园领取营业执照，设立中国区总部及生产营销基地覆盖亚洲市场。", url="https://www.hj.gov.cn/xwzx/ywdt/art/2026/art_430d12858bc64ee08dc572511e44f36d.html", source="邗江政府", country="德国", industry="智能制造装备", event_type="地区总部", region="江苏省", province="江苏省", city="扬州市", date="2026-05-28"),
    dict(title="阿斯利康泰州基地扩建发力ADC与单抗前沿领域", summary="阿斯利康在泰州生物制药基地进一步扩建，重点发力抗体药物偶联物（ADC）和单抗药物等前沿领域，与无锡小分子药物形成差异化协同布局。", url="https://js.ifeng.com/c/8rpsZKTtUtf", source="凤凰网", country="英国", industry="生物医药", event_type="增资扩产", region="江苏省", province="江苏省", city="泰州市", date="2026-01-29"),
    dict(title="新浦化学高端化学品项目入选国家第七批重大外资项目", summary="江苏泰州新浦化学高端化学品项目入选国家发改委第七批标志性重大外资项目，为涉及化工领域的重点项目之一。", url="https://m.cls.cn/detail/1569751", source="财联社", country="多国", industry="新材料", event_type="投资落地", region="江苏省", province="江苏省", city="泰州市", date="2026-01-12"),
    dict(title="宿台融合产业对接会一批台资项目集中签约拟2026年落地", summary="宿台融合高质量发展产业对接会上，6位台商代表获聘宿迁市“台商迁引大使”，现场一批台资项目集中签约，涵盖环保科技、电子元器件、低空飞行器研发制造等领域，拟于2026年落地投产。", url="https://stb.suqian.gov.cn/sqtb/tpxw/202601/3e483b40231f4392ba86d50f633c9a97.shtml", source="宿迁市台办", country="中国台湾", industry="新一代信息通信", event_type="投资落地", region="江苏省", province="江苏省", city="宿迁市", date="2026-01-15"),

    # ---------- 第二批：全国扩充（基于真实网络检索，覆盖更多省份/国别/行业）----------
    # 四川
    dict(title="安利投资3500万美元在蓉建设中国首座自有有机农场", summary="安利(中国)中草药有机农场项目在成都彭州签约，总投资3500万美元，占地约1680亩，将打造高标准有机中药材智慧种植农场，是安利在美洲之外布局的首个自有生产农场。", url="https://m.toutiao.com/article/7621476446883611178/", source="红星新闻", country="美国", industry="生物医药", event_type="投资落地", region="四川省", province="四川省", city="成都市", date="2026-03-26"),
    dict(title="台资企业普思电子将广东两厂迁移合并至四川遂宁", summary="全球最大电阻生产企业国巨集团旗下普思电子将位于广东的两家工厂迁移合并至遂宁经开区，工厂面积扩大3倍，产值去年翻两番，成为川渝地区电子信息产业链重要外资力量。", url="https://www.toutiao.com/article/7655611068638609972/", source="四川日报", country="中国台湾", industry="新一代信息通信", event_type="投资落地", region="四川省", province="四川省", city="遂宁市", date="2026-05-20"),
    # 重庆
    dict(title="世界500强默沙东落户重庆渝中", summary="世界500强企业默沙东在重庆渝中区完成工商注册登记，设立默沙东(中国)投资有限公司重庆分公司，系企业首入重庆、首进渝中，助力重庆世界500强数量达159家。", url="https://www.toutiao.com/article/7600335635274039860", source="重庆日报", country="美国", industry="生物医药", event_type="地区总部", region="重庆市", province="重庆市", city="重庆市", date="2026-01-28"),
    dict(title="芬兰普乐集团联合投资高端消费品包装基地落子重庆江津", summary="全球食品饮料包装巨头普乐集团与本地企业联合投资约2亿元在重庆江津建设高端消费品包装生产基地，其中外资投入约1400万美元，主要为星巴克、麦当劳等配套，预计年产值约3亿元。", url="https://new.qq.com/rain/a/20260320A0868K00", source="江津日报", country="芬兰", industry="新材料", event_type="投资落地", region="重庆市", province="重庆市", city="重庆市", date="2026-03-20"),
    dict(title="60亿级新能源高端装备研发智造基地签约落户重庆巴南", summary="巴南区政府与多家企业签署合作协议，打造60亿级新能源高端装备研发智造基地，涵盖新能源研发智造与高端装备研发智造两大核心子项目，总占地约809亩，预计年总产值超160亿元。", url="https://www.cqnews.net/web/content_1471896068903669760.html", source="华龙网", country="跨国企业", industry="智能网联新能源汽车", event_type="投资落地", region="重庆市", province="重庆市", city="重庆市", date="2026-02-13"),
    # 湖北·武汉
    dict(title="安波福武汉电气分配系统工厂和研发中心将于2026年投产", summary="全球汽车技术巨头安波福在武汉经开区新建电气分配系统制造工厂和研发中心，是其深耕武汉18年后的又一重磅布局，武汉已成为其在华布局核心枢纽。", url="https://3g.wuhan.gov.cn/sy/whyw/202601/t20260106_2707126.shtml", source="武汉市政府", country="美国", industry="智能网联新能源汽车", event_type="投资落地", region="湖北省", province="湖北省", city="武汉市", date="2026-01-06"),
    dict(title="伟世通与欣锐科技签约成立外资公司建设车载电源技术研发中心", summary="伟世通与欣锐科技签约成立外资公司伟世通欣锐(武汉)汽车电子有限公司，建设车载电源技术研发中心，汇聚双方汽车电子研发人员为全球智能汽车主机厂提供技术方案。", url="https://district.ce.cn/newarea/roll/202603/t20260331_2869410.shtml", source="中国经济网", country="美国", industry="智能网联新能源汽车", event_type="研发中心", region="湖北省", province="湖北省", city="武汉市", date="2026-03-31"),
    dict(title="德国普旭将全球最大海外单笔投资项目落户武汉", summary="德国普旭将全球最大海外单笔投资项目落户武汉中德国际产业园，投产首年销售收入超5亿元，成为外资项目快落地、快见效的典范。", url="https://3g.wuhan.gov.cn/sy/whyw/202601/t20260106_2707126.shtml", source="武汉市政府", country="德国", industry="智能制造装备", event_type="投资落地", region="湖北省", province="湖北省", city="武汉市", date="2026-01-06"),
    dict(title="博格华纳持续追加在汉投资新能源汽车业务占比提升", summary="博格华纳不断追加在武汉投资，使新能源汽车业务占比提升至95%，深度融入武汉车谷汽车产业链生态。", url="https://3g.wuhan.gov.cn/sy/whyw/202601/t20260106_2707126.shtml", source="武汉市政府", country="美国", industry="智能网联新能源汽车", event_type="增资扩产", region="湖北省", province="湖北省", city="武汉市", date="2026-01-06"),
    dict(title="湖北首家墨西哥全资外企奥创光电在汉开业", summary="湖北首家墨西哥全资外资企业奥创(湖北)光电有限责任公司在武汉开业，深化中墨两国在光电通信领域的产业合作。", url="https://district.ce.cn/newarea/roll/202603/t20260331_2869410.shtml", source="中国经济网", country="墨西哥", industry="新一代信息通信", event_type="投资落地", region="湖北省", province="湖北省", city="武汉市", date="2026-03-31"),
    dict(title="采埃孚Lifetec将武汉作为中国战略布局支点设创新联合实验室", summary="全球汽车零部件巨头采埃孚Lifetec将武汉作为在中国布局的战略支点，计划依托在汉设立的创新联合实验室攻克智能安全领域核心技术。", url="https://district.ce.cn/newarea/roll/202603/t20260331_2869410.shtml", source="中国经济网", country="德国", industry="智能网联新能源汽车", event_type="研发中心", region="湖北省", province="湖北省", city="武汉市", date="2026-03-31"),
    # 河南
    dict(title="卢森堡SolarCleano光伏清洁机器人基地在郑州航空港投产", summary="卢森堡SolarCleano光伏运维机器人生产基地在郑州航空港投产，首批C1大型光伏运维机器人下线，是郑州—卢森堡空中丝绸之路开通以来首批落地国内的卢森堡实体制造业外资项目。", url="https://new.qq.com/rain/a/20260612A07BY300", source="大河网", country="卢森堡", industry="机器人", event_type="投资落地", region="河南省", province="河南省", city="郑州市", date="2026-06-12"),
    dict(title="白俄罗斯资本首次进入郑州自贸片区", summary="随着郑州斯玛特贸易有限公司一笔实际到资落地，白俄罗斯资本首次进入河南自贸区郑州片区，继越南、澳大利亚之后郑州国际朋友圈再度扩容。", url="https://dahecube.com/article.html?artid=266019%3Frecid%3D463", source="大河财立方", country="白俄罗斯", industry="", event_type="投资落地", region="河南省", province="河南省", city="郑州市", date="2026-03-12"),
    # 辽宁
    dict(title="华晨宝马沈阳生产基地第700万辆整车下线投资超1160亿元", summary="华晨宝马沈阳生产基地第700万辆整车下线，自2010年以来该基地投资总额已超1160亿元，成为宝马集团全球规模最大的生产基地。", url="https://new.qq.com/rain/a/20260528A09QQ400", source="中国新闻网", country="德国", industry="智能网联新能源汽车", event_type="增资扩产", region="辽宁省", province="辽宁省", city="沈阳市", date="2026-05-28"),
    dict(title="法国米其林沈阳工厂累计投资超120亿元", summary="法国米其林落户沈阳30余年，历经多轮增资扩建累计投资超120亿元，成为沈阳汽车产业链重要配套企业。", url="https://new.qq.com/rain/a/20260528A09QQ400", source="中国新闻网", country="法国", industry="智能制造装备", event_type="增资扩产", region="辽宁省", province="辽宁省", city="沈阳市", date="2026-05-28"),
    dict(title="沙特阿美参股的华锦阿美精细化工及原料工程在盘锦推进", summary="总投资837亿元的华锦阿美精细化工及原料工程项目在辽宁盘锦推进，是沙特阿拉伯在华最大投资项目，由沙特阿美与中方企业共同投资。", url="https://vakiodaily.com/news/view/id/679861", source="新华社", country="沙特", industry="新材料", event_type="投资落地", region="辽宁省", province="辽宁省", city="盘锦市", date="2026-01-05"),
    dict(title="总投资37亿元的大连泰星能源纯电汽车电池项目加紧建设", summary="在辽宁自贸试验区大连片区，总投资37亿元的泰星能源纯电汽车电池项目正加紧建设，由日本企业与中方企业共同出资设立，此前已相继在大连投资三期混动汽车电池项目。", url="https://vakiodaily.com/news/view/id/679861", source="新华社", country="日本", industry="智能网联新能源汽车", event_type="投资落地", region="辽宁省", province="辽宁省", city="大连市", date="2026-03-01"),
    dict(title="沙特ACWA Power扩大在辽宁新能源与海水淡化投资", summary="沙特国际电力和水务公司坚定看好辽宁，将围绕海水淡化、新能源等深化全产业链合作，辽宁清洁能源装机占比已突破55%，双方合作全面铺开。", url="https://www.toutiao.com/article/7655290221055033908", source="辽宁日报", country="沙特", industry="智能电网", event_type="投资落地", region="辽宁省", province="辽宁省", city="大连市", date="2026-02-05"),
    # 陕西·西安
    dict(title="德国克诺尔集团一体化生产基地高效落地西安浐灞国际港", summary="全球轨道交通制动系统领军企业德国克诺尔集团一体化生产基地项目在西安浐灞国际港快速签约、开工、建设，预计2026年全面投产，成为其在中国布局的重要综合性产业基地。", url="https://www.toutiao.com/article/7611731995005108778", source="机遇西安", country="德国", industry="智能制造装备", event_type="投资落地", region="陕西省", province="陕西省", city="西安市", date="2026-02-28"),
    dict(title="德国采埃孚气体发生器扩能项目在西安经开区投产", summary="德国采埃孚(ZF LIFETEC)气体发生器扩能项目在西安经开区泾渭工业园正式投产，总投资1.5亿欧元，从破土到投产约15个月，成为采埃孚全球技术最先进基地。", url="https://www.toutiao.com/article/7625904328867349046", source="机遇西安", country="德国", industry="智能制造装备", event_type="增资扩产", region="陕西省", province="陕西省", city="西安市", date="2026-04-07"),
    dict(title="韩国新韩金刚石SDC半导体生产关键耗材项目落子西安高新区", summary="韩国企业新韩金刚石工业株式会社在西安高新区落子，总投资达2.5亿元的SDC半导体生产关键耗材制造项目聚焦半导体制造核心化学机械抛光工艺，有望打破进口依赖。", url="https://www.toutiao.com/article/7625904328867349046", source="机遇西安", country="韩国", industry="集成电路", event_type="投资落地", region="陕西省", province="陕西省", city="西安市", date="2026-04-07"),
    dict(title="芬兰维美德造纸设备生产线等重点外资项目持续跟进西安", summary="西安2026年持续跟进芬兰维美德造纸设备生产线等一批重点外资制造业项目，聚焦韩国、新加坡、中国香港及中东等重点外资来源地，力争实现8.1亿美元实际使用外资目标。", url="https://www.21jingji.com/article/20260213/herald/9924e5df3fad4f6f639ee051d5f2cdab.html", source="21世纪经济报道", country="芬兰", industry="智能制造装备", event_type="投资落地", region="陕西省", province="陕西省", city="西安市", date="2026-02-13"),
    dict(title="香港快仓智能创新产业基地等外资项目持续跟进西安", summary="西安将香港快仓智能创新产业基地等一批重点外资制造业项目纳入持续跟进清单，强化市级战略统筹，聚焦重点外资来源地推动项目落地。", url="https://www.21jingji.com/article/20260213/herald/9924e5df3fad4f6f639ee051d5f2cdab.html", source="21世纪经济报道", country="中国香港", industry="机器人", event_type="地区总部", region="陕西省", province="陕西省", city="西安市", date="2026-02-13"),
    # 天津
    dict(title="德国罗曼胶带追加投资在天津经开区新增产线", summary="工业胶带细分领域隐形冠军、落户天津经开区24年的德国罗曼胶带计划追加投资2000万元新增一条产线，继续扎根中国市场。", url="https://www.tjftz.gov.cn/contents/6302/379364.html", source="天津自贸区", country="德国", industry="新材料", event_type="增资扩产", region="天津市", province="天津市", city="天津市", date="2026-03-15"),
    dict(title="挪威美威集团三文鱼深加工生产线选址天津滨海新区", summary="全球最大三文鱼养殖供应商挪威美威集团选址天津中心渔港国家骨干冷链物流基地，计划建设三文鱼深加工生产线，达产后预计年产值2亿元。", url="https://www.tjftz.gov.cn/contents/6302/379364.html", source="天津自贸区", country="挪威", industry="生物医药", event_type="投资落地", region="天津市", province="天津市", city="天津市", date="2026-03-20"),
    dict(title="巴西汽车配件商WEGA落子泰达设首家外资独资企业", summary="巴西汽车零配件经营商WEGA在天津经开区设立威嘉汽车配件(天津)有限公司，成为泰达MSD在2026年首家落户的外资独资企业，主营汽车零配件零售批发及技术服务。", url="https://teda.gov.cn/contents/216/105954.html", source="泰达", country="巴西", industry="智能网联新能源汽车", event_type="投资落地", region="天津市", province="天津市", city="天津市", date="2026-05-10"),
    dict(title="韩国DL会社GFRP新材料项目签约落户天津武清", summary="韩国株式会社DL独资GFRP新材料项目签约落户京津科技谷，总投资1.2亿元，规划年产7.2万吨高性能GFRP，应用于桥梁隧道、港口码头等关键领域。", url="https://www.toutiao.com/article/7647109486448017974", source="武清发布", country="韩国", industry="新材料", event_type="投资落地", region="天津市", province="天津市", city="天津市", date="2026-06-18"),
    dict(title="瑞典山特维克矿用筛分设备扩产项目落地天津西青", summary="瑞典百年高科技工程集团山特维克与西青经开区签署合作协议，矿用筛分设备生产基地扩产项目落户，新增投资6000万元，达产后年产值超5亿元。", url="http://news.enorth.com.cn/system/2026/07/09/059554992.shtml", source="北方网", country="瑞典", industry="智能制造装备", event_type="增资扩产", region="天津市", province="天津市", city="天津市", date="2026-07-09"),
    # 北京
    dict(title="三星在华首个生物医药研发中心落地北京昌平", summary="三星集团旗下三星艾匹斯在北京昌平区启动生物医药研发中心建设，重点布局抗体偶联药物(ADC)技术平台，是三星在华设立的首个生物医药研发中心。", url="https://so.html5.qq.com/page/real/search_news?docid=70000021_5996a22a72c91752", source="投资昌平", country="韩国", industry="生物医药", event_type="研发中心", region="北京市", province="北京市", city="北京市", date="2026-06-05"),
    dict(title="阿斯利康未来5年将在北京投资25亿美元建战略研发中心", summary="阿斯利康将在北京经济技术开发区国际医药创新公园BioPark投资25亿美元，建设战略研发中心和罕见病中心，其第六个全球战略研发中心下半年入驻。", url="https://fgw.beijing.gov.cn/gzdt/fgzs/tpxw/202606/t20260602_4681811.htm", source="北京日报", country="英国", industry="生物医药", event_type="研发中心", region="北京市", province="北京市", city="北京市", date="2026-05-31"),
    dict(title="礼来再度投资北京与康龙化成合作生产代谢疾病药物", summary="全球药企礼来宣布未来十年在华累计投资约200亿元，并再度投资北京与亦庄企业康龙化成达成协议合作生产治疗2型糖尿病与肥胖症的药物。", url="https://www.163.com/dy/article/KT1FGE4B05568W0A.html", source="北京日报", country="美国", industry="生物医药", event_type="投资落地", region="北京市", province="北京市", city="北京市", date="2026-03-20"),
    # 浙江
    dict(title="日本海舟集团全资跨境电商项目落地嘉兴临空经济区", summary="日本海舟集团全资设立的浙江御空跨境电子商务有限公司在嘉兴临空经济区完成注册，注册资本1亿美元，打造一站式出海日本服务平台，从签约到落地仅一个月。", url="https://www.toutiao.com/article/7611495940305863231", source="浙江日报", country="日本", industry="新一代信息通信", event_type="投资落地", region="浙江省", province="浙江省", city="嘉兴市", date="2026-02-27"),
    dict(title="中荷合资高端机械零部件制造项目签约宁波镇海", summary="荷兰企业Machinefabriek Heerbaart与宁波企业合资打造高端压力设备零部件制造基地，总投资1.1亿元，从首次洽谈到签约仅用5天，融合中欧优势与AI柔性加工。", url="http://www.zj.xinhua.org/20260325/76dbd5cd7c8a4b198e9b04e913afce1b/c.html", source="新华网", country="荷兰", industry="智能制造装备", event_type="投资落地", region="浙江省", province="浙江省", city="宁波市", date="2026-03-24"),
    dict(title="新加坡Certis在杭州西湖设立AI与机器人研发中心", summary="新加坡老牌安防巨头Certis在杭州西湖区注册子公司安睿视，依托该主体建立人工智能与机器人研发中心，深度嵌入全球具身智能版图。", url="https://www.toutiao.com/article/7654186286034534954", source="浙江日报", country="新加坡", industry="人工智能(软件)", event_type="研发中心", region="浙江省", province="浙江省", city="杭州市", date="2026-04-30"),
    dict(title="新加坡能源集团综合能源中国总部落地杭州萧山", summary="淡马锡全资控股的新加坡能源集团将综合能源中国总部落地杭州萧山，与杭州构建国际技术赋能加国有资本加持加区域场景承载的合作模式。", url="https://www.toutiao.com/article/7654186286034534954", source="浙江日报", country="新加坡", industry="智能电网", event_type="地区总部", region="浙江省", province="浙江省", city="杭州市", date="2026-02-15"),
    dict(title="德国泰明顿集团中国总部及亚洲研发中心落子嘉兴平湖", summary="全球制动部件龙头泰明顿集团投资设立中国总部及亚洲研发中心(平湖)项目，涵盖乘用车及商用车制动片研发生产，计划2026年中投产。", url="https://swj.jiaxing.gov.cn/col/col1497201/art/2026/art_87c6b0f561bb4c6ba3bff8c31108a643.html", source="嘉兴市商务局", country="德国", industry="智能网联新能源汽车", event_type="地区总部", region="浙江省", province="浙江省", city="嘉兴市", date="2026-03-10"),
    dict(title="德国伍尔特大中华区供应链中心等外资项目深耕嘉兴海盐", summary="嘉兴国家高新区外向型经济领跑，德国伍尔特集团大中华区供应链中心等项目持续深耕扩容，2025年嘉兴高新区实际利用外资同比增长54.98%。", url="https://www.csjcs.com/news/show/25d3ff30dbcab8b8.html", source="长三角城市网", country="德国", industry="智能制造装备", event_type="地区总部", region="浙江省", province="浙江省", city="嘉兴市", date="2026-01-15"),
    # 福建·厦门
    dict(title="法国道达尔能源与厦门国贸达成LNG与新能源合作", summary="国际能源巨头法国道达尔能源集团与厦门国贸控股集团达成合作共识，在LNG、新能源投资、润滑油及功能材料等领域开展全面合作，提升产业链国际合作层次。", url="https://www.hubpd.com/hubpd/rss/uc/index.html?contentId=5188146770734778595", source="投洽会", country="法国", industry="智能电网", event_type="经贸洽谈", region="福建省", province="福建省", city="厦门市", date="2026-06-10"),
    dict(title="新加坡PSA国际港务战略投资厦门集装箱码头集团", summary="全球领先集装箱港口运营商新加坡PSA国际港务集团通过公开挂牌成为厦门集装箱码头集团战略投资人，释放30%优质股权开展战略合作，加大多式联运智慧物流中心投资。", url="https://swt.fujian.gov.cn/xxgk/jgzn/jgcs/dtgxdc/gzdt/202605/t20260511_7146500.htm", source="福建省商务厅", country="新加坡", industry="", event_type="投资落地", region="福建省", province="福建省", city="厦门市", date="2026-05-11"),
    dict(title="施耐德电气全球最大中压电气设备生产基地在厦门攻坚", summary="厦门火炬电力电气产业园项目全面进入攻坚阶段，建成后将成为施耐德电气全球最大的中压电气设备生产基地，也是其在我国布局的第二座灯塔工厂。", url="http://www.fujian.gov.cn:85/gate/big5/www.fujian.gov.cn/zwgk/ztzl/lwlb/lsqk/202602/t20260207_7090772.htm", source="福建省政府", country="法国", industry="智能电网", event_type="投资落地", region="福建省", province="福建省", city="厦门市", date="2026-02-07"),
    dict(title="丘钛科技计划在厦门设立高端微型驱动器运营总部", summary="丘钛科技计划在厦门投资设立高端微型驱动器运营总部，建设符合工业4.0标准的智能制造基地，是第二十五届投洽会厦门团签约的重大外资项目之一。", url="https://www.hubpd.com/hubpd/rss/uc/index.html?contentId=5188146770734778595", source="投洽会", country="中国香港", industry="新一代信息通信", event_type="地区总部", region="福建省", province="福建省", city="厦门市", date="2026-06-10"),
    # 广西
    dict(title="美国索理思集团北海新材料项目开工", summary="全球造纸助剂龙头美国索理思集团落子广西的首个投资项目北海索理思新材料项目在铁山港工业区开工，总投资2.5亿元，其中合同外资1500万美元，设计年产能6万吨。", url="https://v.gxnews.com.cn/a/21932099", source="广西新闻网", country="美国", industry="新材料", event_type="投资落地", region="广西壮族自治区", province="广西壮族自治区", city="北海市", date="2026-04-15"),
    dict(title="法国爱森集团年产37万吨造纸化学品项目推进南宁", summary="法国爱森集团设立的纯外资企业爱森(南宁)特种材料有限公司造纸化学品项目稳步推进，一期计划明年建成投产，助力南宁造纸产业向高端化绿色化迈进。", url="https://www.nanning.gov.cn/ywzx/nnyw/2026nzwdt/t6593606.html", source="南宁市政府", country="法国", industry="新材料", event_type="投资落地", region="广西壮族自治区", province="广西壮族自治区", city="南宁市", date="2026-04-07"),
    dict(title="新加坡THi控股海工装备产业园签约防城港", summary="防城港市投资促进局与新加坡THi控股发展集团等签约共建THi国际海工装备(防城港)产业园，聚焦船舶修造、海底光缆、海洋机器人及海洋工程科研，补齐高端海工产业空白。", url="https://m.sohu.com/a/1019021262_121106875", source="投资广西", country="新加坡", industry="智能制造装备", event_type="投资落地", region="广西壮族自治区", province="广西壮族自治区", city="防城港市", date="2026-05-06"),
    # 海南
    dict(title="西门子能源燃机总装基地及服务中心落地海南洋浦", summary="封关后首个制造业标杆外资项目西门子能源燃机总装基地及服务中心落地洋浦并开工建设，同步设立西门子能源(海南)有限公司，打造国内燃机总装及服务核心基地。", url="https://news.10jqka.com.cn/20260617/c677544590.shtml", source="同花顺", country="德国", industry="智能电网", event_type="投资落地", region="海南省", province="海南省", city="儋州市", date="2026-06-15"),
    dict(title="新加坡富隆集团投资博鳌富隆医院落户乐城", summary="新加坡富隆集团投资设立的博鳌富隆医院落户海南博鳌乐城先行区，成为海南首家外商独资医院，标志海南医疗健康领域开放提速。", url="https://news.10jqka.com.cn/20260617/c677544590.shtml", source="同花顺", country="新加坡", industry="生物医药", event_type="投资落地", region="海南省", province="海南省", city="琼海市", date="2026-06-15"),
    dict(title="沙特ACWA Power宣布300亿美元重仓中国布局海南绿能", summary="沙特国际电力和水务公司(ACWA Power)宣布至2030年在中国累计投资至少300亿美元，其中2026年预计超50亿美元，并正与海南讨论绿色甲醇、绿氨和绿氢等绿色能源项目。", url="https://cnenergynews.cn/article/4R1MBp27tFO", source="能源新闻网", country="沙特", industry="智能电网", event_type="投资落地", region="海南省", province="海南省", city="海口市", date="2026-03-27"),
    dict(title="海南太古可口可乐绿色智能生产基地开工", summary="海南太古可口可乐绿色智能生产基地等实体产业项目在海南陆续开工建设，借助自贸港封关运作政策红利集聚全球优质资源。", url="https://news.10jqka.com.cn/20260617/c677544590.shtml", source="同花顺", country="中国香港", industry="", event_type="投资落地", region="海南省", province="海南省", city="海口市", date="2026-06-15"),
    # 广东（新增，保持全国均衡）
    dict(title="美国克罗格集团投资3.8亿美元在深圳设大中华区总部", summary="美国第二大综合商超集团克罗格宣布总投资3.8亿美元布局中国，在深圳福田全资设立大中华区零售总部，系其143年来首次走出北美开展实体零售海外布局。", url="https://www.xfrb.com.cn/article/zx/10554940670890.html", source="消费日报", country="美国", industry="", event_type="地区总部", region="广东省", province="广东省", city="深圳市", date="2026-07-02"),
    dict(title="英国章鱼能源携手碧澄能源在广州设立电力交易合资公司", summary="英国章鱼能源与碧澄能源合资设立碧桐能源并在广州正式开业，引入估值超86.5亿美元的Kraken平台，以AI算法驱动电力交易，标志中英能源科技合作标志性落地。", url="https://news.bjx.com.cn/html/20260514/1495612.shtml", source="北极星电力", country="英国", industry="智能电网", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-05-12"),
    dict(title="新加坡格林新能落户深圳前海布局储能平台", summary="由新加坡GREENVLOT与国能日新合资设立的格林新能(深圳)科技有限公司在前海完成注册，外方持股80%，是国际绿色资本抢滩深圳储能赛道的代表性外资控股平台。", url="https://www.sznews.com/news/content/2026-03/25/content_31991560.htm", source="深圳新闻网", country="新加坡", industry="智能电网", event_type="投资落地", region="广东省", province="广东省", city="深圳市", date="2026-03-25"),
    dict(title="韩国STI株式会社东韩半导体广州基地动工布局AMB陶瓷基板", summary="韩国STI株式会社投资的东韩半导体广州基地在白云区动工，整体规划总投资超百亿元，一期投资约23亿元生产功率半导体关键材料AMB陶瓷基板，预计2027年试生产。", url="https://www.dramx.com/News/igbt/20260629-40681.html", source="科创板日报", country="韩国", industry="集成电路", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-06-25"),
    dict(title="新加坡沈氏休闲集团ESCAPE主题乐园项目签约广州黄埔", summary="新加坡沈氏休闲集团旗下ESCAPE市外逃园项目签约落户广州开发区、黄埔区，系其进入中国市场的首个项目，总投资4亿元，预计年客流量可达100万人次。", url="https://daohuangpuqu.gz-cmc.com/pages/2026/03/10/e178d06cfbdd4c3987074e24688cc05b.html", source="广州黄埔区", country="新加坡", industry="", event_type="投资落地", region="广东省", province="广东省", city="广州市", date="2026-03-10"),
    dict(title="德国默克在深圳设立创新中心与加速器", summary="德国默克集团在深圳设立创新中心并作为默克加速器，通过高端实验室和产业基金为全球生命科学、医药健康及电子科技领域初创公司提供技术与金融支持。", url="https://new.qq.com/rain/a/20260603A06WLQ00", source="创新南山", country="德国", industry="生物医药", event_type="研发中心", region="广东省", province="广东省", city="深圳市", date="2026-06-03"),
    # 低空经济（行业补全）
    dict(title="法国皮奈特集团中法低空经济项目落地青岛即墨", summary="法国皮奈特集团与纳天航空签署战略合作协议，中法低空经济合作项目落地青岛即墨，共建复合材料研发中心与高端制造设备基地，系青岛首个低空经济外资项目。", url="https://new.qq.com/rain/a/20260530A071MW00", source="信网", country="法国", industry="低空经济(航空航天)", event_type="投资落地", region="山东省", province="山东省", city="青岛市", date="2026-05-30"),
    dict(title="韩国Verty等中韩低空经济示范项目签约武汉汉阳", summary="武汉汉阳区投资促进大会签约5个低空经济项目，其中韩国Verty公司中韩低空经济示范项目等总金额超10亿元，湖北力争2027年低空经济产业规模超1000亿元。", url="http://www.changjiangtimes.com/2026/03/652467.html", source="长江时报", country="韩国", industry="低空经济(航空航天)", event_type="投资落地", region="湖北省", province="湖北省", city="武汉市", date="2026-03-11"),
    dict(title="沃兰特eVTOL完成3亿美元C轮融资引入中东投资人", summary="国内商用客运eVTOL龙头沃兰特航空完成3亿美元C轮融资，首次引入中东地区投资人，创下国内高等级商用客运eVTOL最大单笔融资纪录，加速全球化市场拓展。", url="https://new.qq.com/rain/a/20260429A08VCM00", source="腾讯新闻", country="阿联酋", industry="低空经济(航空航天)", event_type="投资落地", region="上海市", province="上海市", city="上海市", date="2026-04-29"),
    dict(title="中德飞机考察肇庆砚阳湖低空经济产业园", summary="拥有欧洲技术背景的中德轻型飞机股份有限公司高层实地考察肇庆新区砚阳湖高新区低空经济产业园，双方共商低空经济项目合作，肇庆深度进入低空经济头部企业视野。", url="https://static.nfnews.com/content/202603/19/c12257001.html", source="南方plus", country="德国", industry="低空经济(航空航天)", event_type="考察调研", region="广东省", province="广东省", city="肇庆市", date="2026-03-19"),
    # 考察·经贸交流（扩展省份）
    dict(title="2026投资浙里外国企业浙江行合作对接交流会在杭州举行", summary="2026投资浙里外国企业浙江行合作对接交流会在杭州举行，来自德、英、法、意、西、匈、韩、美、加等23个国家和地区超200家外资企业和机构参会，促成一批项目合作。", url="https://new.qq.com/rain/a/20260424A08G7Z00", source="中国新闻网", country="多国", industry="", event_type="经贸洽谈", region="浙江省", province="浙江省", city="杭州市", date="2026-04-24"),
    dict(title="2026相约春天赏樱花经贸洽谈活动在武汉举办", summary="2026相约春天赏樱花经贸洽谈活动在武汉举办，10余位驻华使节、150余家世界500强高管等海内外嘉宾汇聚，共寻开放合作新机遇。", url="https://district.ce.cn/newarea/roll/202603/t20260331_2869410.shtml", source="中国经济网", country="多国", industry="", event_type="经贸洽谈", region="湖北省", province="湖北省", city="武汉市", date="2026-03-30"),
    dict(title="辽宁行系列活动吸引外资企业代表团走进辽宁", summary="辽宁高水平举办夏季达沃斯论坛、中国辽宁国际投资贸易洽谈会及外资企业代表团、上市公司考察团、百名商协会会长等辽宁行系列活动，吸引众多知名企业走进辽宁选择辽宁。", url="https://paper.people.com.cn/rmrb/pc/content/202606/24/content_30164628.html", source="人民日报", country="多国", industry="", event_type="考察调研", region="辽宁省", province="辽宁省", city="沈阳市", date="2026-06-24"),
    dict(title="2026世界智能产业博览会85个重点项目落地天津", summary="2026世界智能产业博览会重点项目签约仪式在天津举行，85个重点项目正式落地，含一个外资硅光芯片及光电子器件亚太区域总部项目等，赋能天津产业创新。", url="http://news.enorth.com.cn/system/2026/05/27/059435881.shtml", source="北方网", country="多国", industry="新一代信息通信", event_type="经贸洽谈", region="天津市", province="天津市", city="天津市", date="2026-05-27"),

    # ---------- 考察·经贸交流（拓宽定义：外国政府部门/驻华使节/国际组织/非营利机构/基金会/商协会来华考察交流）----------
    dict(title="外国在港政商界参访团赴湖南考察湘港经贸合作", summary="外交部驻港公署组织白俄罗斯、新加坡、英国等国驻港领团、商会及跨国企业负责人赴湖南长株潭考察中联重科、远大集团、圣湘生物等龙头企业，探索依托香港搭建湘港联动、联通国际的合作桥梁。", url="https://www.163.com/dy/article/L1S9F9EJ0514R9M0_pdya11y.html", source="新华社", country="多国", industry="", event_type="考察调研", region="湖南省", province="湖南省", city="长沙市", date="2026-07-14"),
    dict(title="奥地利外长赖辛格携经济代表团访华并参访上海、江苏太仓", summary="奥地利外长赖辛格就职后首次访华，携经济代表团聚焦双边经贸合作，先后参访上海和江苏太仓，参访在华奥企并出席企业圆桌会，表示奥地利企业愿继续深耕中国市场。", url="https://www.mfa.gov.cn/fyrbt_673021/202606/t20260626_11953047.shtml", source="外交部", country="奥地利", industry="", event_type="经贸洽谈", region="江苏省", province="江苏省", city="苏州市", date="2026-06-25"),
    dict(title="哈萨克斯坦驻上海总领事访问南京洽谈经贸投资合作", summary="哈萨克斯坦驻上海总领事阿科什卡罗夫对南京进行工作访问，会见南京市市长及江苏省外办负责人，并与省商务厅、公安厅、教育厅负责人举行系列会谈，拓展哈中区域贸易、投资及人文合作。", url="https://www.toutiao.com/w/1856101521185995/", source="哈萨克斯坦驻华使馆", country="哈萨克斯坦", industry="", event_type="经贸洽谈", region="江苏省", province="江苏省", city="南京市", date="2026-01-20"),
    dict(title="韩国驻华大使卢载宪访江苏考察LG新能源、悦达起亚", summary="2026韩国—中国(江苏)友好周期间，韩国驻华大使卢载宪访问江苏，会见江苏省省长，视察LG新能源南京基地和盐城悦达起亚工厂，并出席韩中(南京)企业经贸交流会。", url="https://cb.yna.co.kr/gate/big5/m-cn.yna.co.kr/view/view/ACK20260521003000881", source="韩联社", country="韩国", industry="智能网联新能源汽车", event_type="经贸洽谈", region="江苏省", province="江苏省", city="南京市", date="2026-05-18"),
    dict(title="2026中国(江苏)赞比亚投资机遇洽谈会在南京举行", summary="赞比亚发展署署长、赞比亚驻华大使率团出席2026中国(江苏)赞比亚投资机遇洽谈会，在南京举办投资机遇闭门会议与参会企业一对一精准对接，推动意向合作项目向实质性落地迈进。", url="https://m.yangtse.com/wap/news/4955829.html", source="扬子晚报", country="赞比亚", industry="", event_type="经贸洽谈", region="江苏省", province="江苏省", city="南京市", date="2026-04-11"),
    dict(title="外交部组织28国驻华使节代表团参访江苏南京、苏州", summary="来自爱尔兰、沙特阿拉伯、日本、非盟等28个国家和国际组织的驻华使节应外交部邀请赴南京、苏州访问，深入企业一线，感受中国高质量发展活力和高水平开放机遇。", url="https://h5.ifeng.com/c/vivo/v0028AcKsYrVSMJjUF4bpxOjc55TWd19yJbCI7J7O8XhHvc__", source="新华社", country="多国", industry="", event_type="考察调研", region="江苏省", province="江苏省", city="南京市", date="2026-03-25"),
    dict(title="江苏省外办会见斐济驻华大使李振凡一行", summary="江苏省外办领导在南京会见斐济驻华大使李振凡一行，双方就发挥中国—太平洋岛国农业合作示范中心平台作用、拓展农业、企业投资、教育等领域务实合作交换意见，代表团还访问江苏省农科院。", url="https://wb.jiangsu.gov.cn/art/2026/3/12/art_331_11741049.html", source="江苏省外事办", country="斐济", industry="", event_type="经贸洽谈", region="江苏省", province="江苏省", city="南京市", date="2026-03-10"),
    dict(title="美国海伦·福斯特·斯诺基金会代表团到访工合国际", summary="美国海伦·福斯特·斯诺基金会主席率代表团到访中国工合国际委员会及北京培黎职业学院，围绕Camp工合项目深化合作、中美青少年民间交流等议题座谈，搭建中美民间友好交流平台。", url="http://gungho.org.cn/cn-info-show.php?infoid=1461", source="工合国际", country="美国", industry="", event_type="考察调研", region="北京市", province="北京市", city="北京市", date="2026-03-23"),
    dict(title="联合国世界丝路论坛十周年全球合作盛典在北京举行", summary="在联合国经社理事会登记的国际非营利非政府组织联合国世界丝路论坛，在北京举办十周年全球合作盛典，全球政商学文化界百余名代表参会，推动丝路沿线国家经贸、文化、科技、教育多领域交流。", url="http://www.sjcj.net.cn/m/view.php?aid=9388", source="世界丝路论坛", country="多国", industry="", event_type="论坛活动", region="北京市", province="北京市", city="北京市", date="2026-04-25"),
    dict(title="中欧美博物馆合作倡议2026高级别圆桌论坛在沪举办", summary="中欧美博物馆合作倡议2026高级别圆桌论坛在上海举办，美国旧金山市市长、旧金山芭蕾舞团、旧金山音乐学院等中美嘉宾出席，围绕文化机构在人类发展与文明交流中的作用深度研讨。", url="https://news.china.com.cn/2026-04/29/content_118469786.shtml", source="中国网", country="美国", industry="", event_type="论坛活动", region="上海市", province="上海市", city="上海市", date="2026-04-19"),
    dict(title="意大利BRIFF非营利组织举办对华出口研讨会暨进博会宣传日", summary="总部设在罗马的国际性非营利组织意大利食品与饲料对华出口促进会(BRIFF)在普利亚大区举办对华出口高级研讨会暨第九届进博会宣传日，与中国国际进口博览局密切合作推进11月参展工作。", url="https://www.ciie.org/zbh/bqgffb/20260615/61936.html", source="中国国际进口博览局", country="意大利", industry="", event_type="参展参会", region="全国", province="", city="", date="2026-06-11"),
    dict(title="非盟等7国官员参加中国改革开放发展女性研修班", summary="来自阿塞拜疆、巴拿马、冈比亚、克罗地亚、肯尼亚、南非、瑙鲁7国及国际组织非盟委员会的26名女性官员齐聚中国，在北京和深圳开展为期14天研修学习，实地考察中国改革发展成就。", url="https://c.m.163.com/news/a/KV5OEGHL05346TWM.html", source="中国新闻网", country="多国", industry="", event_type="考察调研", region="广东省", province="广东省", city="深圳市", date="2026-06-10"),
    dict(title="美中贸易全国委员会最大规模美资企业代表团访粤", summary="美中贸易全国委员会(USCBC)成立53年来最高规格、最大规模的美资企业代表团访粤，近50家世界500强美资企业CEO级高管齐聚广州，与广东政企深度对接，82%在华美企计划未来1—2年追加投资。", url="https://www.toutiao.com/article/7630632892309389864", source="新快报", country="美国", industry="", event_type="经贸洽谈", region="广东省", province="广东省", city="广州市", date="2026-04-18"),
    dict(title="马来西亚企业家代表团四川行在成都举办", summary="外企看四川——马来西亚企业家代表团一行23人深入彭州、双流、新津、蒲江考察，并举办中国(四川)—马来西亚企业家对接会，川马近80家企业围绕电子信息、装备制造、医药健康等领域一对一交流。", url="https://www.toutiao.com/article/7633042822652527156", source="封面新闻", country="马来西亚", industry="", event_type="考察调研", region="四川省", province="四川省", city="成都市", date="2026-04-25"),
    dict(title="2026山东省国际贸易和投资顾问威海行成功举办", summary="来自意大利、墨西哥、肯尼亚等多国商协会、国际组织、跨国公司40余人代表团走进威海，西门子、东盟中国工商总会、德国安顾集团、毕马威等机构代表与威海企业精准洽谈对接，达成多项合作意向。", url="http://mch.weihai.gov.cn/art/2026/7/13/art_8389_6478245.html", source="威海市贸促会", country="多国", industry="", event_type="经贸洽谈", region="山东省", province="山东省", city="威海市", date="2026-07-10"),
    dict(title="2026中外知名企业四川行在成都举行", summary="四川十五五开局之年首场省级综合性重大投资促进平台活动2026中外知名企业四川行在成都举行，通过投资推介、产业专场、实地考察等形式深化产业协作，筹备期间共达成合作项目301个。", url="https://m.chinanews.com/wap/detail/cht/zw/441780.shtml", source="中国新闻网", country="多国", industry="", event_type="经贸洽谈", region="四川省", province="四川省", city="成都市", date="2026-06-25"),
    dict(title="2026德国隐形冠军企业成都园区行举办", summary="蔡司、西门子、卡赫等30余家德国隐形冠军企业及知名机构代表齐聚成都，深入蒲江、邛崃、青白江产业园区考察，通过实地考察、高层会见、专题对接推动中德地方经贸合作从意向走向实景。", url="https://www.sohu.com/a/999108070_115362", source="搜狐城市", country="德国", industry="智能制造装备", event_type="考察调研", region="四川省", province="四川省", city="成都市", date="2026-03-19"),

    # ---------- 第三批：全国再扩充（基于真实网络检索，补齐上海/安徽/河南/湖北/跨国药企头部动态，拓宽来源）----------
    # 上海
    dict(title="英伟达上海张江新办公楼启用 在华员工近4000人", summary="英伟达上海新办公楼在张江纳贤路启用，建筑面积约2.33万平方米；其在华员工近4000人，上海研发中心超2000人，聚焦芯片设计验证、产品优化与自动驾驶研究。", url="https://www.eeo.com.cn/2026/0125/782771.shtml", source="经济观察报", country="美国", industry="人工智能(软件)", event_type="研发中心", region="上海市", province="上海市", city="上海市", date="2026-01-25"),
    dict(title="ABB机器人超级工厂在上海浦东康桥投产", summary="ABB投资约1.5亿美元（约合11亿元人民币）、占地6.7万平方米的机器人超级工厂在浦东康桥开业，采用全自动化柔性生产制造新一代机器人，未来在华销售九成以上产品将在此生产。", url="https://www.iseee.cn?p=/ShopNews/detail/zs/208/id/151", source="北京国际工业自动化展", country="瑞士", industry="机器人", event_type="投资落地", region="上海市", province="上海市", city="上海市", date="2026-04-01"),
    # 安徽
    dict(title="达维诺营养乳业安徽生产基地落户亳州 总投资23.2亿元", summary="由荷兰莱茵投资集团、芬兰法森集团、奥地利阿果那集团联合投资的达维诺营养乳业安徽生产基地在亳州谯城经开区开工，总投资约23.2亿元，规划年产婴幼儿配方奶粉10万吨、燕麦奶50万吨。", url="https://www.muyingjie.com/article-25542.html", source="母婴行业观察", country="荷兰", industry="生物医药", event_type="投资落地", region="安徽省", province="安徽省", city="亳州市", date="2026-07-07"),
    dict(title="安徽怀远年产2000万套高性能橡塑管材及汽车零部件项目签约", summary="外商投资企业安徽摩配斯智能科技有限公司投资建设的年产2000万套高性能橡塑管材及新能源汽车橡胶零部件项目在怀远县签约，引进自动化智能化生产线，丰富当地汽车零部件产品体系。", url="https://www.toutiao.com/article/7595906273850229299", source="怀远发布", country="跨国企业", industry="智能网联新能源汽车", event_type="投资落地", region="安徽省", province="安徽省", city="蚌埠市", date="2026-01-16"),
    # 河南
    dict(title="2026年河南省重大国际产业合作项目名单发布 55个项目", summary="河南省发布2026年重大国际产业合作项目名单，共55个项目，其中外商投资项目27个、总投资252.19亿元，涵盖新一代信息技术、现代装备、新能源与智能网联汽车、生物医药等，含卢森堡SolarCleano光伏清洁机器人基地。", url="https://ha.people.com.cn/BIG5/n2/2026/0618/c351638-41613898.html", source="人民网", country="多国", industry="机器人", event_type="投资落地", region="河南省", province="河南省", city="郑州市", date="2026-06-17"),
    # 湖北
    dict(title="武汉蔡甸中德国际产业园集聚外资企业超70家", summary="武汉蔡甸中德国际产业园作为对外开放核心平台，已集聚知名外资企业超70家，德资、美资、港澳台资企业纷至沓来，诺峰半导体等项目用时60天完成谈判签约落户全流程。", url="https://www.whcdrm.com/thread-22322-1-1.html", source="蔡甸融媒", country="德国", industry="智能制造装备", event_type="投资落地", region="湖北省", province="湖北省", city="武汉市", date="2026-03-30"),
    # 跨国药企千亿级加码（全国层面，行业=生物医药）
    dict(title="跨国药企集体“加仓”中国：一场超千亿元的信任投票", summary="中国发展高层论坛2026期间，阿斯利康宣布2030年前在华投资超1000亿元，诺华新增超33亿元、礼来未来十年30亿美元、罗氏20.4亿元、赛诺菲北京亦庄10亿欧元基地开工，跨国药企从“在中国卖药”转向“在中国创新、生产、共创”。", url="https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html", source="21世纪经济报道", country="多国", industry="生物医药", event_type="投资落地", region="全国", province="", city="", date="2026-03-23"),
    # 新一代信息通信：MWC2026 6G/AI原生
    dict(title="MWC2026展示AI原生6G架构 高通爱立信诺基亚三星同台", summary="2026巴塞罗那世界移动通信大会以“智能新纪元”为主题，高通展示AI原生6G架构（太赫兹、RIS、通感一体），爱立信提出Intelligent Fabric智能织网，诺基亚强化AI自优化，三星展示6G沉浸式通信潜力，6G目标2030年商用。", url="https://www.toutiao.com/article/7613521933497385512", source="21世纪经济报道", country="多国", industry="新一代信息通信", event_type="参展参会", region="全国", province="", city="", date="2026-03-05"),
    # 机器人：美的库卡昆山
    dict(title="美的库卡华东智能制造中心签约落户昆山 增资3000万美元", summary="美的库卡华东智能制造中心项目签约落户昆山高新区，拟增资3000万美元，扩充工业机器人产能并新设智慧仓储物流与轻载柔性机器人产线，达产年产值预计超30亿元。", url="https://www.iianews.com/ca/_01-ABC00000000000371518.shtml", source="中国工控网", country="德国", industry="机器人", event_type="增资扩产", region="江苏省", province="江苏省", city="苏州市", date="2026-04-22"),
    # 人工智能：亚马逊撤离（有进有退信号）
    dict(title="亚马逊关闭上海最后一家AI研究中心 外企在华研发现调整", summary="2026年4月，亚马逊结束其在中国上海的最后一家人工智能研究中心运营，标志中美科技博弈下外企在华本土研发力量的阶段性调整，DGL开源工具曾为其电商带来近10亿美元收入。", url="https://www.vpshk.cn/20260438038.html", source="科技媒体", country="美国", industry="人工智能(软件)", event_type="考察调研", region="上海市", province="上海市", city="上海市", date="2026-04-16"),
]

# 政策文件（level: 国家级/省级/市级/区级）
RAW_POLICIES = [
    dict(title="《2025年稳外资行动方案》（国办函〔2025〕16号）", summary="国务院办公厅转发商务部、国家发改委方案，从有序扩大自主开放、提高投资促进水平、增强开放平台效能、加大服务保障等20条举措稳外资。", url="https://www.gov.cn/gongbao/2025/issue_11906/202503/content_7011165.html", publisher="国务院办公厅", level="国家级", region="全国", province="", city="", date="2025-02-17"),
    dict(title="《利用外资固稳促优行动方案》（商资发〔2026〕97号）", summary="商务部、国家发改委、财政部联合印发，围绕扩大市场准入、提升投资便利度、提高投资促进水平、健全服务保障体系、优化外资管理五方面提出15条举措。", url="https://www.mofcom.gov.cn/zfxxgk/gkml/art/2026/art_544b95c97cf043aa822be835d45e9f69.html", publisher="商务部、国家发改委、财政部", level="国家级", region="全国", province="", city="", date="2026-06-16"),
    dict(title="新版《鼓励外商投资产业目录》修订出台", summary="新版目录延续对外资研发中心进口科研用品免税政策，引导外资投向先进制造、现代服务业、高新技术、节能环保等领域。", url="https://finance.cctv.com/2026/06/23/ARTIjiolej2bXVBy4Oa5JYYT260623.shtml", publisher="国家发展改革委、商务部", level="国家级", region="全国", province="", city="", date="2026-06-23"),
    dict(title="《江苏省促进和保护外商投资条例》", summary="元旦起施行，单列“优化服务”一章，鼓励跨国公司设地区总部、利润再投资，强化投资保护、知识产权快速协同保护与投诉机制。", url="https://yrd.huanqiu.com/article/4FzYaO7iUyJ", publisher="江苏省人大常委会", level="省级", region="江苏省", province="江苏省", city="", date="2026-01-01"),
    dict(title="《江苏省2025年稳外资若干措施》（苏政办发〔2025〕19号）", summary="围绕深化重点领域开放、提升服务业开放水平等提出措施，加快南京服务业扩大开放综合试点，推动苏州服务业扩大开放试点方案。", url="https://www.njls.gov.cn/ztzl/yhyshjzt/zcjc/202505/t20250520_5566368.html", publisher="江苏省人民政府办公厅", level="省级", region="江苏省", province="江苏省", city="", date="2025-04-30"),
    dict(title="《南京市2025年稳外资若干措施》", summary="从加大引资支持力度、强化企业服务保障等方面提出措施，支持外资设立研发中心、鼓励利润再投资、强化重大和重点外资项目服务。", url="https://www.nanjing.gov.cn/zdgk/202505/t20250521_5567148.html", publisher="南京市人民政府办公厅", level="市级", region="南京市", province="江苏省", city="南京市", date="2025-05-21"),
    dict(title="《南京市关于支持工业企业增资扩产的若干政策措施》（宁政办规字〔2026〕1号）", summary="围绕市场需求、技术变革、总部生态等6类施策，明确支持外资企业追加投资增资扩产，鼓励外资企业利润再投资。", url="https://nqt.nanjing.gov.cn/nqtmh/njyst/pages/policy_market_detail.html?policyguid=865E8C96-1666-4C0F-828C-F219C17C7D52", publisher="南京市人民政府办公厅", level="市级", region="南京市", province="江苏省", city="南京市", date="2026-01-10"),
    dict(title="《关于加快培育新质生产力推动高质量发展的若干政策（2026年版）》南京", summary="落实制造业外资准入限制“清零”，对符合方向的外资利润再投资、债转股或转增注册资本达规模的项目，单个最高给予2000万元支持。", url="https://swt.fj.gov.cn/xxgk/jgzn/jgcs/zmsyqzcyjs/zmzcc_gzdt/202602/t20260227_7102433.htm", publisher="南京市人民政府", level="市级", region="南京市", province="江苏省", city="南京市", date="2026-02-27"),
    dict(title="南京江北新区外资扩量提质若干措施", summary="聚焦“3+3+X”产业体系精准招商，对世界500强及大型跨国公司外资项目给予实到外资奖励，最高可达3000万元。", url="https://www.njnaexport.cn/618%e7%bd%91%e7%bb%9c%e9%9b%86%e4%b8%ad%e4%bf%83%e9%94%80%e5%90%88%e8%a7%84%e6%8f%90%e7%a4%ba%e5%8f%91%e5%b8%83/", publisher="南京江北新区", level="区级", region="南京市江北新区", province="江苏省", city="南京市", date="2026-03-01"),
    dict(title="《上海市优化营商环境条例》修订（2026年1月1日施行）", summary="明确对标国际高标准经贸规则，鼓励和促进外商投资，扩大服务贸易、数字贸易开放，在自贸区实行外商投资试验性政策。", url="http://www.why.com.cn/epublish/qnb/html/2025-11/27/content_119_39268.htm", publisher="上海市人大常委会", level="市级", region="上海市", province="上海市", city="上海市", date="2026-01-01"),
    dict(title="苏州被纳入国家服务业扩大开放综合试点", summary="商务部将苏州等9城市纳入服务业扩大开放综合试点，赋予159项试点任务，涵盖电信、医疗康养、金融、商贸文旅等领域。", url="https://www.toutiao.com/article/7593928075348345354/", source_pub="苏州发布", publisher="商务部、苏州市", level="市级", region="苏州市", province="江苏省", city="苏州市", date="2026-01-11"),
    dict(title="江苏加力塑造开放型经济新优势（外资研发中心培育政策）", summary="省商务厅与省科技厅联合出台政策加强外资研发中心培育支持，推进生物医药全产业链开放创新、服务业扩大开放等国家级试点。", url="https://new.qq.com/rain/a/20260618A01VTT00?refer=cp_1009", publisher="江苏省商务厅、科技厅", level="省级", region="江苏省", province="江苏省", city="", date="2026-06-18"),

    # ---------- 省级政策（补全多省，解决省级仅江苏问题）----------
    dict(title="《广东省2026年优化国际化一流营商环境工作方案》", summary="广东省商务厅、省委外事办联合印发，落实放宽外资准入政策，优化省领导联系跨国企业直通车机制，常态化举办外资企业圆桌会，2026年新增认定一批跨国公司地区总部和外资研发中心，落实《广东省外商投资权益保护条例》。", url="http://dgfao.dg.gov.cn/index/news/10980.html", publisher="广东省商务厅、省委外事办", level="省级", region="广东省", province="广东省", city="", date="2026-02-10"),
    dict(title="《浙江省推动经济高质量发展若干政策（2026年版）》", summary="浙江省人民政府印发，强化双向投资合作，实施新一轮外资招引促进政策，落实境外投资者利润再投资税收抵免、外商投资项目进口设备减免税，组织“投资浙里”全球大招商境内外活动500场以上。", url="https://hqpt.jxt.zj.gov.cn/zjhqpt/views/policy/detail.html?id=60843", publisher="浙江省人民政府", level="省级", region="浙江省", province="浙江省", city="", date="2026-01-15"),
    dict(title="《山东省2026年全省商务工作要点》", summary="山东省商务厅印发，围绕优化营商环境更有效吸引利用外资，举办跨国公司领导人青岛峰会、港澳山东周等重大招商活动，推进跨国股权并购，聚焦互联网平台、新能源汽车、半导体等重点领域加大引资力度。", url="http://commerce.shandong.gov.cn/art/2026/2/4/art_106468_10366157.html?xxgkhide=1", publisher="山东省商务厅", level="省级", region="山东省", province="山东省", city="", date="2026-02-04"),
    dict(title="《四川省进一步鼓励外商投资设立研发中心的若干措施》", summary="四川省科技厅等16部门联合印发，围绕六大优势产业引导外商在川设立研发中心，对符合条件、上年度研发投入达50万美元的外资研发中心择优给予每个项目最高200万元支持。", url="https://jhj.sc.gov.cn/scjhj/c112684/2024/12/30/70d40dec72ad4d3e99ee26c40b87d7d1.shtml", publisher="四川省科学技术厅等16部门", level="省级", region="四川省", province="四川省", city="", date="2024-12-30"),
    dict(title="《海南省市场监督管理局第二批外资企业登记便利化措施》", summary="海南省市场监督管理局发布，依据《海南自由贸易港外商投资条例》等，推出承认已办公证认证材料、优化境外证件身份核验等服务措施，服务自贸港封关运作，便利外资企业来琼投资登记。", url="https://amr.hainan.gov.cn//jdhy/zxjd/202605/t20260522_4079676.html", publisher="海南省市场监督管理局", level="省级", region="海南省", province="海南省", city="", date="2026-05-16"),
    dict(title="《辽宁省商务领域优化营商环境若干措施》", summary="辽宁省商务厅印发，围绕贸易便利化、外资保护促进、对外投资合作、利企便民服务四方面推出举措，严格执行《外商投资法》及负面清单，建立省市县三级服务体系对重点外资企业实行三级包保。", url="https://credit.mot.gov.cn/xinyongdongtai/202601/t20260120_4198131.html", publisher="辽宁省商务厅", level="省级", region="辽宁省", province="辽宁省", city="", date="2026-01-20"),
    dict(title="《上海市鼓励外商投资企业境内再投资若干措施》（再投资20条）", summary="上海市发改委、商务委等11部门联合印发，从推动项目落地、便利投资经营、落实税收政策、优化投资促进四个维度提出20条措施，取消外商投资性公司使用境内贷款限制，鼓励外资以利润扩大境内再投资。", url="https://www.163.com/dy/article/KIJEJUN80534A4SC.html?spss=dy_author", publisher="上海市发展改革委、商务委等11部门", level="市级", region="上海市", province="上海市", city="上海市", date="2026-01-06"),

    # ---------- 港澳台相关政策 ----------
    dict(title="《关于促进两岸经济文化交流合作的若干措施》（“31条惠台措施”）", summary="国务院台办、国家发改委等31个部门联合发布31条措施，涵盖产业、财税、用地、金融、就业、教育、文化等领域，为台资企业提供同等待遇。", url="http://www.gwytb.gov.cn/m/xwdt/201802/t20180228_11912700.htm", publisher="国务院台办、国家发改委", level="国家级", region="全国", province="", city="", date="2018-02-28"),
    dict(title="《内地与香港关于建立更紧密经贸关系的安排》（CEPA）", summary="内地与香港签署CEPA，确立货物贸易零关税、服务贸易自由化、贸易投资便利化等制度安排，为港资进入内地提供稳定可预期的政策框架。", url="https://www.tid.gov.hk/sc/trade_with_mainland_CEPA/index.html", publisher="商务部、香港特区政府", level="国家级", region="全国", province="", city="", date="2003-06-29"),
    dict(title="《横琴粤澳深度合作区建设总体方案》", summary="中共中央、国务院印发总体方案，明确横琴合作区战略定位、发展目标、产业布局和制度创新，为澳资进入横琴、促进澳门经济适度多元发展提供顶层政策支撑。", url="https://www.gov.cn/zhengce/2021-09/05/content_5636483.htm", publisher="中共中央、国务院", level="国家级", region="广东省", province="广东省", city="珠海市", date="2021-09-05"),

    # ---------- 更多省级/市级政策（解决政策不全）----------
    dict(title="安徽省《关于巩固拓展经济稳中向好势头若干政策举措》（2026年“三十条”）", summary="安徽省出台2026年“三十条”，统筹省级资金350.2亿元，实施“徽动全球”出海行动，办好世界制造业大会、RCEP地方政府暨友城合作（黄山）论坛、“海客圆桌会”，对新认定省级外资研发中心给予奖励。", url="https://www.ah.gov.cn/zwyw/jryw/565497491.html", publisher="安徽省人民政府", level="省级", region="安徽省", province="安徽省", city="", date="2026-02-14"),
    dict(title="安徽省稳外资16条举措", summary="安徽省商务厅出台稳外资16条，对投资新兴产业、利润再投资及设立研发中心和地区总部给予支持，建立制造业重大外资项目“绿色通道”，探索外资企业注册登记容缺受理、外商再投资外汇免登记试点。", url="https://commerce.ah.gov.cn/public/21711/123399801.html", publisher="安徽省商务厅", level="省级", region="安徽省", province="安徽省", city="", date="2026-02-14"),
    dict(title="湖北省《聚焦支点建设打造一流营商环境若干措施》", summary="湖北省政府办公厅印发措施，落实制造业领域外资准入限制“清零”，推进服务业扩大开放综合试点，推动外资项目增资扩股，提升与欧洲、日韩合作层级，用好进博会等平台策划招商，打造“投资中国·优选湖北”品牌。", url="https://new.qq.com/rain/a/20260424A02CMP00", publisher="湖北省人民政府办公厅", level="省级", region="湖北省", province="湖北省", city="", date="2026-04-24"),
    dict(title="河北省2026年四大举措营造高水平利用外资环境", summary="河北省商务厅2026年聚焦“引得来、落得下、留得住、发展好”，在驻天津/上海/广州办事处设“河北招商会客厅”，为外资项目开辟绿色通道、容缺受理，常态化举办“燕赵会客厅”外资企业圆桌会。", url="http://m1.tibet.cn/cn/Instant/news/202603/t20260302_7937950.html", publisher="河北省商务厅", level="省级", region="河北省", province="河北省", city="", date="2026-03-02"),
    dict(title="陕西自贸试验区落实17项改革举措放宽外资准入", summary="陕西自贸试验区实施提升战略，放宽外资准入：允许外商独资设立经营性职业技能培训机构、港澳台医生开设诊所、知名仲裁机构设业务机构，鼓励外商投资设立全球性区域性研发中心，建立生物医药进口研发用品“白名单”。", url="https://big5.china.com.cn/gate/big5/slzg.china.com.cn/2026-04/20/content_43402159.htm", publisher="陕西省自贸办", level="省级", region="陕西省", province="陕西省", city="", date="2026-04-20"),
    dict(title="《无锡市优化营商环境行动方案（2026版）》", summary="无锡市出台2026版优化营商环境方案，省内率先出台支持外资企业境内再投资“10条”、稳外贸稳就业16条，落地集成电路进口危化品“白名单”试点，港澳商务签注“智能速办”，升级锡企服务平台与AI数字管家。", url="https://www.wuxi.gov.cn/doc/2026/05/27/4782120.shtml", publisher="无锡市人民政府", level="市级", region="无锡市", province="江苏省", city="无锡市", date="2026-05-27"),
    dict(title="《苏州市激发产业创新活力专项行动方案》（苏政发〔2026〕55号）", summary="江苏省政府印发苏州专项行动方案，鼓励外商投资企业利润再投资、在苏州设立地区总部与研发中心，落实制造业外资准入限制“清零”，开展独资医院开放试点，推动“大中小、内外资”企业融通发展。", url="https://www.js.gov.cn/art/2026/6/29/art_64797_11796086.html", publisher="江苏省人民政府", level="市级", region="苏州市", province="江苏省", city="苏州市", date="2026-06-01"),
]

# ============ 四大攻坚产业情报库（industry_intel）============
# 供“四大攻坚产业动态”模块点击产业后展示：头部跨国公司 + 全球/在华动态 + 产业研判
# companies: 头部跨国公司（name/country/dynamic/url）；analysis: 面向南京产业攻坚的研判
INDUSTRY_INTEL = {
    "人工智能(软件)": {
        "analysis": "全球AI竞争进入“研发本土化+生态绑定”阶段。英伟达、微软等持续在华布局研发中心，但受出口管制影响部分外企在华研发布局出现调整（如亚马逊关闭上海AI实验室），呈现“有进有退”。南京软件产业基础雄厚、高校人才密集，应聚焦行业大模型、智能体（Agent）、AI+工业软件等应用层与工具层，承接外企研发外包、联合实验室与生态合作，规避底层算力受制于人风险。",
        "companies": [
            {"name": "英伟达", "country": "美国", "dynamic": "上海张江新办公楼启用，在华员工近4000人、上海研发中心超2000人，聚焦芯片设计验证与自动驾驶研究。", "url": "https://www.eeo.com.cn/2026/0125/782771.shtml"},
            {"name": "微软", "country": "美国", "dynamic": "在上海张江人工智能岛设AI&IoT实验室，提供端到端IoT方案验证，与IBM等共建开放创新生态。", "url": "http://www.urlou.com/news/show-8129.html"},
            {"name": "亚马逊", "country": "美国", "dynamic": "2026年4月关闭上海最后一家AI研究中心，反映中美科技博弈下外企在华研发布局的阶段性调整。", "url": "https://www.vpshk.cn/20260438038.html"},
        ],
    },
    "机器人": {
        "analysis": "外资机器人巨头加速在华“本土化制造+系统集成”。ABB、库卡（美的）、发那科、安川等纷纷落子扩产，竞争从“卖本体”转向“机器人本体+移动机器人+智能物流+行业解决方案”全场景。南京可依托智能制造与汽车、电子产业需求，重点承接工业机器人集成应用、具身智能（人形机器人核心零部件）、智能物流产线，并争取外企区域应用展示与培训中心。",
        "companies": [
            {"name": "ABB", "country": "瑞士", "dynamic": "投资约1.5亿美元、占地6.7万㎡的机器人超级工厂在上海浦东康桥投产，未来在华销售九成以上产品在此生产。", "url": "https://www.iseee.cn?p=/ShopNews/detail/zs/208/id/151"},
            {"name": "美的库卡", "country": "德国", "dynamic": "华东智能制造中心签约落户昆山，增资3000万美元，达产年产值预计超30亿元，六大业务板块首次在华东协同。", "url": "https://www.iianews.com/ca/_01-ABC00000000000371518.shtml"},
            {"name": "发那科", "country": "日本", "dynamic": "上海机器人超级工厂持续扩产，深耕中国高端制造，与广州、重庆基地协同服务全国。", "url": "https://www.ciie.org/zbh/bqxwbd/20260408/58821.html"},
            {"name": "安川", "country": "日本", "dynamic": "在华布局工业机器人及运动控制，常州、常州武进等地持续深耕，服务长三角装备制造集群。", "url": "https://www.ciie.org/zbh/bqxwbd/20260408/58821.html"},
        ],
    },
    "生物医药": {
        "analysis": "跨国药企掀起“千亿级”在华投资热潮，战略从“在中国卖药”全面升级为“在中国研发、生产、共创”，聚焦细胞与基因治疗、放射配体疗法、GLP-1、RSV疫苗等高壁垒赛道。南京生物医药（基因与细胞治疗、创新药、CXO）基础扎实，应争取跨国药企研发合作、临床转化与特色原料药/制剂生产基地，并借力“健康中国2030”将生物医药列为新兴支柱产业的窗口期。",
        "companies": [
            {"name": "阿斯利康", "country": "英国", "dynamic": "2030年前在华投资超1000亿元，广州建RDC基地、上海建细胞疗法基地、北京建全球第六大研发中心，并与清华共建AI药物研发联合中心。", "url": "https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html"},
            {"name": "诺华", "country": "瑞士", "dynamic": "2026年新增超33亿元在华投资，扩建北京昌平工厂与上海园区，浙江海盐建中国首个放射配体药品生产基地。", "url": "https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html"},
            {"name": "礼来", "country": "美国", "dynamic": "未来十年在华投资30亿美元，扩建苏州工厂，布局GLP-1减重与代谢药物本土化产能，累计在华投资近60亿美元。", "url": "https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html"},
            {"name": "罗氏", "country": "瑞士", "dynamic": "投资20.4亿元在张江建中国第二个创新药生产基地（眼科药物），苏州诊断工厂扩建为亚太最重要生产基地。", "url": "https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html"},
            {"name": "赛诺菲", "country": "法国", "dynamic": "北京亦庄10亿欧元胰岛素原料药基地开工（在华最大单笔投资），上海研发中心升级为最大转化医学研究中心。", "url": "https://www.21jingji.com/article/20260323/herald/82a6eaf862e9baccbd6ccc8a83f91485.html"},
        ],
    },
    "新一代信息通信": {
        "analysis": "6G进入标准前夜、AI原生网络成产业共识。爱立信、诺基亚、高通、三星等在华深度参与6G研发与标准制定，MWC2026集中展示太赫兹、智能超表面（RIS）、通感一体（ISAC）等方向。南京可布局6G试验网、通信芯片设计、AI网络（自智网络）与卫星互联网配套，依托紫金山实验室等载体争取外企联合研发与试验场景合作。",
        "companies": [
            {"name": "高通", "country": "美国", "dynamic": "MWC2026发布AI原生新一代连接与终端平台，展示AI原生6G架构（太赫兹、RIS、ISAC、数字孪生网络）。", "url": "https://www.toutiao.com/article/7613521933497385512"},
            {"name": "爱立信", "country": "瑞典", "dynamic": "提出Intelligent Fabric智能织网理念，强调下一代网络需具备感知、预测、决策、执行全链路AI能力，参与6G通感一体验证。", "url": "https://www.toutiao.com/article/7613521933497385512"},
            {"name": "诺基亚", "country": "芬兰", "dynamic": "强化AI在RAN与核心网中的自动化价值，聚焦自优化、自愈合、节能降耗，帮助运营商提升ROI。", "url": "https://www.toutiao.com/article/7613521933497385512"},
            {"name": "三星", "country": "韩国", "dynamic": "展示6G在超高速率、超低时延、通感融合方面的潜力，围绕沉浸式通信与全域无缝覆盖布局。", "url": "https://www.toutiao.com/article/7613521933497385512"},
        ],
    },
}

def enrich_items():
    out = []
    for i, it in enumerate(RAW_ITEMS, 1):
        d = dict(it)
        d["id"] = f"inv{i:03d}"
        d["category"] = "investment" if it["event_type"] in INVEST_TYPES else "exchange"
        d["is_jiangsu"] = (it.get("province") == "江苏省")
        d["is_nanjing"] = (it.get("city") == "南京市")
        d["image"] = it.get("image", "")  # 轮播用：留空则前端用行业渐变兜底；生产爬虫会填入文章 og:image
        out.append(d)
    return out

def enrich_policies():
    out = []
    for i, p in enumerate(RAW_POLICIES, 1):
        d = dict(p)
        d["id"] = f"pol{i:03d}"
        out.append(d)
    return out

def main():
    items = enrich_items()
    # 合并自动检索增量（auto_items.json，由 WorkBuddy 定时任务写入）
    # 与人工基线去重（url + 归一化标题），按日期降序，截断到 500 条。
    auto_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_items.json")
    if os.path.exists(auto_path):
        try:
            with open(auto_path, encoding="utf-8") as f:
                auto = json.load(f)
            seen = {(x.get("url"), norm_title(x.get("title", ""))) for x in items}
            for a in auto:
                key = (a.get("url"), norm_title(a.get("title", "")))
                if key in seen:
                    continue
                items.append(a)
                seen.add(key)
        except Exception:
            pass
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    if len(items) > 500:
        items = items[:500]
    policies = enrich_policies()
    # AI 研判：独立文件 ai_insights.json（由 generate_insights.py 按周生成），
    # 此处并入输出，确保每 3 小时的数据刷新不会覆盖 AI 研判内容。
    ai_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_insights.json")
    ai_insights = None
    if os.path.exists(ai_path):
        try:
            with open(ai_path, encoding="utf-8") as f:
                ai_insights = json.load(f)
        except Exception:
            ai_insights = None
    data = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "industries": INDUSTRIES,
        "items": items,
        "policies": policies,
        "industry_intel": INDUSTRY_INTEL,
    }
    if ai_insights:
        data["ai_insights"] = ai_insights
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 同时生成 data.js：用 <script> 加载，兼容本地双击打开(file://)场景
    js_path = os.path.join(here, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("/* 自动生成，请勿手改。由 build_data.py / crawler.py 生成。*/\n")
        f.write("window.DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"已生成 {out_path}")
    print(f"已生成 {js_path}（供本地双击打开使用）")
    print(f"  投资/考察动态: {len(items)} 条 (投资 {sum(1 for x in items if x['category']=='investment')} / 考察经贸 {sum(1 for x in items if x['category']=='exchange')})")
    print(f"  其中 江苏相关: {sum(1 for x in items if x['is_jiangsu'])} 条, 南京相关: {sum(1 for x in items if x['is_nanjing'])} 条")
    print(f"  政策文件: {len(policies)} 条 (国家级 {sum(1 for x in policies if x['level']=='国家级')} / 省级 {sum(1 for x in policies if x['level']=='省级')} / 市级 {sum(1 for x in policies if x['level']=='市级')} / 区级 {sum(1 for x in policies if x['level']=='区级')})")
    print(f"  四大产业情报: {len(INDUSTRY_INTEL)} 个产业 (头部跨国公司合计 {sum(len(v['companies']) for v in INDUSTRY_INTEL.values())} 家)")
    if ai_insights:
        print(f"  AI 研判: 已并入（生成于 {ai_insights.get('generated_at','')}）")
    else:
        print("  AI 研判: 未找到 ai_insights.json（请先运行 generate_insights.py）")

if __name__ == "__main__":
    main()
