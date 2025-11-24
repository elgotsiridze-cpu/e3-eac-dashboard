# e3_eac_dashboard.py
# E3 Energy Trading | EAC Market Dashboard
# FULL SCRIPT (Revenue in USD bn)
# - Branding cleaned
# - Global map fully yellow outside UK/EU/US/MENA
# - Intro simplified & investor-ready (passport / proof of consumption)
# - Wind described as premium (no scarcity claim)
# - Demand & Supply works per region + global, in TWh (both demand + supply)
# - Scenario toggle Base / Upside / Aggressive affects prices + demand + revenue + DS
# - Revenue chart filters by region correctly
# - Global revenue shows per-year totals + grand total
# - Single-scheme revenue shows only one total (2025–2030)
# - Thousand separators, centered tables
# - Revenue displayed as USD bn (billions)
# - No certificate-tech tab/filter
# - Dash 2.x / 3.x compatible run

import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, no_update
import plotly.express as px

# ---------------------------
# BRANDING
# ---------------------------
APP_TITLE = "E3 Energy Trading | EAC Market Dashboard"
PRIMARY = "#0B3558"
BG = "#F5F7FA"
CARD_BG = "white"

# ---------------------------
# SCENARIOS (BCG style)
# ---------------------------
SCENARIOS = {
    "Base":        {"demand_mult": 1.00, "price_mult": 1.00},
    "Upside":      {"demand_mult": 1.25, "price_mult": 1.50},
    "Aggressive":  {"demand_mult": 1.50, "price_mult": 2.00},
}

# ---------------------------
# REGIONS / SCHEMES
# ---------------------------
REGION_SCHEME = {
    "Middle East / MENA": "I-RECs (incl. UAE)",
    "United Kingdom": "REGOs",
    "European Union": "GOs",
    "United States": "RECs",
    "Global": "I-RECs (International) / Cross-scheme"
}

REGION_COUNTRIES = {
    "Middle East / MENA": ["UAE","Saudi Arabia","Egypt","Jordan","Morocco","Oman","Qatar","Bahrain","Kuwait"],
    "United Kingdom": ["United Kingdom"],
    "European Union": ["Germany","France","Netherlands","Spain","Italy","Sweden","Norway","Denmark"],
    "United States": ["United States"],
    "Global": ["Global"]
}

# ---------------------------
# MAP REGIONS
# ---------------------------
MENA = set(REGION_COUNTRIES["Middle East / MENA"])
UK = set(REGION_COUNTRIES["United Kingdom"])
EU = set(REGION_COUNTRIES["European Union"])
US = set(REGION_COUNTRIES["United States"])

COUNTRY_REGION = {}
for c in MENA: COUNTRY_REGION[c] = "Middle East / MENA"
for c in UK:   COUNTRY_REGION[c] = "United Kingdom"
for c in EU:   COUNTRY_REGION[c] = "European Union"
for c in US:   COUNTRY_REGION[c] = "United States"

# ---------------------------
# PRICE DATA (public anchors + indicative trends)
# ---------------------------
price_rows, years = [], list(range(2020, 2026))
for y in years:
    mena_price = {2020:1.8, 2021:2.0, 2022:2.1, 2023:2.2, 2024:2.25, 2025:2.39}[y]
    rego_price = {2020:0.3, 2021:0.6, 2022:2.8, 2023:20.0, 2024:2.0, 2025:1.5}[y]
    go_price   = {2020:0.8, 2021:1.5, 2022:4.0, 2023:7.0, 2024:3.2, 2025:3.5}[y]
    rec_price  = {2020:4.5, 2021:5.0, 2022:5.8, 2023:6.2, 2024:5.7, 2025:5.9}[y]

    price_rows += [
        ("I-RECs (incl. UAE)", y, mena_price),
        ("REGOs", y, rego_price),
        ("GOs", y, go_price),
        ("RECs", y, rec_price),
    ]
prices_df = pd.DataFrame(price_rows, columns=["Scheme","Year","Price"])

anchors_df = pd.DataFrame([
    ("I-RECs (incl. UAE)", 2023, 2.20),
    ("I-RECs (incl. UAE)", 2025, 2.39),
    ("REGOs", 2022, 2.8),
    ("REGOs", 2023, 20.0),
    ("REGOs", 2024, 2.0),
    ("GOs", 2023, 7.0),
    ("GOs", 2024, 3.2),
], columns=["Scheme","Year","Price"])

SCHEME_UNIT = {"REGOs":"£/MWh","GOs":"€/MWh","I-RECs (incl. UAE)":"$/MWh","RECs":"$/MWh"}
UNIT_PREFIX = {"£/MWh":"£","€/MWh":"€","$/MWh":"$"}

