# Outil de construction de réseau multimodal

ArcGIS Pro toolbox that automates the creation of a **multimodal transport network dataset**
(walking + public transport) from street data and a GTFS feed. Done by hand, this requires
several separate geoprocessing steps; the toolbox chains them in two tools.

Author: Yahya Younes – Citec internship, version 0.1 (July 2023).

## Contents

| Path | Description |
|---|---|
| `Toolbox/Construire un réseau de transport multimodal.atbx` | The toolbox to add in ArcGIS Pro (scripts are embedded) |
| `SourceCode/ClipAndExtract.py` | Source of tool 1 – *Clip and extract streets* |
| `SourceCode/ConstruireReseauMultimodal.py` | Source of tool 2 – *Construire un réseau multimodal* |
| `Templates/ConstruireUnReseauMultimodalCitec082023.xml` | Network dataset template used to create the network |
| `GTFS_Toulouse/` | Sample GTFS feed for Toulouse (Tisséo): agency, calendar, routes, shapes, stops |
| `OutilNetworkDataset.aprx` | ArcGIS Pro project used during development |
| `Documentation/` | User guide, implementation documentation and quick-start slides (French) |

## Tools

### 1. Clip and extract streets (`ClipAndExtract.py`)

Extracts the streets of a study area and prepares them for the network.

| # | Parameter | Description |
|---|---|---|
| 0 | Streets | Street feature class (HERE-style attributes) |
| 1 | Zone layer | Polygon layer of administrative zones |
| 2 | Zone name field | Field holding the zone names |
| 3 | Zones | Zones to keep (multi-value) |
| 4 | Output layer name | Name of the extracted street layer |
| 5 | Feature dataset | Feature dataset to create/use (optional) |
| 6 | Workspace | Output geodatabase |
| 7 | Filter option | Keep only streets usable by vehicles/pedestrians (filter on `AR_*` access fields) |
| 8 | Projection | Output coordinate system (default WGS 1984 – EPSG:4326; Web Mercator EPSG:3857 when chosen) |

Steps: select the zones → select streets → pairwise clip → project → export with field mapping.

### 2. Construire un réseau multimodal (`ConstruireReseauMultimodal.py`)

| # | Parameter | Description |
|---|---|---|
| 0 | Feature dataset | Dataset containing the `Streets` layer from tool 1 |
| 1 | GTFS folder | Folder with the GTFS `.txt` files |
| 2 | Network dataset template | e.g. `Templates/ConstruireUnReseauMultimodalCitec082023.xml` |

Steps:
1. `GTFSToPublicTransitDataModel` – import the GTFS into the Public Transit data model.
2. `ConnectPublicTransitDataModelToStreets` – connect stops to streets (100 m search, pedestrian streets).
3. `CreateNetworkDatasetFromTemplate` – create the network dataset.
4. `BuildNetwork` – build `TransitNetwork_ND`.

The tool stops with an error if `Stops`, `LineVariantElements`, `StopsOnStreets` or
`StopConnectors` already exist in the geodatabase — use a new geodatabase or delete them first.

## Usage

1. ArcGIS Pro → Catalog → *Add Toolbox* → `Toolbox/Construire un réseau de transport multimodal.atbx`.
2. Run **Clip and extract streets** on your study area.
3. Run **Construire un réseau multimodal** with the resulting feature dataset, a GTFS folder and the template.
4. Use the network in Network Analyst (service areas, routes, OD cost matrices…).

Requires ArcGIS Pro 3.x with the Network Analyst extension.

> The sample `GTFS_Toulouse/` folder does not contain `stop_times.txt` / `trips.txt`
> (too large for the repository); download the full Tisséo GTFS feed to run the tool.
