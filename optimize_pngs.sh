#!/usr/bin/env bash
# Compressão SEM PERDA dos PNGs do projeto (roda no lugar).
# oxipng é o mais rápido/eficiente; optipng é o fallback.
set -e
cd "$(dirname "$0")"
if command -v oxipng >/dev/null; then
  oxipng -o4 --strip safe -r images maps
else
  find images maps -name '*.png' -print0 | xargs -0 -n1 -P4 optipng -quiet -o5 -strip all
fi
