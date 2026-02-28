# filter_bad_movies

Scores video files via OMDb (RT + IMDB). Outputs paths below both thresholds, one per line — pipe to `rm`, or use `--delete` to remove directly.

A file is bad if it scores below **both** thresholds when both are available. If only one score exists, that one decides.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate && pip install requests
```

Free API key (1000 req/day): https://www.omdbapi.com/apikey.aspx — put it in `.env`:
```
OMDBAPIKEY=your_key_here
```

## Arguments

| Argument | Default | Description |
|---|---|---|
| `--rt N` | 50 | Min Rotten Tomatoes score (0–100) |
| `--imdb N` | 5.0 | Min IMDB rating (0–10) |
| `--base-dir DIR` | — | Root dir; bad files in subfolders → subfolder path is output (for folder deletion) |
| `--flag-not-found` | off | Treat movies not found in OMDb as bad |
| `--dry-run` | off | Parse only, no API calls |
| `--delay N` | 0.5 | Seconds between API calls |
| `--debug` | off | Print title, scores and decision to stderr |
| `--delete` | off | Delete bad files/folders directly (implies `--debug`) |

## Examples

```sh
# Check parsed titles, no API calls:
find /downloads -type f | python filter_bad_movies.py --dry-run

# Custom thresholds:
find /downloads -type f | python filter_bad_movies.py --rt 70 --imdb 7.0

# Show what the script decides (title, scores, BAD/KEEP):
find /downloads -type f | python filter_bad_movies.py --rt 70 --imdb 7.0 --debug

# Slow down requests (e.g. free API key):
find /downloads -type f | python filter_bad_movies.py --delay 1.5

# Also flag movies not found in OMDb:
find /downloads -type f | python filter_bad_movies.py --flag-not-found

# Delete bad files directly (debug output is automatic):
find /downloads -type f | python filter_bad_movies.py --delete

# Delete bad folders directly:
find /downloads -type f | python filter_bad_movies.py --base-dir /downloads --delete

# Pipe to rm instead of --delete:
find /downloads -type f | python filter_bad_movies.py | xargs -d '\n' rm -f

# Pipe folder paths to rm:
find /downloads -type f | python filter_bad_movies.py --base-dir /downloads | xargs -d '\n' rm -rf
```

## Usage with sudo

When files are owned by root, run the script with `sudo`. To preserve the `.env` API key, pass the env var explicitly:

```sh
# Direct delete as root:
find /downloads -type f | sudo -E python filter_bad_movies.py --delete

# Or pass the key explicitly:
find /downloads -type f | sudo OMDB_API_KEY="$OMDB_API_KEY" python filter_bad_movies.py --delete

# Pipe mode with sudo rm:
find /downloads -type f | python filter_bad_movies.py | sudo xargs -d '\n' rm -rf
```

`sudo -E` preserves environment variables. If `.env` is used, make sure the script path is absolute so it can locate the file.
```