# ---------------------------
# DEMAND & SUPPLY (TWh)
# ---------------------------
demand_index_df = pd.DataFrame({
    "Year": list(range(2021, 2026)),
    "Middle East / MENA": [1.0,1.2,1.5,1.9,2.4],
    "United Kingdom":     [1.0,1.1,1.25,1.35,1.5],
    "European Union":     [1.0,1.2,1.4,1.65,1.9],
    "United States":      [1.0,1.3,1.7,2.1,2.6],
})

BASE_DEMAND_TWH_2021 = {
    "Middle East / MENA": 8,
    "United Kingdom": 25,
    "European Union": 140,
    "United States": 220
}

BASE_SUPPLY_TWH_2021 = {
    "Middle East / MENA": 9,
    "United Kingdom": 27,
    "European Union": 150,
    "United States": 230
}

SUPPLY_GROWTH_MULTIPLIER = {
    "Middle East / MENA": 0.90,
    "United Kingdom": 0.95,
    "European Union": 0.92,
    "United States": 0.94
}

def region_twh_series(region, scenario_name="Base", kind="Demand"):
    mult = SCENARIOS[scenario_name]["demand_mult"]
    rows = []
    for y in demand_index_df["Year"]:
        idx = float(demand_index_df.set_index("Year").loc[y, region])
        if kind == "Demand":
            base = BASE_DEMAND_TWH_2021[region]
            val = base * idx * mult
        else:
            base = BASE_SUPPLY_TWH_2021[region]
            val = base * (1 + (idx-1)*SUPPLY_GROWTH_MULTIPLIER[region]) * mult
        rows.append((y, val))
    return pd.DataFrame(rows, columns=["Year", f"{kind}TWh"])

COUNTRY_SHARES = {
    "Middle East / MENA": {
        "UAE":0.28,"Saudi Arabia":0.32,"Egypt":0.16,"Jordan":0.06,"Morocco":0.07,
        "Oman":0.05,"Qatar":0.03,"Bahrain":0.02,"Kuwait":0.01
    },
    "European Union": {
        "Germany":0.18,"France":0.14,"Netherlands":0.10,"Spain":0.11,"Italy":0.12,
        "Sweden":0.10,"Norway":0.10,"Denmark":0.05
    },
    "United Kingdom":{"United Kingdom":1.0},
    "United States":{"United States":1.0}
}

def country_demand_twh(region, year, scenario_name="Base"):
    mult = SCENARIOS[scenario_name]["demand_mult"]
    idx = float(demand_index_df.set_index("Year").loc[year, region])
    total = BASE_DEMAND_TWH_2021[region] * idx * mult
    shares = COUNTRY_SHARES.get(region, {})
    return pd.DataFrame(
        [(c, year, total*s) for c, s in shares.items()],
        columns=["Country","Year","DemandTWh"]
    )

