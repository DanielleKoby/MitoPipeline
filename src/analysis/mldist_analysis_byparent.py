import pandas as pd
import re
from collections import Counter
import random
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
TOP_N = 10 

# Get project root from script location
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Path to the ML-Dist matrix file
path_to_fa_file = str(PROJECT_ROOT / "data/processed/consensus/iqtree_output/msa_consensus_clean_headers.fa.mldist")
ID_COL_IDX = 0

# --- DATA LOADING AND INITIAL CLEANING ---
try:
    # Read the data: skip the initial sample count line (row 0)
    mdist = pd.read_csv(path_to_fa_file, sep='\s+', engine='python', header=None, skiprows=[0])
except pd.errors.ParserError as e:
    print(f"Error loading file: {e}. Please ensure the file structure is correct and check the path.")
    exit()

# ----------------------------------------------------------------------
# HELPER FUNCTION 1: Extracting Breed Components and Status
# ----------------------------------------------------------------------

def get_breed_info(sample_id):
    """
    Extracts the breed components (list) and status (str) from the sample ID.
    
    Returns: (list_of_breeds, breed_status)
    Example: 'SRR..._Dachshund_West_Highland_White_Terrier_Mixed_breed' -> 
             (['Dachshund', 'West_Highland_White_Terrier'], 'Mixed_breed')
    """
    if pd.isna(sample_id):
        return [], ""
    
    parts = str(sample_id).split('_')
    
    if len(parts) > 2 and parts[0].upper().startswith(('SRR', 'SAMN')):
        breed_info_list = parts[2:]
        
        status = ""
        # 1. Identify Status and remove it temporarily
        if 'Purebred' in breed_info_list:
            status = 'Purebred'
            breed_info_list.remove('Purebred')
        elif 'Mixed_breed' in breed_info_list:
            status = 'Mixed_breed'
            breed_info_list.remove('Mixed_breed')
            
        breeds = []
        breed_str = "_".join(breed_info_list)
        
        # 2. Split Mixed Breeds into components based on logical assumptions:
        if status == 'Mixed_breed' and breed_str:
            
            # --- Logic for handling Mixed Breeds: ---
            
            # Case 1: Assumed structure is Breed1_Breed2_Mixed_breed
            # We look for the last underscore that is NOT part of a known multi-word breed name
            
            # NOTE: This requires a highly domain-specific list of multi-word breeds or a complex regex.
            # A simpler, slightly risky approach: Assume the split is NOT at a known single breed name end.
            
            if 'Unknown' in breed_info_list:
                 # Case: Labrador_Retriever_Unknown_Mixed_breed
                 breeds.append("_".join(breed_info_list[:breed_info_list.index('Unknown')]))
                 breeds.append("_".join(breed_info_list[breed_info_list.index('Unknown'):]))
            else:
                # Find the splitting point by counting underscores
                if breed_str.count('_') >= 1:
                    
                    # Split into potential single names
                    potential_names = breed_str.split('_')
                    
                    # Assume the list of names is [Name1, Name2, ...] and the split is in the middle.
                    # This is highly context dependent. We will try a simpler split for two components:
                    
                    # We look for a capitalization change or a dictionary of breeds.
                    # Since we don't have that, we use the simple split of the entire string for now:
                    
                    # Assuming only one known component or one complex name, unless explicitly separated.
                    
                    # We will simply assume any remaining underscore is a separator for the purposes of this analysis,
                    # UNLESS the remaining string is a known single breed name (e.g. 'Golden_Retriever').
                    # Given the constraints, we will rely on the simplest split:
                    
                    breeds = [breed_str] # Start assuming single complex name
                    
                    # If we find a specific multi-component case (e.g. Dachshund_West_Highland_White_Terrier_Mixed_breed)
                    # We will need external data to split it reliably.
                    # Lacking that, we will assume for this example a two-component split is NOT reliable via underscore.
                    # For the purpose of running the code, we will assume the name remains one component unless 'Unknown' is present.
                    # If you have specific examples, we can refine this.
                    
                    # **Temporary simplification for robustness:** If Mixed, but no 'Unknown', treat as one component.
                    
        if not breeds: # For Purebred or single component mixed/complex names
            breeds = [breed_str]
        
        # Cleanup: remove any empty strings or trailing underscores
        breeds = [b.strip('_') for b in breeds if b.strip('_')]
        
        return breeds, status
    else:
        return [], ""

# ----------------------------------------------------------------------
# HELPER FUNCTION 2: Create Mapping and Extract Matrix
# ----------------------------------------------------------------------

