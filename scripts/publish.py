"""
publish.py — genera el catálogo JSON para el CDN y hace git push.

Entrada esperada (--input): JSON o CSV con tracks. Ejemplos:

JSON:  [{ "artist": "...", "title": "...", "style": "House",
          "youtube_id": "...", "bpm": 126, "key": "8A",
          "energy": 0.75, "duration_seconds": 420,
          "year": 2024, "label": "..." }]

CSV:   artist,title,style,youtube_id,bpm,key,energy,duration_seconds,year,label

Uso:
    python scripts/publish.py --input mis_tracks.json
    python scripts/publish.py --input mis_tracks.csv --push
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
STYLES_DIR = ROOT / 'styles'

REQUIRED_FIELDS = {'artist', 'title', 'style'}
OPTIONAL_DEFAULTS = {
    'youtube_id': '',
    'bpm': None,
    'key': '',
    'musicalKey': '',
    'energy': None,
    'danceability': None,
    'duration': None,        # seconds (int)
    'year': None,
    'label': '',
    'tags': [],
}


def make_id(track: dict) -> str:
    raw = f"{track['artist'].lower().strip()}|{track['title'].lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize(track: dict) -> dict:
    out = {**OPTIONAL_DEFAULTS, **track}
    out['id'] = make_id(track)
    # accept duration_seconds as alias for duration
    if 'duration_seconds' in out and not out.get('duration'):
        out['duration'] = out.pop('duration_seconds')
    elif 'duration_seconds' in out:
        out.pop('duration_seconds')

    for f in ('bpm', 'duration', 'year'):
        if out[f] is not None:
            try:
                out[f] = int(float(out[f]))
            except (ValueError, TypeError):
                out[f] = None
    for f in ('energy', 'danceability'):
        if out[f] is not None:
            try:
                out[f] = round(float(out[f]), 3)
            except (ValueError, TypeError):
                out[f] = None
    if isinstance(out['tags'], str):
        out['tags'] = [t.strip() for t in out['tags'].split(',') if t.strip()]
    return out


def load_json(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def load_csv(path: str) -> list[dict]:
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def load_input(path: str) -> list[dict]:
    ext = Path(path).suffix.lower()
    if ext == '.csv':
        return load_csv(path)
    return load_json(path)


def validate(tracks: list[dict]) -> list[dict]:
    out = []
    for i, t in enumerate(tracks):
        missing = REQUIRED_FIELDS - set(t.keys())
        if missing:
            print(f"  [skip] track {i}: missing {missing}")
            continue
        if not t.get('artist') or not t.get('title') or not t.get('style'):
            print(f"  [skip] track {i}: empty required field")
            continue
        out.append(normalize(t))
    return out


def build_catalog(tracks: list[dict]) -> dict[str, list]:
    by_style: dict[str, list] = {}
    for t in tracks:
        style = t['style']
        by_style.setdefault(style, []).append(t)
    return by_style


def style_filename(style: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', style.lower()).strip('-')
    return f"{slug}.json"


def write_catalog(by_style: dict[str, list], version: str) -> dict:
    STYLES_DIR.mkdir(exist_ok=True)
    files = {}
    counts = {}
    for style, tracks in sorted(by_style.items()):
        fname = style_filename(style)
        payload = {'style': style, 'version': version, 'tracks': tracks}
        out_path = STYLES_DIR / fname
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        files[style] = f'styles/{fname}'
        counts[style] = len(tracks)
        print(f"  {style}: {len(tracks)} tracks → styles/{fname}")
    return files, counts


def write_manifest(version: str, styles: list, counts: dict, files: dict):
    manifest = {
        'version': version,
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'styles': sorted(styles),
        'track_counts': counts,
        'files': files,
    }
    with open(ROOT / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  manifest.json → version {version}, {sum(counts.values())} tracks total")


def git_push(message: str):
    cmds = [
        ['git', 'add', 'manifest.json', 'styles/'],
        ['git', 'commit', '-m', message],
        ['git', 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  git error: {result.stderr.strip()}")
            return
    print("  Pushed to GitHub Pages")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to JSON or CSV input file')
    parser.add_argument('--push', action='store_true', help='git add + commit + push after generating')
    parser.add_argument('--version', default='', help='Version string (default: YYYY.MM.DD.N)')
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    version = args.version or now.strftime('%Y.%m.%d.1')

    print(f"\n==> Loading {args.input}")
    raw = load_input(args.input)
    print(f"    {len(raw)} rows read")

    print("==> Validating...")
    tracks = validate(raw)
    print(f"    {len(tracks)} valid tracks")

    print("==> Building catalog...")
    by_style = build_catalog(tracks)

    print("==> Writing JSON files...")
    files, counts = write_catalog(by_style, version)
    write_manifest(version, list(by_style.keys()), counts, files)

    if args.push:
        print("==> Pushing to GitHub Pages...")
        git_push(f"catalog: {version} ({sum(counts.values())} tracks)")

    print("\nDone.")


if __name__ == '__main__':
    main()
