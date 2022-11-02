from pathlib import Path
import os
import logging
import geopandas as gpd
import pandas as pd

# setup paths to data
data = Path(os.getenv('DATA_PATH', '/data'))

inputs = data / 'inputs'
outputs = data / 'outputs'

outputs.mkdir(exist_ok=True)

year = os.getenv('YEAR')
ssp = os.getenv('SSP')
region_field = os.getenv('REGION_FIELD')

logger = logging.getLogger('extract-ssp-population')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(outputs / 'extract-ssp-population.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info('Reading regions')
regions_paths = []
for ext in ['shp', 'gpkg']:
    regions_paths.extend(list(inputs.glob(f"regions/*.{ext}")))

assert len(regions_paths) > 0, 'No input regions_paths found'
regions = gpd.read_file(regions_paths[0])
if len(regions_paths) > 1:
    for path in regions_paths[1:]:
        regions = regions.append(gpd.read_file(path))

logger.info('Reading SSP data')
population = pd.read_csv(next(inputs.glob('ssp/*.csv')),
                         usecols=['x', 'y', f'POP.{year}.SSP{ssp}', f'POP.2020.SSP{ssp}'])
population.columns = ['x', 'y', 'initial_population', 'final_population']

logger.info('Converting x and y values to geometries')
population = gpd.GeoDataFrame(population, geometry=gpd.points_from_xy(population.x, population.y), crs=regions.crs)

logger.info('Joining population data to regions')
population = gpd.sjoin(population, regions)

logger.info('Summing population data for each region')
population = population.groupby(region_field)[['initial_population', 'final_population']].sum()

# write a metadata file
with open(outputs/'metadata.csv', 'w') as f:
    # write header row
    f.write('PARAMETER, VALUE\n')
    # write parameters and values
    f.write('SSP,SSP%s\n' %ssp)
    f.write('YEAR,%s\n' %year)
    
logger.info('Saving to CSV')
population.to_csv(outputs/'population.csv')
