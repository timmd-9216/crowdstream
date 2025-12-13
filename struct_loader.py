"""Utility for loading DJ structure JSON files into a single mapping.

Each JSON file in the target directory is assumed to describe one track.
The returned mapping uses the JSON file name (without extension) as the key
and the parsed JSON document as the value.
"""

from __future__ import annotations

import argparse
import csv
import json
import wave
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass
import subprocess
import shutil

DEFAULT_STRUCT_DIR = Path(__file__).resolve().parent.parent / "stems" / "dj" / "struct"
DEFAULT_AUDIO_DIR = Path(__file__).resolve().parent.parent / "stems" / "dj"


def search_tracks(
    tracks: Dict[str, "Track"],
    bpm: float | None = None,
    delta: float = 2.0,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    key: str | None = None,
) -> List["Track"]:
    """Filter tracks by BPM range and optional key.

    BPM filtering:
      - If bpm_min/bpm_max provided, use that range (inclusive).
      - Else if bpm provided, use [bpm - delta, bpm + delta] (inclusive).
      - Else no BPM filtering.

    Key filtering:
      - Comma-separated list of keys (case-insensitive, e.g., 'Gm,Cm').
      - If key is None/empty, no key filtering.
    """
    key_norm = (key or "").strip()
    key_list = [k.strip().lower() for k in key_norm.split(",") if k.strip()] if key_norm else []
    use_key = bool(key_list)

    if bpm_min is not None or bpm_max is not None:
        lo = bpm_min if bpm_min is not None else float("-inf")
        hi = bpm_max if bpm_max is not None else float("inf")
    elif bpm is not None:
        lo = bpm - delta
        hi = bpm + delta
    else:
        lo = float("-inf")
        hi = float("inf")

    results: List[Track] = []
    for t in tracks.values():
        if not (lo <= t.bpm <= hi):
            continue
        if use_key:
            if t.key.strip().lower() not in key_list:
                continue
        results.append(t)

    # Deterministic ordering
    results.sort(key=lambda x: x.path)
    return results

@dataclass
class Segment:
    start: float
    end: float
    label: str


@dataclass
class TempoMarker:
    inizio: float
    bpm: float
    metro: str
    battito: int


@dataclass
class RekordboxTrack:
    track_id: int
    name: str
    average_bpm: float
    location: str
    tonality: str
    total_time: int
    tempos: List[TempoMarker]

@dataclass
class Track:
    path: str
    bpm: float
    beats: List[float]
    downbeats: List[float]
    beat_positions: List[int]
    segments: List[Segment]
    speed: float
    key: str

def _decimal_places(value: float) -> int:
    """Return the number of decimal places in the original float representation."""
    text = f"{value}"
    if "." not in text:
        return 0
    fractional = text.split(".")[1].rstrip("0")
    return len(fractional)

def _scale_with_same_decimals(values: List[float], factor: float) -> List[float]:
    """Scale each value by factor, keeping the same number of decimal places."""
    scaled: List[float] = []
    for v in values:
        decimals = _decimal_places(v)
        new_v = v * factor
        if decimals > 0:
            new_v = round(new_v, decimals)
        scaled.append(new_v)
    return scaled

def transform(track: Track, target_bpm: float) -> Track:
    """Return a new Track adjusted to target_bpm, scaling time fields and setting speed."""
    if track.bpm == 0:
        raise ValueError("Cannot transform a track with bpm = 0")

    factor = target_bpm / track.bpm

    new_beats = _scale_with_same_decimals(track.beats, factor)
    new_downbeats = _scale_with_same_decimals(track.downbeats, factor)

    new_segments: List[Segment] = []
    for seg in track.segments:
        start_decimals = _decimal_places(seg.start)
        end_decimals = _decimal_places(seg.end)
        new_start = seg.start * factor
        new_end = seg.end * factor
        if start_decimals > 0:
            new_start = round(new_start, start_decimals)
        if end_decimals > 0:
            new_end = round(new_end, end_decimals)
        new_segments.append(
            Segment(
                start=new_start,
                end=new_end,
                label=seg.label,
            )
        )

    return Track(
        path=track.path,
        bpm=target_bpm,
        beats=new_beats,
        downbeats=new_downbeats,
        beat_positions=list(track.beat_positions),
        segments=new_segments,
        speed=factor,
        key=track.key,
    )

def ini_cue(track: Track) -> float | None:
    """Return the end time of the last 'intro' segment in the track."""
    intros = [seg for seg in track.segments if seg.label.lower() == "intro"]
    if not intros:
        return None
    return intros[-1].end


