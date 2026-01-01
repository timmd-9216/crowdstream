export DISPLAY=:0.0
./scripts/start-all-services.sh --visualizer cosmic_skeleton --no-dashboard
chromium http://localhost:8091 --start-fullscreen --disable-session-crashed-bubble
