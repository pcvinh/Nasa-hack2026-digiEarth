# Notices and data attributions

## NASA data
Trend results are derived from NASA Earth science data. Cite the datasets when you use results:

| Variable | Dataset | DOI / source |
|---|---|---|
| Rainfall | GPM IMERG Final monthly, GPM_3IMERGM V07 | 10.5067/GPM/IMERG/3B-MONTH/07 (NASA GES DISC) |
| Air temperature (2 m) | MERRA-2 M2TMNXSLV 5.12.4 | 10.5067/AP1B0BA5PD2K (NASA GES DISC) |
| Topsoil moisture | GLDAS Noah 0.25° monthly, GLDAS_NOAH025_M 2.1 | 10.5067/SXAVCZFAQLNO (NASA GES DISC) |
| Vegetation greenness (NDVI) | MODIS Terra MOD13C2 061 | 10.5067/MODIS/MOD13C2.061 (NASA LP DAAC) |

Basemap imagery: NASA GIBS (Blue Marble). Values shown are processed (resampled to about 0.5° and aggregated); they are not the original products.

## Region boundaries (`backend/src/edt/regions/presets.geojson`)
- Mekong Delta: geoBoundaries gbOpen ADM1 (Vietnam), Public Domain per geoBoundaries metadata.
- Central Java (Indonesia) and Johor (Malaysia): geoBoundaries gbOpen ADM1, derived from OpenStreetMap/Wambacher data. **© OpenStreetMap contributors, Open Database Licence (ODbL) 1.0.** Our simplified geometries for these two regions are a derived database and remain under ODbL 1.0 (attribution and share-alike).
- Central Amazon and Sahel: simple documented rectangles/bands defined by this project, not official boundaries.

geoBoundaries: Runfola et al. (2020), PLoS ONE 15(4): e0231866.

## Code licence
The source code is released under the MIT License (see `LICENSE`). The MIT License does not cover third-party data: NASA data keeps its own terms, and `backend/src/edt/regions/presets.geojson` keeps the ODbL 1.0 terms described above for the OpenStreetMap-derived regions.
