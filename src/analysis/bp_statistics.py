import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# --- Configuration ---
# Set the path to your CSV file as specified in your query
PATH_CSV = str(PROJECT_ROOT / "data/processed/analysis/preprocessing_metrics.csv")
# Define the output directory for all generated plots
OUTPUT_DIR = str(PROJECT_ROOT / "results/plots") 

# List of all columns for which you requested summary statistics
COLUMNS_TO_ANALYZE = [
    "Total_Reads",
    "Total_Mapped_Reads_w_Dups",
    "Total_Mapped_Reads_wo_Dups",
    "Mito_Reads_w_Dups",
    "Mito_Reads_wo_Dups",
    "Total_HQ_Reads_w_Dups",
    "Total_HQ_Reads_wo_Dups",
    "Mito_HQ_Reads_w_Dups",
    "Mito_HQ_Reads_wo_Dups",
    "Total_Depth_w_Dups",
    "Total_Depth_wo_Dups",
    "Mito_Depth_w_Dups",
    "Mito_HQ_Depth_w_Dups",
]


# --- Plotting Function ---
def create_box_plot(data_df, column_list, title, filename, output_dir, scale_factor=1, y_tick_interval=None):
    """
    Generates a box plot showing the distribution (median, quartiles, and outliers) 
    of specified metrics using the raw DataFrame, and adds numerical labels to 
    the median and quartiles.

    Args:
        data_df (pd.DataFrame): The raw DataFrame containing all sample data.
        column_list (list): List of specific column names to plot.
        title (str): Title for the plot.
        filename (str): Output filename for the PNG image.
        output_dir (str): Directory where the file will be saved.
        scale_factor (float): Factor to divide the values (e.g., 1e6 for millions).
        y_tick_interval (float, optional): Sets the major tick spacing on the y-axis.
    """

    if not column_list:
        print(f"No columns provided for plotting. Skipping plot: {title}")
        return

    # Select the raw data only for the specified list of columns and apply scaling
    plot_data = data_df[column_list] / scale_factor
    
    # Prepare labels: Clean up underscores for display
    labels = [col.replace('_', ' ').strip() for col in column_list]

    plt.figure(figsize=(12, 7)) # Increased figure size for better clarity
    
    # Create the box plot, saving the results dictionary to access median/quartiles
    # FIX: Removed 'return_type="dict"' for compatibility with older Matplotlib versions.
    # The function now returns the dictionary by default.
    box_results = plt.boxplot(plot_data.values, labels=labels, patch_artist=True, 
                              boxprops=dict(facecolor='lightblue', color='teal'),
                              medianprops=dict(color='black'))

    # --- Add Numerical Labels for Median and Quartiles ---
    for i, col in enumerate(column_list):
        # Calculate statistics from the plot data for the current column
        stats = plot_data.iloc[:, i].describe()
        q1 = stats['25%']
        median = stats['50%']
        q3 = stats['75%']

        # X position of the current box (1-indexed)
        x_pos = i + 1
        
        # Round the display value based on its magnitude
        if scale_factor == 1e6:
            # For millions, show one decimal for millions
            round_val = 1
        elif any(val > 1000 for val in [q1, median, q3]):
            # For thousands, show no decimals
            round_val = 0
        else:
            # For depths and small numbers, show two decimals
            round_val = 2 

        # Corrected format string creation: build the format string and apply it later
        format_spec = f'{{:,.{round_val}f}}'

        # Apply the format specification to the values
        q1_formatted = format_spec.format(q1)
        median_formatted = format_spec.format(median)
        q3_formatted = format_spec.format(q3)
        
        # Annotate Q1 (bottom of the box)
        plt.text(x_pos - 0.2, q1, q1_formatted, va='center', ha='right', fontsize=9, color='darkred')
        
        # Annotate Median (line inside the box)
        plt.text(x_pos + 0.2, median, median_formatted, va='center', ha='left', fontsize=9, fontweight='bold', color='black')

        # Annotate Q3 (top of the box)
        plt.text(x_pos - 0.2, q3, q3_formatted, va='center', ha='right', fontsize=9, color='darkred')
    
    
    # --- Plot Customization ---
    plt.title(title, fontsize=16, fontweight='bold')
    
    # Set Y-axis label based on scaling and metric type
    if scale_factor == 1e6:
        y_label = "Read Count (in Millions)"
    else:
        is_depth_plot = any('Depth' in col for col in column_list)
        y_label = "Depth" if is_depth_plot else "Read Count"

    plt.ylabel(y_label, fontsize=12)
    
    # Apply custom Y-axis tick interval if specified
    if y_tick_interval:
        plt.gca().yaxis.set_major_locator(MultipleLocator(y_tick_interval))

    # Improve X-axis readability
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    # Add a note about the elements
    plt.text(0.98, 0.02, 'Line = Median, Box = IQR (25%-75%), Dots = Outliers', transform=plt.gca().transAxes, 
             fontsize=8, color='gray', ha='right')

    # Save the plot
    full_path = os.path.join(output_dir, filename)
    plt.savefig(full_path)
    print(f"Generated plot saved to: {full_path}")
    plt.close()


