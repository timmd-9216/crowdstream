#!/usr/bin/env bash
set -e

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

./kill_audio.sh # kill all audio processes

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# activar venv
source venv/bin/activate

# sanity check (opcional pero recomendable)
which python
python --version

sleep_if_rpi 3

# Ensure playlist CSV exists (try to generate, fallback to existing selected CSV)
CSV_NAME="track_data_Cm-Gm_122-d3.csv"
if [ ! -f "$CSV_NAME" ]; then
	echo "CSV '$CSV_NAME' not found — attempting to generate with struct_loader.py..."
	set +e
	./venv/bin/python struct_loader.py \
		--bpm 122 --delta 2 --key "Cm,Gm" \
		--rekordbox-xml track_data_rekordbox.xml \
		--csv-out "$CSV_NAME" \
		--n-sections 3 \
		--parts-dir parts_temp_26
	rc=$?
	set -e
	if [ $rc -ne 0 ]; then
		if [ -f selected26.csv ]; then
			echo "struct_loader failed (rc=$rc). Copying 'selected26.csv' → '$CSV_NAME' as fallback."
			cp selected26.csv "$CSV_NAME"
		else
			echo "struct_loader failed (rc=$rc) and no 'selected26.csv' fallback found. Exiting." >&2
			exit 1
		fi
	else
		echo "CSV generated: $CSV_NAME"
	fi
fi

# Ensure we're in the audio-mixer directory for relative paths to work
cd "$SCRIPT_DIR"

# Run audio_server.py from current directory (audio-mixer/)
# Filters are disabled by default (use --enable-filters to enable)
python audio_server.py --port 57122 &
sleep_if_rpi 8  # Wait for audio server to fully initialize (ALSA probing takes time on RPi)
sleep 2

# Run mixer.py with correct search root for parts_temp_26
python mixer.py --preflight-only --search-root "$SCRIPT_DIR/parts_temp_26" #run first time, to generate a csv?
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters --search-root "$SCRIPT_DIR/parts_temp_26" &
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters --search-root "$SCRIPT_DIR/parts_temp_26" &
#python mixer_3tracks.py --host 0.0.0.0 --port 57120 &
# Use localhost as destination for OSC client (0.0.0.0 is invalid as a target).
# mixer_tracks.py reads paths from CSV (relative paths like parts_temp_26/...)
# so we need to be in audio-mixer directory for them to resolve correctly
python mixer_tracks.py --host 127.0.0.1 --port 57122 --movement-port 57120 --csv "$CSV_NAME" &
#python mixer.py --host 127.0.0.1 --port 57120 &

# Con filtros estándar (slower pero funciona sin scipy)
#python audio_server.py --enable-filters
