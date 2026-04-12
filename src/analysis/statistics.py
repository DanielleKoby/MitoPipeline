import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# --- Configuration ---
# Set the path to your CSV file as specified in your query
PATH_CSV = str(PROJECT_ROOT / "data/processed/analysis/preprocessing_metrics.csv")

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
def create_bar_plot(df_summary, column_list, title, filename, scale_factor=1):
    """
    Generates a bar plot showing the mean and standard deviation of specified metrics.

    Args:
        df_summary (pd.DataFrame): The descriptive statistics summary table.
        column_list (list): List of specific column names to plot.
        title (str): Title for the plot.
        filename (str): Output filename for the PNG image.
        scale_factor (float): Factor to divide the values (e.g., 1e6 for millions).
    """

    if not column_list:
        print(f"No columns provided for plotting. Skipping plot: {title}")
        return

    # Select the data only for the specified list of columns
    plot_data = df_summary.loc[column_list]
    
    # Extract mean and standard deviation, scaled
    means = plot_data['mean'] / scale_factor
    stds = plot_data['std'] / scale_factor
    
    # Prepare labels: Clean up underscores for display
    # Labels use the full, descriptive column name for clarity
    labels = [col.replace('_', ' ').strip() for col in column_list]

    plt.figure(figsize=(12, 7)) # Increased figure size for better clarity
    
    # Create the bar plot with error bars (Standard Deviation)
    bars = plt.bar(labels, means, yerr=stds, capsize=5, color='teal', edgecolor='black', alpha=0.7)

    # Set title and labels
    plt.title(title, fontsize=16, fontweight='bold')
    
    # Set Y-axis label based on scaling and metric type
    if scale_factor == 1e6:
        y_label = "Average Read Count (in Millions)"
    else:
        # Check if the plot contains 'Depth' metrics to set appropriate Y-label
        is_depth_plot = any('Depth' in col for col in column_list)
        y_label = "Average Depth" if is_depth_plot else "Average Read Count"

    plt.ylabel(y_label, fontsize=12)
    
    # Improve X-axis readability
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    # Add a note about the error bars
    plt.text(0.98, 0.02, 'Error Bars = Standard Deviation', transform=plt.gca().transAxes, 
             fontsize=8, color='gray', ha='right')

    # Save the plot
    plt.savefig(filename)
    print(f"Generated plot saved to: {filename}")
    plt.close()


# --- Data Loading and Analysis ---
def run_analysis(csv_path, columns):
    """
    Loads data from the specified CSV and computes descriptive statistics
    for the given list of columns.
    
    NOTE: If the CSV file is not found, the program will terminate with a 
    FileNotFoundError from pandas/Python.
    """
    # Load the data
    data = pd.read_csv(csv_path)
    print(f"Successfully loaded data from: {csv_path}\n")

    # 1. Filter the DataFrame to include only the requested columns
    # This also checks if the columns exist in the loaded data
    analysis_df = data.filter(items=columns)

    # 2. Use the .describe() method to calculate all requested statistics (mean, std, min, max, Q1, Q3)
    # The transpose (.T) makes the output readable, with metrics as columns and features as rows
    summary_stats = analysis_df.describe().T
    
    # 3. Rename the percentile columns to match your Q1 and Q3 terminology
    summary_stats = summary_stats.rename(columns={'25%': 'Q1', '75%': 'Q3', '50%': 'Median (Q2)'})

    return summary_stats


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

    # 3. All Depth Metrics (Total and Mitochondrial) - NEW SEPARATE PLOT
    ALL_DEPTH_METRICS = [
        "Total_Depth_w_Dups",
        "Total_Depth_wo_Dups",
        "Mito_Depth_w_Dups",
        "Mito_HQ_Depth_w_Dups",
    ]

    # Execute the analysis
    results_table = run_analysis(PATH_CSV, COLUMNS_TO_ANALYZE)
    
    # Print the resulting table
    print("--- Comprehensive Read & Depth Statistical Summary ---")
    
    # Format the output to suppress scientific notation for readability
    with pd.option_context('display.float_format', '{:,.2f}'.format):
        print(results_table)

    print("\nSuccessfully calculated descriptive statistics for all requested columns.")
    print("The table includes: count, mean, standard deviation (std), min, max, and the quartiles (Q1, Median/Q2, Q3).")

    # --- Generate Plots as Requested ---
    
    # -------------------------------------------------------------------------
    # Plot 1: TOTAL READ COUNTS (Scaled to Millions) - Reads only
    # -------------------------------------------------------------------------
    create_bar_plot(
        df_summary=results_table,
        column_list=TOTAL_READ_METRICS, 
        title='Average Total Read Counts (in Millions of Reads)',
        filename='Total_Reads_Bar_Chart.png',
        scale_factor=1e6 # Scaling to Millions for big numbers
    )

    # -------------------------------------------------------------------------
    # Plot 2: MITOCHONDRIAL READ COUNTS (Absolute Counts) - Reads only
    # -------------------------------------------------------------------------
    create_bar_plot(
        df_summary=results_table,
        column_list=MITO_READ_METRICS, 
        title='Average Mitochondrial Read Counts (Original Counts)',
        filename='Mito_Reads_Bar_Chart.png',
        scale_factor=1 # Keep as absolute counts
    )

    # -------------------------------------------------------------------------
    # Plot 3: ALL DEPTH METRICS (Absolute Depth) - NEW SEPARATE PLOT
    # -------------------------------------------------------------------------
    create_bar_plot(
        df_summary=results_table,
        column_list=ALL_DEPTH_METRICS, 
        title='Average Total and Mitochondrial Depth Metrics',
        filename='All_Depth_Metrics_Bar_Chart.png',
        scale_factor=1 # Depth values are typically small
    )

    print("\nPlotting complete. Check your directory for 'Total_Reads_Bar_Chart.png', 'Mito_Reads_Bar_Chart.png', and 'All_Depth_Metrics_Bar_Chart.png'.")
