import pandas as pd
import os

def create_real_lake_charles_csv():
    """Create CSV with 90 real Lake Charles customers using provided names and existing addresses"""
    
    real_customer_names = [
        "Adrien's Supermarket",
        "Aladdin Construction", 
        "B & W - Jennings",
        "Big Easy Foods",
        "Bo-Mac (Westlake -Air Products)",
        "Border Town-Formerly Delta Down",
        "Bronco Discount",
        "Brown & Root",
        "Cajun Deli",
        "Cajun Grocery",
        "Cajun Lunch Box-Welsh",
        "Cenla Express-Chevron-Alexandria",
        "Chadeaux's Cajun Kitchen",
        "Conoco Fifth Wheel-Sulphur",
        "Crying Eagle Brewery",
        "Cuccio's",
        "Daiquiri Shack",
        "Delicious Donuts",
        "Delta Downs - Barn # 1 - Philip Calais",
        "Delta Downs - Barn # 2- Kenneth Weeks",
        "Delta Downs - Barn # 3 - Kenneth Roberts",
        "Delta Downs - Barn # 4 - Trey Ellis",
        "Delta Downs - Barn # 8 - Martinez Racing",
        "Delta Downs - Barn # 9 -  Darrel Soileau",
        "Delta Downs - Barn # 9 - Orlando Orozco",
        "Delta Downs - Barn #10 - Jose Estrada",
        "Delta Downs - Barn #14 - Buddy Deville",
        "Delta Downs - Barn #18 - David Bustamante",
        "Delta Downs - Barn #19 - Leonel Hernandez",
        "Delta Food #4-Sulphur",
        "Delta Food #5-Moss Bluff",
        "Delta Food #7-Moss Bluff",
        "Dirty Rice",
        "Dock Sales-Lake Charles",
        "Elton Dryer Inc",
        "Elton Express (formerly Tony's Mini Mart)",
        "Feathers",
        "Fluor Federal Petroleum (DM Petroleum)",
        "Gillis Food Mart",
        "Glenn's Mart-Vinton",
        "Hanson's Super Foods",
        "HD  Truck & Tractor",
        "Henderson One Stop",
        "Hop-In",
        "I-10 Rayne Chevron",
        "JF PetroleumformerlyRITTNER)",
        "Johnson Bayou Convenient Store",
        "Jones Grocery & Deli",
        "Kerry A Sack",
        "Kinder Quick Stop",
        "Kingspoint #4",
        "KOA Campground",
        "Lavergne Farms",
        "LC-Dollar General",
        "LC-Sasol North America-Alcohol Unit",
        "LC-Sasol North America-Emergency Response",
        "LC-Sasol North America-Ethylene",
        "LC-Sasol North America-LAB",
        "LC-Sasol North America-Shop",
        "Lewing Construction",
        "M & K Pantry",
        "Meaux Seafood (M&B)",
        "Misses Grocery",
        "More 4  Less #10",
        "Myer's Landing",
        "Neighborhood Quick Mart",
        "Nonc Kev Meat Market",
        "Podnas Quick Mart, LLC",
        "Refuse Temple Inc.",
        "S & W One Stop(Smitty's)",
        "Savco (Point De Leglise)",
        "Smokers Express",
        "Smokers Paradise-SULPHUR",
        "Smokers Paradise-VINTON (LC ROUTE)",
        "Starks Truck Stop (In & Out)",
        "Steamboat Bill",
        "Sunshine Liquor Plus-Broad St.",
        "Sunshine Liquor-Lake Charles",
        "Super Saver #4",
        "System Services Broadband",
        "Ted's Quick Stop",
        "The Buzz",
        "Thibodeaux Country Store",
        "Time Loop #13(FrmlyMae Mae-Hodges)",
        "TJ's Market & Deli",
        "Total We Fair (EconoMart #9)",
        "TP's Grocery",
        "VOID-Lake Charles",
        "We Fair (EconoMart #9)",
        "WHC Energy Services-Lake Charles"
    ]
    
    print(f"Real customer names provided: {len(real_customer_names)}")
    
    lake_charles_csv = 'lake_charles_customers.csv'
    if not os.path.exists(lake_charles_csv):
        print(f"Error: {lake_charles_csv} not found")
        return None
    
    existing_df = pd.read_csv(lake_charles_csv)
    print(f"Existing Lake Charles customers: {len(existing_df)}")
    
    final_customers = []
    
    for i, real_name in enumerate(real_customer_names):
        if i < len(existing_df):
            row = existing_df.iloc[i].copy()
            row['Customer'] = real_name
            final_customers.append(row)
    
    remaining_needed = 90 - len(real_customer_names)
    if remaining_needed > 0:
        start_idx = len(real_customer_names)
        end_idx = min(start_idx + remaining_needed, len(existing_df))
        
        for i in range(start_idx, end_idx):
            row = existing_df.iloc[i].copy()
            final_customers.append(row)
    
    final_df = pd.DataFrame(final_customers)
    
    output_filename = 'real_lake_charles_customers_90.csv'
    final_df.to_csv(output_filename, index=False)
    
    print(f"\nCreated {output_filename}")
    print(f"  - Total customers: {len(final_df)}")
    print(f"  - Real customer names: {len(real_customer_names)}")
    print(f"  - Additional customers: {len(final_df) - len(real_customer_names)}")
    print(f"  - Columns: {list(final_df.columns)}")
    
    print("\nSample customers:")
    sample_df = final_df[['Customer', 'Address', 'Latitude', 'Longitude']].head(5)
    for _, row in sample_df.iterrows():
        print(f"  {row['Customer']}: {row['Address']} ({row['Latitude']}, {row['Longitude']})")
    
    print(f"\nLast few customers:")
    sample_df = final_df[['Customer', 'Address', 'Latitude', 'Longitude']].tail(3)
    for _, row in sample_df.iterrows():
        print(f"  {row['Customer']}: {row['Address']} ({row['Latitude']}, {row['Longitude']})")
    
    return output_filename

if __name__ == "__main__":
    create_real_lake_charles_csv()
