import requests
import pandas as pd
import json

# EXPLORING CATALOG

BASE = "https://api.insee.fr/melodi"

catalog = requests.get(f"{BASE}/catalog/all").json()

df_catalog = pd.DataFrame([
    {
        "id": d["identifier"],
        "title_fr": next(t["content"] for t in d["title"] if t["lang"] == "fr"),
        "desc_fr":  next((x["content"] for x in d.get("description", []) if x["lang"] == "fr"), ""),
    }
    for d in catalog
])


# LOADING DATA
#DD_CNA_CONSO_MENAGES_PRODUITS   DS_ANTIPOL

data_id =  "DD_CNA_CONSO_MENAGES_PRODUITS"

api_url = f"https://api.insee.fr/melodi/data/{data_id}"

get_data = requests.get(api_url, verify= False)
data_from_net = get_data.content
data = json.loads(data_from_net)

# Extraction des informations du jeu de données
title = data['title']['fr']
identifier = data['identifier']

# Extraction des observations du jeu de données filtré, sur lesquelles on va boucler
observations = data['observations']
extracted_data = []

# Boucle de lecture des observations dans le json
for obs in observations:
    dimensions = obs['dimensions']

    # Suivant les jeux de données attributes est présent ou non
    if 'attributes' in obs:
        attributes = obs['attributes']
    else:
        attributes = None

    # Suivant les jeux de données value peut être absent
    if 'value' in obs['measures']['OBS_VALUE_NIVEAU']:
        measures = obs['measures']['OBS_VALUE_NIVEAU']['value']
    else:
        mesures = None

    # on rassemble tout dans un objet
    if 'attributes' in obs:
        combined_data = {**dimensions, **attributes, 'OBS_VALUE_NIVEAU': measures}
    else:
        combined_data = {**dimensions, 'OBS_VALUE_NIVEAU': measures}

    extracted_data.append(combined_data)

# Création d'un dataframe python
df = pd.DataFrame(extracted_data)

print(f'Jeu de données : {identifier} \nTitre : {title} ')
print(df)

#Moyen intéressant car cela se focalise sur la consommation plutôt que les dechets

