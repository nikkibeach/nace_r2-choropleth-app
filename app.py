"""My first Streamlit web app."""

from urllib.request import urlopen
import json
import eurostat
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


st.title(
    "Employment in technology and knowledge-intensive sectors by NUTS 2 "
    + "regions and sex (from 2008 onwards, NACE Rev. 2)"
)

st.caption("(Source: https://ec.europa.eu/eurostat/web/science-technology-innovation/)")

st.markdown(
    """This web application lets you explore employment data for the European
        high-tech industry by country and NUTS-1/NUTS-2 division. All data is
        sourced from Eurostat (`HTEC_EMP_REG2`) and licensed under the [Creative """
    + "Commons Attribution 4.0 International (CC BY 4.0) licence](https://creative"
    + """commons.org/licenses/by/4.0/ 'Creative Commons Attribution 4.0 International').
    For definitions of high-technology manufacturing and knowledge-intensive
    services, as well as information on the Nomenclature of Territorial Units for
    Statistics (NUTS) and the Statistical Classification of Economic Activities
    in the European Community (NACE Rev.2), feel free to consult Eurostat's glossary:
    [High-tech](https://ec.europa.eu/eurostat/statistics-explained/"""
    + "index.php?title=Glossary:High-tech)."
)


@st.experimental_memo
def load_df():
    """Load, clean and return eurostat's NACE data as a pandas `DataFrame`."""
    nace_df = eurostat.get_data_df("htec_emp_reg2")
    location_dict = eurostat.get_dic("geo")
    # Filter and clean data
    nace_df = nace_df[nace_df.nace_r2 == "HTC"]
    nace_df = nace_df.rename(columns={"geo\\time": "geo"})
    nace_df = nace_df.drop(columns=["nace_r2"])
    # Drop aggregates
    nace_df = nace_df[~nace_df.geo.isin(["EU27_2020", "EU28", "EU15", "EA19"])]
    # Unpivot data
    nace_df = pd.melt(nace_df, id_vars=["sex", "geo", "unit"], var_name="year")
    # Add location names
    nace_df["location"] = nace_df.geo.apply(lambda x: location_dict[x])
    # Rename column values
    nace_df.sex = nace_df.sex.str.replace("T", "C")
    nace_df.location = nace_df.location.str.replace(
        "Germany \(until 1990 former territory of the FRG\)", "Germany"
    )
    return nace_df


@st.experimental_memo
def load_geojson():
    """Load and return Eurostat's NUTS geometries."""
    api_requests = []
    # Request geometries for each NUTS level
    for i in range(3):
        url = (
            "https://raw.githubusercontent.com/eurostat/Nuts2json/master/pub/"
            + f"v2/2021/4326/20M/nutsrg_{i}.json"
        )
        with urlopen(url) as response:
            json_response = json.load(response)
            api_requests.append(json_response)
    # Combine geometries in single object
    nuts_geojson = api_requests[0]
    nuts_geojson["features"].extend(api_requests[1]["features"])
    nuts_geojson["features"].extend(api_requests[2]["features"])

    return nuts_geojson


@st.experimental_singleton
def update_df(nace_df, year, nuts, sex, unit):
    """Return `nace_df` changed according to user input."""
    nuts = ["Country", "NUTS-1", "NUTS-2"].index(nuts) + 2
    unit = "PC_EMP" if unit == "Rel." else "THS"
    nace_df = nace_df[
        (nace_df.year == year)
        & (nace_df.geo.str.len() == nuts)
        & (nace_df.sex == sex[0])
        & (nace_df.unit == unit)
    ]
    return nace_df


@st.experimental_singleton(show_spinner=False)
def draw_figure(nace_df, json_file):
    """Return `choropleth_mapbox` figure."""
    figure = go.Figure(
        px.choropleth_mapbox(
            data_frame=nace_df,
            geojson=json_file,
            featureidkey="properties.id",
            locations="geo",
            color="value",
            hover_name="location",
            opacity=0.4,
            zoom=4,
            center={"lat": 51.163361, "lon": 10.447683},
            mapbox_style="open-street-map",
        )
    )
    figure.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return figure


YEAR = st.slider("Year", 2008, 2021, value=2021)
col1, col2, col3 = st.columns([6, 3, 2])
NUTS = col1.select_slider(
    "Political Entity Level", ["Country", "NUTS-1", "NUTS-2"], value="NUTS-1"
)
SEX = col2.select_slider("Sex", ["Female", "Combined", "Male"], value="Combined")
UNIT = col3.select_slider("Frequency", ["Abs.", "Rel."], value="Rel.")


df = load_df()
updated_df = update_df(df, YEAR, NUTS, SEX, UNIT)
geojson = load_geojson()
fig = draw_figure(updated_df, geojson)


st.plotly_chart(
    fig,
    config={"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
)


col1, col2 = st.columns([7, 3])
show_df = col1.checkbox("Show DataFrame")
col2.markdown(
    "[View source code on GitHub](https://github.com/nikkibeach/nace_r2-choropleth-app)"
)
if show_df:
    st.write(updated_df.sort_values(by="value", ascending=False).reset_index(drop=True))

HIDE_STREAMLIT_STYLE = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(HIDE_STREAMLIT_STYLE, unsafe_allow_html=True)
