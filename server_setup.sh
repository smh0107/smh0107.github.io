#!/usr/bin/env bash
# ============================================================
# 南京市外商投资动态监测平台 — 腾讯云 Ubuntu 22.04 一键部署脚本
# 适用：新购轻量应用服务器（南京/上海地域，系统镜像 Ubuntu 22.04）
# 用法：
#   chmod +x server_setup.sh
#   echo '你的密码' | sudo -S bash server_setup.sh
# 说明：
#   - 大陆服务器无法直接 git clone github.com（被墙），故改为用 curl 从
#     raw.githubusercontent.com 拉取站点文件（已验证服务器可稳定访问）。
#   - “每3小时自动更新”由 GitHub Actions（海外节点，可抓 Google News/GDELT）
#     完成：爬取最新数据 → 提交回仓库；本服务器每3小时 curl 拉取最新 data.json。
#   - 因此：国内访问稳定 + 数据每3小时自动刷新，唯一成本为服务器（几十元/月）。
# ============================================================
set -e

APP_DIR=/var/www/fdi
RAW="https://raw.githubusercontent.com/smh0107/smh0107.github.io/main"
# 站点必需文件（静态前端 + 数据 + Logo）
FILES="index.html style.css app.js data.json data.js logo_white.png"

echo "==[1/5]== 安装依赖（nginx / git / python3 / certbot）"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx git python3 certbot python3-certbot-nginx

echo "==[2/5]== 从 raw.githubusercontent.com 拉取站点文件到 $APP_DIR"
mkdir -p "$APP_DIR"
cd "$APP_DIR"
for f in $FILES; do
  for try in 1 2 3; do
    if curl -fsSL --retry 2 -m 60 "$RAW/$f" -o "$f"; then
      echo "  [OK] $f ($(wc -c < "$f") 字节)"
      break
    else
      echo "  [重试 $try] 下载 $f 失败"
      sleep 3
    fi
  done
done

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

echo "==[4/5]== 配置每3小时自动拉取最新数据"
# 从 raw.githubusercontent.com 拉取最新 data.json / data.js（海外 Actions 已生成好），
# 下载成功才原子替换，避免网络抖动时丢失已有数据。
cat > /usr/local/bin/fdi-update.sh <<'UPD'
#!/usr/bin/env bash
RAW="https://raw.githubusercontent.com/smh0107/smh0107.github.io/main"
APP_DIR=/var/www/fdi
cd "$APP_DIR" || exit 1
for f in data.json data.js; do
  if curl -fsSL --retry 2 -m 60 "$RAW/$f" -o "$f.tmp"; then
    mv -f "$f.tmp" "$f"
    echo "$(date) [OK] 更新 $f"
  else
    echo "$(date) [WARN] 拉取 $f 失败，保留旧数据"
  fi
done
UPD
chmod +x /usr/local/bin/fdi-update.sh

cat > /etc/cron.d/fdi-update <<'CRON'
# m h dom mon dow user  command
0 */3 * * * root /usr/local/bin/fdi-update.sh >>/var/log/fdi-update.log 2>&1
CRON
echo "已写入 /etc/cron.d/fdi-update 与 /usr/local/bin/fdi-update.sh"

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
