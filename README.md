# 南京市外商投资动态监测平台

面向南京市商务·外国投资管理处的外商投资工作辅助系统。自动聚合全网可检索的
**外国来华投资、来华考察、经贸交流**，以及**国家 / 省 / 市三级外商投资政策**，
按南京“1+4+6”攻坚办产业口径分类呈现，供招商与外资管理决策参考。

> 数据来源为**免费、公开、可检索**的渠道（Google News RSS、GDELT 全球新闻库），
> 非“爬遍整个互联网”，而是“定时聚合多源 + 智能分类”，更新频率为**每 3 小时**。

---

## 一、目录结构

```
.
├── index.html        # 页面骨架（左侧 6 模块导航 + 顶栏）
├── style.css         # 样式（深蓝主 + 江苏红，政务简洁风）
├── app.js           # 前端逻辑（数据加载 / 6 模块渲染 / 筛选 / 页码翻页 / 图表）
├── data.json        # 数据（前端 fetch 的数据源，由下方脚本生成）
├── data.js          # 同份数据以 window.DATA 形式提供，供“双击本地文件”直接打开
├── build_data.py    # 手工录入 / 初始生成 data.json（已内置一批真实样例数据）
├── crawler.py       # 生产级自动爬虫：每 3 小时抓取并重新生成 data.json
├── logo_white.png   # 左上角“南京商务”白色 Logo（透明底，显示于深蓝栏）
└── README.md
```

字段约定见文末“数据字段说明”。所有文本均为中文；每条动态 / 政策均带可点击的**原文链接**。

---

## 二、本地预览（看效果）

**方式一：直接双击打开（最简单）**
直接双击 `index.html` 即可。页面会通过 `data.js`（`<script>` 加载，不受 file:// 限制）读取数据，
无需启动服务器。适合日常本地查看、传给同事离线打开。

**方式二：HTTP 方式打开（推荐，更接近线上环境）**

```bash
cd 项目目录
python -m http.server 8099
# 浏览器访问 http://localhost:8099
```

---

## 三、部署到公网（两种形态）

### 形态 A：快速公网展示（当前数据快照）
直接把本目录作为静态站点托管到任意支持静态托管的平台（如 CloudStudio / Nginx / 对象存储 + CDN），
即可获得一个公网可访问的网址。当前 `data.json` 已含一批真实最新数据，开箱即看。

> 此形态数据是“快照”，要更新内容需在能出网的服务器上跑爬虫（见形态 B），或本地重跑 `build_data.py` 后重新上传。

### 形态 B：生产级自动刷新（推荐长期使用）
在你方**可正常访问外网**的服务器（Linux / Windows 均可）上：

1. 安装 Python 3.10+，把本目录上传到服务器；
2. 安装依赖（仅标准库，通常无需额外安装；如需可建虚拟环境）；
3. 设置定时任务，每 3 小时运行一次 `crawler.py`：

**Linux（crontab）：**
```bash
crontab -e
# 每 3 小时执行一次
0 */3 * * *  cd /path/to/project && /usr/bin/python3 crawler.py >>crawl.log 2>&1
```

**Windows（任务计划程序）：**
- 触发器：每隔 3 小时
- 操作：启动程序 `python.exe`，参数 `crawler.py`，起始于项目目录

4. 用同样的静态托管方式对外提供 `index.html` 访问。

`crawler.py` 会自动抓取 → 分类（国家 / 行业 10 类 / 活动类型 / 江苏·南京标记）→ 去重 →
覆盖 `data.json` 的 `items` 部分；**政策文件 `policies` 由人工维护，不会被爬虫覆盖**（见第五节）。

---

## 四、手动维护数据

- **重新生成整份动态数据（用内置真实样例）：** `python build_data.py`
- **直接编辑数据：** 用任意文本编辑器打开 `data.json`，按文末字段说明增删 `items` 条目，保存即可（页面刷新后生效）。
- **调整初始样例：** 编辑 `build_data.py` 顶部的 `RAW_ITEMS` / `RAW_POLICIES` 列表后重跑。

---

## 五、如何修改配置与外观

| 想改什么 | 在哪里改 |
|---|---|
| 左侧 6 个模块名称 | `app.js` 顶部 `TITLES` |
| 行业分类口径（10 类） | `app.js` 的 `DATA.industries`（同时改 `build_data.py` / `crawler.py` 顶部的 `INDUSTRIES`） |
| 每页显示条数 | `app.js` 顶部 `PAGE_SIZE`（默认 10） |
| 右上角机构名 | `index.html` 中 `topbar-org` 文本 |
| 左上角 Logo | 替换 `logo_white.png`（白色图形 + 透明底） |
| 爬虫关键词 / 抓取量 / 数据源 | `crawler.py` 顶部 `GOOGLE_QUERIES` / `GDELT_QUERIES` / `--max` |
| 自动刷新频率 | 定时任务的触发间隔（cron / 任务计划程序） |

---

## 六、数据字段说明（data.json）

`items[]`（动态）每条：
`id, title, summary, url, source, country, industry, event_type,
 category("investment"投资 / "exchange"考察经贸), region, province, city,
 date, is_jiangsu(bool), is_nanjing(bool)`

`policies[]`（政策）每条：
`id, title, summary, url, publisher, level(国家级/省级/市级/区级),
 region, province, city, date`

模块与字段的对应关系（前端自动计算，无需手工标模块）：
- **总览** → 全部 `items` + 统计
- **外商来华投资动态** → `category == "investment"`（全国含江苏）
- **外商来苏投资动态** → `category == "investment"` 且 `is_jiangsu == true`（江苏含南京）
- **来华考察·经贸交流** → `category == "exchange"`
- **四大攻坚产业动态** → `industry` 属于 {人工智能(软件)、机器人、生物医药、新一代信息通信}
- **各级外商投资政策文件** → `policies`（按 level 筛选，未出台的不显示）

---

## 七、合规与说明

- 抓取对象为公开可检索的新闻 / 政策信源与官方发布，遵循平台 robots 与合理访问频率；
  政府用途下建议以**授权 API + 官方信源 + RSS** 为主，避免对商业站点无授权高频爬取。
- 本系统为**决策辅助**工具，新闻内容以原文链接为准，摘要由系统自动生成，引用前请核对原文。
- 当前 `data.json` 由检索整理的真实公开信息填充，部署到可出网服务器后由 `crawler.py` 持续自动更新。
