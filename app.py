from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, ctx, no_update

# First im locating the CSV right next to this script file
DATA_PATH = Path("Global Roadkill data.csv")

# Then creating the variables for consistent lookup lists and color palettes used across the multiple charts
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CLASS_ORDER = ["Mammalia", "Amphibia", "Reptilia", "Aves"]
METHOD_ORDER = ["Systematic", "Opportunistic"]
CONTINENT_ORDER = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]
BLUE = "#3156A6"
ORANGE = "#B45309"
PALETTE = {"Systematic": BLUE, "Opportunistic": ORANGE}

# In case i cannot find the csv file, im failing fast with a clear message
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Could not find {DATA_PATH.name}. Put the supplied CSV beside app.py and run again.")

# im only loading the columns we actually care about from the dataset to keep memory usage and startup time low
FIELDS = ["continent", "country", "decimalLatitude", "decimalLongitude", "class","scientificName", "numberOfRoadkill", "year", "month", "surveyType","coordinateUncertaintyInMeters"]
df = pd.read_csv(DATA_PATH, usecols=FIELDS, low_memory=False)

# Doing some data cleaning to clean up types and coerce bad data gracefully rather than crashing
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["month"] = pd.to_numeric(df["month"], errors="coerce")
df["numberOfRoadkill"] = pd.to_numeric(df["numberOfRoadkill"], errors="coerce").fillna(0)
df["decimalLatitude"] = pd.to_numeric(df["decimalLatitude"], errors="coerce")
df["decimalLongitude"] = pd.to_numeric(df["decimalLongitude"], errors="coerce")

# Im dropping rows missing important grouping categories
df = df[df["continent"].notna() & df["class"].notna() & df["surveyType"].notna()].copy()

# After that im converting the numeric month numbers into clean 3-letter labels (Jan, Feb, etc.)
df["month_label"] = df["month"].map(lambda x: MONTHS[int(x)-1] if pd.notna(x) and 1 <= x <= 12 and float(x).is_integer() else None)
df["class"] = df["class"].replace({"Mammalia": "Mammalia", "Amphibia": "Amphibia", "Reptilia": "Reptilia", "Aves": "Aves"})

# Now caching the baseline stats for the unfiltered dataset
YEAR_MIN = int(df["year"].min())
YEAR_MAX = int(df["year"].max())
BASE_ROWS = len(df)
BASE_ANIMALS = int(df["numberOfRoadkill"].sum())
BASE_COUNTRIES = int(df["country"].nunique())
BASE_SPECIES = int(df["scientificName"].nunique())

# Initializing the dash application
app = Dash(__name__)
app.title = "The Blind Spots of Roadkill Data"

