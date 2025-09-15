import pandas as pd
import os
import json
import asyncio
from typing import List, Dict, Tuple
from app.google_maps_service import GoogleMapsService

def parse_customer_data(data_text: str) -> List[Dict]:
    """Parse the customer data from the provided text format"""
    customers = []
    lines = data_text.strip().split('\n')
    
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split('\t')
        if len(parts) < 6:
            continue
            
        customer_name = parts[0].strip()
        address_parts = []
        phone = ""
        city = ""
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
                
            if any(word in part.lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'hwy', 'highway', 'blvd', 'boulevard', 'drive', 'dr', 'lane', 'ln', 'pkwy', 'parkway']):
                address_parts.append(part)
            elif any(city_name in part for city_name in ['Lafayette', 'Lake Charles', 'Sulphur', 'Westlake', 'Breaux Bridge', 'St. Martinville', 'Jennings', 'Iowa', 'Scott', 'Churchpoint', 'Rayne', 'Crowley', 'Welsh', 'Starks', 'Vinton', 'Fenton', 'Kinder', 'REEVES', 'Lake Arthur', 'Hayes', 'Elton', 'Hackberry']):
                city = part
            elif '-' in part and len(part.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')) >= 10:
                phone = part
        
        address = ' '.join(address_parts) if address_parts else ""
        
        if customer_name and (address or city):
            full_address = f"{address}, {city}" if address and city else (address or city)
            customers.append({
                'name': customer_name,
                'address': full_address,
                'phone': phone
            })
    
    return customers

def create_google_maps_html(customers_with_coords: List[Dict], output_file: str = "customer_map.html"):
    """Create an interactive HTML map with Google Maps pins"""
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Customer Locations Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
            height: 100vh;
            width: 100%;
        }}
        .info-window {{
            font-family: Arial, sans-serif;
            max-width: 300px;
        }}
        .customer-name {{
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 5px;
        }}
        .customer-address {{
            color: #666;
            margin-bottom: 3px;
        }}
        .customer-phone {{
            color: #2e7d32;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <script>
        function initMap() {{
            const map = new google.maps.Map(document.getElementById("map"), {{
                zoom: 8,
                center: {{ lat: 30.5, lng: -93.0 }},
                mapTypeId: google.maps.MapTypeId.ROADMAP
            }});
            
            const customers = {json.dumps(customers_with_coords, indent=12)};
            
            const bounds = new google.maps.LatLngBounds();
            
            const depotColors = {{
                'Lake Charles': '#FF6B6B',
                'Lufkin': '#4ECDC4', 
                'Leesville': '#45B7D1',
                'Other': '#96CEB4'
            }};
            
            customers.forEach((customer, index) => {{
                const position = {{ lat: customer.latitude, lng: customer.longitude }};
                
                let depot = 'Other';
                const addr = customer.address.toLowerCase();
                if (addr.includes('lake charles') || addr.includes('sulphur') || addr.includes('westlake') || addr.includes('hackberry')) {{
                    depot = 'Lake Charles';
                }} else if (addr.includes('tx') || addr.includes('lufkin')) {{
                    depot = 'Lufkin';
                }} else if (addr.includes('leesville') || addr.includes('la')) {{
                    depot = 'Leesville';
                }}
                
                const color = depotColors[depot];
                
                const marker = new google.maps.Marker({{
                    position: position,
                    map: map,
                    title: customer.name,
                    icon: {{
                        url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
                            <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="16" cy="16" r="12" fill="${{color}}" stroke="#FFFFFF" stroke-width="2"/>
                                <text x="16" y="20" text-anchor="middle" fill="white" font-size="8" font-weight="bold">${{index + 1}}</text>
                            </svg>
                        `),
                        scaledSize: new google.maps.Size(32, 32),
                    }}
                }});
                
                const infoContent = `
                    <div class="info-window">
                        <div class="customer-name">${{customer.name}}</div>
                        <div class="customer-address">${{customer.address}}</div>
                        ${{customer.phone ? `<div class="customer-phone">📞 ${{customer.phone}}</div>` : ''}}
                        <div style="margin-top: 8px; font-size: 0.8em; color: #888;">
                            Depot: ${{depot}}<br>
                            Coordinates: ${{customer.latitude.toFixed(4)}}, ${{customer.longitude.toFixed(4)}}
                        </div>
                    </div>
                `;
                
                const infoWindow = new google.maps.InfoWindow({{
                    content: infoContent
                }});
                
                marker.addListener('click', () => {{
                    infoWindow.open(map, marker);
                }});
                
                bounds.extend(position);
            }});
            
            if (customers.length > 0) {{
                map.fitBounds(bounds);
            }}
            
            const legend = document.createElement('div');
            legend.style.cssText = `
                background: white;
                padding: 10px;
                margin: 10px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif;
                font-size: 14px;
            `;
            legend.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">Customer Locations (${{customers.length}} total)</div>
                <div><span style="color: #FF6B6B;">●</span> Lake Charles Region</div>
                <div><span style="color: #4ECDC4;">●</span> Lufkin Region</div>
                <div><span style="color: #45B7D1;">●</span> Leesville Region</div>
                <div><span style="color: #96CEB4;">●</span> Other Locations</div>
            `;
            map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(legend);
        }}
    </script>
    
    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
    </script>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    return output_file

async def main():
    """Main function to create Google Maps pins from customer data"""
    
    customer_data_text = """
Adrien's Supermarket	√		1.25			3842 West Congress	Lafayette	337-501-0673  Herb
Henderson 1 Stop		√	1.25			504 HENDERSON HWY	Breaux Bridge	337-434-4019
Cash Saver	√		1.25			1714 Main HWY Street	St. Martinville	337-394-2333
Speedway		√	1.25			1100 North University Avenue	Lafayette	337-412-6916
B & W Evangeline		√	1.25			2013 Evangeline HWY	Jennings	337-824-6313
Hanson Super Foods		√	1.25			401 West Plaquemine Street	Jennings	337-824-6463
Dirty Rice		√	1.25		10.75%	608 East HWY 90	Iowa	337-391-9663/337-582-2333
Kerry A Sac		√	1.25	3.00		103 HWY 90 East	Iowa	337-582-6678
MORE 4 LESS 			1.40			3350 MAPLEWOOD DR.	Sulphur	
BAYOU FOOD MART-NEW			1.40	3.25				
CHEVRON-NEW			1.40	3.25		2211 RYAN ST	Lake Charles	337-240-8143
Piggly Wiggly-Scott	√		1.25	3.00		5525 Cameron Street	Scott	337-232.9877
Savco		√	1.25			620 West Canal Street	Churchpoint	337-684-3127
AJ's		√	1.25			7009 Churchpoint HWY	Rayne	337-334-0288
I-10 Chevron-Rayne	√		1.25			1045 Churchpoint HWY	Rayne	337-334-9684
I-10 Rayne Travel Center	√		1.25			1044 Churchpoint HWY	Rayne	337-334-7233
Nonc Kev Meat Market		√	1.25	3.00		1421 The Blvd	Rayne	337-393-2750
Champagne's-Rayne	√		1.25	3.00		500 South Adams Avenue	Rayne	337-334-3869
Piggly Wiggly-Rayne	√		1.25	3.00		702 South Adams Avenue	Rayne	337-334-4233
We Fair	√		1.25			300 West Branche	Rayne	337-334-4620
Cuccio's		√	1.25			1025 North Avenue G	Crowley	337-783-2140
Crawfish Nest		√	1.25			805 West 2nd Street	Crowley	337-783-9900
Cajun Lunch Box		√	1.25			605 North Adams Street	Welsh	337-734-4661
Starks Truck Stop		√	1.25	3.00		4344 HWY 12	Starks	337-743-5471
Glenn's Mart		√	1.25	3.00		1312 Gum Cove Road	Vinton	337-589-3520
M & K Pantry		√	1.25	3.00		1601 HWY 90 West	Vinton	337-589-3333
PHILLIP CALAIS		1		3.25	10.75%	NORTH SIDE/ROAD SIDE	1	337-377-8817
KENNETH WEEKS		2		3.25	10.75%	LEAVE TICKET ON DESK/CK DEL	2	251-689-6789
KENNETH ROBERTS-2BOXES	3			3.25	10.75%	SOUTH EAST/WEST ROAD SIDE	3	(337-802-9706)
TREY ELLIS	4			3.25	10.75%	WEST END ROAD SIDE	4	251-209-7385
G. MARTINEZ	8			3.25	10.75%	EAST SIDE/ROAD SIDE	8	979-215-0031
ORLANDO OROZCO	9			3.25	10.75%	EAST END/ROAD SIDE	9	979-482-6153
TREVOR SOILEAU	9			3.25	10.75%	WEST SIDE / TRACK SIDE	9	337-459-8490
JOSE ESTRADA	10			3.25	10.75%	NEEDS NEW CUSTOMER FORM	10	601-813-4763
BUDDY DEVILLE	14			3.25	10.75%	CUSTOMER HAS ALL OF BARN	14	225-235-1654
GAYLA BUSTAMONTE	18			3.25	10.75%	NORTH END/ EAST SIDE	18	337-661-1879
L. HERNANDEZ		19		3.25	10.75%	FACING ROAD SIDE	19	469-236-3593
Missies		√	1.25	3.00		106 E. Lincoln Street	Sulphur	337-527-6924
Conoco 5th Wheel		√	1.25	3.00		500 N. BEGLIS PARKWAY	Sulphur	337-274-1532
KINGSPOINT #4		√	1.38	3.03		3610 E. HWY 90 (NAPOLEAN)	Sulphur	337-244-6692
Ponda's		√	1.25			20005 HWY 165	Fenton	337-756-2222
TP's Grocery		√	1.25			1519 HWY 165	Fenton	337-756-2227
Ted's Quick Stop		√	1.25			708 1st Street	Kinder	337-738-4765
Feather's	√		1.25			121 Panther Trail Drive	Kinder	337-738-7150
Kinder Quick Stop		√	1.25			13916 HWY 154	Kinder	337-738-7896
Dollar General-REEVES-11635	√		1.25		10.75%	18208 HWY 190	REEVES	337-419-2065
Chadeaux's		√	1.25			14440 HWY 165	Kinder	337-738-3040
Myer's Landing		√	1.25			169 Myers Landing Road	Lake Arthur	337-774-2338
Dollar General-03480-KINDER	√		1.25		10.75%	14612 HWY 165	Kinder	985-589-7618
The Buzz		√	1.25			1222 3rd Avenue	Kinder	337-292-2007
Kerry A Sac		√	1.25	3.00		103 HWY 90 East	Iowa	337-582-6678
Dirty Rice		√	1.25		10.75%	608 East HWY 90	Iowa	337-391-9663/337-582-2333
Aladdin Construction	√		1.45		10.75%	777 COUSHATTA	Kinder	228-348-1889
Dollar General-Hayes  20369	√		1.25		10.75%	8110 Jone Primeaux Road	Hayes	337-347-6708
Cajun Grocery		√	1.25	3.00		7744 East HWY 14	Hayes	337-662-3348
ELTON EXPRESS		√	1.25			1807 HWY 190	Elton	337-584-2032
S & W		√	1.25			3955 HWY 190	Elton	337-584-3663
Kerry A Sac		√	1.25	3.00		103 HWY 90 East	Iowa	337-582-6678
Dirty Rice		√	1.25		10.75%	608 East HWY 90	Iowa	337-391-9663/337-582-2333
Smoker's Express		√	1.25			3501 Gerstner Memorial Drive	Lake Charles	337-474-6585
JONES GROCERY		√	1.25	3.00		1843 Gerstner Memorial Drive	Lake Charles	337-436-2810
GX Louisiana **HOP-IN		√	1.25			1717 Gerstner Memorial Dr.	Lake Charles	337-494-5902
Crying Eagle Brewing Co.		√		3.00		1165 E. McNeese st	Lake Charles	337-564-9210
JF Peto	√		1.25		10.75%	1848 1st Street	Lake Charles	337-433-5272
HD Trucking	√		1.25		10.75%	5501 Oplelousas Street	Lake Charles	337-439-9710
System Service Broadband	√		1.40		10.75%	201 Fred Road	Lake Charles	337-278-3058
WHC-ENERGY	√		1.45		10.75%	8120 INTERCOASTAL PKWY	Hackberry	337-773-7073-SANDY
Dollar General-Hackberry 	√	2WK	1.25			805 Main Street	Hackberry	337-443-0910
Sasol-Ethylene	√		1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
SASOL-ALCOHOL	√		1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-Lab	√		1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-South Shop	√		1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-ERT	√		1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Johnson Bayou Convience	W/C	√	1.25	3.00		6328 Gulf Beach HWY	Lake Charles	337-569-2128
More 4 Less # 10		√	1.25	3.00		4119 Louisiana Avenue	Lake Charles	337-562-2191
Time Loop 13		√	1.25			428 7th Street	Lake Charles	409-221-2169
Sunshine Liquor- (HWY 14)		√	1.25			3031 GERSHNER MEMORIAL DR.	Lake Charles	337-462-3666
Sunshine Liquor (BROAD)		√	1.25			1824 Broad Street	Lake Charles	337-491-0507
Delta Food 5			1.25	3.00		112 US HWY 171	Lake Charles	337-855-8766
Sasol-Ethylene			1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
SASOL-ALCOHOL			1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-Lab			1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-South Shop			1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
Sasol-ERT			1.40			2201 Old Spanish Trail	Westlake	337-244-5911/SHAWN
TJ's						1115 Sam Houston Jones PKWay	Lake Charles	337-855-4615
Delta Food 7			1.25			923 Park Road	Lake Charles	337-499-7215
Neighborhood Quick Mart			1.25			1414 North Prater Road	Lake Charles	337-400-5443
STOP N SAVE		√	1.40	3.25		3215 HIGHWAY 90	Westlake	318-554-9337
GILLIS FOOD		√	1.40	3.25	W/C			
BRONCO DISCOUNT		√	1.38	3.03	W/C	393 N. HWY 171	Lake Charles	337-526-7082
Mike Hooks			1.25			409 Mike Hooks Road	Westlake	337-855-8766
"""
    
    print("Parsing customer data...")
    customers = parse_customer_data(customer_data_text)
    print(f"Found {len(customers)} customers with addresses")
    
    maps_service = GoogleMapsService()
    
    print("Geocoding addresses...")
    customers_with_coords = []
    
    for i, customer in enumerate(customers):
        print(f"Processing {i+1}/{len(customers)}: {customer['name']}")
        
        full_address = customer['address']
        if not any(state in full_address.upper() for state in ['LA', 'TX', 'LOUISIANA', 'TEXAS']):
            full_address += ", LA"
        
        try:
            lat, lng = await maps_service.geocode_address(full_address)
            customers_with_coords.append({
                'name': customer['name'],
                'address': customer['address'],
                'phone': customer['phone'],
                'latitude': lat,
                'longitude': lng
            })
            print(f"  -> Coordinates: ({lat}, {lng})")
        except Exception as e:
            print(f"  -> Error geocoding: {e}")
            if 'Lake Charles' in full_address:
                lat, lng = 30.2266, -93.2174
            elif 'Lafayette' in full_address:
                lat, lng = 30.2241, -92.0198
            elif 'Sulphur' in full_address:
                lat, lng = 30.2366, -93.3774
            else:
                lat, lng = 30.5, -93.0
            
            customers_with_coords.append({
                'name': customer['name'],
                'address': customer['address'],
                'phone': customer['phone'],
                'latitude': lat,
                'longitude': lng
            })
            print(f"  -> Using fallback coordinates: ({lat}, {lng})")
    
    print(f"\nCreating interactive map with {len(customers_with_coords)} customer pins...")
    html_file = create_google_maps_html(customers_with_coords)
    
    print(f"✅ Google Maps HTML file created: {html_file}")
    print(f"📍 Total customer pins: {len(customers_with_coords)}")
    
    df = pd.DataFrame(customers_with_coords)
    csv_file = "customer_locations_with_coordinates.csv"
    df.to_csv(csv_file, index=False)
    print(f"📊 CSV file with coordinates created: {csv_file}")
    
    return html_file, csv_file

if __name__ == "__main__":
    asyncio.run(main())