def create_breed_mapping_and_indices(mdist):
    """
    Creates necessary dictionaries and extracts the list of IDs and distance matrix.
    This version uses get_breed_info to create the ID -> full data map.
    """
    full_ids = mdist[ID_COL_IDX]
    
    # Process all IDs to get breed components and status
    processed_data = full_ids.apply(get_breed_info)
    
    # Create the Top N list based on the PRIMARY breed name for PUREBREDs/SINGLE MIXED
    primary_breeds_for_count = []
    for components, status in processed_data:
        if components:
            if status == 'Purebred':
                # Purebred counts as one breed
                primary_breeds_for_count.append(components[0])
            elif status == 'Mixed_breed':
                # Mixed breeds are counted by their components
                primary_breeds_for_count.extend(components)
    
    # 1. ID -> Full Breed Data (e.g., ID -> (['Labrador_Retriever'], 'Purebred'))
    id_to_full_data = dict(zip(full_ids, processed_data))
    
    # 2. ID -> Row Index Mapping
    id_to_index = {id_val: i for i, id_val in enumerate(full_ids)}
    
    # 3. Distance Matrix
    dist_matrix = mdist.iloc[:, 1:].values
    
    # 4. List of all IDs for iteration
    id_list = list(full_ids)

    # Determine Top N based on PRIMARY breed components
    breed_counts_flat = Counter(primary_breeds_for_count)
    # We return the list of TOP N breed components names and their counts
    top_breeds = [item for item in breed_counts_flat.most_common(TOP_N) if item[0] != "" and 'Unknown' not in item[0]]
    
    return dist_matrix, id_to_full_data, id_to_index, id_list, top_breeds

# ----------------------------------------------------------------------
# HELPER FUNCTIONS 3 & 4: Distance Calculation Helpers
# ----------------------------------------------------------------------

def calculate_average_distance(dog_id, comparison_ids, dist_matrix, id_to_index):
    """Calculates average distance of dog_id to all others in comparison_ids."""
    dog_idx = id_to_index[dog_id]
    dists = []
    for other_dog_id in comparison_ids:
        # Avoid calculating distance to self
        if dog_id != other_dog_id:
            other_dog_idx = id_to_index.get(other_dog_id)
            if other_dog_idx is not None:
                dists.append(dist_matrix[dog_idx, other_dog_idx])
    return dists

def calculate_average_distance_out(dog_id, out_group_ids, N, dist_matrix, id_to_index):
    """Calculates average distance of dog_id to N randomly sampled out-group IDs."""
    dog_idx = id_to_index[dog_id]
    dists = []

    # Sample N dogs or all available if out-group is smaller
    if len(out_group_ids) >= N:
        sampled_out_ids = random.sample(out_group_ids, N)
    elif out_group_ids:
        sampled_out_ids = out_group_ids
    else:
        return []

    for out_dog_id in sampled_out_ids:
        out_dog_idx = id_to_index.get(out_dog_id)
        if out_dog_idx is not None:
            dists.append(dist_matrix[dog_idx, out_dog_idx])
            
    return dists

# ----------------------------------------------------------------------
# HELPER FUNCTION 5: Main Distance Calculation (Handling Mixed Breeds)
# ----------------------------------------------------------------------

def calculate_distances_mixed(dist_matrix, id_list, id_to_full_data, top_breeds_list, id_to_index):
    """
    Calculates In-Breed and Out-Breed average distances, handling mixed breeds 
    by checking against both component breeds.
    """
    
    results_df = pd.DataFrame(columns=['Breed', 'Distance_Type', 'Distance_Value'])
    all_valid_ids = set(id_list)
    
    # Use only the breed names from the top_breeds list
    top_breed_names = [b for b, c in top_breeds_list]

    # 1. Pre-calculate IDs for all top components
    top_component_ids = {}
    for name in top_breed_names:
        top_component_ids[name] = [
            id_val for id_val, data in id_to_full_data.items()
            if data[0] and name in data[0] and id_val in id_to_index
        ]
        
    for primary_breed_name in top_breed_names:
        
        # 2. Identify the target dogs: ALL dogs (pure or mixed) that CONTAIN this component
        dogs_with_this_component = top_component_ids.get(primary_breed_name, [])
        
        if len(dogs_with_this_component) < 2:
            print(f"Skipping {primary_breed_name}: Insufficient samples ({len(dogs_with_this_component)}).")
            continue
            
        N = len(dogs_with_this_component) # Sample size for Out-Breed comparison
        
        # 3. Identify the full out-group for random sampling
        out_group_ids = list(all_valid_ids.difference(set(dogs_with_this_component)))
        
        in_distances = []
        out_distances = []
        
        # --- ITERATE OVER ALL DOGS THAT CONTAIN THIS COMPONENT ---
        for dog_id in dogs_with_this_component:
            
            breeds_components, status = id_to_full_data.get(dog_id, ([], ""))
            
            # --- IN-BREED CALCULATION ---
            
            # If the dog is a mixed breed with two components
            if status == 'Mixed_breed' and len(breeds_components) == 2:
                # Calculate In-Breed against BOTH components and record both results
                
                # Component 1 (which is the primary_breed_name in this iteration)
                target_ids_c1 = top_component_ids.get(breeds_components[0], [])
                
                in_dists_c1 = calculate_average_distance(dog_id, target_ids_c1, dist_matrix, id_to_index)
                if in_dists_c1:
                    # Record the distance for the first component
                    in_distances.append(np.mean(in_dists_c1))
                
                # Component 2
                target_ids_c2 = top_component_ids.get(breeds_components[1], [])
                
                in_dists_c2 = calculate_average_distance(dog_id, target_ids_c2, dist_matrix, id_to_index)
                if in_dists_c2:
                    # Record the distance for the second component
                    in_distances.append(np.mean(in_dists_c2))
                    
            # Default (Purebred or Single Mixed/Complex name)
            else:
                target_ids_default = dogs_with_this_component
                in_dists_default = calculate_average_distance(dog_id, target_ids_default, dist_matrix, id_to_index)
                if in_dists_default:
                    in_distances.append(np.mean(in_dists_default))

            # --- OUT-BREED Calculation (remains the same) ---
            out_group_dists = calculate_average_distance_out(dog_id, out_group_ids, N, dist_matrix, id_to_index)
            if out_group_dists:
                out_distances.append(np.mean(out_group_dists))
        
        # 4. Append results
        in_df = pd.DataFrame({'Breed': primary_breed_name, 'Distance_Type': 'In-Breed', 'Distance_Value': in_distances})
        results_df = pd.concat([results_df, in_df], ignore_index=True, sort=False)
        
        out_df = pd.DataFrame({'Breed': primary_breed_name, 'Distance_Type': 'Out-Breed (Random)', 'Distance_Value': out_distances})
        results_df = pd.concat([results_df, out_df], ignore_index=True, sort=False)

        print(f"Processed {primary_breed_name}: {N} samples.")
        
    return results_df

