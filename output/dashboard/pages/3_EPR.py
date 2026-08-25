"""
AUTHOR: abrie
DATE: 27/07/2026

                                   __
     ,                           ," e`--o
    ((                          (  | __,'
     \\~------------------------' \_;/
     (                             /
     /) .______________________.  )
    (( (                      (( (
     ``-'                      ``-'
"""

import streamlit as st
import pandas as pd

#DATA STUFF
#
#LOADING
df = pd.read_csv("data/raw/REP.csv")
df_actors = pd.read_excel("data/raw/Referentiels_MSM.xlsx", sheet_name="Acteurs")
df_filieres = pd.read_excel("data/raw/Referentiels_MSM.xlsx", sheet_name="Filieres")

#TREATMENT & CLEANING
acteur_count = df.groupby('filiere')['acteur'].nunique()
is_monopoly = acteur_count == 1

# Data for EPR analysis
df_epr = (
    df[['filiere', 'acteur']].drop_duplicates()
    .merge(df_actors, left_on='acteur', right_on='Acteur', how='left')
    .assign(is_monopoly=lambda x: x['filiere'].map(is_monopoly))
    .rename(columns={'filiere': 'code', 'acteur': 'actors', 'Acteur': 'ID'})
    [['code', 'actors', 'raison_sociale', 'ID', 'is_monopoly']]
)

df_chart1 = pd.merge(df_epr, df_filieres, how='left')
df_chart1 = df_chart1.drop(['actors', 'ID'], axis=1).rename(columns={'is_monopoly': 'Monopole', 'raison_sociale': 'Nom'})

df_chart2 = (
    df.groupby(['annee', 'filiere'], as_index=False)[['quantite', 'tonnage']].sum()
    .assign(is_monopoly=lambda x: x['filiere'].map(is_monopoly))
    .rename(columns={'quantite': 'total_quantity', 'tonnage': 'total_tonnage'})
    [['annee', 'filiere', 'total_quantity', 'total_tonnage', 'is_monopoly']]
)


#WEBSITE
st.write("""
Institute of Circular Economy -  France
""")


# EPR - list of eco-organisms by category
st.header("Éco-organismes par filière REP")

with st.sidebar:
    st.header("Filtres")
    selected_filieres = st.multiselect(
        "Filière",
        options=sorted(df_chart1['code'].unique()),
        default=[],
        placeholder="Toutes"
    )
    monopole_filter = st.selectbox(
        "Structure de marché",
        options=["Tous", "Monopole", "Compétition"]
    )
    chart_type = st.radio("Type de graphique", options=["Barres", "Lignes"])
    color_by = st.radio("Couleur par", options=["Filière", "Structure de marché"])

filtered = df_chart1.copy()
if selected_filieres:
    filtered = filtered[filtered['code'].isin(selected_filieres)]
if monopole_filter == "Monopole":
    filtered = filtered[filtered['Monopole']]
elif monopole_filter == "Compétition":
    filtered = filtered[~filtered['Monopole']]

st.dataframe(
    filtered[['code', 'libelle', 'Nom', 'Monopole']].reset_index(drop=True),
    use_container_width=True,
    column_config={
        'code': st.column_config.TextColumn('Code'),
        'libelle': st.column_config.TextColumn('Filière'),
        'Nom': st.column_config.TextColumn('Éco-organisme'),
        'Monopole': st.column_config.CheckboxColumn('Monopole'),
    }
)

# CHARTS
st.header("Tonnage par filière REP")

filtered_chart2 = df_chart2.copy()
if selected_filieres:
    filtered_chart2 = filtered_chart2[filtered_chart2['filiere'].isin(selected_filieres)]
if monopole_filter == "Monopole":
    filtered_chart2 = filtered_chart2[filtered_chart2['is_monopoly']]
elif monopole_filter == "Compétition":
    filtered_chart2 = filtered_chart2[~filtered_chart2['is_monopoly']]

color_col = 'filiere' if color_by == "Filière" else 'is_monopoly'
render_chart = st.bar_chart if chart_type == "Barres" else st.line_chart

chart_tonnage = filtered_chart2.pivot_table(index='annee', columns=color_col, values='total_tonnage', aggfunc='sum')
if color_col == 'is_monopoly':
    chart_tonnage = chart_tonnage.rename(columns={True: 'Monopole', False: 'Compétition'})
render_chart(chart_tonnage)

st.header("Quantité par filière REP")
chart_quantity = filtered_chart2.pivot_table(index='annee', columns=color_col, values='total_quantity', aggfunc='sum')
if color_col == 'is_monopoly':
    chart_quantity = chart_quantity.rename(columns={True: 'Monopole', False: 'Compétition'})
render_chart(chart_quantity)


# EXTRA INFORMATION
