import pandas as pd
import sys
import matplotlib.pyplot as plt
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Using a relative path for the execution environment
CSV_FILE_PATH = str(PROJECT_ROOT / "data/processed/analysis/preprocessing_metrics.csv") 

def create_bar_chart(df_stats, title, filename):
    """Generates and saves a bar chart for given statistics."""
    
    # Sort by mean value for better visualization
    df_stats_sorted = df_stats.sort_values(by='mean', ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    bars = ax.bar(df_stats_sorted['Metric_Label'], df_stats_sorted['mean'], 
                  yerr=df_stats_sorted['std'], capsize=5, color='skyblue', edgecolor='blue', 
                  label='Mean Value')

    ax.set_title(title, fontsize=16)
    ax.set_ylabel('Value', fontsize=12)
    ax.set_xlabel('Metric', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add mean value labels on top of the bars
    for i, bar in enumerate(bars):
        yval = bar.get_height()
        error = df_stats_sorted['std'].iloc[i]
        
        # Determine format based on magnitude (for better readability of large numbers)
        if yval >= 1_000_000:
            label = f'{yval/1_000_000:,.1f}M'
        elif yval >= 1_000:
            label = f'{yval/1_000:,.1f}K'
        else:
            label = f'{yval:,.1f}'
            
        # Position the label slightly above the error bar
        ax.text(bar.get_x() + bar.get_width()/2, 
                yval + error + df_stats_sorted['std'].max() * 0.05, 
                label, ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(filename)
    print(f"Plot saved as {filename}")
    plt.close(fig)


def analyze_statistics_and_plot(csv_path):
    """
    Loads the CSV file, performs basic statistical analysis, and generates
    two separate bar charts for Depth and Read Count metrics.
    """
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: The file '{csv_path}' was not found. Please upload it.")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"Error: The file '{csv_path}' is empty.")
        sys.exit(1)

    print(f"--- Analysis for {csv_path} ---")
    
    # --- Original Analysis Part (keeping this for context) ---
    # Display basic info, data types, and statistical summaries...
    print(f"\n[Shape of Data]")
    print(f"Total Samples (Rows): {df.shape[0]}")
    print(f"Total Metrics (Columns): {df.shape[1]}")
    
    print("\n[Column Data Types]")
    import io
    buffer = io.StringIO()
    df.info(buf=buffer)
    print(buffer.getvalue())

    # ... (Rest of the original print statements for stats) ...
    df['Mito_Ratio_w_Dups'] = (df['Mito_Reads_w_Dups'] / df['Total_Mapped_Reads_w_Dups']).fillna(0)
    df['Mito_HQ_Ratio_w_Dups'] = (df['Mito_HQ_Reads_w_Dups'] / df['Total_HQ_Reads_w_Dups']).fillna(0)
    
    numeric_cols = df.select_dtypes(include=['number'])
    print("\n[Statistical Summary (Mean, Median, Min/Max, etc.)]")
    print(numeric_cols.describe().to_string())
    print("\n[Mitochondrial Ratio Analysis (w/ Duplicates)]")
    print(df[['Mito_Ratio_w_Dups', 'Mito_HQ_Ratio_w_Dups']].describe().to_string())

    high_mito_depth = df[df['Mito_Depth_w_Dups'] > 100]
    print(f"\n[Samples with High Mito Depth (>100x)]")
    if not high_mito_depth.empty:
        print(high_mito_depth[['Sample_ID', 'Mito_Depth_w_Dups', 'Mito_HQ_Depth_w_Dups']].to_string())
    else:
        print("No samples found with mitochondrial depth > 100x.")
    # --- End of Original Analysis Part ---
        
    # --- Revised Plotting Logic (Two Separate Plots) ---
    print("\n[Generating Separate Plots for Depth and Read Count Metrics...]")

    metric_labels = {
        'Mito_Depth_w_Dups': 'Mito Depth (w/ Dups)',
        'Mito_HQ_Depth_w_Dups': 'Mito HQ Depth (w/ Dups)',
        'Total_Reads_w_Dups': 'Total Reads (w/ Dups)',
        'Total_HQ_Reads_w_Dups': 'Total HQ Reads (w/ Dups)',
        'Mito_Reads_w_Dups': 'Mito Reads (w/ Dups)',
        'Mito_HQ_Reads_w_Dups': 'Mito HQ Reads (w/ Dups)'
    }

    # 1. Depth Metrics Plot
    depth_metrics = ['Mito_Depth_w_Dups', 'Mito_HQ_Depth_w_Dups']
    available_depth_metrics = [col for col in depth_metrics if col in df.columns]
    
    if available_depth_metrics:
        depth_stats_df = df[available_depth_metrics].agg(['mean', 'std']).T
        depth_stats_df['Metric_Label'] = depth_stats_df.index.map(metric_labels)
        create_bar_chart(
            depth_stats_df, 
            'Mean and STD of Mitochondrial Depth Metrics (in X)', 
            "mito_depth_stats_bar_chart.png"
        )
    else:
        print("Warning: No depth metrics found for plotting.")


    # 2. Read Count Metrics Plot (Total Reads vs Mito Reads)
    read_metrics = [
        'Total_Reads_w_Dups', 'Total_HQ_Reads_w_Dups',
        'Mito_Reads_w_Dups', 'Mito_HQ_Reads_w_Dups'
    ]
    available_read_metrics = [col for col in read_metrics if col in df.columns]

    if available_read_metrics:
        read_stats_df = df[available_read_metrics].agg(['mean', 'std']).T
        read_stats_df['Metric_Label'] = read_stats_df.index.map(metric_labels)
        create_bar_chart(
            read_stats_df, 
            'Mean and STD of Total and Mitochondrial Read Counts', 
            "read_counts_stats_bar_chart.png"
        )
    else:
        print("Warning: No read count metrics found for plotting.")


if __name__ == "__main__":
    analyze_statistics_and_plot(CSV_FILE_PATH)