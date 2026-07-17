# -*- coding: utf-8 -*-
"""
gen_china_map.py —— 把中国省级 GeoJSON 转成前端可用的 SVG path 数据。

输入：china_raw.json（DataV 中国省级边界，由 build_data 流程下载）
输出：china_map.js（window.CHINA_MAP = { viewBox, provinces:[{name, short, d}] }）

- 采用等距圆柱投影（Web Mercator 风格 y），使中国轮廓自然；坐标取整缩减体积。
- short 仅用于与数据 province 字段匹配、以及悬停 tooltip 显示，地图上不渲染省名。
- 海域/九段线等附属要素若含独立 feature，一并输出（无数据时渲染为浅色，不影响热区）。
"""
import json, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'china_raw.json')


def norm(n):
    """省级全称 → 简称，用于与数据 province 字段匹配。"""
    if not n:
        return ''
    alias = {'中国台湾': '台湾', '中国香港': '香港', '中国澳门': '澳门'}
    if n in alias:
        return alias[n]
    n = (n.replace('维吾尔自治区', '').replace('壮族自治区', '').replace('回族自治区', '')
          .replace('自治区', '').replace('省', '').replace('市', ''))
    return n


def proj_merc(lon, lat):
    """等距圆柱投影（线性），使中国轮廓呈熟悉的“横宽”形态。"""
    return lon, -lat


def iter_coords(geom):
    t = geom['type']
    c = geom['coordinates']
    if t == 'Polygon':
        for ring in c:
            for pt in ring:
                yield pt
    elif t == 'MultiPolygon':
        for poly in c:
            for ring in poly:
                for pt in ring:
                    yield pt


def ring_path(ring, sx, sy, minx, maxy):
    pts = []
    for lon, lat in ring:
        x, y = proj_merc(lon, lat)
        px = round((x - minx) * sx, 1)
        py = round((maxy - y) * sy, 1)
        pts.append(f'{px} {py}')
    return 'M' + ' L'.join(pts) + ' Z'


def geom_path(geom, sx, sy, minx, maxy):
    t = geom['type']
    c = geom['coordinates']
    parts = []
    if t == 'Polygon':
        for ring in c:
            parts.append(ring_path(ring, sx, sy, minx, maxy))
    elif t == 'MultiPolygon':
        for poly in c:
            for ring in poly:
                parts.append(ring_path(ring, sx, sy, minx, maxy))
    return ' '.join(parts)


def main():
    with open(RAW, encoding='utf-8') as f:
        gj = json.load(f)

    # 第一遍：全局包围盒
    xs, ys = [], []
    for feat in gj['features']:
        g = feat.get('geometry')
        if not g:
            continue
        for lon, lat in iter_coords(g):
            x, y = proj_merc(lon, lat)
            xs.append(x)
            ys.append(y)
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    W = 1000.0
    sx = W / (maxx - minx)
    sy = sx
    H = round((maxy - miny) * sy, 1)

    provinces = []
    for feat in gj['features']:
        name = (feat.get('properties') or {}).get('name', '')
        g = feat.get('geometry')
        if not g:
            continue
        d = geom_path(g, sx, sy, minx, maxy)
        provinces.append({'name': name, 'short': norm(name), 'd': d})

    out = {'viewBox': f'0 0 {W:.0f} {H:.0f}', 'provinces': provinces}
    with open(os.path.join(HERE, 'china_map.js'), 'w', encoding='utf-8') as f:
        f.write('/* 自动生成：中国省级 SVG 地图路径。由 gen_china_map.py 从 china_raw.json 转换，请勿手改。*/\n')
        f.write('window.CHINA_MAP = ')
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print(f'已生成 china_map.js：{len(provinces)} 个省级单元，viewBox {out["viewBox"]}')
    print('  short 示例：', [p["short"] for p in provinces[:8]])


if __name__ == '__main__':
    main()
