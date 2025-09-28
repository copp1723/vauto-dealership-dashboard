#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path so we can import from database.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from database import get_database_manager
        
        # Initialize database manager
        db_manager = get_database_manager()
        
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            # Search for Corvette vehicles
            corvette_vehicles = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.vehicle_name.ilike('%corvette%')
            ).all()
            
            print(f"Found {len(corvette_vehicles)} Corvette vehicles:")
            print("=" * 80)
            
            for vehicle in corvette_vehicles:
                print(f"Stock #: {vehicle.stock_number}")
                print(f"Vehicle: {vehicle.vehicle_name}")
                print(f"VIN: {vehicle.vin}")
                print(f"Processing Date: {vehicle.processing_date}")
                print("-" * 40)
                
                # Check specifically for 2024 Corvette Stingray 3LT
                if (vehicle.vehicle_name and 
                    '2024' in vehicle.vehicle_name and 
                    'corvette' in vehicle.vehicle_name.lower() and 
                    'stingray' in vehicle.vehicle_name.lower() and 
                    '3lt' in vehicle.vehicle_name.lower()):
                    print("🎯 FOUND: 2024 Chevrolet Corvette Stingray 3LT")
                    print(f"   Stock Number: {vehicle.stock_number}")
                    print(f"   Full Name: {vehicle.vehicle_name}")
                    print(f"   VIN: {vehicle.vin}")
                    print("=" * 80)
            
            # Also search for any 2024 Chevrolet vehicles
            print("\nSearching for 2024 Chevrolet vehicles...")
            chevrolet_2024 = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.vehicle_name.ilike('%2024%chevrolet%')
            ).limit(20).all()
            
            print(f"Found {len(chevrolet_2024)} 2024 Chevrolet vehicles (showing first 20):")
            for vehicle in chevrolet_2024:
                if 'corvette' in vehicle.vehicle_name.lower():
                    print(f"🏎️  Stock #: {vehicle.stock_number} - {vehicle.vehicle_name}")
                else:
                    print(f"   Stock #: {vehicle.stock_number} - {vehicle.vehicle_name}")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
