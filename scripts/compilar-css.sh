#!/usr/bin/env bash
# Compila frontend/css/tailwind.css con el ejecutable oficial de Tailwind
# (no requiere Node). Descarga una versión fija y verifica su checksum SHA-256
# contra el valor fijado aquí: compararlo con uno descargado del mismo sitio no
# protegería si esa publicación estuviera comprometida.
#
# Uso:  bash scripts/compilar-css.sh
# Volver a ejecutarlo después de agregar clases nuevas al HTML o al JS.
set -euo pipefail

VERSION="v3.4.17"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$RAIZ/.tailwind"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)  BINARIO="tailwindcss-linux-x64";   ESPERADO="7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4" ;;
  Linux-aarch64) BINARIO="tailwindcss-linux-arm64"; ESPERADO="69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b" ;;
  Darwin-arm64)  BINARIO="tailwindcss-macos-arm64"; ESPERADO="a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3" ;;
  Darwin-x86_64) BINARIO="tailwindcss-macos-x64";   ESPERADO="6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3" ;;
  *) echo "Plataforma no soportada: $(uname -s)-$(uname -m)"; exit 1 ;;
esac

mkdir -p "$CACHE"
URL="https://github.com/tailwindlabs/tailwindcss/releases/download/$VERSION"

if [ ! -x "$CACHE/$BINARIO-$VERSION" ]; then
  echo "Descargando Tailwind $VERSION ($BINARIO)..."
  curl -sSfL -o "$CACHE/$BINARIO-$VERSION" "$URL/$BINARIO"
  OBTENIDO="$(sha256sum "$CACHE/$BINARIO-$VERSION" | cut -d' ' -f1)"
  if [ "$ESPERADO" != "$OBTENIDO" ]; then
    echo "ERROR: el checksum no coincide. No se ejecuta el binario."
    rm -f "$CACHE/$BINARIO-$VERSION"
    exit 1
  fi
  echo "Checksum verificado: $OBTENIDO"
  chmod +x "$CACHE/$BINARIO-$VERSION"
fi

cd "$RAIZ"
"$CACHE/$BINARIO-$VERSION" \
  -c tailwind.config.js \
  -i frontend/css/tailwind.entrada.css \
  -o frontend/css/tailwind.css \
  --minify

echo "Listo: frontend/css/tailwind.css ($(wc -c < frontend/css/tailwind.css) bytes)"
