# Function to detect Raspberry Pi
is_raspberry_pi() {
    if [ -f /proc/cpuinfo ]; then
        if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
            return 0
        fi
    fi
    if [ -f /sys/firmware/devicetree/base/model ]; then
        if grep -qi "raspberry" /sys/firmware/devicetree/base/model 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Function to sleep only on Raspberry Pi
sleep_if_rpi() {
    local duration=$1
    if is_raspberry_pi; then
        sleep "$duration"
    fi
}

source src/audio-engine/venv/bin/activate


python audio_server.py --port 57120 --disable-filters &
sleep_if_rpi 5
python mixer.py --preflight-only 
#python mixer.py --host 127.0.0.1 --port 57120 &
python mixer.py --host 0.0.0.0 --port 57120 &
