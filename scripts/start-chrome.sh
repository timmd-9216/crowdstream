export DISPLAY=:0.0
killall chromium
PORT=$1
#chromium http://localhost:8082 --start-fullscreen
chromium http://localhost:$PORT --start-fullscreen --disable-session-crashed-bubble

