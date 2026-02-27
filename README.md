# filter_bad_movies

Reads video filenames from stdin, scores them via OMDb API (Rotten Tomatoes + IMDB), outputs filenames below thresholds. Only files with video extensions (mkv, avi, mp4, ts, m4v, mov, wmv) are processed.

A file is "bad" if it scores below BOTH thresholds. Good on either one = kept.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

Get a free API key (1000 req/day): https://www.omdbapi.com/apikey.aspx

Put it in `.env`:
```
OMDBAPIKEY=your_key_here
```

Or pass `--api-key KEY` or set `OMDB_API_KEY` env var.

## Usage

```
find /movies/ -type f | python filter_bad_movies.py --rt 80 --imdb 8.0
find /movies/ -type f -name '*.mkv' -o -name '*.mp4' | python filter_bad_movies.py --rt 60 --imdb 6.0
```

Output is one filename per line, ready to pipe.

## Arguments

| Argument | Default | Description |
|---|---|---|
| `--rt N` | 50 | Min Rotten Tomatoes tomatometer (0-100) |
| `--imdb N` | 5.0 | Min IMDB rating (0-10) |
| `--api-key KEY` | .env | OMDb API key |
| `--flag-not-found` | off | Flag movies not found in IMDB/RT as bad |
| `--dry-run` | off | Parse filenames only, no API calls |
| `--delay N` | 0.5 | Seconds between API calls |
| `--debug` | off | Show scores and details on stderr |

## Examples

```sh
# Preview parsing (no API):
find /movies/ -type f | python filter_bad_movies.py --dry-run

# Find bad movies with debug info:
find /movies/ -type f | python filter_bad_movies.py --rt 70 --imdb 7.0 --debug

# Include movies not found in IMDB/RT:
find /movies/ -type f | python filter_bad_movies.py --rt 80 --imdb 8.0 --flag-not-found

# Delete bad files:
find /movies/ -type f | python filter_bad_movies.py --rt 80 --imdb 8.0 | xargs -d'\n' rm -rf

# Delete with confirmation:
find /movies/ -type f | python filter_bad_movies.py --rt 80 --imdb 8.0 | while read f; do
  rm -ri "$f"
done
```
