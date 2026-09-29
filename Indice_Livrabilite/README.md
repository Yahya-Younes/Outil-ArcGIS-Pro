# Indice de livrabilité – Urban freight delivery performance index

ArcGIS Pro tool that scores every street segment of a study area on how easy it is to
deliver goods there, for heavy trucks (**PL**) or light commercial vehicles (**VUL**).

Author: **Niels Balimann** – EPFL master project carried out at Citec (supervision Citec:
Franco Tufo & Frédéric Schettini; EPFL: Nikolaos Geroliminis). Version 1.0, June 2023.
Applied here to Toulouse.

## Contents

| Path | Description |
|---|---|
| `Toolbox/Indice Livrabilite.atbx` | ArcGIS Pro toolbox |
| `SourceCode/outilIndiceLivraison_execution.py` | Execution script of the tool (~1,700 lines) |
| `Data/TOULOUSE_PL.gdb` | File geodatabase for Toulouse (heavy-truck study) |
| `Data/Indice livrabilité_Données de base.gdb.zip` | Zipped base geodatabase (input data) |
| `Config/config_GetHereSpeedData_Toulouse.json` | Request configuration for HERE traffic (speed) data over Toulouse |
| `Results/table_valeur_defaut.csv` | Default thresholds per indicator and vehicle type (`BORNE_B` good / `BORNE_M` bad) |
| `Results/TableRuesSonia.*`, `Results/RueAlsaceLorraine.*` | Output tables for studied streets |
| `Results/resultsToulouse.ipynb` | Analysis/plots of the results (pandas, seaborn) |
| `Documentation/Manuel d'utilisation IndiceLivrabilité v2.pdf` | User manual |
| `Documentation/Indice de performance livraison - Rapport PDM Niels Balimann.pdf` | Master-project report (method) |

## Method

Each street gets a score per indicator (good / medium / bad from the thresholds `BORNE_B` /
`BORNE_M` in `Results/table_valeur_defaut.csv`), grouped into two families that are weighted
into a global score (with a road-hierarchy ratio and points of interest):

| Group | Criterion | Indicators |
|---|---|---|
| **Circulation** | Partage de l'espace | Number of lanes (incl. bike lanes), public-transport stops |
| | Fluidité | Obstacles, intersection type |
| | Déplacement | Speed limit, congestion (HERE speed data), road works (HERE incidents or external layer) |
| **Accessibilité** | Réglementations | Height, width, length, weight, axle-weight limits, delivery time windows |
| | Manutention | Slope (HERE map attributes), parking / delivery spaces |

Outputs: a street layer with the scores, a summary table and charts in the ArcGIS Pro project.
Inputs and options are described in the user manual.

## Usage

1. Unzip `Data/Indice livrabilité_Données de base.gdb.zip`.
2. ArcGIS Pro → Catalog → *Add Toolbox* → `Toolbox/Indice Livrabilite.atbx`.
3. Run the tool, following `Documentation/Manuel d'utilisation IndiceLivrabilité v2.pdf`.

The slope and road-works criteria call the HERE APIs (congestion uses a HERE speed-data table) and need your own HERE credentials.
