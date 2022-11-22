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
run_pdo = os.getenv('RUN_PDO')

# get environment values
# fetch Population Decrease Overwrite Value
if run_pdo is None:
    run_pdo = False
elif run_pdo == True or run_pdo.lower() == 'true':
    run_pdo = True
else:
    run_pdo = False

logger = logging.getLogger('extract-ssp-population')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(outputs / 'extract-ssp-population.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Read in the regions to be modelled - the file needs to have a header 'code' with the ID of the LAD
logger.info('Reading regions')
regions_paths = []
for ext in ['shp', 'gpkg']:
    regions_paths.extend(list(inputs.glob(f"regions/*.{ext}")))

assert len(regions_paths) > 0, 'No input regions_paths found'
regions = gpd.read_file(regions_paths[0])
if len(regions_paths) > 1:
    for path in regions_paths[1:]:
        regions = regions.append(gpd.read_file(path))

# If the user has selected to know the maximum population value in the projection then:
if run_pdo == True :
    logger.info('Population Decrease Overwrite')
    # Reads in the population information from the CSV, including the baseline year
    logger.info('Reading in Population')
    population = pd.read_csv(next(inputs.glob('ssp/*.csv')),
                            usecols=['ID','LAD19CD','LAD19NM','Age Class','Scenario','2020'])

    # Reads in the population for all years leading up to the year of interest
    for i in range(0,int(((int(year)-2020)))):
        i = int((i+1)+2020)
        pop = pd.read_csv(next(inputs.glob('ssp/*.csv')),
                             usecols=['ID',f'{i}'])
        population = population.merge(pop,how='inner')

    # Filters the data by chosen SSP and locates the total population per LAD
    logger.info('Identifying SSP')
    population = population.loc[population['Scenario'] == f'SSP{ssp}']
    population = population.loc[population['Age Class'] == 'Total']
    population = population.assign(ID=range(len(population))).set_index('ID')

    # Selects the columns of interest (the population per year per LAD) and identifies the max value
    logger.info('Calcaulting Max Values')
    year_columns = population.loc[:,'2020':]
    max_values = year_columns.max(axis=1)
    max_values=max_values.to_frame()
    max_values = max_values.assign(ID=range(len(max_values))).set_index('ID')
    max_values.columns=['max_values']

    # Removes columns that are no needed (the intemediatry years, class and SSP)
    population = population.drop(population.loc[:,'2021':].columns,axis=1)
    population = population.drop(['Age Class','Scenario'],axis=1)

    # Appends the max population to the data frame and renames the columns
    max_pop = population.merge(max_values,on='ID',how ='inner')
    max_pop.columns = ['code', 'Lad_Name','initial_population','final_population']

    # Convert population figures to 1000s
    max_pop.loc[:, 'initial_population'] *=1000
    max_pop.loc[:, 'final_population'] *=1000

    # Identify which LADs are of interest and outputs only the population data for those LADs
    logger.info('Filtering by Required LAD')
    clipped_pop = max_pop["code"].isin(regions['code'])
    clipped_pop=clipped_pop.to_frame()
    clipped_pop = clipped_pop.assign(ID=range(len(clipped_pop))).set_index('ID')
    max_pop = max_pop.merge(clipped_pop,on='ID',how ='inner')
    max_pop = max_pop.loc[max_pop['code_y'] == 1]
    max_pop = max_pop.drop(['code_y'],axis=1)
    max_pop = max_pop.rename(columns = {"code_x":"code"})

    # Save to CSV - only columns of interest
    logger.info('Output CSV')
    max_pop[['code', 'initial_population','final_population']].to_csv(
        os.path.join(outputs, 'population.csv'), index=False,  float_format='%g')


# If the user has selected to have the static time slice of the year of interest:
if run_pdo == False :
    logger.info('Static Population Output')
    # Reads in the population information from the CSV, including the baseline year and year of interest
    logger.info('Reading in Population')
    population = pd.read_csv(next(inputs.glob('ssp/*.csv')),
                            usecols=['ID','LAD19CD','LAD19NM','Age Class','Scenario','2020',f'{year}'])

    # Filters the data by chosen SSP and locates the total population per LAD
    logger.info('Identifying SSP')
    population = population.loc[population['Scenario'] == f'SSP{ssp}']
    population = population.loc[population['Age Class'] == 'Total']
    population = population.assign(ID=range(len(population))).set_index('ID')

    # Removes columns that are no needed (class and SSP)
    population = population.drop(['Age Class','Scenario'],axis=1)
    population.columns = ['code', 'Lad_Name','initial_population','final_population']

    # Identify which LADs are of interest and outputs only the population data for those LADs
    logger.info('Filtering by Required LAD')
    clipped_pop = population["code"].isin(regions['code'])
    clipped_pop=clipped_pop.to_frame()
    clipped_pop = clipped_pop.assign(ID=range(len(clipped_pop))).set_index('ID')
    population = population.merge(clipped_pop,on='ID',how ='inner')
    population= population.loc[population['code_y'] == 1]
    population = population.drop(['code_y'],axis=1)
    population = population.rename(columns = {"code_x":"code"})

    # Convert population figures to 1000s
    population.loc[:, 'initial_population'] *=1000
    population.loc[:, 'final_population'] *=1000

    # Save to CSV - only columns of interest
    logger.info('Output CSV')
    population[['code', 'initial_population','final_population']].to_csv(
        os.path.join(outputs, 'population.csv'), index=False,  float_format='%g')

# write a metadata file
logger.info('Output Metadata File with Parameters')
with open(outputs/'metadata.csv', 'w') as f:
    # write header row
    f.write('PARAMETER, VALUE\n')
    # write parameters and values
    f.write('SSP,SSP%s\n' %ssp)
    f.write('YEAR,%s\n' %year)
    f.write('IGNORE POPULATION DECREASE,%s\n' %run_pdo)

