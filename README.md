# extract-ssp-population
## Description
Extracts from an archive of SSP data for the UK the population for local authority districts (LADs) passed as a spatial file (.shp or .gpkg) for a given SSP (1-5) and for a single year (2020-2080). 

## Inputs

## Outputs
- Returns a .csv titled population.csv of data with the following columns 'code|initial_popualtion|final_population'
- Returns a single .csv file titled 'metadata.csv' containing the SSP and year values used to extract the data. Columns: 'PARAMETER|VALUE'

