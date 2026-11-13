# The Blind Spots of Roadkill Data

## Research questions
1. How unevenly are occurrence records distributed across continents and geographic areas in the map?
2. How does the balance between systematic and opportunistic surveys differ across continents?
3. How do recorded monthly patterns vary by animal class, and how should geographic coverage and survey methods shape their interpretation?

## Run locally
1. Install Python 3.10 or newer.
2. The submission includes the dataset Global Roadkill data.csv beside app.py
3. Create/activate a virtual environment by running the following commands: 
4. python -m venv .venv
5. source .venv/bin/activate
6. python -m pip install -r requirements.txt
7. python app.py
8. Open http://127.0.0.1:8050

## Current prototype features
1. Three coordinated views are available which are aggregated geographic map, month × animal-class heatmap and survey-method composition by continent
2. Shared filters for year, continent, survey type, and animal class
3. Linked selections from map, heatmap, and method chart as well as clear/reset control
4. Per-method counts, totals and other additional information are available upon hovering
5. Responsive and accessibility-frinedly layout with blue/orange method colors rather than a rainbow scale