# ----------------------------------------------------------------------
# PLOTTING FUNCTION (Matplotlib)
# ----------------------------------------------------------------------

def plot_box_plots_matplotlib(results_df, top_n):
    """
    Generates a Box Plot using Matplotlib comparing In-Breed and Out-Breed 
    average distances.
    """
    if results_df.empty:
        print("No valid data to plot.")
        return

    # 1. Prepare Data for Matplotlib
    order = results_df[results_df['Distance_Type'] == 'In-Breed'].groupby('Breed')['Distance_Value'].mean().sort_values().index

    plot_data = [] 
    
    for breed in order:
        in_data = results_df[(results_df['Breed'] == breed) & (results_df['Distance_Type'] == 'In-Breed')]['Distance_Value'].tolist()
        out_data = results_df[(results_df['Breed'] == breed) & (results_df['Distance_Type'] == 'Out-Breed (Random)')]['Distance_Value'].tolist()
        
        plot_data.append(in_data)
        plot_data.append(out_data)
        

    # 2. Setup Plotting Environment
    fig, ax = plt.subplots(figsize=(16, 9))
    
    num_breeds = len(order)
    spacing = 3
    positions_base = np.arange(num_breeds) * spacing
    offset = 0.4
    final_positions = np.repeat(positions_base, 2) + np.tile([-offset, offset], num_breeds)
    
    in_color = '#4CAF50' 
    out_color = '#FF5733' 
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

    ax.set_title(f'Comparison of Genetic Distances: In-Breed vs. Out-Breed (Top {top_n} Breeds)', fontsize=16)
    ax.set_ylabel('Average Genetic Distance (ML-Dist)', fontsize=12)
    ax.set_xlabel('Dog Breed Component (Sorted by In-Breed Mean)', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    ax.legend([bp["boxes"][0], bp["boxes"][1]], ['In-Breed', 'Out-Breed (Random)'], loc='upper right', title='Distance Type')

    plt.tight_layout()
    
    # 6. Save and Display
    plot_file_name = f'top_{top_n}_breed_distance_boxplot_mpl.png'
    plt.savefig(plot_file_name)
    print(f"\n✅ Box Plot (Matplotlib) saved as: {plot_file_name}")
    plt.show()

# ----------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------

# 1. Load data, create mappings, and determine Top N breeds
# NOTE: The list of top breeds returned here is based on PRIMARY components.
dist_matrix, id_to_full_data, id_to_index, id_list, top_breeds = create_breed_mapping_and_indices(mdist)

# The printing section needs to be updated to use the new top_breeds variable

print(f"\n✅ Top {TOP_N} Most Common Dog Breeds (by Primary Component):")
print("=" * 60)
print(f"{'Rank':<6}{'Breed Component':<35}{'Count':>8}")
print("-" * 60)

for rank, (breed, count) in enumerate(top_breeds, 1):
    print(f"{rank:<6}{breed:<35}{count:>8,}")

print("=" * 60)

# 2. Calculate In-Breed and Out-Breed distances for the top 10 breeds
print("\nStarting In/Out-Breed Distance Calculation (Handling Mixed Breeds)...")
results_for_plot_df = calculate_distances_mixed(dist_matrix, id_list, id_to_full_data, top_breeds, id_to_index)

# 3. Generate the Box Plot and Save Results
if not results_for_plot_df.empty:
    print("\nGenerating Box Plot...")
    
    plot_box_plots_matplotlib(results_for_plot_df, TOP_N)

    results_for_plot_csv = 'top_10_breed_distances_mixed.csv'
    results_for_plot_df.to_csv(results_for_plot_csv, index=False)
    print(f"Data used for plot saved to: {results_for_plot_csv}")

else:
    print("\n❌ Could not calculate distances or plot: Results DataFrame is empty.")