# ---------------------------
# BUYERS
# ---------------------------
buyers_df = pd.DataFrame([
    ("Middle East / MENA","EGA","Heavy Industry",1_100_000,"Confirmed buyer (UAE)"),
    ("Middle East / MENA","DP World","Ports/Logistics",200_000,"Confirmed buyer"),
    ("Middle East / MENA","ADNEC","Real Estate/Venues",13_700,"Confirmed buyer"),
    ("Middle East / MENA","Emirates Airline","Aviation",180_000,"Priority target"),
    ("Middle East / MENA","Etihad Airways","Aviation",120_000,"Priority target"),
    ("Middle East / MENA","ADNOC","Industry",250_000,"Priority target"),
    ("Middle East / MENA","Aramco","Industry",500_000,"Priority target"),
    ("Middle East / MENA","SABIC","Chemicals",350_000,"Priority target"),
    ("Middle East / MENA","Majid Al Futtaim","Retail/Real Estate",140_000,"Priority target"),
    ("Middle East / MENA","Dubai Airports","Infrastructure",100_000,"Priority target"),

    ("United Kingdom","BT Group","Telecom",250_000,"Large buyer"),
    ("United Kingdom","Vodafone UK","Telecom",180_000,"Large buyer"),
    ("United Kingdom","Unilever UK","FMCG",160_000,"RE100 buyer"),
    ("United Kingdom","Tesco","Retail",220_000,"Large buyer"),
    ("United Kingdom","Sainsbury's","Retail",140_000,"Large buyer"),
    ("United Kingdom","HSBC UK","Finance",90_000,"RE100 buyer"),
    ("United Kingdom","Barclays","Finance",80_000,"RE100 buyer"),
    ("United Kingdom","AstraZeneca","Pharma",60_000,"Corporate claims"),
    ("United Kingdom","Google UK","Tech",150_000,"Corporate claims"),
    ("United Kingdom","British Land","Real Estate",70_000,"Corporate claims"),

    ("European Union","IKEA","Retail",900_000,"Large GO buyer"),
    ("European Union","BMW Group","Automotive",650_000,"Large GO buyer"),
    ("European Union","BASF","Chemicals",520_000,"Large GO buyer"),
    ("European Union","Schneider Electric","Industrial/Tech",450_000,"RE100 buyer"),
    ("European Union","Nestlé Europe","FMCG",600_000,"Corporate claims"),
    ("European Union","L'Oréal","FMCG",280_000,"RE100 buyer"),
    ("European Union","Heineken","Beverage",260_000,"Corporate claims"),
    ("European Union","Telefonica","Telecom",310_000,"RE100 buyer"),
    ("European Union","Apple (EU ops)","Tech",400_000,"Corporate claims"),
    ("European Union","TotalEnergies (EU ops)","Energy",350_000,"Corporate claims"),

    ("United States","Amazon","Tech/Logistics",12_000_000,"Largest buyer"),
    ("United States","Google","Tech",8_000_000,"Large buyer"),
    ("United States","Microsoft","Tech",7_500_000,"Large buyer"),
    ("United States","Meta","Tech",4_500_000,"Large buyer"),
    ("United States","Apple","Tech",3_200_000,"Large buyer"),
    ("United States","Walmart","Retail",2_400_000,"Large buyer"),
    ("United States","Verizon","Telecom",1_600_000,"Corporate claims"),
    ("United States","AT&T","Telecom",1_400_000,"Corporate claims"),
    ("United States","General Motors","Automotive",1_200_000,"Corporate claims"),
    ("United States","PepsiCo","FMCG",900_000,"Corporate claims"),

    ("Global","Amazon","Tech/Logistics",15_000_000,"Global leader"),
    ("Global","Google","Tech",10_000_000,"Global leader"),
    ("Global","Microsoft","Tech",9_000_000,"Global leader"),
    ("Global","Apple","Tech",5_000_000,"Global leader"),
    ("Global","Meta","Tech",6_000_000,"Global leader"),
    ("Global","IKEA","Retail",2_000_000,"Global leader"),
    ("Global","Unilever","FMCG",1_700_000,"Global leader"),
    ("Global","BMW Group","Automotive",1_500_000,"Global leader"),
    ("Global","Schneider Electric","Industrial/Tech",1_200_000,"Global leader"),
    ("Global","Nestlé","FMCG",1_100_000,"Global leader"),
], columns=["Region","Buyer","Segment","AnnualMWh","StatusNote"])

# ---------------------------
# GENERATORS
# ---------------------------
gens_df = pd.DataFrame([
    ("Middle East / MENA","UAE","Noor Abu Dhabi","Solar","I-RECs",3.5),
    ("Middle East / MENA","UAE","MBR Solar Park","Solar","I-RECs",2.2),
    ("Middle East / MENA","Saudi Arabia","ACWA solar fleet","Solar","I-RECs",4.0),
    ("Middle East / MENA","Egypt","Gulf of Suez wind cluster","Wind","I-RECs",5.0),
    ("Middle East / MENA","Morocco","Noor + wind parks","Solar/Wind","I-RECs",2.8),

    ("United Kingdom","United Kingdom","Ørsted Hornsea Offshore","Wind","REGOs",6.0),
    ("United Kingdom","United Kingdom","SSE Renewables fleet","Wind","REGOs",5.2),
    ("United Kingdom","United Kingdom","RWE UK Offshore","Wind","REGOs",3.8),
    ("United Kingdom","United Kingdom","ScottishPower Renewables","Wind","REGOs",3.0),
    ("United Kingdom","United Kingdom","Lightsource BP UK","Solar","REGOs",1.6),
    ("United Kingdom","United Kingdom","Statkraft UK Hydro","Hydro","REGOs",0.9),
    ("United Kingdom","United Kingdom","Drax biomass","Biomass","REGOs",3.5),

    ("European Union","Norway","Statkraft Hydro","Hydro","GOs",20.0),
    ("European Union","Spain","Iberdrola Renewables","Wind/Solar","GOs",12.0),
    ("European Union","Italy","Enel Green Power","Wind/Solar","GOs",10.0),
    ("European Union","Germany","RWE Renewables","Wind/Solar","GOs",9.0),
    ("European Union","Sweden","Vattenfall wind/hydro","Wind/Hydro","GOs",8.0),

    ("United States","United States","NextEra Energy Resources","Wind/Solar","RECs",35.0),
    ("United States","United States","Avangrid Renewables","Wind/Solar","RECs",12.0),
    ("United States","United States","Invenergy","Wind/Solar","RECs",10.0),
    ("United States","United States","Brookfield Renewable","Hydro/Wind","RECs",14.0),
    ("United States","United States","Duke Energy Renewables","Wind/Solar","RECs",8.0),
], columns=["Region","Country","Generator","Tech","Scheme","AnnualGenerationTWh"])