# --- Data Loading and Analysis ---
def run_analysis(csv_path, columns):
    # Load the data
    data = pd.read_csv(csv_path)
    print(f"Successfully loaded data from: {csv_path}\n")

    # 1. Filter the DataFrame to include only the requested columns
    analysis_df = data.filter(items=columns)

    # 2. Use the .describe() method to calculate all requested statistics
    summary_stats = analysis_df.describe().T
    
    # 3. Rename the percentile columns
    summary_stats = summary_stats.rename(columns={'25%': 'Q1', '75%': 'Q3', '50%': 'Median (Q2)'})

    # Return both the raw data (data) and the summary statistics (summary_stats)
    return data, summary_stats


if __name__ == "__main__":
    
    # --- Define Metric Groups for Separate Plots ---
    
    # 1. Total Read Counts (excluding Total_Depth metrics)
    TOTAL_READ_METRICS = [
        "Total_Reads",
        "Total_Mapped_Reads_w_Dups",
        "Total_Mapped_Reads_wo_Dups",
        "Total_HQ_Reads_w_Dups",
        "Total_HQ_Reads_wo_Dups",
    ]

    # 2. Mitochondrial Read Counts (excluding Mito_Depth metrics and the first Mito_Read metric)
    # The first Mito_ column ("Mito_Reads_w_Dups") is excluded as requested previously.
    MITO_READ_METRICS = [
        "Mito_Reads_wo_Dups",
        "Mito_HQ_Reads_w_Dups",
        "Mito_HQ_Reads_wo_Dups",
    ]

    # 3. Total Depth Metrics 
    TOTAL_DEPTH_METRICS = [
        "Total_Depth_w_Dups",
        "Total_Depth_wo_Dups",
    ]
    
    # 4. Mitochondrial Depth Metrics
    MITO_DEPTH_METRICS = [
        "Mito_Depth_w_Dups",
        "Mito_HQ_Depth_w_Dups",
    ]

    # Execute the analysis
    raw_data, results_table = run_analysis(PATH_CSV, COLUMNS_TO_ANALYZE)
    
    # Print the resulting table
    print("--- Comprehensive Read & Depth Statistical Summary ---")
    
    # Format the output to suppress scientific notation for readability
    with pd.option_context('display.float_format', '{:,.2f}'.format):
        print(results_table)

    print("\nSuccessfully calculated descriptive statistics for all requested columns.")
    print("The table includes: count, mean, standard deviation (std), min, max, and the quartiles (Q1, Median/Q2, Q3).")

    # --- Generate Plots as Requested ---
    
    # -------------------------------------------------------------------------
    # Plot 1: TOTAL READ COUNTS (Box Plot)
    # -------------------------------------------------------------------------
    create_box_plot(
        data_df=raw_data,
        column_list=TOTAL_READ_METRICS, 
        title='Distribution of Total Read Counts (in Millions of Reads)',
        filename='Total_Reads_Box_Plot.png',
        output_dir=OUTPUT_DIR,
        scale_factor=1e6, # Scaling to Millions for big numbers
        y_tick_interval=10 # Major ticks every 10 Million
    )

    # -------------------------------------------------------------------------
    # Plot 2: MITOCHONDRIAL READ COUNTS (Box Plot)
    # -------------------------------------------------------------------------
    create_box_plot(
        data_df=raw_data,
        column_list=MITO_READ_METRICS, 
        title='Distribution of Mitochondrial Read Counts',
        filename='Mito_Reads_Box_Plot.png',
        output_dir=OUTPUT_DIR,
        scale_factor=1, # Keep as absolute counts
        y_tick_interval=5000 # Major ticks every 5000 reads
    )

    # -------------------------------------------------------------------------
    # Plot 3: TOTAL DEPTH METRICS (Box Plot)
    # -------------------------------------------------------------------------
    create_box_plot(
        data_df=raw_data,
        column_list=TOTAL_DEPTH_METRICS, 
        title='Distribution of Total Depth Metrics',
        filename='Total_Depth_Box_Plot.png',
        output_dir=OUTPUT_DIR,
        scale_factor=1, # Depth values are typically small
        y_tick_interval=1 # Major ticks every 1 units
    )
    
    # -------------------------------------------------------------------------
    # Plot 4: MITOCHONDRIAL DEPTH METRICS (Box Plot)
    # -------------------------------------------------------------------------
    create_box_plot(
        data_df=raw_data,
        column_list=MITO_DEPTH_METRICS, 
        title='Distribution of Mitochondrial Depth Metrics',
        filename='Mito_Depth_Box_Plot.png',
        output_dir=OUTPUT_DIR,
        scale_factor=1, # Depth values are typically small
        y_tick_interval=100 # Major ticks every 100 units
    )

    print("\n--- Final Plotting Summary ---")
    print(f"Plotting complete. Please check the new directory '{OUTPUT_DIR}' for the 4 generated Box Plot files.")