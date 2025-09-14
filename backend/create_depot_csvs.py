import pandas as pd
import os

def create_depot_csv_files():
    """Create separate CSV files for each depot with customer coordinates"""
    
    csv_path = 'customer_data_582.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        return []
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} customers from {csv_path}")
    
    depots = df['Depot_Assignment'].unique()
    print(f"Found depots: {list(depots)}")
    
    created_files = []
    for depot in depots:
        depot_df = df[df['Depot_Assignment'] == depot].copy()
        
        filename = f"{depot.lower().replace(' ', '_')}_customers.csv"
        
        depot_df.to_csv(filename, index=False)
        created_files.append(filename)
        
        print(f"\nCreated {filename}")
        print(f"  - {len(depot_df)} customers")
        print(f"  - Columns: {list(depot_df.columns)}")
        
        if len(depot_df) > 0:
            print("  - Sample customers:")
            sample_df = depot_df[['Customer', 'Address', 'Latitude', 'Longitude']].head(3)
            for _, row in sample_df.iterrows():
                print(f"    {row['Customer']}: {row['Address']} ({row['Latitude']}, {row['Longitude']})")
    
    print(f"\nSummary: Created {len(created_files)} CSV files:")
    for file in created_files:
        print(f"  - {file}")
    
    return created_files

if __name__ == "__main__":
    create_depot_csv_files()
