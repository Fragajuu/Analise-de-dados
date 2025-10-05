- Fire Guardian -
Monitor nearby fires using real-time NASA satellite data.

- Features
Supports multiple satellites: MODIS and VIIRS.
Filters fires by distance, intensity, and confidence.
Calculates distance from a reference point.
Classifies fire risk: Low, Medium, High.
Displays results in a formatted table in the terminal.

- Requirements
Python 3.8+
Libraries: requests, pandas, numpy

- Installation
git clone <repository>
cd <repository>
pip install -r requirements.txt

requirements.txt should include:
- requests
- pandas
- numpy

- Usage
  python main.py

- Example
Enter latitude: -23.55
Enter longitude: -46.63
Enter radius in km: 200
Enter number of days to check: 7

- The script outputs a table with:
Satellite
Latitude & Longitude
Date & Time
Fire intensity
Confidence
Fire risk
Distance from reference point

- Notes
Only fires with confidence ≥ 40% are considered reliable.
Intensity is classified as Low, Moderate, or High based on FRP (Fire Radiative Power).


