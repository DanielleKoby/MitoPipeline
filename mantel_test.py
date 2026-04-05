import pandas as pd
from skbio.stats.distance import mantel
from skbio import DistanceMatrix
import numpy as np

bc_dist_path = "trees_analysis/DAP_b7_BC.csv"
wuf_dist_path = "trees_analysis/DAP_b7_WUF.csv"

meta_path = "trees_analysis/filtered_metadata.tsv"
mito_dist_path = "/Users/daniellekoby/Documents/uni/thirdYear/lab/trees_analysis/msa_consensus_clean_headers.fa.mldist"


mito_raw = pd.read_csv(mito_dist_path, sep=r'\s+', engine='python', header=None, skiprows=[0])
meta_data = pd.read_csv(meta_path, sep='\t', header=0)

raw_lables_biosamples = mito_raw.iloc[:, 0].str.split('_').str[1]
mito_raw_values = mito_raw.iloc[:, 1:].values 

labels_df = pd.DataFrame({'biosample': raw_lables_biosamples})
labels_df = pd.merge(labels_df, meta_data[['biosample', 'dog']], on='biosample', how='left')

# Checking dups - found one before - same bioproject id, different srr id
to_keep = ~labels_df['dog'].duplicated(keep='first')

final_mito_dog_ids = labels_df.loc[to_keep, 'dog'].tolist()
final_mito_values = mito_raw_values[to_keep.values][:, to_keep.values]


mito_distance_matrix = DistanceMatrix(final_mito_values, final_mito_dog_ids)

# Bray curtis
bc_dist_matrix = pd.read_csv(bc_dist_path,header=None, skiprows=[0])
bc_dog_id_lables = bc_dist_matrix.iloc[:, 0].tolist()
bc_clean_dist_matrix = bc_dist_matrix.iloc[:,1:]

# make symetric
data = bc_clean_dist_matrix.values
symmetric_data = (data + data.T) / 2
np.fill_diagonal(symmetric_data, 0)

bc_distance_matrix = DistanceMatrix(symmetric_data, ids=bc_dog_id_lables)

# filter out 
common_ids = list(set(mito_distance_matrix.ids) & set(bc_distance_matrix.ids))
# Run mantel 
corr_coef, p_value, n = mantel(mito_distance_matrix.filter(common_ids), bc_distance_matrix.filter(common_ids),
                method='pearson',
                permutations=999, alternative='two-sided', strict=True, lookup=None, seed=None)

print(p_value)

#WUF
wuf_dist_matrix = pd.read_csv(wuf_dist_path,header=None, skiprows=[0])
wuf_dog_id_lables = wuf_dist_matrix.iloc[:, 0].tolist()
wuf_clean_dist_matrix = wuf_dist_matrix.iloc[:,1:]

# make symetric
data = wuf_clean_dist_matrix.values

wuf_symmetric_data = (data + data.T) / 2
np.fill_diagonal(wuf_symmetric_data, 0)

wuf_dist_matrix = DistanceMatrix(wuf_symmetric_data, ids=wuf_dog_id_lables)

# filter out 
common_ids = list(set(mito_distance_matrix.ids) & set(wuf_dist_matrix.ids))
# Run mantel 
corr_coef, p_value, n = mantel(mito_distance_matrix.filter(common_ids), wuf_dist_matrix.filter(common_ids),
                method='pearson',
                permutations=999, alternative='two-sided', strict=True, lookup=None, seed=None)

print(p_value)
