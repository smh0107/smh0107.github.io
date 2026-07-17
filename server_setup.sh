#!/usr/bin/env bash
# ============================================================
# 南京市外商投资动态监测平台 — 腾讯云 Ubuntu 22.04 一键部署脚本
# 适用：新购轻量应用服务器（南京/上海地域，系统镜像 Ubuntu 22.04）
# 用法：
#   1) 把本文件传到服务器（或用 vim 直接粘贴内容新建）
#   2) chmod +x server_setup.sh
#   3) sudo ./server_setup.sh
# 原理：
#   - 本机（大陆网络）无法直接抓取 Google News/GDELT，故“每3小时自动更新”
#     由 GitHub Actions（海外节点）完成：爬取最新数据 → 提交回仓库；
#   - 本服务器仅每3小时 git pull 拉取最新 data.json，由 nginx 对外提供。
#   - 因此：国内访问稳定 + 数据每3小时自动刷新，唯一成本为服务器（几十元/月）。
# ============================================================
set -e

APP_DIR=/var/www/fdi
REPO_URL=https://github.com/smh0107/smh0107.github.io.git
BRANCH=main

echo "==[1/5]== 安装依赖（nginx / git / python3 / certbot）"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx git python3 certbot python3-certbot-nginx

echo "==[2/5]== 克隆仓库到 $APP_DIR"
mkdir -p /var/www
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "目录已存在，执行 git pull 更新"
  cd "$APP_DIR" && git pull --ff-only origin "$BRANCH"
fi

echo "==[3/5]== 配置 nginx（监听80端口，托管静态站点）"
cat > /etc/nginx/sites-available/fdi.conf <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/fdi;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
    # data.json 为实时数据，禁用缓存，保证每3小时自动更新即时生效
    location = /data.json {
        add_header Cache-Control "no-store";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/fdi.conf /etc/nginx/sites-enabled/fdi.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "==[4/5]== 配置每3小时自动拉取并重新生成数据"
# GitHub Actions 在海外跑爬虫，把“人工基线 + 增量”合并后的干净数据提交回仓库；
# 本机每3小时 git pull 拉最新代码与 auto_items.json，再用 build_data.py 以
# “人工基线 + 增量”重新生成干净 data.json（即便仓库 data.json 有异常也不受影响）。
cat > /etc/cron.d/fdi-update <<CRON
# m h dom mon dow user  command
0 */3 * * * root cd /var/www/fdi && git checkout -- data.json data.js 2>/dev/null; git pull --ff-only origin $BRANCH >>/var/log/fdi-update.log 2>&1 && python3 build_data.py >>/var/log/fdi-update.log 2>&1
CRON
echo "已写入 /etc/cron.d/fdi-update"

echo "==[5/5]== 完成"
IP=$(curl -s -m 10 https://api.ipify.org || echo "你的服务器公网IP")
echo "=============================================="
echo " 部署完成！请用浏览器访问："
echo "   http://$IP"
echo "（若打不开，请到腾讯云控制台“防火墙”放行 80 端口）"
echo ""
echo " 如需 HTTPS（绑定已备案域名后执行）："
echo "   sudo certbot --nginx -d 你的域名"
echo "=============================================="
