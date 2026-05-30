# bandcamp-dl (Web UI Fork)

> **This is a modified fork of [bandcamp-dl](https://github.com/evolution0/bandcamp-dl)** that adds a simple mobile-friendly web UI and Docker support, making it easy to self-host and run as a service.

Download audio from [bandcamp.com](https://www.bandcamp.com)


---

## What's added in this fork

- **Web UI** — mobile-friendly dark interface, accessible in any browser
- **Real-time progress** — track-by-track download status streamed live
- **Download history** — persistent log of past downloads
- **Docker support** — single container, configurable download volume

---

## Running with Docker

### docker run

```bash
docker run -d \
  --name bandcamp-dl \
  -p 5000:5000 \
  -v /path/to/your/music:/downloads \
  -e DOWNLOAD_DIR=/downloads \
  --restart unless-stopped \
  git.steltner.cloud/2tap2b/bandcamp-dl-webui:latest
```

Replace `/path/to/your/music` with the local directory where you want downloads saved.

### docker compose

Create a `docker-compose.yml`:

```yaml
services:
  bandcamp-dl:
    image: git.steltner.cloud/2tap2b/bandcamp-dl-webui:latest
    ports:
      - "5000:5000"
    volumes:
      - /path/to/your/music:/downloads
    environment:
      - DOWNLOAD_DIR=/downloads
    restart: unless-stopped
```

Then start it:

```bash
docker compose up -d
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### Build from source

```bash
git clone <this-repo>
cd bandcamp-dl
docker compose up -d --build
```

---

## Original bandcamp-dl

### Synopsis

```
bandcamp-dl URL
```

### Installation (CLI only)

**From PyPI:**
```bash
pip3 install bandcamp-downloader
```

**From source:**
```bash
git clone https://github.com/evolution0/bandcamp-dl
cd bandcamp-dl
pip install .
```

**[OSX] Homebrew:**
```bash
brew install bandcamp-dl
```

**[Arch] AUR:**
```bash
yay -S bandcamp-dl-git
```

### Description

bandcamp-dl is a small command-line app to download audio from bandcamp.com. It requires Python 3.4 or higher and is not platform specific. It is released to the public domain.

### Options

```
Usage:
    bandcamp-dl [options] [URL]

Arguments:
    URL         Bandcamp album/track URL

Options:
  -h, --help            show this help message and exit
  -v, --version         Show version
  -d, --debug           Verbose logging
  --artist ARTIST       Specify an artist's slug to download their full discography
  --track TRACK         Specify a track's slug to download a single track (requires --artist)
  --album ALBUM         Specify an album's slug to download a single album (requires --artist)
  --template TEMPLATE   Output filename template, default: %{artist}/%{album}/%{track} - %{title}
  --base-dir BASE_DIR   Base location of which all files are downloaded
  -f, --full-album      Download only if all tracks are available
  -o, --overwrite       Overwrite tracks that already exist
  -n, --no-art          Skip grabbing album art
  -e, --embed-lyrics    Embed track lyrics (if available)
  -g, --group           Use album/track label as iTunes grouping
  -r, --embed-art       Embed album art (if available)
  --cover-quality {0,10,16}
                        Set cover art quality: 0=source, 10=1200x1200, 16=700x700 (default)
  -y, --no-slugify      Disable slugification of track, album, and artist names
  -c OK_CHARS           Specify allowed chars in slugify, default: -_~
  -s SPACE_CHAR         Specify the char to use in place of spaces, default: -
  -a, --ascii-only      Only allow ASCII characters
  -k, --keep-spaces     Retain whitespace in filenames
  -x {lower,upper,camel,none}
                        Specify char case conversion, default: lower
  --no-confirm          Override confirmation prompts
  --embed-genres        Embed album/track genres
  --truncate-album LEN  Truncate album title to max length (0 = no limit)
  --truncate-track LEN  Truncate track title to max length (0 = no limit)
```

### Filename Template

The `--template` option allows users to indicate a template for output file names. Templates use tokens with the format `%{token}`:

| Token | Description |
|---|---|
| `trackartist` | The artist name |
| `artist` | The album artist name |
| `album` | The album name |
| `track` | The track number |
| `title` | The track title |
| `date` | The album date |
| `label` | The album label |

Default template: `%{artist}/%{album}/%{track} - %{title}`

### Dependencies

- [BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4) — HTML parsing
- [Mutagen](https://pypi.python.org/pypi/mutagen) — ID3 encoding
- [Requests](https://pypi.python.org/pypi/requests) — HTTP

### Bugs

Report bugs for the original CLI at the [upstream issue tracker](https://github.com/evolution0/bandcamp-dl/issues). For issues specific to the web UI or Docker setup, open an issue in this repository.

---

## Copyright

bandcamp-dl is released into the public domain by the copyright holders.
