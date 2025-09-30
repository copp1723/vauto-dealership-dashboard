#!/usr/bin/env python3

import json
import sqlite3
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_month_start, get_year_start

def main():
    print("Testing statistics calculation directly...")
    
    # Connect to database
    conn = sqlite3.connect('vehicle_processing.db')
    
    try:
        # Call the statistics function directly (without authentication)
        # We'll simulate the database session and user context
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Create engine and session
        engine = create_engine('sqlite:///vehicle_processing.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get month and year start dates
        month_start = get_month_start()
        year_start = get_year_start()
        
        print(f"Month start: {month_start}")
        print(f"Year start: {year_start}")
        
        # Query vehicles directly
        from app import VehicleProcessingRecord
        
        # Get vehicles with book values for MTD
        mtd_vehicles = session.query(VehicleProcessingRecord).filter(
            VehicleProcessingRecord.processing_date >= month_start,
            VehicleProcessingRecord.book_values_processed == True,
            VehicleProcessingRecord.book_values_before_processing.isnot(None),
            VehicleProcessingRecord.book_values_after_processing.isnot(None)
        ).all()
        
        print(f"Found {len(mtd_vehicles)} MTD vehicles with book values")
        
        # Calculate insights manually
        from app import calculate_book_value_insights, calculate_book_value_difference
        
        total_book_value_mtd = 0.0
        mtd_insights = {
            'categories': {},
            'total_difference': 0.0,
            'best_improvement': {
                'category': '',
                'amount': 0.0,
                'vehicle_name': None,
                'stock_number': None,
                'before_value': None,
                'after_value': None,
                'before_detail': None,
                'after_detail': None
            },
            'primary_source': 'KBB',
            'summary': 'No MTD data available'
        }
        
        def ensure_category_entry(container, category):
            if category not in container:
                container[category] = {
                    'before': 0.0,
                    'after': 0.0,
                    'difference': 0.0,
                    'improvement': False,
                    'top_vehicle': None
                }
            return container[category]
        
        def update_top_vehicle_reference(category_entry, before_value, after_value, diff_value, vehicle, before_detail, after_detail):
            vehicle_data = {
                'vehicle_name': vehicle.vehicle_name,
                'stock_number': vehicle.stock_number,
                'before_value': before_value,
                'after_value': after_value,
                'difference': diff_value,
                'before_detail': before_detail,
                'after_detail': after_detail
            }
            
            if diff_value > 0:
                if 'top_positive' not in category_entry or diff_value > category_entry['top_positive']['difference']:
                    category_entry['top_positive'] = vehicle_data
            elif diff_value < 0:
                if 'top_negative' not in category_entry or diff_value < category_entry['top_negative']['difference']:
                    category_entry['top_negative'] = vehicle_data
        
        for vehicle in mtd_vehicles:
            try:
                before_data = json.loads(vehicle.book_values_before_processing) if vehicle.book_values_before_processing else {}
                after_data = json.loads(vehicle.book_values_after_processing) if vehicle.book_values_after_processing else {}
                
                print(f"\nProcessing vehicle: {vehicle.vehicle_name} ({vehicle.stock_number})")
                print(f"Before data: {before_data}")
                print(f"After data: {after_data}")
                
                # Calculate vehicle insights
                vehicle_insights = calculate_book_value_insights(before_data, after_data)
                difference = calculate_book_value_difference(before_data, after_data)
                total_book_value_mtd += difference
                
                print(f"Vehicle insights: {vehicle_insights}")
                print(f"Difference: {difference}")
                
                # Aggregate insights
                for category, data in vehicle_insights['categories'].items():
                    has_before = data.get('before') is not None
                    has_after = data.get('after') is not None
                    before_value = data.get('before_numeric', 0.0)
                    after_value = data.get('after_numeric', 0.0)

                    print(f"  Category {category}: before={before_value}, after={after_value}, has_before={has_before}, has_after={has_after}")

                    # Only include legitimate changes (both values exist and are non-zero)
                    # This excludes initial merchandising (0 -> value) which isn't automation impact
                    if not (has_before and has_after) or before_value == 0.0 or after_value == 0.0:
                        print(f"    FILTERED OUT: not legitimate change")
                        continue

                    diff_value = after_value - before_value
                    category_entry = ensure_category_entry(mtd_insights['categories'], category)
                    category_entry['before'] += before_value
                    category_entry['after'] += after_value
                    category_entry['difference'] += diff_value
                    category_entry['improvement'] = category_entry['difference'] > 0
                    update_top_vehicle_reference(
                        category_entry,
                        before_value,
                        after_value,
                        diff_value,
                        vehicle,
                        data.get('before_detail'),
                        data.get('after_detail')
                    )
                    
                    print(f"    INCLUDED: diff={diff_value}, category_total={category_entry['difference']}")
                    
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error processing vehicle {vehicle.stock_number}: {e}")
                continue
        
        print(f"\nFinal MTD insights:")
        print(f"Total book value MTD: {total_book_value_mtd}")
        print(f"Categories: {json.dumps(mtd_insights['categories'], indent=2)}")
        
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
