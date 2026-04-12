import pandas as pd
from skbio.stats.distance import mantel
from skbio import DistanceMatrix
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

bc_dist_path = str(PROJECT_ROOT / "taxonomy/DAP_b7_BC.csv")
meta_path = str(PROJECT_ROOT / "data/raw/metadata/filtered_metadata.tsv")
mito_dist_path = str(PROJECT_ROOT / "data/processed/consensus/iqtree_output/msa_consensus_clean_headers.fa.mldist")


# Create distanceMatrix and ID array
mito_dist_matrix = pd.read_csv(mito_dist_path, sep='\s+', engine='python', header=None, skiprows=[0])
print(mito_dist_matrix.columns[0])
first_column_name = mito_dist_matrix.columns[0]

# mito_lables = mito_dist_matrix.iloc[:, :1] # tbd
# mito_clean_dist_matrix = mito_dist_matrix.iloc[:,1:]

# # Bray curtis
# bc_dist_matrix = pd.read_csv(bc_dist_path,hea)

# # dictionery
# meta_data = pd.read_csv(biosample_to_dog_id_path, sep='\t', header=0)

#  = mito_dist_matrix.index.str.extract(r'_(SAMN\d+)_')

# # Run mantel 
# skbio.stats.distance.mantel(x, y, method='pearson', permutations=999, alternative='two-sided', strict=True, lookup=None, seed=None)

