ENVIRONMENTAL_QUESTIONS = [
    # Waste Management
    {"question": "Asbestos Waste", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs"]},
    {"question": "Hazardous Waste (HW) of last month /sent/Accumulated", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs"]},
    {"question": "Unused well ashestos of last month /sent/Accumulated", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs"]},
    {"question": "Non-Hazardous Waste (Disposed/Sent)", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs", "cubic-m"]},
    {"question": "Non-Hazardous Waste (Recycled)", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs", "cubic-m"]},
    {"question": "Aluminium (Scrap)sent waste consumed", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs"]},
    {"question": "Hazardous Waste sent (HDPE, PP, MS Barrels, L.boards, Polythenes)", "default_unit": "MT", "unit_options": ["MT", "kg", "lbs", "Count"]},
    
    # Safety Metrics
    {"question": "Fatalities", "default_unit": "Count", "unit_options": ["Count", "Rate", "Percentage"]},
    {"question": "Lost Time Injuries (LTI)", "default_unit": "Count", "unit_options": ["Count", "Rate"]},
    {"question": "Medical Treatment Injury (MTI)", "default_unit": "Count", "unit_options": ["Count", "Rate"]},
    {"question": "First Aid Cases", "default_unit": "Count", "unit_options": ["Count", "Rate"]},
    {"question": "Near miss incidents (MTI1)", "default_unit": "Count", "unit_options": ["Count", "Rate"]},
    {"question": "No. of Man days Lost", "default_unit": "Days", "unit_options": ["Days", "Hours"]},
    {"question": "Fire Incidents", "default_unit": "Count", "unit_options": ["Count"]},
    
    # Compliance & Training
    {"question": "Statutory Compliance (Water, Wastewater)", "default_unit": "Yes/No", "unit_options": ["Yes/No", "Percentage"]},
    {"question": "Asbestos spillage/Leam Bags; Incedents from Legged", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Employees who attended", "default_unit": "Count", "unit_options": ["Count", "Percentage"]},
    
    # Air Quality
    {"question": "Dust by quality for workplaces and Total dust (monthly)", "default_unit": "mg/m³", "unit_options": ["mg/m³", "µg/m³"]},
    {"question": "Stack Emission/Leakage-chimney", "default_unit": "mg/m³", "unit_options": ["mg/m³", "µg/m³"]},
    {"question": "SPM Near/compliance", "default_unit": "mg/m³", "unit_options": ["mg/m³", "µg/m³"]},
    {"question": "Leakage of chimney (%)as seen on site /checked", "default_unit": "%", "unit_options": ["%", "PPM"]},
    
    # Water & Effluent
    {"question": "Total recycled & Rainwater Harvested", "default_unit": "KL", "unit_options": ["KL", "m³", "Liters"]},
    {"question": "Number of monitoring (contracting)", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Quantity of Water utilized by Contract Offices", "default_unit": "KL", "unit_options": ["KL", "m³", "Liters"]},
    {"question": "Monthly Volume of effluent", "default_unit": "KL", "unit_options": ["KL", "m³", "Liters"]},
    {"question": "Inputs received for soaring at", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Norms compliance as per", "default_unit": "Yes/No", "unit_options": ["Yes/No", "Percentage"]},
    {"question": "BOD", "default_unit": "mg/L", "unit_options": ["mg/L", "ppm"]},
    {"question": "Observations (MPCB) Close", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Complaints from people nearby reported", "default_unit": "Count", "unit_options": ["Count"]},
    
    # Energy & Resources
    {"question": "Electricity Consumption", "default_unit": "kWh", "unit_options": ["kWh", "MWh", "GJ"]},
    {"question": "Safety Inspections with Feedback/Daily Team", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Number of trainings/Awareness organized", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "No. of Participants in training programme", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Liters (>132 Rating) Points identified", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "BRSR data for the last month", "default_unit": "Yes/No", "unit_options": ["Yes/No"]},
    
    # Additional
    {"question": "No. of ETP", "default_unit": "Count", "unit_options": ["Count"]},
    {"question": "Asbestos work(through paints) reported", "default_unit": "Count", "unit_options": ["Count"]},
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Unit display names
UNIT_DISPLAY_NAMES = {
    "MT": "Metric Tons",
    "kg": "Kilograms",
    "lbs": "Pounds",
    "cubic-m": "Cubic Meters",
    "Count": "Count",
    "Rate": "Per 1000 employees",
    "Percentage": "Percentage",
    "Days": "Days",
    "Hours": "Hours",
    "Yes/No": "Yes/No",
    "mg/m³": "mg/m³",
    "µg/m³": "µg/m³",
    "%": "Percentage",
    "PPM": "Parts Per Million",
    "KL": "Kiloliters",
    "m³": "Cubic Meters",
    "Liters": "Liters",
    "mg/L": "mg/L",
    "ppm": "Parts Per Million",
    "kWh": "Kilowatt-hours",
    "MWh": "Megawatt-hours",
    "GJ": "Gigajoules",
}