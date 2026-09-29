# Stage-Outil-ArcGIS-Pro

For the users of ArcGIS Pro i developped this tool during my internship it allows you to construct automatically a network where you can apply several studies meanwhile this has to be done in several steps before.

---

## Contents

This repository gathers ArcGIS Pro tools and analyses on mobility data for **Toulouse**, developed during an internship at [Citec](https://www.citec.ch/) (2023).

| Folder | What it is | Author |
|---|---|---|
| [`Outil_Reseau_Multimodal/`](Outil_Reseau_Multimodal) | **Main tool** – ArcGIS Pro toolbox that builds a multimodal (streets + public transport) network dataset from street data and a GTFS feed in one run | Yahya Younes |
| [`Indicateur_TC/`](Indicateur_TC) | Public-transport quality indicators computed from GTFS (waiting-time and service-span indicators) | Yahya Younes |
| [`Indice_Livrabilite/`](Indice_Livrabilite) | "Indice de livrabilité" – ArcGIS Pro toolbox scoring each street for urban freight delivery performance, with Toulouse data and results | Niels Balimann (EPFL master project at Citec) |

## Repository layout

```
.
├── Outil_Reseau_Multimodal/
│   ├── Toolbox/              # Construire un réseau de transport multimodal.atbx
│   ├── SourceCode/           # Python scripts behind the toolbox tools
│   ├── Templates/            # Network dataset template (.xml)
│   ├── GTFS_Toulouse/        # Sample GTFS feed (Tisséo)
│   ├── Documentation/        # User guide, implementation doc, quick-start slides
│   └── OutilNetworkDataset.aprx
├── Indicateur_TC/
│   ├── SourceCode/
│   │   ├── Indicateur_Amplitude/
│   │   └── Indicateur_Temps_Attente/
│   └── GTFS/                 # Sample GTFS feed (Tisséo)
└── Indice_Livrabilite/
    ├── Toolbox/              # Indice Livrabilite.atbx
    ├── SourceCode/           # outilIndiceLivraison_execution.py
    ├── Data/                 # TOULOUSE_PL.gdb + zipped base geodatabase
    ├── Config/               # HERE traffic-data request config
    ├── Results/              # Output tables and analysis notebook
    └── Documentation/        # User manual and master-project report (PDF)
```

## Requirements

- **ArcGIS Pro 3.x** with the **Network Analyst** extension (for the multimodal tool) and the
  *Public Transit* tools (`arcpy.transit`).
- Street data with HERE/NAVTEQ-style attributes (`AR_AUTO`, `AR_PEDEST`, `AR_BUS`, …),
  e.g. the Citec *Streets* feature class.
- For the notebooks: Python 3 with `pandas`, `geopandas`, `gtfs_functions`, `matplotlib`, `seaborn`.

## Quick start

1. Clone or download the repository.
2. In ArcGIS Pro, open **Catalog → Toolboxes → Add Toolbox** and select the `.atbx` file
   of the tool you want (`Outil_Reseau_Multimodal/Toolbox/…` or `Indice_Livrabilite/Toolbox/…`).
3. Run the tools from the toolbox and follow the documentation in each folder's README.

Folder names were made ASCII and consistent (no spaces or accents); file names and contents are unchanged.