# ---------------------------
# POLICY
# ---------------------------
policy_df = pd.DataFrame([
    ("Middle East / MENA","UAE Scope-2 reporting mandatory from 30 May 2025; EWEC auctions each quarter create local demand."),
    ("Middle East / MENA","I-REC Standard expanding globally, enabling emerging-market supply to reach premium buyers."),
    ("United Kingdom","Fuel Mix Disclosure creates annual compliance cycles; scarcity can create price spikes."),
    ("United Kingdom","High-quality REGOs (wind/new-build/local) trade at premiums."),
    ("European Union","AIB GO system harmonised; exchange trading is growing."),
    ("European Union","Supply shifts drive volatility, creating timing/arbitrage edge."),
    ("United States","State RPS compliance plus voluntary ESG demand produces highest liquidity."),
    ("United States","Corporate forward offtake supports multi-year contracts."),
], columns=["Region","PolicySummary"])

# ---------------------------
# REVENUE FORECAST (scenario-dependent)
# ---------------------------
forecast_years = list(range(2025, 2031))
FORECAST_CAGR = {"I-RECs (incl. UAE)":0.20, "REGOs":0.08, "GOs":0.10, "RECs":0.12}
BASE_DEMAND_2025_TWH = {"I-RECs (incl. UAE)":25, "REGOs":55, "GOs":850, "RECs":1200}

def price_forecast_base(scheme):
    hist = prices_df[prices_df["Scheme"] == scheme].sort_values("Year")
    if hist["Year"].nunique() < 2:
        p2025 = float(hist[hist["Year"] == 2025]["Price"].iloc[0])
        return {y: p2025 for y in forecast_years}

    y0, y1 = int(hist["Year"].iloc[0]), int(hist["Year"].iloc[-1])
    p0, p1 = float(hist["Price"].iloc[0]), float(hist["Price"].iloc[-1])
    n = max(1, y1 - y0)
    price_cagr = (p1 / p0) ** (1 / n) - 1

    p2025 = float(hist[hist["Year"] == 2025]["Price"].iloc[0])
    return {y: p2025 * ((1 + price_cagr) ** (y - 2025)) for y in forecast_years}

PRICE_FWD_BASE = {s: price_forecast_base(s) for s in BASE_DEMAND_2025_TWH.keys()}

def build_revenue_df(scenario_name="Base"):
    d_mult = SCENARIOS[scenario_name]["demand_mult"]
    p_mult = SCENARIOS[scenario_name]["price_mult"]

    rows=[]
    for scheme in BASE_DEMAND_2025_TWH.keys():
        base, cagr = BASE_DEMAND_2025_TWH[scheme], FORECAST_CAGR[scheme]
        for i, y in enumerate(forecast_years):
            demand = base * ((1 + cagr) ** i) * d_mult
            price  = PRICE_FWD_BASE[scheme][y] * p_mult
            revenue_musd = demand * price
            rows.append((scheme, y, demand, price, revenue_musd))
    df = pd.DataFrame(rows, columns=["Scheme","Year","DemandTWh","PricePerMWh","RevenueMUSD"])
    df["RevenueBUSD"] = df["RevenueMUSD"] / 1000.0  # convert to USD bn
    return df

# ---------------------------
# APP
# ---------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = APP_TITLE

def card(children):
    return html.Div(children, style={
        "background": CARD_BG,
        "padding": "14px",
        "borderRadius": "14px",
        "boxShadow": "0 4px 18px rgba(0,0,0,0.08)"
    })

