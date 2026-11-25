# Bulk download (`aq-downloader`)

```sh
aq-downloader <outpath> [-y YEAR_START]
```

Downloads UBA data for **every** UBA station (all of Germany) from `YEAR_START` (default
2016) up to last year:

| Component | Scope |
|---|---|
| PM10, PM2.5, O₃, NO₂, SO₂ | hourly mean |
| CO | 8-hour mean |

- Each result is stored as a pickled dict (`model_dump(mode="json")`) at
  `<outpath>/<year>/<station_code>/<component>_<scope>.pkl`.
- Combinations whose data range (from [`get_measures_limits`](apis/uba.md#data-availability))
  misses the year are skipped; no file or station directory is written for them.
- Progress is logged to `<outpath>/download.log`.

Expect this to run for a long time.

## Docker

A Docker image for the downloader lives in
[`downloader/`](https://github.com/UKEIAM/canairy/tree/develop/downloader):

```sh
cd downloader
./build.zsh                 # builds canairy_downloader:latest
./run.zsh /path/to/data     # runs aq-downloader /data with the host dir mounted
```