def end_cue(track: Track, n_sections: int = 2) -> float | None:
    """Return the end time of the n-th segment counting from ini_cue (1-indexed).

    We treat ini_cue as a boundary time. The "first" section after ini_cue is the
    first segment whose start time is >= ini_cue.
    """
    ini = ini_cue(track)
    if ini is None:
        return None
    if n_sections <= 0:
        return None

    # Find the first segment starting at/after the ini_cue boundary
    start_idx: int | None = None
    for i, seg in enumerate(track.segments):
        if seg.start >= ini:
            start_idx = i
            break

    if start_idx is None:
        return None

    target_idx = start_idx + (n_sections - 1)
    if target_idx >= len(track.segments):
        return None

    return track.segments[target_idx].end

def begin_cue(track: Track, n_sections: int = 6) -> float | None:
    """Return the start time of the n-th segment counting from ini_cue (1-indexed).

    This mirrors end_cue(), but returns the start time of the selected segment.
    """
    ini = ini_cue(track)
    if ini is None:
        return None
    if n_sections <= 0:
        return None

    start_idx: int | None = None
    for i, seg in enumerate(track.segments):
        if seg.start >= ini:
            start_idx = i
            break

    if start_idx is None:
        return None

    target_idx = start_idx + (n_sections - 1)
    if target_idx >= len(track.segments):
        return None

    return track.segments[target_idx].start


