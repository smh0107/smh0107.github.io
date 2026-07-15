# -*- coding: utf-8 -*-
"""
append_auto.py —— 自动检索增量写入（供 WorkBuddy 定时任务调用）

从 stdin 读取一个 JSON 数组，每个元素至少含 title / url，可选 source / date / summary。
脚本调用 crawler.classify 补全 country / industry / event_type / category /
region / province / city / is_jiangsu / is_nanjing，再按 url + 归一化标题去重，
追加进 auto_items.json，最多保留 400 条（按日期保留最新）。

用法（由定时任务的助手执行）：
  python append_auto.py  <<'EOF'
  [ {"title":"...","url":"https://...","source":"...","date":"2026-07-14","summary":"..."}, ... ]
  EOF
"""
import json, sys, os, hashlib, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from crawler import classify, norm_title  # 复用同一套分类口径，保证与爬虫/手工一致

PATH = os.path.join(HERE, "auto_items.json")
MAX = 400


def main():
    raw = sys.stdin.read()
    try:
        new_items = json.loads(raw)
    except Exception as e:
        print("ERR 解析 JSON 失败:", e)
        sys.exit(1)
    if not isinstance(new_items, list):
        print("ERR: 期望 JSON 数组")
        sys.exit(1)

    existing = []
    if os.path.exists(PATH):
        try:
            with open(PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    seen_urls = {it.get("url") for it in existing}
    seen_titles = {norm_title(it.get("title", "")) for it in existing}
    added = 0
    for it in new_items:
        url = (it.get("url") or "").strip()
        title = (it.get("title") or "").strip()
        if not url or not title:
            continue
        if url in seen_urls or norm_title(title) in seen_titles:
            continue
        meta = classify(title, it.get("summary", "") or "")
        rec = {
            "id": "auto_" + hashlib.md5(url.encode("utf-8")).hexdigest()[:10],
            "title": title,
            "summary": it.get("summary") or title,
            "url": url,
            "source": it.get("source") or "网络媒体",
            "date": it.get("date") or datetime.datetime.now().strftime("%Y-%m-%d"),
            "image": it.get("image", "") or "",
            **meta
        }
        existing.append(rec)
        seen_urls.add(url)
        seen_titles.add(norm_title(title))
        added += 1

    # 按日期降序，截断到 MAX
    existing.sort(key=lambda x: x.get("date", ""), reverse=True)
    if len(existing) > MAX:
        existing = existing[:MAX]

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"auto_items.json 现有 {len(existing)} 条（本次新增 {added} 条）")


if __name__ == "__main__":
    main()