app.layout = html.Div(style={"background":BG,"minHeight":"100vh","padding":"18px"}, children=[
    html.Div(style={"display":"flex","justifyContent":"space-between","alignItems":"center"}, children=[
        html.Div([
            html.H1("E3 Energy Trading", style={"margin":"0","color":PRIMARY}),
            html.Div("Energy Attribute Certificates (EACs)", style={"color":"#555","fontSize":"14px"})
        ]),
        html.Div(style={"display":"flex","gap":"10px","alignItems":"end"}, children=[
            html.Div([
                html.Div("Scenario", style={"fontSize":"12px"}),
                dcc.Dropdown(
                    id="scenario",
                    options=[{"label":s,"value":s} for s in SCENARIOS.keys()],
                    value="Base",
                    clearable=False,
                    style={"width":"190px"}
                )
            ]),
            html.Div([
                html.Div("Region", style={"fontSize":"12px"}),
                dcc.Dropdown(
                    id="region",
                    options=[{"label":r,"value":r} for r in REGION_SCHEME],
                    value="Middle East / MENA",
                    clearable=False,
                    style={"width":"260px"}
                )
            ])
        ])
    ]),

    html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr 1fr","gap":"10px","marginTop":"12px"}, children=[
        card([html.Div("Scheme"), html.H3(id="scheme_kpi")]),
        card([html.Div("Indicative Price (latest year)"), html.H3(id="price_kpi")]),
        card([html.Div("Demand growth (2025 vs 2021)"), html.H3(id="demand_kpi")]),
    ]),

    html.Div(style={"display":"flex","gap":"10px","marginTop":"12px"}, children=[
        html.Div([
            html.Div("Country", style={"fontSize":"12px"}),
            dcc.Dropdown(id="country", clearable=False, placeholder="Select...", style={"width":"260px"})
        ]),
    ]),

    dcc.Tabs(id="tabs", value="tab_intro", children=[
        dcc.Tab(label="Intro", value="tab_intro"),
        dcc.Tab(label="Map (click country)", value="tab_map"),
        dcc.Tab(label="Prices", value="tab_prices"),
        dcc.Tab(label="Demand & Supply", value="tab_ds"),
        dcc.Tab(label="Top Buyers", value="tab_buyers"),
        dcc.Tab(label="Generators", value="tab_gens"),
        dcc.Tab(label="Policy & Trading", value="tab_policy"),
        dcc.Tab(label="Revenue Forecast", value="tab_rev"),
    ]),
    html.Div(id="tab_content", style={"marginTop":"12px"})
])

# ---------------------------
# CALLBACKS
# ---------------------------
@app.callback(
    Output("country","options"),
    Output("country","value"),
    Input("region","value")
)
def update_countries(region):
    countries = REGION_COUNTRIES[region]
    return [{"label":c,"value":c} for c in countries], countries[0]

@app.callback(
    Output("scheme_kpi","children"),
    Output("price_kpi","children"),
    Output("demand_kpi","children"),
    Input("region","value"),
    Input("scenario","value")
)
def update_kpis(region, scenario):
    scheme = REGION_SCHEME[region]
    latest_year = prices_df["Year"].max()
    d_mult = SCENARIOS[scenario]["demand_mult"]
    p_mult = SCENARIOS[scenario]["price_mult"]

    if region == "Global":
        latest_price = prices_df.query("Year==@latest_year")["Price"].mean() * p_mult
        growth = (
            demand_index_df.set_index("Year").loc[2025].mean() /
            demand_index_df.set_index("Year").loc[2021].mean()
        ) * d_mult
        return scheme, f"${latest_price:.2f} $/MWh", f"{growth:.1f}×"

    latest_price = prices_df.query("Scheme==@scheme and Year==@latest_year")["Price"].iloc[0] * p_mult
    unit = SCHEME_UNIT[scheme]
    prefix = UNIT_PREFIX[unit]
    d = demand_index_df.set_index("Year")
    growth = float(d.loc[2025,region] / d.loc[2021,region]) * d_mult
    return scheme, f"{prefix}{latest_price:.2f} {unit}", f"{growth:.1f}×"

