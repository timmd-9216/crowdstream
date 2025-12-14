export DISPLAY=:0.0
killall chromium
PORT=$1
#chromium http://localhost:8082 --start-fullscreen
#chromium http://localhost:$PORT --start-fullscreen --disable-session-crashed-bubble



chromium \
  --kiosk \
  --start-fullscreen \
  --no-first-run \
  --no-default-browser-check \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-features=TranslateUI \
  --lang=es-AR \
  --user-data-dir=/tmp/chromium-kiosk \
  http://localhost:$PORT 