def write_wav_section(
    src_wav: str | Path,
    dst_wav: str | Path,
    start_sec: float,
    end_sec: float,
    out_framerate: int | None = None,
) -> None:
    """Write a cropped WAV segment [start_sec, end_sec] (seconds) to dst_wav."""
    src_path = Path(src_wav).expanduser()
    dst_path = Path(dst_wav).expanduser()
    if not src_path.is_file():
        raise FileNotFoundError(f"Source WAV not found: {src_path}")
    if end_sec <= start_sec:
        raise ValueError(f"Invalid section: start={start_sec}, end={end_sec}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(src_path), "rb") as wf:
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        start_frame = int(round(start_sec * framerate))
        end_frame = int(round(end_sec * framerate))
        start_frame = max(0, min(start_frame, n_frames))
        end_frame = max(0, min(end_frame, n_frames))
        if end_frame <= start_frame:
            raise ValueError(f"Invalid frame window after clamp: {start_frame}..{end_frame}")

        wf.setpos(start_frame)
        data = wf.readframes(end_frame - start_frame)
        params = wf.getparams()

    with wave.open(str(dst_path), "wb") as out:
        if out_framerate is None:
            out.setparams(params)
        else:
            # params: (nchannels, sampwidth, framerate, nframes, comptype, compname)
            out.setparams(params._replace(framerate=int(out_framerate)))
        out.writeframes(data)


# --- ffmpeg tempo helpers ---


def write_wav_section_speed_ffmpeg(
    src_wav: str | Path,
    dst_wav: str | Path,
    start_sec: float,
    end_sec: float,
    speed: float,
) -> None:
    """Crop [start_sec, end_sec] then tempo-adjust by `speed` using ffmpeg.

    - speed > 1.0 speeds up (higher BPM)
    - speed < 1.0 slows down
    - Output is standard PCM WAV (sample rate stays normal)
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH; cannot tempo-adjust audio")

    src_path = Path(src_wav).expanduser()
    dst_path = Path(dst_wav).expanduser()
    if not src_path.is_file():
        raise FileNotFoundError(f"Source WAV not found: {src_path}")
    if end_sec <= start_sec:
        raise ValueError(f"Invalid section: start={start_sec}, end={end_sec}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if not (0.5 <= speed <= 2.0):
        raise ValueError(f"ffmpeg atempo supports speed in [0.5, 2.0]; got {speed}")

    filt = f"atempo={speed:.8f}"

    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start_sec),
        "-to",
        str(end_sec),
        "-i",
        str(src_path),
        "-filter:a",
        filt,
        "-acodec",
        "pcm_s16le",
        str(dst_path),
    ]

    subprocess.run(cmd, check=True)


# --- Helper: format seconds as M:SS.ss for debugging durations ---
def _fmt_mmss(seconds: float | None) -> str:
    """Format seconds as M:SS.ss for easier debugging."""
    if seconds is None:
        return ""
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = seconds - 60 * m
    return f"{m}:{s:05.2f}"

def write_selected_tracks_csv(
    tracks: List[Track],
    csv_path: str | Path,
    n_sections: int = 6,
    parts_dir: str | Path = Path(__file__).resolve().parent / "parts_temp",
    target_bpm: float | None = None,
    audio_dir: str | Path | None = None,
) -> None:
    """Write selected tracks to CSV and create section WAVs.

    - Discards tracks where begin_cue or end_cue are missing.
    - Writes cropped WAVs to parts_dir named <stem>_sectioned.wav
      cropping the original file by (ini_cue, end_cue).
    - Also writes a speed-adjusted WAV <stem>_sectioned_speed.wav by changing output framerate.

    Timing output:
      - ini is assumed to be 0 for the exported part.
      - speed = target_bpm / original_bpm (if target_bpm provided, else 1.0)
      - begin_cue_adj = (begin_cue - ini_cue) / speed  # time within the sped-up part (ini=0)
      - end_cue_adj   = (end_cue   - ini_cue) / speed  # time within the sped-up part (ini=0)
    """
    out_csv = Path(csv_path).expanduser()
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    parts = Path(parts_dir).expanduser()
    parts.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "bpm",
                "key",
                "target_bpm",
                "speed",
                "ini_cue",
                "begin_cue",
                "end_cue",
                "begin_cue_adj",
                "end_cue_adj",
                "duration_orig",
                "duration_sectioned",
                "part_file_orig",
                "part_file",
            ],
        )
        writer.writeheader()

        for t in tracks:
            ic = ini_cue(t)
            bc = begin_cue(t, n_sections=n_sections)
            ec = end_cue(t, n_sections=n_sections)

            # Discard row if cues are missing
            if ic is None or bc is None or ec is None:
                continue

            tbpm = float(target_bpm) if target_bpm is not None else t.bpm
            if tbpm == 0:
                continue

            # Speed factor to bring original BPM to target BPM
            # Example: original 120 -> target 122 => speed = 122/120 (>1, speeds up)
            speed = tbpm / t.bpm
            if speed == 0:
                continue

            begin_cue_adj = (bc - ic) / speed
            end_cue_adj = (ec - ic) / speed

            if audio_dir:
                # Prefer provided audio directory; fall back to original path if file not found.
                candidate = Path(audio_dir) / Path(t.path).name
                src = candidate if candidate.is_file() else Path(t.path)
            else:
                src = Path(t.path)

            if not src.is_file():
                # Skip tracks whose audio file is unavailable.
                continue
            part_path = parts / f"{src.stem}_sectioned.wav"

            parts_orig = parts / "orig"
            parts_orig.mkdir(parents=True, exist_ok=True)
            part_orig_path = parts_orig / f"{src.stem}_sectioned.wav"

            # True tempo change to target BPM using ffmpeg (atempo), keeping normal WAV sample rate
            write_wav_section_speed_ffmpeg(src, part_path, float(ic), float(ec), speed=speed)

            # Also write an original-speed cut for debugging / comparison
            write_wav_section(src, part_orig_path, float(ic), float(ec))

            duration_orig_sec = float(ec) - float(ic)

            duration_sectioned_sec: float | None = None
            try:
                with wave.open(str(part_path), "rb") as pf:
                    duration_sectioned_sec = pf.getnframes() / float(pf.getframerate())
            except Exception:
                duration_sectioned_sec = None

            writer.writerow(
                {
                    "path": t.path,
                    "bpm": t.bpm,
                    "key": t.key,
                    "target_bpm": tbpm,
                    "speed": speed,
                    "ini_cue": ic,
                    "begin_cue": bc,
                    "end_cue": ec,
                    "begin_cue_adj": begin_cue_adj,
                    "end_cue_adj": end_cue_adj,
                    "duration_orig": _fmt_mmss(duration_orig_sec),
                    "duration_sectioned": _fmt_mmss(duration_sectioned_sec),
                    "part_file_orig": str(part_orig_path),
                    "part_file": str(part_path),
                }
            )


# --- Rekordbox XML parsing ---
def parse_rekordbox_xml(xml_path: str | Path) -> List[RekordboxTrack]:
    """Parse a Rekordbox track collection XML into OO records.

    Notes
    -----
    - Rekordbox encodes file paths in the TRACK Location attribute (URI form).
    - Tempo change points appear as nested <TEMPO .../> elements.
    """
    xml_file = Path(xml_path).expanduser()
    if not xml_file.is_file():
        raise FileNotFoundError(f"Rekordbox XML not found: {xml_file}")

    tree = ET.parse(xml_file)
    root = tree.getroot()

    collection = root.find("COLLECTION")
    if collection is None:
        return []

    tracks: List[RekordboxTrack] = []
    for tr in collection.findall("TRACK"):
        tempos: List[TempoMarker] = []
        for t in tr.findall("TEMPO"):
            tempos.append(
                TempoMarker(
                    inizio=float(t.get("Inizio", "0") or 0),
                    bpm=float(t.get("Bpm", "0") or 0),
                    metro=t.get("Metro", "") or "",
                    battito=int(t.get("Battito", "0") or 0),
                )
            )

        location = tr.get("Location", "") or ""
        decoded_location = unquote(location)

        tracks.append(
            RekordboxTrack(
                track_id=int(tr.get("TrackID", "0") or 0),
                name=tr.get("Name", "") or "",
                average_bpm=float(tr.get("AverageBpm", "0") or 0),
                location=decoded_location,
                tonality=tr.get("Tonality", "") or "",
                total_time=int(tr.get("TotalTime", "0") or 0),
                tempos=tempos,
            )
        )

    return tracks


# --- Helpers for Rekordbox BPM override ---
def _rekordbox_location_to_path(location: str) -> str:
    """Convert Rekordbox TRACK Location (URI) into a local filesystem path string."""
    loc = (location or "").strip()
    if loc.startswith("file://localhost"):
        loc = loc[len("file://localhost") :]
    elif loc.startswith("file://"):
        loc = loc[len("file://") :]
    # Ensure leading slash for absolute paths on macOS/Linux
    if loc and not loc.startswith("/"):
        loc = "/" + loc
    return str(Path(loc).expanduser())


def _norm_path(p: str) -> str:
    """Normalize a filesystem path for matching (case-insensitive)."""
    try:
        return str(Path(p).expanduser()).strip().lower()
    except Exception:
        return (p or "").strip().lower()


def build_rekordbox_bpm_index(xml_path: str | Path) -> Dict[str, float]:
    """Return mapping of normalized audio file path -> AverageBpm from Rekordbox XML."""
    rb_tracks = parse_rekordbox_xml(xml_path)
    idx: Dict[str, float] = {}
    for t in rb_tracks:
        fs_path = _rekordbox_location_to_path(t.location)
        k = _norm_path(fs_path)
        if not k:
            continue
        # Prefer non-zero BPM if present
        bpm = float(t.average_bpm or 0.0)
        if bpm > 0:
            idx[k] = bpm
    return idx


# --- Helper functions for Rekordbox Tonality merging ---

def _normalize_name(text: str) -> str:
    """Normalize track identifiers for matching."""
    return (text or "").strip().lower()


def build_rekordbox_tonality_index(xml_path: str | Path) -> Dict[str, str]:
    """Return a mapping of normalized track name -> Tonality."""
    rb_tracks = parse_rekordbox_xml(xml_path)
    index: Dict[str, str] = {}
    for t in rb_tracks:
        name_key = _normalize_name(t.name)
        if name_key and t.tonality:
            index[name_key] = t.tonality
    return index


def apply_rekordbox_keys_to_struct_dir(struct_dir: str | Path, xml_path: str | Path) -> int:
    """Update each *.json in struct_dir to include a 'key' from Rekordbox Tonality.

    Matching rule:
      - If a Rekordbox TRACK Name is contained in the JSON's 'path' (case-insensitive),
        we assign that Tonality to JSON field 'key'.
    Returns the number of JSON files updated.
    """
    tonality_by_name = build_rekordbox_tonality_index(xml_path)
    if not tonality_by_name:
        return 0

    base = Path(struct_dir).expanduser()
    if not base.is_dir():
        raise NotADirectoryError(f"Struct directory does not exist: {base}")

    updated = 0
    for json_path in sorted(base.glob("*.json")):
        data: Dict[str, Any]
        with json_path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        track_path = _normalize_name(str(data.get("path", "")))
        if not track_path:
            continue

        matched_key: str | None = None
        matched_tonality: str | None = None
        for name_key, tonality in tonality_by_name.items():
            if name_key and name_key in track_path:
                matched_key = name_key
                matched_tonality = tonality
                break

        if matched_tonality and data.get("key") != matched_tonality:
            data["key"] = matched_tonality
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            updated += 1

    return updated


def load_track_structs(struct_dir: str | Path) -> Dict[str, Any]:
    """Load all ``*.json`` files from ``struct_dir`` into a dictionary.

    Parameters
    ----------
    struct_dir:
        Directory containing JSON files for each track. The file's stem (file
        name without extension) is used as the dictionary key.

    Returns
    -------
    dict
        Mapping of ``{file_stem: json_contents}`` for every ``*.json`` file in
        the directory. Files are processed in sorted order to keep deterministic
        output.
    """

    base = Path(struct_dir).expanduser()
    if not base.is_dir():
        raise NotADirectoryError(f"Struct directory does not exist: {base}")

    tracks: Dict[str, Any] = {}
    for json_path in sorted(base.glob("*.json")):
        with json_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        key = json_path.stem
        if key in tracks:
            raise ValueError(f"Duplicate track key encountered: {key}")
        segments_data = data.get("segments", [])
        segments: List[Segment] = [
            Segment(
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                label=seg.get("label", ""),
            )
            for seg in segments_data
        ]

        tracks[key] = Track(
            path=data.get("path", ""),
            bpm=float(data.get("bpm", 0)),
            beats=[float(b) for b in data.get("beats", [])],
            downbeats=[float(d) for d in data.get("downbeats", [])],
            beat_positions=[int(p) for p in data.get("beat_positions", [])],
            segments=segments,
            speed=1.0,
            key=str(data.get("key", "") or ""),
        )

    return tracks


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load all JSON track struct files from a directory and emit a single "
            "dictionary keyed by file name."
        )
    )
    parser.add_argument(
        "struct_dir",
        nargs="?",
        default=DEFAULT_STRUCT_DIR,
        help="Directory containing track JSON files (default: repo-relative stems/dj/struct)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Optional path to write the aggregated JSON mapping; prints to stdout when omitted.",
    )
    parser.add_argument("--bpm", type=float, help="Center BPM for search (used with --delta).")
    parser.add_argument(
        "--target-bpm",
        type=float,
        default=None,
        help="BPM to export sectioned files at (time-stretch target). If omitted, defaults to --bpm.",
    )
    parser.add_argument(
        "--delta",
        type=float,
        default=2.0,
        help="BPM +/- range around --bpm (default: 2.0).",
    )
    parser.add_argument("--bpm-min", type=float, help="Minimum BPM (inclusive) for search.")
    parser.add_argument("--bpm-max", type=float, help="Maximum BPM (inclusive) for search.")
    parser.add_argument(
        "--key",
        type=str,
        help="Musical key(s) to match (comma-separated, case-insensitive). Example: 'Gm,Cm'.",
    )
    parser.add_argument(
        "--csv-out",
        type=Path,
        help="Write selected tracks to this CSV file.",
    )
    parser.add_argument(
        "--n-sections",
        type=int,
        default=6,
        help="Segment number (1-indexed) used to compute end_cue (default: 6).",
    )
    parser.add_argument(
        "--parts-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "parts_temp",
        help="Directory where cropped section WAVs are written (default: ./parts_temp).",
    )
    parser.add_argument(
        "--rekordbox-xml",
        type=Path,
        default=None,
        help="Optional Rekordbox XML to override JSON bpm using AverageBpm (matched by file path).",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=DEFAULT_AUDIO_DIR,
        help="Directory containing WAV files; matched by filename (default: repo-relative stems/dj).",
    )
    args = parser.parse_args()

    tracks = load_track_structs(args.struct_dir)
    if args.rekordbox_xml is not None:
        bpm_idx = build_rekordbox_bpm_index(args.rekordbox_xml)
        if bpm_idx:
            for trk in tracks.values():
                k = _norm_path(trk.path)
                if k in bpm_idx:
                    trk.bpm = bpm_idx[k]

    matches = search_tracks(
        tracks,
        bpm=args.bpm,
        delta=args.delta,
        bpm_min=args.bpm_min,
        bpm_max=args.bpm_max,
        key=args.key,
    )

    # Drop tracks without an intro-based ini_cue
    matches = [t for t in matches if ini_cue(t) is not None]

    # Drop tracks missing begin/end cues for the requested n_sections
    matches = [
        t
        for t in matches
        if begin_cue(t, n_sections=args.n_sections) is not None
        and end_cue(t, n_sections=args.n_sections) is not None
    ]

    if args.csv_out:
        write_selected_tracks_csv(
            matches,
            args.csv_out,
            n_sections=args.n_sections,
            parts_dir=args.parts_dir,
            target_bpm=args.target_bpm or args.bpm,
            audio_dir=args.audio_dir,
        )

    for t in matches:
        print(t.path)


if __name__ == "__main__":
    _main()
