#!/usr/bin/env bash
# Generuje ikony PNG aplikacji z plików SVG w public/icons/ (źródło prawdy).
# Uruchamiać ręcznie po zmianie SVG; wynikowe PNG są w repozytorium, więc build ich nie generuje.
#
# Wymagania: Firefox (tryb headless robi zrzut SVG w zadanym rozmiarze) oraz Python 3 z Pillow.
# Zrzut ekranu nie ma kanału alfa, więc ikona jest renderowana obok siebie na czarnym i białym tle
# (jeden zrzut), a przezroczystość wynika z różnicy: alfa = 1 − (biały − czarny), kolor = czarny / alfa.
set -euo pipefail

cd "$(dirname "$0")/.."
ICONS="$PWD/public/icons"
# Firefox ze snapa (Ubuntu) widzi tylko nieukryte katalogi w $HOME, więc pracujemy w jego katalogu.
if [ -d "$HOME/snap/firefox/common" ]; then
  WORK="$(mktemp -d "$HOME/snap/firefox/common/kupto-icons.XXXXXX")"
else
  WORK="$(mktemp -d)"
fi
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/profile"

shot() { # shot <svg> <rozmiar> <wynik.png> — po lewej ikona na czarnym tle, po prawej na białym
  local svg="$1" size="$2" out="$3"
  cp "$svg" "$WORK/icon.svg"
  cat >"$WORK/page.html" <<EOF
<!doctype html><html><body style="margin:0;display:flex">
<div style="background:#000"><img src="icon.svg" style="display:block;width:${size}px;height:${size}px"></div>
<div style="background:#fff"><img src="icon.svg" style="display:block;width:${size}px;height:${size}px"></div>
</body></html>
EOF
  firefox --headless --no-remote --profile "$WORK/profile" \
    --window-size="$((size * 2)),$size" --screenshot "$out" "file://$WORK/page.html" >/dev/null 2>&1
}

render() { # render <svg> <rozmiar> <wynik.png> <transparent|opaque>
  local svg="$ICONS/$1" size="$2" out="$ICONS/$3" mode="$4"
  shot "$svg" "$size" "$WORK/shot.png"
  python3 - "$WORK/shot.png" "$out" "$size" "$mode" <<'EOF'
import sys
from PIL import Image

shot_path, out, size, mode = sys.argv[1:]
size = int(size)
shot = Image.open(shot_path).convert("RGB")
assert shot.size == (2 * size, size), f"zrzut ma rozmiar {shot.size}, oczekiwano {2 * size}×{size}"
black = shot.crop((0, 0, size, size))
white = shot.crop((size, 0, 2 * size, size))
if mode == "opaque":
    black.save(out, optimize=True)
    sys.exit()
result = Image.new("RGBA", (size, size))
px_b, px_w, px_r = black.load(), white.load(), result.load()
for y in range(size):
    for x in range(size):
        b, w = px_b[x, y], px_w[x, y]
        alpha = 255 - max(0, min(255, round(sum(wc - bc for wc, bc in zip(w, b)) / 3)))
        if alpha == 0:
            px_r[x, y] = (0, 0, 0, 0)
        else:
            px_r[x, y] = tuple(min(255, round(bc * 255 / alpha)) for bc in b) + (alpha,)
result.save(out, optimize=True)
EOF
  echo "  $3 (${size}×${size}, $mode)"
}

echo "Generowanie ikon w $ICONS:"
render icon.svg 192 icon-192.png transparent
render icon.svg 512 icon-512.png transparent
render icon-maskable.svg 512 icon-maskable-512.png opaque
render icon-maskable.svg 180 apple-touch-icon.png opaque
