#!/usr/bin/env python3
"""Filter video filenames by Rotten Tomatoes / IMDB scores via OMDb API."""

import sys, re, os, time, argparse
from pathlib import Path
import requests

# -- Config --------------------------------------------------------------------

VIDEO_EXT = re.compile(r"\.(mkv|avi|mp4|part|ts|m4v|mov|wmv)$", re.I)

# -- Helpers -------------------------------------------------------------------

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def parse(raw):
    """Parse a video filename into {title, year, content_type, omdb_type} or None."""
    name = raw.strip().strip("'\"").replace("'\\''", "'").strip()
    if not VIDEO_EXT.search(name):
        return None

    name = re.sub(VIDEO_EXT, "", name)
    name = re.sub(r"^\[\s*[^\]]+\]\s*", "", name)

    tv = re.search(r"[\.\s]S\d{2}(E\d{2})?", name, re.I)
    year, year_pos = None, len(name)
    for pat in [r"\((\d{4})(?:\s*-\s*\d{4})?\)", r"[\.\s](\d{4})[\.\s]", r"[\.\s](\d{4})$"]:
        m = re.search(pat, name)
        if m:
            year, year_pos = m.group(1), m.start()
            break

    # Use resolution (e.g. 1080p) as generic title boundary
    res = re.search(r"[\.\s]\d{3,4}p\b", name, re.I)
    res_pos = res.start() if res else len(name)

    if tv:
        end = min(tv.start(), res_pos)
        if year and year_pos < end:
            end = year_pos
    elif year:
        end = min(year_pos, res_pos)
    else:
        end = res_pos

    title = name[:end]
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"[\.\-_]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) < 2:
        return None

    ctype = "tv" if tv else "movie"
    return dict(title=title, year=year, content_type=ctype,
                omdb_type="series" if tv else "movie")


def omdb_lookup(title, year, omdb_type, api_key):
    """Query OMDb. Returns {imdb, rt, found_title} or None."""
    params = {"apikey": api_key, "t": title}
    if year:
        params["y"] = year
    if omdb_type:
        params["type"] = omdb_type

    def fetch(p):
        try:
            return requests.get("https://www.omdbapi.com/", params=p, timeout=10).json()
        except Exception:
            return None

    data = fetch(params)
    if not data or data.get("Response") == "False":
        if year:
            params.pop("y")
            data = fetch(params)
        if not data or data.get("Response") == "False":
            return None

    imdb = None
    v = data.get("imdbRating", "N/A")
    if v != "N/A":
        try: imdb = float(v)
        except ValueError: pass

    rt = None
    for r in data.get("Ratings", []):
        if r.get("Source") == "Rotten Tomatoes":
            try: rt = int(r["Value"].replace("%", ""))
            except ValueError: pass
            break

    return dict(imdb=imdb, rt=rt, found_title=data.get("Title", ""))


def score_is_bad(imdb, rt, min_imdb, min_rt):
    """Bad = below BOTH thresholds (or the only available one)."""
    if imdb is not None and rt is not None:
        return imdb < min_imdb and rt < min_rt
    if imdb is not None:
        return imdb < min_imdb
    if rt is not None:
        return rt < min_rt
    return False


def dbg(msg, debug):
    if debug:
        print(msg, file=sys.stderr)

# -- Main ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Output filenames scoring below thresholds (pipe to rm).")
    ap.add_argument("--rt", type=int, default=50, help="Min RT score 0-100 (default: 50)")
    ap.add_argument("--imdb", type=float, default=5.0, help="Min IMDB 0-10 (default: 5.0)")
    ap.add_argument("--api-key", default=None, help="OMDb API key")
    ap.add_argument("--flag-not-found", action="store_true",
                    help="Flag movies not found in IMDB/RT as bad")
    ap.add_argument("--dry-run", action="store_true", help="Parse only, no API calls")
    ap.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls")
    ap.add_argument("--debug", action="store_true", help="Show scores/details on stderr")
    args = ap.parse_args()

    load_env()
    api_key = args.api_key or os.environ.get("OMDB_API_KEY") or os.environ.get("OMDBAPIKEY")
    if not api_key and not args.dry_run:
        print("Error: API key required. Use --api-key, OMDB_API_KEY env, or .env",
              file=sys.stderr)
        sys.exit(1)

    lines = [l.rstrip("\n") for l in sys.stdin if l.strip()]
    entries = [(raw, p) for raw in lines if (p := parse(raw))]

    if args.dry_run:
        counts = {}
        for _, p in entries:
            counts[p["content_type"]] = counts.get(p["content_type"], 0) + 1
        print(f"Total: {len(lines)}  Video: {len(entries)}  "
              f"Skipped: {len(lines)-len(entries)}  "
              + "  ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
              file=sys.stderr)
        for raw, p in entries:
            yr = p.get("year") or "?"
            print(f"  [{p['content_type']:7s}] {p['title']:45s} ({yr})",
                  file=sys.stderr)
        return

    cache = {}
    dbg(f"Checking {len(entries)} titles (RT>={args.rt}, IMDB>={args.imdb})", args.debug)

    for raw, p in entries:
        fname = raw.strip()

        ckey = (p["title"].lower(),
                None if p["content_type"] == "tv" else p["year"],
                p["omdb_type"])

        if ckey not in cache:
            cache[ckey] = omdb_lookup(p["title"], p["year"], p["omdb_type"], api_key)
            time.sleep(args.delay)
        result = cache[ckey]

        if not result:
            dbg(f"  [?????] {p['title']:45s} -- not found", args.debug)
            if args.flag_not_found:
                print(fname)
            continue

        bad = score_is_bad(result["imdb"], result["rt"], args.imdb, args.rt)
        if args.debug:
            tag = " BAD " if bad else " KEEP"
            i = f"{result['imdb']:.1f}" if result["imdb"] is not None else "N/A"
            r = f"{result['rt']}%" if result["rt"] is not None else "N/A"
            dbg(f"  [{tag}] {result['found_title']:45s} IMDB={i:>4s} RT={r:>4s}",
                args.debug)

        if bad:
            print(fname)


if __name__ == "__main__":
    main()
