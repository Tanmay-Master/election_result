#!/usr/bin/env python3
"""
Election Result Analysis Dashboard - Setup Script
Automated setup and validation for the election analysis system
"""

import subprocess
import sys
import os
import pandas as pd
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ All packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        return False

def check_data_file():
    """Check if election data file exists and is valid"""
    print("\n📊 Checking data file...")
    
    if not os.path.exists("election.csv"):
        print("❌ Error: election.csv not found")
        print("Please ensure your election data file is named 'election.csv' and placed in the project directory")
        return False
    
    try:
        df = pd.read_csv("election.csv")
        required_columns = ['Name', 'Prabhag', 'Party', 'Election_type', 'Round', 'Votes']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"❌ Error: Missing required columns: {missing_columns}")
            return False
        
        print(f"✅ Data file valid: {len(df)} records found")
        print(f"   - Prabhags: {df['Prabhag'].nunique()}")
        print(f"   - Candidates: {df['Name'].nunique()}")
        print(f"   - Parties: {df['Party'].nunique()}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading data file: {e}")
        return False

def create_sample_data():
    """Create sample data file if none exists"""
    print("\n📝 Creating sample data file...")
    
    sample_data = {
        'Name': ['Candidate A', 'Candidate B', 'Candidate A', 'Candidate B'] * 3,
        'Prabhag': ['prabhag 1'] * 4 + ['prabhag 2'] * 4 + ['prabhag 3'] * 4,
        'SeatDesignation': [''] * 12,
        'Party': ['BJP', 'SS-UBT', 'BJP', 'SS-UBT'] * 3,
        'Election_type': ['Nagaradhyaksha'] * 8 + ['Nagarsevak'] * 4,
        'Round': [1, 1, 2, 2] * 3,
        'Votes': [45, 38, 42, 35, 52, 41, 48, 39, 67, 58, 0, 0]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv("election_sample.csv", index=False)
    print("✅ Sample data created as 'election_sample.csv'")
    print("   Rename it to 'election.csv' to use as your data source")

def run_application():
    """Launch the Streamlit application"""
    print("\n🚀 Starting the Election Analysis Dashboard...")
    print("The application will open in your default web browser")
    print("Press Ctrl+C to stop the application")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

def main():
    """Main setup function"""
    print("🗳️  Election Result Analysis Dashboard - Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install requirements
    if not install_requirements():
        return
    
    # Check data file
    data_exists = check_data_file()
    
    if not data_exists:
        create_sample = input("\n❓ Would you like to create sample data? (y/n): ").lower().strip()
        if create_sample in ['y', 'yes']:
            create_sample_data()
    
    # Ask to run application
    run_app = input("\n❓ Would you like to start the application now? (y/n): ").lower().strip()
    if run_app in ['y', 'yes']:
        run_application()
    else:
        print("\n✅ Setup complete!")
        print("To start the application later, run: streamlit run app.py")

if __name__ == "__main__":
    main()