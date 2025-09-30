#!/usr/bin/env python3

import json
import sqlite3
from datetime import datetime, timedelta

def get_month_start():
    """Get the start of the current month"""
    now = datetime.now()
    return datetime(now.year, now.month, 1)

def resolve_book_value(value):
    """Resolve a representative numeric book value from potentially nested data."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value) if value != 0 else None

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        
        import re
        match = re.search(r'-?\d[\d,]*(?:\.\d+)?', cleaned)
        if not match:
            return None

        try:
            return float(match.group(0).replace(',', ''))
        except ValueError:
            return None

    if isinstance(value, dict):
        priority_keys = [
            'total', 'Total', 'overall', 'Overall', 'aggregate', 'Aggregate',
            'value', 'Value', 'amount', 'Amount', 'current', 'Current',
            'after', 'After', 'before', 'Before', 'retail', 'Retail',
            'clean_retail', 'cleanRetail', 'Clean Retail', 'cleanRetailValue',
            'clean_trade', 'cleanTrade', 'Clean Trade-In', 'wholesale', 'Wholesale'
        ]

        for key in priority_keys:
            if key in value:
                resolved = resolve_book_value(value[key])
                if resolved is not None:
                    return resolved

        for key, sub_value in value.items():
            if isinstance(key, str) and 'difference' in key.lower():
                continue
            resolved = resolve_book_value(sub_value)
            if resolved is not None:
                return resolved

        return None

    return None

def main():
    # Connect to database
    conn = sqlite3.connect('vehicle_processing.db')
    cursor = conn.cursor()
    
    # Get month start
    month_start = get_month_start()
    
    # Query ALL vehicles with book values (remove date filter to see all data)
    query = """
    SELECT stock_number, vehicle_name,
           book_values_before_processing, book_values_after_processing
    FROM vehicle_processing_records
    WHERE book_values_processed = 1
    AND (book_values_before_processing IS NOT NULL OR book_values_after_processing IS NOT NULL)
    ORDER BY processing_date DESC
    LIMIT 50
    """

    cursor.execute(query)
    vehicles = cursor.fetchall()

    print(f"Found {len(vehicles)} vehicles with book values (all time)")
    print("=" * 80)

    problematic_vehicles = []

    for vehicle in vehicles:
        stock_number, vehicle_name, before_raw, after_raw = vehicle
        
        try:
            before_data = json.loads(before_raw) if before_raw else {}
            after_data = json.loads(after_raw) if after_raw else {}
            
            print(f"\nVehicle: {vehicle_name or 'Unknown'} (Stock: {stock_number})")
            print("-" * 50)
            
            # Check each category
            all_categories = set()
            all_categories.update(before_data.keys())
            all_categories.update(after_data.keys())
            
            for category in sorted(all_categories):
                if not category:
                    continue
                    
                before_raw_val = before_data.get(category)
                after_raw_val = after_data.get(category)
                
                before_val = resolve_book_value(before_raw_val)
                after_val = resolve_book_value(after_raw_val)
                
                print(f"  {category}:")
                print(f"    Before: {before_raw_val} -> {before_val}")
                print(f"    After:  {after_raw_val} -> {after_val}")
                
                # Check for problematic cases
                if before_val == 0.0 and after_val and after_val > 0:
                    print(f"    ⚠️  PROBLEMATIC: $0 -> ${after_val:,.0f} (initial merchandising)")
                    problematic_vehicles.append({
                        'vehicle': vehicle_name or 'Unknown',
                        'stock_number': stock_number,
                        'category': category,
                        'before': before_val,
                        'after': after_val,
                        'change': after_val - (before_val or 0)
                    })
                elif before_val is None and after_val and after_val > 0:
                    print(f"    ⚠️  PROBLEMATIC: None -> ${after_val:,.0f} (initial merchandising)")
                    problematic_vehicles.append({
                        'vehicle': vehicle_name or 'Unknown',
                        'stock_number': stock_number,
                        'category': category,
                        'before': before_val,
                        'after': after_val,
                        'change': after_val
                    })
                elif before_val and after_val and before_val > 0 and after_val > 0:
                    change = after_val - before_val
                    print(f"    ✅ LEGITIMATE: ${before_val:,.0f} -> ${after_val:,.0f} (${change:+,.0f})")
                    
        except Exception as e:
            print(f"Error processing vehicle {stock_number}: {e}")
    
    print("\n" + "=" * 80)
    print("PROBLEMATIC VEHICLES (should be filtered out):")
    print("=" * 80)
    
    for pv in problematic_vehicles:
        print(f"{pv['vehicle']} ({pv['stock_number']}) - {pv['category']}: ${pv['change']:+,.0f}")

    # Also look for vehicles with very large changes (>$50k) that might be problematic
    print("\n" + "=" * 80)
    print("VEHICLES WITH LARGE CHANGES (>$50,000):")
    print("=" * 80)

    cursor.execute("""
    SELECT stock_number, vehicle_name,
           book_values_before_processing, book_values_after_processing
    FROM vehicle_processing_records
    WHERE book_values_processed = 1
    AND book_values_before_processing IS NOT NULL
    AND book_values_after_processing IS NOT NULL
    ORDER BY processing_date DESC
    LIMIT 100
    """)

    all_vehicles = cursor.fetchall()
    large_changes = []

    for vehicle in all_vehicles:
        stock_number, vehicle_name, before_raw, after_raw = vehicle

        try:
            before_data = json.loads(before_raw) if before_raw else {}
            after_data = json.loads(after_raw) if after_raw else {}

            all_categories = set()
            all_categories.update(before_data.keys())
            all_categories.update(after_data.keys())

            for category in all_categories:
                if not category:
                    continue

                before_val = resolve_book_value(before_data.get(category))
                after_val = resolve_book_value(after_data.get(category))

                if before_val and after_val:
                    change = abs(after_val - before_val)
                    if change > 50000:  # Changes over $50k
                        large_changes.append({
                            'vehicle': vehicle_name or 'Unknown',
                            'stock_number': stock_number,
                            'category': category,
                            'before': before_val,
                            'after': after_val,
                            'change': after_val - before_val
                        })
                elif (before_val is None or before_val == 0) and after_val and after_val > 50000:
                    large_changes.append({
                        'vehicle': vehicle_name or 'Unknown',
                        'stock_number': stock_number,
                        'category': category,
                        'before': before_val,
                        'after': after_val,
                        'change': after_val,
                        'type': 'INITIAL_MERCHANDISING'
                    })

        except Exception as e:
            continue

    for lc in large_changes:
        change_type = lc.get('type', 'LARGE_CHANGE')
        print(f"{lc['vehicle']} ({lc['stock_number']}) - {lc['category']}: ${lc['change']:+,.0f} [{change_type}]")

    conn.close()

if __name__ == "__main__":
    main()
