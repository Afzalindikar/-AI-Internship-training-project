"""
data/input/create_sample_xlsx.py
---------------------------------
Creates a sample Excel file for testing the CSVExtractor.
Run once: python data/input/create_sample_xlsx.py
"""

import sys
from pathlib import Path

try:
    import pandas as pd
    import openpyxl
except ImportError:
    print("Install pandas and openpyxl: pip install pandas openpyxl")
    sys.exit(1)

OUTPUT = Path(__file__).parent / "sample.xlsx"

data = {
    "Customer Name": [
        "Liam Anderson", "Sophia Robinson", "Noah Williams",
        "Emma Davis", "Oliver Martinez", "Ava Thompson",
        "William Jackson", "Isabella White", "James Harris", "Mia Clark",
    ],
    "E-Mail": [
        "liam@mail.com", "sophia@mail.com", "noah@mail.com",
        "emma@mail.com", "oliver@mail.com", "ava@mail.com",
        "will@mail.com", "isabella@mail.com", "james@mail.com", "mia@mail.com",
    ],
    "Mobile": [
        "+1-555-2001", "+1-555-2002", "+1-555-2003", "+1-555-2004",
        "+1-555-2005", "+1-555-2006", "+1-555-2007", "+1-555-2008",
        "+1-555-2009", "+1-555-2010",
    ],
    "Organisation": [
        "AlphaTech", "BetaSoft", "GammaData", "DeltaCloud",
        "EpsilonAI", "ZetaLabs", "EtaGroup", "ThetaWorks",
        "IotaNet", "KappaBase",
    ],
    "Designation": [
        "Developer", "Analyst", "Engineer", "Manager",
        "Designer", "Architect", "Lead", "Consultant",
        "Director", "Intern",
    ],
    "Annual Income": [
        95000, 72000, 88000, 110000,
        65000, 120000, 105000, 93000,
        150000, 42000,
    ],
    "Country": [
        "USA", "UK", "Canada", "Australia",
        "Germany", "France", "India", "Brazil",
        "Japan", "Mexico",
    ],
}

df = pd.DataFrame(data)
df.to_excel(OUTPUT, index=False, engine="openpyxl")
print(f"✅ Sample Excel created: {OUTPUT}")
