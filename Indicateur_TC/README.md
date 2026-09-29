# Indicateurs TC – Public-transport indicators from GTFS

Prototype indicators of public-transport service quality per stop area, computed from a GTFS
feed (Toulouse, Tisséo) with [`gtfs_functions`](https://pypi.org/project/gtfs-functions/) and pandas.

| Path | Description |
|---|---|
| `SourceCode/Indicateur_Temps_Attente/Indicateur_Temps_Attente.ipynb` | Waiting-time indicator: number of trips per stop area over a week, `trips / 7 / 240 × 100`, then min–max normalised to 0–100. Includes a comparison of two stop areas (Jean Jaurès, Ponts Jumeaux) and a check against ArcGIS Pro's *Calculate Transit Service Frequency* |
| `SourceCode/Indicateur_Temps_Attente/Indice_temps_attente.py` | Same indicator as an ArcGIS Pro script tool (parameters: zipped GTFS, start date, end date) – draft |
| `SourceCode/Indicateur_Amplitude/Indicateur_Amplitude.ipynb` | Service-span (amplitude) indicator: first and last departure per stop area and day |
| `SourceCode/Indicateur_Amplitude/Indice_Ampl_Ref.ipynb` | Reference version of the amplitude indicator (service day starting at 03:45) |
| `GTFS/` | Sample GTFS files: agency, calendar, calendar_dates, routes, shapes, stops |

## Running

```bash
pip install pandas geopandas gtfs_functions
jupyter notebook
```

The notebooks load the feed from an absolute Windows path
(`C:\Users\sd\OneDrive\Indicateur TC\GTFS.zip`); change it to your own zipped GTFS.
The sample `GTFS/` folder lacks `stop_times.txt` and `trips.txt`, which the indicators need,
so download the full Tisséo feed.

`Indice_temps_attente.py` is work in progress: `preprocess_data` still reads the hard-coded
path, and its result is not yet passed to `calculate_indicator`.
