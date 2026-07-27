import pandas as pd
import matplotlib.pyplot as plt
import eurostat


df = pd.read_csv("data/raw/REP.csv")
print(df.annee.nunique())
print(f"{df.annee.min()} to {df.annee.max()}")

df_tlc = df[df['filiere'].isin(['TLC','BPS'])]
print(df_tlc.statut_prod.nunique())
# Précis sur les sous-catégories, pas beaucoup de granularité et quelques années tout de même

df_tlc_avg = df_tlc.groupby(['annee', 'filiere'], as_index=False)['tonnage'].mean()

df_piv = df_tlc_avg.pivot(index='annee', columns='filiere', values='tonnage').reset_index()
time = df_piv['annee']
fig, ax = plt.subplots(figsize=(4,5))
ax.plot(time, df_piv['TLC'], color='red', label = "code")
ax.plot(time, df_piv['BPS'], color='blue', label = "Boats")
# ax.plot(time, df_piv['VETEMENTS'], color='green', label = "Clothes")
ax.set_xticks(time)
ax.set_xticklabels(time.astype(int))
plt.legend()
plt.show()

# TRAITEMENTS REP
dft = pd.read_csv("data/traitements_REP.csv", sep=';')

dft_fr = dft[dft['filiere'].isin(['TLC', 'BPS']) & (dft['pays_site_trt'] == 'FR')]

dft_trt = dft_fr.groupby(['annee', 'filiere', 'typ_trt'], as_index=False)['masse'].sum()




filieres = ['TLC', 'BPS']
fig, axes = plt.subplots(1, len(filieres), figsize=(12, 5), sharey=False)
for ax, filiere in zip(axes, filieres):
    piv = (dft_trt[dft_trt['filiere'] == filiere]
           .pivot(index='annee', columns='typ_trt', values='masse')
           .fillna(0))
    ax.stackplot(piv.index, piv.T.values, labels=piv.columns)
    ax.set_title(filiere)
    ax.set_xlabel("Année")
    ax.set_xticks(piv.index)
    ax.legend(fontsize=7, loc='upper left')
axes[0].set_ylabel("Masse totale (tonnes)")
fig.suptitle("TLC & BPS traitements — France, par type de traitement")
plt.tight_layout()
plt.savefig('image1.png')

dft_simple = dft_fr.groupby(['annee', 'filiere'], as_index=False)['masse'].sum()
dft_piv2 = dft_simple.pivot(index='annee', columns='filiere', values='masse')

fig2, axes2 = plt.subplots(1, len(filieres), figsize=(12, 5), sharey=False)
for ax, filiere in zip(axes2, filieres):
    ax.plot(dft_piv2.index, dft_piv2[filiere], marker='o', color='steelblue')
    ax.set_title(filiere)
    ax.set_xlabel("Année")
    ax.set_xticks(dft_piv2.index)
    ax.set_ylabel("Masse totale (tonnes)")
fig2.suptitle("TLC & BPS traitements — France")
plt.tight_layout()
plt.savefig('image2.png')

# Eurostat — total waste generation France
dfe = eurostat.get_data_df('env_wasgen', filter_pars={'geo': ['FR']})
dfe_total = dfe[
    (dfe['unit'] == 'T') &
    (dfe['hazard'] == 'HAZ_NHAZ') &
    (dfe['nace_r2'] == 'TOTAL_HH') &
    (dfe['waste'] == 'TOTAL')
]
year_cols = [c for c in dfe_total.columns if str(c).isdigit()]
series_eu = dfe_total[year_cols].iloc[0]
series_eu.index = series_eu.index.astype(int)
series_eu = series_eu.sort_index().dropna()

fig3, ax3 = plt.subplots(figsize=(9, 5))
l1, = ax3.plot(series_eu.index, series_eu.values / 1e6, marker='o', linewidth=2, color='steelblue', label='Total waste (Eurostat)')
ax3.set_xlabel("Année")
ax3.set_ylabel("Million tonnes", color='steelblue')
ax3.tick_params(axis='y', labelcolor='steelblue')
ax3.grid(True, alpha=0.3)

ax3b = ax3.twinx()
l2, = ax3b.plot(dft_piv2.index, dft_piv2['TLC'], marker='s', linewidth=2, color='red', label='TLC')
l3, = ax3b.plot(dft_piv2.index, dft_piv2['BPS'], marker='^', linewidth=2, color='green', label='BPS')
ax3b.set_ylabel("Masse traitée (tonnes)", color='gray')
ax3b.tick_params(axis='y', labelcolor='gray')

ax3.legend(handles=[l1, l2, l3], loc='upper left')
ax3.set_title("Total waste generation & TLC/BPS traitements — France")
plt.tight_layout()
plt.savefig('image3.png')