def base_layout():
    # Here constructing the main HTML skeleton, header, KPI cards, sidebar controls, and chart grids
    return html.Div([
        html.Header([html.H1("The Blind Spots of Roadkill Data"),], className="page-header"),
        html.Div([
            html.Div([html.Div("Occurrence rows", className="kpi-label"), html.Div(id="kpi-rows", className="kpi-value")], className="kpi"),
            html.Div([html.Div("Animals represented", className="kpi-label"), html.Div(id="kpi-animals", className="kpi-value")], className="kpi"),
            html.Div([html.Div("Countries", className="kpi-label"), html.Div(id="kpi-countries", className="kpi-value")], className="kpi"),
            html.Div([html.Div("Species names", className="kpi-label"), html.Div(id="kpi-species", className="kpi-value")], className="kpi"),
        ], className="kpi-row"),
        html.Div([
            html.Aside([
                html.H2("Explore the records"),
                html.Label("Year range"),
                dcc.RangeSlider(id="year-range", min=YEAR_MIN, max=YEAR_MAX, step=1,value=[YEAR_MIN, YEAR_MAX], marks={y: str(y) for y in range(YEAR_MIN, YEAR_MAX+1, max(1, (YEAR_MAX-YEAR_MIN)//5))},tooltip={"placement": "bottom", "always_visible": False}),
                html.Label("Continent"),
                dcc.Dropdown(id="continent-filter", options=[{"label": c, "value": c} for c in CONTINENT_ORDER],multi=True, placeholder="All continents"),
                html.Label("Survey type"),
                dcc.Dropdown(id="method-filter", options=[{"label": m, "value": m} for m in METHOD_ORDER],multi=True, placeholder="All survey types"),
                html.Label("Animal class"),
                dcc.Dropdown(id="class-filter", options=[{"label": c, "value": c} for c in CLASS_ORDER],multi=True, placeholder="All animal classes"),
                html.Button("Clear filters and selections", id="reset", n_clicks=0, className="reset"),
                html.Div(id="selection-status", className="selection-status"),
            ], className="filter-panel"),
            html.Main([
                html.Section([
                    html.Div([html.Div("Geographic distribution", className="view-title")], className="chart-heading"),
                    dcc.Graph(id="map-chart", config={"displayModeBar": False}, className="map-graph"),
                ], className="chart-card map-card"),
                html.Div([
                    html.Section([
                        html.Div([
                            html.Div("Seasonal patterns", className="view-title"),
                            html.Div([html.Label("Display", className="heatmap-mode-label"),
                                dcc.RadioItems(id="heatmap-mode",options=[{"label": " Raw counts", "value": "count"},{"label": " Within-class %", "value": "share"},],
                                    value="count",inline=True,className="heatmap-mode",inputStyle={"marginRight": "4px", "marginLeft": "10px"},labelStyle={"fontSize": "10px", "color": "#5c6679"},
                                ),
                            ], className="heatmap-mode-control"),
                        ], className="chart-heading heatmap-heading"),
                        dcc.Graph(id="heatmap-chart", config={"displayModeBar": False}),
                    ], className="chart-card"),
                    html.Section([
                        html.Div([
                            html.Div("Survey methods", className="view-title"),
                            html.P("Share of occurrence records by survey method and continent",className="chart-description")
                        ], className="chart-heading"),
                        dcc.Graph(id="method-chart", config={"displayModeBar": False}),
                    ], className="chart-card"),
                ], className="bottom-grid"),
            ], className="visuals"),
        ], className="workspace"),
        html.Footer([
        ], className="footer"),
        # Storing the component to track the cross-chart click selections explicitly
        dcc.Store(id="linked-selection", data={"continent": None, "month": None, "class": None, "surveyType": None}),
    ], className="app-shell")

# Seting the app layout here
app.layout = base_layout()

@app.callback(
    Output("linked-selection", "data"),
    Input("map-chart", "clickData"),
    Input("heatmap-chart", "clickData"),
    Input("method-chart", "clickData"),
    Input("reset", "n_clicks"),
    State("linked-selection", "data"),
    prevent_initial_call=True,
)
def update_selection(map_click, heat_click, method_click, reset_clicks, current):
    # This is for syncing the cross-chart clicks so that clicking one graph filters the others while dropdowns stay independent
    trigger = ctx.triggered_id
    empty = {"continent": None, "month": None, "class": None, "surveyType": None}
    
    # Reset button forclearing all chart interactions
    if trigger == "reset":
        return empty
        
    # Handling the map point clicks..... extract continent
    if trigger == "map-chart" and map_click and map_click.get("points"):
        cd = map_click["points"][0].get("customdata")
        if cd is not None:
            continent = cd[0] if isinstance(cd, (list, tuple)) else cd
            return {**empty, "continent": continent}
            
    # Handling heatmap cell clicks....extract month and animal class
    elif trigger == "heatmap-chart" and heat_click and heat_click.get("points"):
        point = heat_click["points"][0]
        x, y = point.get("x"), point.get("y")
        if x in MONTHS and y in CLASS_ORDER:
            return {**empty, "month": x, "class": y}
            
    # Handling the survey method bar clicks....extract continent and survey type
    elif trigger == "method-chart" and method_click and method_click.get("points"):
        point = method_click["points"][0]
        cd = point.get("customdata")
        if isinstance(cd, (list, tuple)) and len(cd) >= 2:
            return {**empty, "continent": cd[0], "surveyType": cd[1]}
            
    return no_update

@app.callback(
    Output("year-range", "value"),
    Output("continent-filter", "value"),
    Output("method-filter", "value"),
    Output("class-filter", "value"),
    Input("reset", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_reset_clicks):
    # Here resetting the all sidebar filter controls and input ranges back to defaults
    return [YEAR_MIN, YEAR_MAX], None, None, None

@app.callback(
    Output("kpi-rows", "children"),
    Output("kpi-animals", "children"),
    Output("kpi-countries", "children"),
    Output("kpi-species", "children"),
    Output("map-chart", "figure"),
    Output("heatmap-chart", "figure"),
    Output("method-chart", "figure"),
    Output("selection-status", "children"),
    Input("year-range", "value"),
    Input("continent-filter", "value"),
    Input("method-filter", "value"),
    Input("class-filter", "value"),
    Input("linked-selection", "data"),
    Input("heatmap-mode", "value"),
)
def render_dashboard(years, continents, methods, classes, selection, heatmap_mode):
    # Core important rendering function for filtering the dataframe based on widgets/clicks and building all the figures and KPIs
    d = df
    
    # Below im applying the sidebar filter criteria
    if years:
        d = d[d["year"].between(years[0], years[1]) | d["year"].isna()]
    if continents:
        d = d[d["continent"].isin(continents)]
    if methods:
        d = d[d["surveyType"].isin(methods)]
    if classes:
        d = d[d["class"].isin(classes)]
        
    selection = selection or {}
    
    # Then applying the cross-chart linked selections if active
    if selection.get("continent"):
        d = d[d["continent"] == selection["continent"]]
    if selection.get("surveyType"):
        d = d[d["surveyType"] == selection["surveyType"]]

    # Keeping a copy of the scoped data so that the heatmap retains its full baseline denominator across months
    seasonal_scope = d.copy()

    # Further narrowingg down data if specific heatmap cells or classes were clicked
    if selection.get("month"):
        d = d[d["month_label"] == selection["month"]]
    if selection.get("class"):
        d = d[d["class"] == selection["class"]]

    # Here im preparing the map by rounding the lat/lon coordinates to 1-degree bins to make rendering fast
    geo = d.dropna(subset=["decimalLatitude", "decimalLongitude"]).copy()
    if not geo.empty:
        geo["lat_cell"] = geo["decimalLatitude"].round(0)
        geo["lon_cell"] = geo["decimalLongitude"].round(0)
        cells = geo.groupby(["lat_cell", "lon_cell", "continent"], as_index=False).agg(records=("continent", "size"))
        cells = cells.sort_values("records", ascending=False).head(6000)
        
        # Then building the geographic scatter plot on a natural earth projection
        map_fig = px.scatter_geo(
            cells, lat="lat_cell", lon="lon_cell", size="records", color="continent",
            color_discrete_sequence=px.colors.qualitative.Safe,
            custom_data=["continent", "records"],
            hover_data={"lat_cell": False, "lon_cell": False, "records": True, "continent": True},
            projection="natural earth", size_max=16,
        )
        map_fig.update_traces(marker={"opacity": 0.72, "line": {"width": 0}}, selector={"type": "scattergeo"})
        map_fig.update_layout(legend_title_text="Continent", margin={"l": 0, "r": 0, "t": 0, "b": 0},
                              paper_bgcolor="white", font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#172033", "size": 11},
                              geo={"showframe": False, "showcoastlines": True,
                              "coastlinecolor": "#cbd5e1", "showland": True, "landcolor": "#f3f5f8",
                              "showocean": True, "oceancolor": "#ffffff"})
    else:
        map_fig = go.Figure()
        map_fig.update_layout(title="No georeferenced records match these filters")
    map_fig.update_layout(clickmode="event+select")

    # Setting up the heatmap to track occurrence rows rather than individual animal counts
    # Calculating either raw counts or percentage share within each animal class across the 12 months
    h = seasonal_scope[seasonal_scope["month_label"].notna() & seasonal_scope["class"].isin(CLASS_ORDER)]
    heat_counts = h.groupby(["class", "month_label"]).size().rename("records").reset_index()
    full = pd.MultiIndex.from_product([CLASS_ORDER, MONTHS], names=["class", "month_label"]).to_frame(index=False)
    heat_counts = full.merge(heat_counts, how="left", on=["class", "month_label"]).fillna({"records": 0})
    raw_heat = heat_counts.pivot(index="class", columns="month_label", values="records").reindex(index=CLASS_ORDER, columns=MONTHS).fillna(0)
    class_totals = raw_heat.sum(axis=1).replace(0, pd.NA)
    share_heat = raw_heat.div(class_totals, axis=0).fillna(0) * 100

    # Also im switching the display metrics depending on user's radio toggle choice
    if heatmap_mode == "share":
        heat = share_heat
        colorbar_title = "Within-class share (%)"
        hover_value = "Within-class share: %{z:.1f}%"
        label_values = [[f"{v:.0f}%" for v in row] for row in heat.values]
        color_max = 100
    else:
        heat = raw_heat
        colorbar_title = "Occurrence rows"
        hover_value = "Occurrence records: %{z:,.0f}"
        label_values = [[(f"{v/1000:.1f}k" if v >= 1000 else f"{int(v)}") for v in row] for row in heat.values]
        color_max = None

    # Then constructing the Plotly heatmap figure
    heat_fig = go.Figure(data=go.Heatmap(
        z=heat.values, x=MONTHS, y=CLASS_ORDER, colorscale="Blues",
        zmin=0, zmax=color_max,
        colorbar={"title": colorbar_title}, customdata=raw_heat.values,
        hovertemplate="Class: %{y}<br>Month: %{x}<br>" + hover_value +"<br>Occurrence records: %{customdata:,.0f}<extra></extra>",
        xgap=2, ygap=2,
    ))

    # Adding the text labels directly onto the cells so that key values are readable without hovering
    max_value = float(heat.to_numpy().max()) if heat.size else 0
    for row_i, class_name in enumerate(CLASS_ORDER):
        for col_i, month_name in enumerate(MONTHS):
            value = float(heat.iloc[row_i, col_i])
            label = label_values[row_i][col_i]
            text_color = "#ffffff" if max_value and value >= max_value * 0.48 else "#172033"
            heat_fig.add_annotation(x=month_name, y=class_name, text=label, showarrow=False,font={"size": 9, "color": text_color}, xref="x", yref="y")

    heat_fig.update_layout(margin={"l": 5, "r": 5, "t": 8, "b": 10}, paper_bgcolor="white",font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#172033", "size": 11},xaxis={"side": "bottom", "categoryorder": "array", "categoryarray": MONTHS},yaxis={"categoryorder": "array", "categoryarray": CLASS_ORDER, "autorange": "reversed"})
    heat_fig.update_layout(clickmode="event+select")

    # Calculating the survey type distribution across continents
    m = d[d["surveyType"].isin(METHOD_ORDER)].groupby(["continent", "surveyType"], as_index=False).size().rename(columns={"size": "records"})
    totals = m.groupby("continent")["records"].sum().rename("total")
    m = m.join(totals, on="continent")
    m["share"] = m["records"] / m["total"] * 100
    
    # Im keeping the axis label clean and showing more detailed record counts which will be available when hovered on
    continent_ticktext = CONTINENT_ORDER.copy()
    m["continent"] = pd.Categorical(m["continent"], categories=CONTINENT_ORDER, ordered=True)
    m = m.sort_values("continent")
    
    # For survey methods, im building the stacked horizontal bar chart
    method_fig = go.Figure()
    for method in METHOD_ORDER:
        part = m[m["surveyType"] == method]
        method_fig.add_trace(go.Bar(
            y=part["continent"].astype(str), x=part["share"], orientation="h", name=method,
            marker_color=PALETTE[method], customdata=list(zip(part["continent"].astype(str), part["surveyType"], part["records"], part["total"])),
            text=[f"{v:.0f}%" if v >= 8 else "" for v in part["share"]],
            textposition="inside", textfont={"color": "#FFFFFF"},
            legendrank=1 if method == "Systematic" else 2,
            hovertemplate="Continent: %{customdata[0]}<br>Survey: %{customdata[1]}<br>Share: %{x:.1f}%<br>Records: %{customdata[2]:,}<br>Continent total: %{customdata[3]:,}<extra></extra>",
        ))
    method_fig.update_layout(barmode="stack", xaxis={"title": "Share of occurrence records (%)", "range": [0, 100]},
                             yaxis={"title": "", "categoryorder": "array", "categoryarray": CONTINENT_ORDER,"tickmode": "array", "tickvals": CONTINENT_ORDER, "ticktext": continent_ticktext,"autorange": "reversed"},
                             legend={"title": "Survey type", "orientation": "h", "y": 1.18,"traceorder": "normal"},
                             margin={"l": 5, "r": 5, "t": 15, "b": 25}, paper_bgcolor="white",
                             font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": "#172033", "size": 11})
    method_fig.update_layout(clickmode="event+select")

    # Generating the status text for summarizing active cross-chart filters
    status_parts = []
    for key, label in [("continent", "Continent"), ("surveyType", "Survey"), ("month", "Month"), ("class", "Class")]:
        if selection.get(key):
            status_parts.append(f"{label}: {selection[key]}")
    status = "Linked selection: " + (" · ".join(status_parts) if status_parts else "none")
    
    # Returning the all the updated KPI values, figures, and filter status string
    return (
        f"{len(d):,}", f"{int(d['numberOfRoadkill'].sum()):,}",
        f"{d['country'].nunique():,}", f"{d['scientificName'].nunique():,}",
        map_fig, heat_fig, method_fig, status
    )

# Starting up the local development server when run as the main script
if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)