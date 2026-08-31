import os
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

# Make sure directories exist
demo_dir = Path("data/demo")
demo_dir.mkdir(parents=True, exist_ok=True)

# 1. Create Finance CSV
finance_data = {
    "Date": ["2023-01-15", "2023-01-22", "2023-02-10", "2023-03-05", "2023-03-12", "2023-04-01", "2023-04-18"],
    "Department": ["Engineering", "Operations", "Engineering", "Marketing", "HR", "Operations", "Engineering"],
    "Category": ["Software", "Maintenance", "Hardware", "Advertising", "Training", "Logistics", "Consulting"],
    "Vendor": ["TechCorp", "FixIt Services", "HardwareCo", "AdAgency", "LearnFast", "ShipIt", "Expertise LLC"],
    "Amount": [12500, 4300, 28000, 15000, 3200, 8900, 45000]
}
df = pd.DataFrame(finance_data)
df.to_csv(demo_dir / "demo_finance.csv", index=False)
print("Created demo_finance.csv")

# 2. Create a basic PDF using matplotlib
fig, ax = plt.subplots(figsize=(8.5, 11))
ax.axis('off')
text = """
INDUSTRIAL INSPECTION REPORT
--------------------------------

Date: 2023-05-12
Location: Plant Sector B
Inspector: John Doe

Summary of Findings:
- Valve V-104 is showing signs of corrosion and needs replacement within 3 months.
- Pump P-201 operating within normal pressure limits.
- No major safety non-compliances were found.

Action Items:
1. Schedule replacement for V-104.
2. Routine maintenance for P-201 next quarter.
"""
ax.text(0.1, 0.9, text, fontsize=12, va='top', family='monospace')
plt.savefig(demo_dir / "demo_inspection_report.pdf", format='pdf', bbox_inches='tight')
plt.close()
print("Created demo_inspection_report.pdf")

# 3. Create a mock P&ID Image
img = Image.new('RGB', (800, 600), color=(255, 255, 255))
d = ImageDraw.Draw(img)

# Draw some lines and shapes to mimic a P&ID
d.line([(100, 300), (300, 300)], fill=(0,0,0), width=3)
d.ellipse([(300, 250), (400, 350)], outline=(0,0,0), width=3)
d.text((330, 290), "P-201", fill=(0,0,0)) # Mock label

d.line([(400, 300), (700, 300)], fill=(0,0,0), width=3)
d.rectangle([(500, 280), (520, 320)], outline=(0,0,0), width=3)
d.text((490, 260), "V-104", fill=(0,0,0)) # Mock label

img.save(demo_dir / "demo_pid.png")
print("Created demo_pid.png")

print("All demo data created successfully.")
