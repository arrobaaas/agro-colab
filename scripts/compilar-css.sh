#!/usr/bin/env bash
# Compila frontend/css/tailwind.css con el ejecutable oficial de Tailwind
# (no requiere Node). Descarga una versión fija y verifica su checksum
# SHA-256 contra el publicado por Tailwind antes de ejecutarla.
#
# Uso:  bash scripts/compilar-css.sh
# Volver a ejecutarlo después de agregar clases nuevas al HTML o al JS.
set -euo pipefail

VERSION="v3.4.17"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$RAIZ/.tailwind"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)  BINARIO="tailwindcss-linux-x64" ;;
  Linux-aarch64) BINARIO="tailwindcss-linux-arm64" ;;
  Darwin-arm64)  BINARIO="tailwindcss-macos-arm64" ;;
  Darwin-x86_64) BINARIO="tailwindcss-macos-x64" ;;
  *) echo "Plataforma no soportada: $(uname -s)-$(uname -m)"; exit 1 ;;
esac

mkdir -p "$CACHE"
URL="https://github.com/tailwindlabs/tailwindcss/releases/download/$VERSION"

if [ ! -x "$CACHE/$BINARIO-$VERSION" ]; then
  echo "Descargando Tailwind $VERSION ($BINARIO)..."
  curl -sSfL -o "$CACHE/$BINARIO-$VERSION" "$URL/$BINARIO"
  curl -sSfL -o "$CACHE/sha256sums-$VERSION.txt" "$URL/sha256sums.txt"

  ESPERADO="$(grep " $BINARIO\$" "$CACHE/sha256sums-$VERSION.txt" | cut -d' ' -f1)"
  OBTENIDO="$(sha256sum "$CACHE/$BINARIO-$VERSION" | cut -d' ' -f1)"
  if [ -z "$ESPERADO" ] || [ "$ESPERADO" != "$OBTENIDO" ]; then
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
