# 🚀 Quick Start Guide

Get your Election Analysis Dashboard running in 5 minutes!

## Option 1: Automated Setup (Recommended)

### Step 1: Run Setup Script
```bash
python setup.py
```

The setup script will:
- ✅ Check Python version compatibility
- 📦 Install all required packages
- 📊 Validate your data file
- 🚀 Launch the application

### Step 2: Access Dashboard
- Open your browser to `http://localhost:8501`
- Start analyzing your election data!

## Option 2: Manual Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Prepare Data
- Place your election CSV file as `election.csv`
- Ensure it has the required columns (see [Data Format](README.md#data-format))

### Step 3: Run Application
```bash
streamlit run app.py
```

## 📊 Sample Data

If you don't have election data yet, the setup script can create sample data for testing:

```bash
python setup.py
# Choose 'y' when asked to create sample data
# Rename 'election_sample.csv' to 'election.csv'
```

## 🔧 Troubleshooting

### Common Issues:
- **Module not found**: Run `pip install -r requirements.txt`
- **Data file error**: Check CSV format and column names
- **Port already in use**: Use `streamlit run app.py --server.port 8502`

### Need Help?
- Check the [full README](README.md)
- Review [troubleshooting section](README.md#troubleshooting)
- See [analysis guide](ANALYSIS_AND_IMPROVEMENTS.md)

## 🎯 What's Next?

Once running, explore these features:
1. **Prabhag Dashboard** - Ward-level analysis
2. **Margin Comparison** - Victory margins
3. **City Insights** - Overall performance
4. **Export Center** - Generate PDF reports

Happy analyzing! 🗳️