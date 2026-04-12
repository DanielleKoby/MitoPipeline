import pandas as pd
import re
from collections import Counter
import random
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats
from scipy import stats
from statsmodels.stats.multitest import fdrcorrection

# --- CONFIGURATION ---
TOP_N = 13 

# Get project root from script location
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Path to the ML-Dist matrix file
path_to_fa_file = str(PROJECT_ROOT / "data/processed/consensus/iqtree_output/msa_consensus_clean_headers.fa.mldist")
path_to_dist_csv = str(PROJECT_ROOT / "data/processed/analysis/breed_distances_purebred.csv")

ID_COL_IDX = 0
path_to_plots_dir = str(PROJECT_ROOT / "results/plots")

# --- DATA LOADING AND INITIAL CLEANING ---
mdist = pd.read_csv(path_to_fa_file, sep='\s+', engine='python', header=None, skiprows=[0])

def get_breed_info(sample_id):
    """
    Extracts the cleaned breed identifier from the full sample ID string.
    Skips the first two underscore-separated fields (SRR_SAMN).
    """

    # Ensure sample_id is treated as a string before splitting
    parts = str(sample_id).split('_')
    
    # Validation check: Ensure the ID has the expected structure
    if len(parts) > 2 and parts[0].upper().startswith(('SRR')):
        breed_info_list = parts[2:]
        
        # Rejoin the remaining parts
        breed_info = '_'.join(breed_info_list)
        
        # Optional cleaning: Remove common suffixes and trailing underscore
        # cleaned_name = breed_info.replace('Purebred', '')
        # cleaned_name = cleaned_name.replace('Mixed_breed', '')
        cleaned_name = breed_info.strip('_')
                                
        return cleaned_name
    else:
        return ""

# Perform initial breed extraction and counting
breed_series = mdist[ID_COL_IDX].apply(get_breed_info)
breed_counts = Counter(breed_series)
top_breeds = [item for item in breed_counts.most_common(TOP_N) if item[0] != ""] # Filter out empty string

# Print Top N Breeds
print(f"\n Top {TOP_N} Most Common Dog Breeds:")
print("=" * 40)
print(f"{'Rank':<6}{'Breed ID':<25}{'Count':>8}")
print("-" * 40)

for rank, (breed, count) in enumerate(top_breeds, 1):
    print(f"{rank:<6}{breed:<25}{count:>8,}")

print("=" * 40)

def create_breed_mapping_and_indices(mdist, breed_series):
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
    """
    Calculates In-Breed and Out-Breed average distances for the top N breeds.
    """
    
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


    for breed_name in top_breed_names:
        
        # 1. Identify IDs belonging to the current breed
        current_breed_ids = [
            id_val for id_val, breed in id_to_breed.items() 
            if breed == breed_name and id_val in id_to_index
        ]
        
        if len(current_breed_ids) < 2:
            print(f"Skipping {breed_name}: Insufficient samples ({len(current_breed_ids)}).")
            continue
            
        N = len(current_breed_ids) # Sample size for Out-Breed comparison
        
        # 2. Identify IDs for the OUT-GROUP (all other dogs)
        out_group_ids = list(all_valid_ids.difference(set(current_breed_ids)))
        
        in_distances = []
        out_distances = []
        
        # 3. Calculate distances for EACH dog in the current breed
        for dog_id in current_breed_ids:
            dog_idx = id_to_index[dog_id]
            
            # --- IN-BREED CALCULATION ---
            in_group_dists = []

            for other_dog_id in current_breed_ids:
                if dog_id != other_dog_id:
                    other_dog_idx = id_to_index[other_dog_id]
                    # Distance is at [row_index, col_index] in the distance matrix
                    dist = dist_matrix[dog_idx, other_dog_idx] 
                    in_group_dists.append(dist)
            
            # Record the average in-breed distance for this dog
            if in_group_dists:
                in_distances.append(np.mean(in_group_dists))

            # --- OUT-BREED CALCULATION (Random Sampling) ---
            avg_out_group_dists = 0
            for i in range(10):
                if len(out_group_ids) >= N:
                    sampled_out_ids = random.sample(out_group_ids, N)
                elif out_group_ids:
                    sampled_out_ids = out_group_ids 
                else:
                    continue

                out_group_dists = []
                for out_dog_id in sampled_out_ids:
                    out_dog_idx = id_to_index[out_dog_id]
                    dist = dist_matrix[dog_idx, out_dog_idx]
                    out_group_dists.append(dist)
                
                
                if out_group_dists:
                    avg_out_group_dists += np.mean(out_group_dists)


            # Record the average out-breed distance for this dog
            if out_group_dists:
                avg_out_group_dists /= 10
                out_distances.append(avg_out_group_dists)
        
        # 4. Append results to the main DataFrame (Using sort=False to resolve FutureWarning)
        
        in_df = pd.DataFrame({'Breed': breed_name, 'Distance_Type': 'In-Breed', 'Distance_Value': in_distances})
        results_df = pd.concat([results_df, in_df], ignore_index=True, sort=False)
        
        out_df = pd.DataFrame({'Breed': breed_name, 'Distance_Type': 'Out-Breed (Random)', 'Distance_Value': out_distances})
        results_df = pd.concat([results_df, out_df], ignore_index=True, sort=False)

        print(f"Processed {breed_name}: {N} samples.")
    return results_df

