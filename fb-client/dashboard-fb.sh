#!/bin/bash
# eink-dashboard display client (dedicated HDMI, 24/7).
# Writes the dashboard PNG straight to the framebuffer (/dev/fb0) as raw BGRA
# via ImageMagick — NO fbi (fbi's black background + VT churn render badly on
# e-ink). Change-gated: only re-fetches + redraws when /version changes, so the
# e-ink refreshes only on real updates. On outage, keeps the last good image.
SERVER="${DASHBOARD_SERVER:-https://dash.plexlab.site}"
TMP=/run/dashboard.png
FB=/dev/fb0
last=""

# Framebuffer geometry (e.g. 3200x1800). Stride is WxH*4 (no line padding),
# so a contiguous WxH*4 BGRA blob maps 1:1 onto the panel.
read -r W H < <(tr ',' ' ' < /sys/class/graphics/fb0/virtual_size 2>/dev/null)
: "${W:=3200}" "${H:=1800}"

# Keep the console from ever clobbering the image: no blanking/powersave, no
# cursor, quiet kernel messages, clear any text.
setterm --blank 0 --powersave off --cursor off > /dev/tty1 2>/dev/null || true
dmesg -n 1 2>/dev/null || true
printf '\033[2J\033[3J\033[H' > /dev/tty1 2>/dev/null || true

draw() {
    [ -s "$TMP" ] || return
    convert "$TMP" -resize "${W}x${H}!" -depth 8 "bgra:$FB" 2>/dev/null
}

while :; do
    ver=$(curl -sk --max-time 8 "$SERVER/version" 2>/dev/null)
    if [ -n "$ver" ] && [ "$ver" != "$last" ]; then
        if curl -sk --max-time 20 -o "${TMP}.new" "$SERVER/dashboard.png" 2>/dev/null && [ -s "${TMP}.new" ]; then
            mv -f "${TMP}.new" "$TMP"
            draw
            last="$ver"
        fi
    fi
    sleep 30
done
