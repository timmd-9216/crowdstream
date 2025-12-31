#!/usr/bin/env bash
set -e


# activar venv
source venv/bin/activate

# sanity check (opcional pero recomendable)
which python
python --version

sleep 1
sleep 3

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

python audio_server.py --port 57120 &
sleep 8  # Wait for audio server to fully initialize (ALSA probing takes time)
sleep 2
python mixer.py --preflight-only #run first time, to generate a csv?
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters &
#python mixer.py --host 0.0.0.0 --port 57120 --optimized-filters &
#python mixer_3tracks.py --host 0.0.0.0 --port 57120 &
#python mixer_tracks.py --host 0.0.0.0 --port 57120 &
python mixer_tracks.py --host 127.0.0.1 --port 57120 &
#python mixer.py --host 127.0.0.1 --port 57120 &

# Con filtros estándar (slower pero funciona sin scipy)
#python audio_server.py --enable-filters