@app.callback(
    Output("tab_content","children"),
    Input("tabs","value"),
    Input("region","value"),
    Input("country","value"),
    Input("scenario","value"),
)
def render_tab(tab, region, country, scenario):
    scheme = REGION_SCHEME[region]
    if not country:
        country = REGION_COUNTRIES[region][0]

    revenue_df = build_revenue_df(scenario)

    # INTRO
    if tab == "tab_intro":
        return html.Div(style={"display":"grid","gridTemplateColumns":"1.2fr 0.8fr","gap":"10px"}, children=[
            card([
                html.H3("What are Energy Attribute Certificates (EACs)?", style={"color":PRIMARY}),
                html.P(
                    "Electricity from gas, solar, wind and other sources mixes together in the grid. "
                    "Once power enters the grid, it is impossible to trace which generator produced "
                    "the exact electrons a customer consumes."
                ),
                html.P(
                    "EACs solve this problem. They act like a passport for electricity: "
                    "each certificate represents 1 MWh of verified renewable or clean generation. "
                    "When a company buys and retires (cancels) an EAC, it gets proof that 1 MWh of its "
                    "electricity consumption can be claimed as renewable."
                ),
                html.P(
                    "Certificates can be issued from wind, solar, hydro, and biomass generation. "
                    "Wind certificates are usually treated as a premium product, "
                    "while biomass certificates are typically lower-priced."
                ),
                html.H4("Global naming map"),
                html.Ul([
                    html.Li("RECs (United States)"),
                    html.Li("I-RECs (International: MENA, Asia, Africa, Latin America, Australia)"),
                    html.Li("GOs (EU Guarantees of Origin)"),
                    html.Li("REGOs (United Kingdom)"),
                ]),
                html.P("All follow the same logic: 1 MWh equals 1 tradable clean-energy attribute.")
            ]),
            card([
                html.H4("Why investors care", style={"color":PRIMARY}),
                html.Ul([
                    html.Li("Structural demand tailwind: Scope-2 reporting, RE100, and net-zero targets drive recurring annual demand for certificates."),
                    html.Li("Digital, registry-based commodity: traded and retired in registries (I-REC, AIB GO, REGO, REC) with no shipping, storage, or physical logistics."),
                    html.Li("Balance-sheet light growth: far lower working-capital needs than physical power or fuels, enabling scalable trading expansion."),
                    html.Li("Multiple monetisation levers: regional arbitrage, forward hedges, premium tech/origin bundles, and portfolio aggregation from generators."),
                    html.Li("MENA advantage + global reach: fast renewable build-out creates exportable surplus while EU/UK/US remain premium demand hubs.")
                ]),
                html.Hr(),
                html.P(f"In {region}, the dominant instrument is {scheme}.")
            ])
        ])

    # MAP
    if tab == "tab_map":
        all_countries = px.data.gapminder()["country"].unique().tolist()
        map_df = pd.DataFrame({"Country": all_countries})

        def assign_region(c):
            if c in COUNTRY_REGION:
                return COUNTRY_REGION[c]
            if c in MENA: return "Middle East / MENA"
            if c in UK:   return "United Kingdom"
            if c in EU:   return "European Union"
            if c in US:   return "United States"
            return "Global"

        map_df["Region"] = map_df["Country"].apply(assign_region)
        map_df["Scheme"] = map_df["Region"].map(REGION_SCHEME)

        color_map = {
            "Middle East / MENA": "#3B82F6",
            "United Kingdom": "#10B981",
            "European Union": "#8B5CF6",
            "United States": "#EF4444",
            "Global": "#FBBF24"
        }

        fig = px.choropleth(
            map_df,
            locations="Country",
            locationmode="country names",
            color="Region",
            hover_data={"Scheme": True, "Region": True, "Country": False},
            title="Global EAC map — hover to see scheme, click to filter",
            color_discrete_map=color_map
        )
        fig.update_layout(height=540, margin=dict(l=0,r=0,t=60,b=0))
        return card([dcc.Graph(id="country_map", figure=fig, config={"displayModeBar": False})])

    # PRICES
    if tab == "tab_prices":
        subset = prices_df.query("Scheme==@scheme") if region != "Global" else prices_df
        anchors = anchors_df.query("Scheme==@scheme")

        unit = SCHEME_UNIT.get(scheme, "$/MWh")
        prefix = UNIT_PREFIX.get(unit, "$")

        fig = px.line(
            subset, x="Year", y="Price",
            color="Scheme" if region=="Global" else None,
            markers=True, title=f"Price signals ({unit})"
        )
        if region != "Global":
            fig.add_scatter(
                x=anchors["Year"], y=anchors["Price"],
                mode="markers", marker=dict(size=12, symbol="diamond"),
                name="Public anchors"
            )
        fig.update_layout(height=440, yaxis_title=unit)
        fig.update_yaxes(tickprefix=prefix)

        return card([
            dcc.Graph(figure=fig),
            html.Div(
                "Public anchors are price points visible in public press or market notes. "
                "The line interpolates between anchors where live vendor data is not freely available.",
                style={"fontSize":"12px","color":"#64748b"}
            )
        ])

    # DEMAND & SUPPLY
    if tab == "tab_ds":
        if region == "Global":
            long=[]
            for r in BASE_DEMAND_TWH_2021.keys():
                dser = region_twh_series(r, scenario, "Demand")
                sser = region_twh_series(r, scenario, "Supply")
                merged = dser.merge(sser, on="Year")
                merged["Region"]=r
                long.append(merged)
            long_df = pd.concat(long, ignore_index=True)

            fig_d = px.line(long_df, x="Year", y="DemandTWh", color="Region",
                            markers=True, title="Demand (TWh) by region (scenario-adjusted)")
            fig_d.update_layout(height=360, yaxis_title="TWh")

            fig_s = px.line(long_df, x="Year", y="SupplyTWh", color="Region",
                            markers=True, title="Supply (TWh) by region (scenario-adjusted)")
            fig_s.update_layout(height=360, yaxis_title="TWh")

            return html.Div([
                card([dcc.Graph(figure=fig_d)]),
                html.Div(style={"height":"10px"}),
                card([dcc.Graph(figure=fig_s)])
            ])

        if region not in BASE_DEMAND_TWH_2021:
            return card([
                html.H4("Demand & supply data not available for this region."),
                html.Div(f"Selected region: {region}")
            ])

        dser = region_twh_series(region, scenario, "Demand")
        sser = region_twh_series(region, scenario, "Supply")
        merged = dser.merge(sser, on="Year")

        fig1 = px.line(
            merged.melt(id_vars="Year",
                        value_vars=["DemandTWh","SupplyTWh"],
                        var_name="Type", value_name="TWh"),
            x="Year", y="TWh", color="Type",
            markers=True, title=f"{region} demand vs supply (TWh, scenario-adjusted)"
        )
        fig1.update_layout(height=360, yaxis_title="TWh")

        cdf = country_demand_twh(region, 2025, scenario)
        fig2 = px.bar(cdf, x="Country", y="DemandTWh",
                      title=f"{region} country demand breakdown (2025, indicative)")
        fig2.update_layout(height=360, yaxis_title="TWh")

        return html.Div([
            card([dcc.Graph(figure=fig1)]),
            html.Div(style={"height":"10px"}),
            card([dcc.Graph(figure=fig2)])
        ])

    # BUYERS
    if tab == "tab_buyers":
        regional = buyers_df.query("Region==@region") if region!="Global" else buyers_df.query("Region=='Global'")
        fig = px.bar(regional, x="Buyer", y="AnnualMWh", color="Segment",
                     title=f"Top buyers / targets — {region}")
        fig.update_layout(height=420)
        return card([dcc.Graph(figure=fig)])

    # GENERATORS
    if tab == "tab_gens":
        g = gens_df.query("Region==@region") if region!="Global" else gens_df

        fig1 = px.scatter(
            g, x="Country", y="Tech", color="Scheme",
            size="AnnualGenerationTWh",
            hover_name="Generator",
            title=f"Main renewable generators — {region}"
        )
        fig1.update_layout(height=380)

        fig2 = px.bar(
            g.sort_values("AnnualGenerationTWh", ascending=False),
            x="Generator", y="AnnualGenerationTWh", color="Tech",
            title="Indicative annual renewable volume eligible for certificates (TWh)"
        )
        fig2.update_layout(height=360, xaxis_tickangle=-30, yaxis_title="TWh")

        return html.Div([
            card([dcc.Graph(figure=fig1)]),
            html.Div(style={"height":"10px"}),
            card([dcc.Graph(figure=fig2)])
        ])

    # POLICY
    if tab == "tab_policy":
        p = policy_df.query("Region==@region") if region!="Global" else policy_df
        return card([
            html.H3("Policy tailwinds & trading opportunities", style={"color":PRIMARY}),
            html.Ul([html.Li(x) for x in p["PolicySummary"]]),
            html.Hr(),
            html.H4("Trading angles E3 can monetise"),
            html.Ul([
                html.Li("Regional arbitrage: source low-cost MENA I-RECs and sell into higher-priced EU/UK demand."),
                html.Li("Forward structures: lock multi-year pricing for corporates needing budget certainty."),
                html.Li("Premium bundles: wind, new-build or local issuance can sell at price uplifts."),
                html.Li("Portfolio trading: aggregate generator supply, deliver global resale and recurring cashflow."),
            ])
        ])

    # -----------------------------------------
    # REVENUE (scenario-dependent) -- USD bn
    # -----------------------------------------
    if tab == "tab_rev":

        if region != "Global":
            scheme_filter = REGION_SCHEME[region]
            chart_df = revenue_df.query("Scheme==@scheme_filter").copy()
            chart_title = f"{scheme_filter} revenue pool (2025–2030) — {scenario}"
            chart_color = None
        else:
            chart_df = revenue_df.copy()
            chart_title = f"Indicative global EAC revenue pool by scheme (2025–2030) — {scenario}"
            chart_color = "Scheme"

        fig = px.line(
            chart_df,
            x="Year",
            y="RevenueBUSD",
            color=chart_color,
            markers=True,
            title=chart_title
        )
        fig.update_layout(height=420, yaxis_title="USD billions")

        if region != "Global":
            scheme_filter = REGION_SCHEME[region]
            tdf = revenue_df.query("Scheme==@scheme_filter").copy()

            total_demand = tdf["DemandTWh"].sum()
            total_revenue_musd = tdf["RevenueMUSD"].sum()
            total_revenue_busd = total_revenue_musd / 1000.0
            vwap = (total_revenue_musd * 1_000_000) / (total_demand * 1_000_000)

            tdf2 = pd.concat([tdf, pd.DataFrame([{
                "Scheme": "TOTAL (2025–2030)",
                "Year": "",
                "DemandTWh": total_demand,
                "PricePerMWh": vwap,
                "RevenueMUSD": total_revenue_musd,
                "RevenueBUSD": total_revenue_busd
            }])], ignore_index=True)

        else:
            tdf = revenue_df.copy()

            totals=[]
            for y in forecast_years:
                s = tdf[tdf["Year"] == y]
                td = s["DemandTWh"].sum()
                tr_musd = s["RevenueMUSD"].sum()
                tr_busd = tr_musd / 1000.0
                vwap = (tr_musd * 1_000_000) / (td * 1_000_000)
                totals.append({
                    "Scheme":"TOTAL",
                    "Year":y,
                    "DemandTWh":td,
                    "PricePerMWh":vwap,
                    "RevenueMUSD":tr_musd,
                    "RevenueBUSD":tr_busd
                })
            totals_df = pd.DataFrame(totals)

            grand_d = tdf["DemandTWh"].sum()
            grand_r_musd = tdf["RevenueMUSD"].sum()
            grand_r_busd = grand_r_musd / 1000.0
            grand_vwap = (grand_r_musd * 1_000_000) / (grand_d * 1_000_000)

            grand_df = pd.DataFrame([{
                "Scheme":"GRAND TOTAL (2025–2030)",
                "Year":"",
                "DemandTWh":grand_d,
                "PricePerMWh":grand_vwap,
                "RevenueMUSD":grand_r_musd,
                "RevenueBUSD":grand_r_busd
            }])

            tdf2 = pd.concat([tdf, totals_df, grand_df], ignore_index=True)
            tdf2 = tdf2.sort_values(["Year","Scheme"], na_position="last")

        def fmt0(x):
            try:
                return f"{x:,.0f}"
            except:
                return x

        tdf2["DemandTWh_f"] = tdf2["DemandTWh"].apply(fmt0)
        tdf2["PricePerMWh_f"] = tdf2["PricePerMWh"].apply(lambda x: f"{x:,.2f}" if x != "" else "")
        tdf2["RevenueBUSD_f"] = tdf2["RevenueBUSD"].apply(lambda x: f"{x:,.1f}" if x != "" else "")

        table = html.Table([
            html.Thead(html.Tr([
                html.Th("Scheme"), html.Th("Year"),
                html.Th("Demand (TWh)"),
                html.Th("VWAP Price / MWh"),
                html.Th("Revenue (USD bn)"),
            ], style={"textAlign":"center"})),
            html.Tbody([
                html.Tr([
                    html.Td(r["Scheme"], style={"textAlign":"center",
                                               "fontWeight":"700" if "TOTAL" in str(r["Scheme"]) else "400"}),
                    html.Td(r["Year"], style={"textAlign":"center"}),
                    html.Td(r["DemandTWh_f"], style={"textAlign":"center"}),
                    html.Td(r["PricePerMWh_f"], style={"textAlign":"center"}),
                    html.Td(r["RevenueBUSD_f"], style={"textAlign":"center"}),
                ]) for _, r in tdf2.iterrows()
            ])
        ], style={"width":"100%","fontSize":"12px","textAlign":"center"})

        return html.Div([
            card([dcc.Graph(figure=fig)]),
            html.Div(style={"height":"10px"}),
            card([html.H4("Revenue table (USD bn)"), table])
        ])

    return html.Div()

# MAP CLICK → auto-switch region + country
@app.callback(
    Output("region","value", allow_duplicate=True),
    Output("country","value", allow_duplicate=True),
    Input("country_map","clickData"),
    prevent_initial_call=True
)
def map_click(clickData):
    if clickData and "points" in clickData:
        loc = clickData["points"][0].get("location")
        if loc in COUNTRY_REGION:
            return COUNTRY_REGION[loc], loc
        return "Global", loc
    return no_update, no_update

if __name__ == "__main__":
    if hasattr(app, "run"):
        app.run(debug=True)
    else:
        app.run_server(debug=True)
