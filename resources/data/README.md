# Live TV data

The canonical live TV lists live here, in the add-on's own repository, and are read over
`raw.githubusercontent.com` — see `GITHUB_LIVE` / `GITHUB_M3U` in
`resources/lib/modules/constants.py`.

| file | read by | format |
|---|---|---|
| `gr_ch.json` | `Indexer.live()` | `{"updated": "<date>", "channels": [...]}` |
| `greek.m3u` | `Indexer.cached_live_m3u()` | `#EXTM3U` playlist |

Both are **optional**. `Indexer.fetch_chain()` tries this directory first, then the
`repo.elarepo.org` website copies, then the original upstreams, and validates each tier before
accepting it. While a file is absent its URL simply 404s and the website copy is served, so the
add-on behaves exactly as it did before these files existed.

## `gr_ch.json` channel fields

`name`, `logo`, `group`, `url` (a **list** — only `url[0]` is used), `website`, `info`, and
optionally `headers` (the literal string `random` synthesises a User-Agent and Referer) and
`drm`. `group` must be one of the `LIVE_GROUPS` keys in `constants.py`; anything unrecognised
falls back to `Web TV`.

## `greek.m3u`

Standard `#EXTINF` entries. `group-title` is read and mapped through `M3U_GROUPS` in
`constants.py`, which translates the playlist's Greek group names onto the same `LIVE_GROUPS`
keys the JSON list uses — that mapping is what lets the playlist merge into the main Live TV
list rather than sitting in a separate one.

## Editing

Changes take effect for users when the cache expires (`cache_duration(480)`) or when they use
the *reset live cache* setting. No add-on release is needed — these files are fetched at
runtime, not read from the installed copy.