def run_u_test(top_breed_csv, top_breed_names):   
    df = pd.read_csv(top_breed_csv)
    breed_pval_lst = []
    for breed_name in top_breed_names:
        in_breed_df = df[(df['Breed'] == breed_name) & (df['Distance_Type'] == 'In-Breed')]
        out_breed_df = df[(df['Breed'] == breed_name) & (df['Distance_Type'] == 'Out-Breed (Random)')]
        
        # Running mannwhitneyu
        if(in_breed_df['Distance_Value'].size == 0 or out_breed_df['Distance_Value'].size == 0):
            print("something is wrong")
            exit(1)
        
        u_statistic, p_value = stats.mannwhitneyu(
                in_breed_df['Distance_Value'], 
                out_breed_df['Distance_Value'],
                alternative='less'  # Expecting in_breed dist less than out_breed
            )
        breed_pval_lst.append((breed_name, p_value))

    # Applying FDR
    p_vals_pre_fdr = []
    for breed in breed_pval_lst:
        p_vals_pre_fdr.append(breed[1])

    reject, pvals_corrected = fdrcorrection(p_vals_pre_fdr, method='indep', alpha=0.05, is_sorted=False)

    # The assumption: raw_p_values_list, pvals_corrected, and reject are defined 
    # in the preceding code block (Steps 2-4).

    # 1. Prepare the output header
    print("\n--- Comparison of Raw vs. FDR Corrected P-Values ---")
    print("---------------------------------------------------------------")
    print(f"{'Breed Name':<35}{'Raw P-Value':<20}{'FDR Corrected P-Value':<25}{'Significant (Alpha=0.05)':<20}")
    print("---------------------------------------------------------------")

    # The loop compares the values side-by-side
    # We iterate over the list of raw P-values tuples
    for i, (breed_name, raw_p) in enumerate(breed_pval_lst):
        
        # Extract the corresponding corrected value and boolean result (reject)
        corrected_p = pvals_corrected[i]
        is_significant = reject[i]
        
        # Print the results using Fixed-Point Format (8 decimal places)
        print(
            f"{breed_name:<35}"
            f"{raw_p:.8f}{'':<12}" # Printing the raw P-value
            f"{corrected_p:.8f}{'':<17}" # Printing the corrected P-value
            f"{str(is_significant):<20}" # Printing the boolean significance result
        )

    print("---------------------------------------------------------------")
    print("\nNote: Only corrected P-values (FDR Corrected P-Value) smaller than 0.05 lead to a True conclusion.")

