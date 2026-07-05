#!/usr/bin/env bash
# 產生 SMSBridge 自簽 TLS 憑證（用於 WiFi 直連場景）
# 產出：server/certs/server.crt + server/certs/server.key
# 使用：bash scripts/gen-certs.sh [--host 192.168.1.100] [--host 127.0.0.1]

set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/../server/certs" && pwd)"
HOSTS=()

# 解析參數
while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOSTS+=("$2"); shift 2 ;;
        *) echo "usage: $0 [--host <ip>] ..."; exit 1 ;;
    esac
done

if [[ ${#HOSTS[@]} -eq 0 ]]; then
    HOSTS=("127.0.0.1")
fi

mkdir -p "$CERT_DIR"

# 建立 OpenSSL 設定（加入 SAN 支援 Android 信任檢查）
CONFIG="$CERT_DIR/openssl.cnf"
cat > "$CONFIG" <<EOF
[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
x509_extensions    = v3_req

[dn]
CN = SMSBridge

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
EOF

for i in "${!HOSTS[@]}"; do
    echo "DNS.${i}" | tr -d '\n' >> "$CONFIG"
    printf ".$((i+1)) = ${HOSTS[$i]}\n" >> "$CONFIG"
    is_ip=0
    if [[ "${HOSTS[$i]}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "IP.$((i+1)) = ${HOSTS[$i]}" >> "$CONFIG"
    fi
done

# 產生憑證 + 私鑰
openssl req -x509 -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -config "$CONFIG" \
    -days 3650 \
    -nodes 2>/dev/null

rm -f "$CONFIG"
echo ""
echo "✅ 自簽憑證已產生："
echo "   憑證: $CERT_DIR/server.crt"
echo "   私鑰: $CERT_DIR/server.key"
echo "   主機: ${HOSTS[*]}"
echo ""
echo "啟動方式:"
echo "   uv run smsbridge start --tls-cert $CERT_DIR/server.crt --tls-key $CERT_DIR/server.key"
echo ""
echo "或在 .env 加入："
echo "   TLS_CERTFILE=$CERT_DIR/server.crt"
echo "   TLS_KEYFILE=$CERT_DIR/server.key"
echo ""
echo "⚠️  自簽憑證不被 Android 原生信任。手機端需先安裝 server.crt 至信任憑證。"
echo "   推送到手機: adb push $CERT_DIR/server.crt /sdcard/Download/"
echo "   然後去 設定 → 安全 → 憑證安裝 → CA 憑證 → 選擇 server.crt"
