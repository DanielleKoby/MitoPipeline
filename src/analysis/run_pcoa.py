import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from skbio import DistanceMatrix
from skbio.stats.ordination import pcoa
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

path_to_fa_file = str(PROJECT_ROOT / "data/processed/consensus/iqtree_output/msa_consensus_clean_headers.fa.mldist")
path_to_plots_dir = str(PROJECT_ROOT / "results/plots")

raw_df = pd.read_csv(path_to_fa_file, sep='\s+', engine='python', header=None, skiprows=[0])
dog_names = raw_df.iloc[:, 0].values # only samples name
distances = raw_df.iloc[:, 1:].to_numpy() # only distances values
dist_matrix = DistanceMatrix(distances, ids = dog_names) 

pcoa_res = pcoa(dist_matrix)
coords = pcoa_res.samples[['PC1', 'PC2']].copy()
breed_series = pd.series(dog_names)
def create_breed_mapping_and_indices(dist_matrix, breed_series):
    """
    Creates necessary dictionaries for mapping IDs to breeds and to matrix indices.
    """
    full_ids = mdist[ID_COL_IDX]
    id_list = list(full_ids)

    # 1. ID -> Breed Mapping
    id_to_breed = dict(zip(full_ids, breed_series))
    
    # 2. ID -> Row Index Mapping (for efficient distance lookup)
    # The index is the row number in the DataFrame (mdist)
    id_to_index = {id_val: i for i, id_val in enumerate(full_ids)}
    
    # 3. Distance Matrix (excluding the ID column)
    dist_matrix = mdist.iloc[:, 1:].values
    
    return dist_matrix, id_to_breed, id_to_index, id_list

def calculate_distances(dist_matrix, id_list, id_to_breed, top_breeds_list, id_to_index):

    # DataFrame to store results for plotting
    results_df = pd.DataFrame(columns=['Breed', 'Distance_Type', 'Distance_Value'])
    all_valid_ids = set(id_list)
    top_breed_names = [b for b, c in top_breeds_list]

    # Remove unknown or mixed breeds
    all_valid_ids = {
        id_val for id_val in all_valid_ids 
        if 'Unknown' not in id_val and 'Mixed_breed' not in id_val
    }
    top_breed_names = [
        breed for breed, count in top_breeds_list 
        if 'Unknown' not in breed and 'Mixed_breed' not in breed
    ]
    return top_dogs_dist_matrix


# 6. Helper function to extract breed name from the full string
def clean_dog_name(full_name):
    parts = full_name.split('_')
    if len(parts) >= 3:
        # Join the parts that typically represent the breed name
        return "_".join(parts[2:]) 
    return full_name

# Add a 'Breed' column to use for grouping/coloring
coords['Breed'] = [clean_dog_name(name) for name in dog_names]
# 7. Calculate Percentage of Variance Explained for axes
pc1_var = pcoa_res.proportion_explained[0] * 100
pc2_var = pcoa_res.proportion_explained[1] * 100

# 8. Create the visualization using Seaborn
plt.figure(figsize=(14, 10))
sns.set_style("whitegrid")

# Create scatter plot - colored by extracted Breed
plot = sns.scatterplot(
    data=coords, 
    x='PC1', 
    y='PC2', 
    hue='Breed', 
    alpha=0.7, 
    edgecolor='none',
    s=60
)

# Manage legend (hide if there are too many unique breeds to keep the plot clean)
unique_breeds = coords['Breed'].nunique()
if unique_breeds > 20:
    plt.legend([],[], frameon=False)
    print(f"Detected {unique_breeds} breeds. Legend hidden to avoid clutter.")
else:
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Add titles and axis labels
plt.title(f'PCoA of Dog Genetic Distances\n(Total Samples: {len(dog_names)})', fontsize=16)
plt.xlabel(f'PCoA 1 ({pc1_var:.2f}%)', fontsize=12)
plt.ylabel(f'PCoA 2 ({pc2_var:.2f}%)', fontsize=12)

# 9. Save the figure to the server
output_png = "dog_pcoa_analysis.png"
plt.savefig(path_to_plots_diroutput_png, dpi=300, bbox_inches='tight')
plt.savefig(f"{path_to_plots_dir}/{plot_file_name}")

# Output basic stats to terminal
print(f"PCoA complete.")
print(f"Top 5 explained variance: {pcoa_res.proportion_explained[:5].values}")
print(f"Plot saved as: {output_png}")