def plot_box_plots_matplotlib(results_df, top_n):
    """
    Generates a Box Plot using Matplotlib comparing In-Breed and Out-Breed 
    average distances.
    """
    # 1. Prepare Data for Matplotlib
    # Determine the plotting order by the mean 'In-Breed' distance
    order = results_df[results_df['Distance_Type'] == 'In-Breed'].groupby('Breed')['Distance_Value'].mean().sort_values().index
    samples_count =[]
    plot_data = [] # List to hold the distance values for each box
    
    for breed in order:
        # Extract and append data for the 'In-Breed' box
        in_data = results_df[(results_df['Breed'] == breed) & (results_df['Distance_Type'] == 'In-Breed')]['Distance_Value'].tolist()
        # Extract and append data for the 'Out-Breed' box
        out_data = results_df[(results_df['Breed'] == breed) & (results_df['Distance_Type'] == 'Out-Breed (Random)')]['Distance_Value'].tolist()
        
        plot_data.append(in_data)
        plot_data.append(out_data)
        samples_count.append(len(in_data))
    print(samples_count) 
    # 2. Setup Plotting Environment
    fig, ax = plt.subplots(figsize=(16, 9))
    
    # Calculate positions for side-by-side boxes
    num_breeds = len(order)
    spacing = 3
    positions_base = np.arange(num_breeds) * spacing
    offset = 0.4
    final_positions = np.repeat(positions_base, 2) + np.tile([-offset, offset], num_breeds)
    
    # Define colors
    in_color = '#4CAF50' # Green
    out_color = '#FF5733' # Red-Orange
    colors = [in_color, out_color] * num_breeds
    
    # 3. Create the Box Plot 
    bp = ax.boxplot(
        plot_data,
        positions=final_positions, 
        widths=0.6,
        patch_artist=True, 
        medianprops={'color': 'black'}
    )
    
    # 4. Color the boxes manually
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    # 5. Set Axes and Labels
    ax.set_xticks(positions_base) 
    ax.set_xticklabels(order, rotation=45, ha='right')

    ax.set_title(f'Comparison of Genetic Distances: In-Breed vs. Out-Breed', fontsize=16)
    ax.set_ylabel('Average Genetic Distance (ML-Dist)', fontsize=12)
    ax.set_xlabel('Dog Breed (Sorted by In-Breed Mean)', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # y_min, y_max = ax.get_ylim()
    # y_range = y_max - y_min
    
    # vertical_offset = y_range * 0.015
    # for i, pos in enumerate(final_positions):
    #     if (i % 2 == 0):
    #         ax.text(
    #             pos,
    #             bp['caps'][i * 2 + 1].get_ydata()[0] + vertical_offset ,
    #             samples_count[i // 2],
    #             ha='center', 
    #             va='bottom',
    #             fontsize=10,
    #             color = 'black',
    #             fontweight='bold'
    #             )
    # Create manual legend
    ax.legend([bp["boxes"][0], bp["boxes"][1]], ['In-Breed', 'Out-Breed (Random)'], loc='upper left', title='Distance Type', framealpha= 0)

    plt.tight_layout()
    
    # 6. Save and Display
    plot_file_name = f'top_breed_distance_boxplot_purebred_only_random.png'
    plt.savefig(f"{path_to_plots_dir}/{plot_file_name}")
    print(f"\nBox Plot (Matplotlib) saved as: {plot_file_name}")


# ----------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------

# 1. Create necessary mappings and extract the matrix
dist_matrix, id_to_breed, id_to_index, id_list = create_breed_mapping_and_indices(mdist, breed_series)

# 2. Calculate In-Breed and Out-Breed distances for the top 10 breeds
print("\nStarting In/Out-Breed Distance Calculation...")
results_for_plot_df = calculate_distances(dist_matrix, id_list, id_to_breed, top_breeds, id_to_index)

# 3. Generate the Box Plot and Save Results
print("\nGenerating Box Plot...")

# Call the Matplotlib plotting function
plot_box_plots_matplotlib(results_for_plot_df, TOP_N)

# # Save the raw data used for the plot
# results_for_plot_csv = 'top_10_breed_distances.csv'
# results_for_plot_df.to_csv(results_for_plot_csv, index=False)
# print(f"Data used for plot saved to: {results_for_plot_csv}")

top_breeds = [
        breed for breed, count in top_breeds 
        if 'Unknown' not in breed and 'Mixed_breed' not in breed
    ]

run_u_test(path_to_dist_csv, top_breeds)
