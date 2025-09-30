#!/usr/bin/env python3
"""
Script to add test data to the vehicle processing database for testing the dashboard
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

def create_test_data():
    # Connect to database
    db_path = 'vehicle_processing.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table first
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'USER',
            store_id VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Add a test superadmin user (password: "admin123")
    # This is the bcrypt hash for "admin123"
    hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5u"

    cursor.execute('''
        INSERT OR IGNORE INTO users (username, hashed_password, role)
        VALUES (?, ?, ?)
    ''', ('superadmin', hashed_password, 'SUPER_ADMIN'))

    # Create the table if it doesn't exist (using the schema from database.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicle_processing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_number VARCHAR(50) NOT NULL,
            vin VARCHAR(17),
            vehicle_name VARCHAR(200),
            environment_id VARCHAR(100),
            processing_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            processing_session_id VARCHAR(100),
            odometer VARCHAR(20),
            days_in_inventory VARCHAR(10),
            original_description TEXT,
            ai_generated_description TEXT,
            final_description TEXT,
            description_updated BOOLEAN DEFAULT 0,
            starred_features TEXT,
            marked_features_count INTEGER DEFAULT 0,
            feature_decisions TEXT,
            no_fear_certificate BOOLEAN DEFAULT 0,
            no_fear_certificate_text TEXT,
            processing_successful BOOLEAN DEFAULT 1,
            processing_duration VARCHAR(50),
            errors_encountered TEXT,
            ai_analysis_result TEXT,
            screenshot_path VARCHAR(500),
            no_build_data_found BOOLEAN DEFAULT 0,
            book_values_processed BOOLEAN DEFAULT 0,
            book_values_before_processing TEXT,
            book_values_after_processing TEXT,
            media_tab_processed BOOLEAN DEFAULT 0,
            media_totals_found TEXT
        )
    ''')
    
    # Sample book values data
    book_values_before = {
        'MMR': 15500,
        'J.D. Power': 16200,
        'KBB.com': 15800,
        'Black Book': 15300,
        'Auction': 14900,
        'KBB': 15750
    }
    
    book_values_after = {
        'MMR': 16800,
        'J.D. Power': 16200,
        'KBB.com': 16100,
        'Black Book': 16500,
        'Auction': 14900,
        'KBB': 16050
    }
    
    # Sample vehicles data
    test_vehicles = [
        {
            'stock_number': '29P1744A',
            'vin': '2C3CDYAG3EH164555',
            'vehicle_name': '2014 Dodge Challenger Rallye Redline',
            'processing_date': datetime.now() - timedelta(hours=2),
            'odometer': '45,230',
            'days_in_inventory': '12',
            'final_description': 'Premium navigation and audio system with satellite radio, Bluetooth, and hard drive storage. Power sunroof/moonroof with tinted glass. Heated front seats with leather upholstery.',
            'marked_features_count': 11,
            'processing_successful': True,
            'book_values_before_processing': json.dumps(book_values_before),
            'book_values_after_processing': json.dumps(book_values_after),
            'book_values_processed': True
        },
        {
            'stock_number': 'T12345B',
            'vin': '1HGBH41JXMN109186',
            'vehicle_name': '2021 Honda Accord Sport',
            'processing_date': datetime.now() - timedelta(hours=5),
            'odometer': '28,450',
            'days_in_inventory': '8',
            'final_description': 'Sport package with upgraded wheels and suspension. Honda Sensing safety suite included.',
            'marked_features_count': 8,
            'processing_successful': True,
            'book_values_before_processing': json.dumps({
                'MMR': 22500,
                'KBB': 23200,
                'Black Book': 22800
            }),
            'book_values_after_processing': json.dumps({
                'MMR': 23800,
                'KBB': 24100,
                'Black Book': 23500
            }),
            'book_values_processed': True
        }
    ]
    
    # Insert test data
    for vehicle in test_vehicles:
        cursor.execute('''
            INSERT INTO vehicle_processing_records (
                stock_number, vin, vehicle_name, processing_date, odometer, days_in_inventory,
                final_description, marked_features_count, processing_successful,
                book_values_before_processing, book_values_after_processing, book_values_processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vehicle['stock_number'],
            vehicle['vin'],
            vehicle['vehicle_name'],
            vehicle['processing_date'],
            vehicle['odometer'],
            vehicle['days_in_inventory'],
            vehicle['final_description'],
            vehicle['marked_features_count'],
            vehicle['processing_successful'],
            vehicle['book_values_before_processing'],
            vehicle['book_values_after_processing'],
            vehicle['book_values_processed']
        ))
    
    conn.commit()
    conn.close()

    print(f"✅ Added {len(test_vehicles)} test vehicles to the database")
    print("✅ Added superadmin user (username: superadmin, password: admin123)")
    print("Test vehicles:")
    for vehicle in test_vehicles:
        print(f"  - {vehicle['stock_number']}: {vehicle['vehicle_name']}")

if __name__ == '__main__':
    create_test_data()
