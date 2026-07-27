import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("data/raw/REP.csv")
df_avg = df.groupby(['annee', 'filiere'], as_index=False)['tonnage'].sum()
#df_avg['tonnage'] = np.log1p(df_avg['tonnage'])
df_piv = df_avg.pivot(index='annee', columns='filiere', values='tonnage').reset_index()

desc = df_piv.drop(columns='annee').describe().round(2)
desc.to_csv("output/table/df_piv_describe.csv")
print(desc)




acteur_count = df.groupby('filiere')['acteur'].nunique()
is_monopoly = acteur_count == 1

col_max = df_piv.drop(columns='annee').max()
q1, q3 = col_max.quantile(0.25), col_max.quantile(0.75)
keep_cols = col_max[col_max <= q3 + 1.5 * (q3 - q1)].index
keep_cols = keep_cols.drop(['TABAC', 'MNU'])
fig, ax = plt.subplots(figsize=(12, 6))
for col in keep_cols:
    ax.plot(df_piv['annee'], df_piv[col], marker='o', label=col)
ax.set_xlabel("Année")
ax.set_ylabel("log(Tonnage)")
ax.set_xticks(df_piv['annee'])
ax.set_xticklabels(df_piv['annee'].astype(int), rotation=45)
ax.legend(fontsize=7, bbox_to_anchor=(1.01, 1), loc='upper left')
plt.tight_layout()
plt.savefig('aggregate.png')

fig2, ax2 = plt.subplots(figsize=(12, 6))
for col in keep_cols:
    color = 'crimson' if is_monopoly[col] else 'steelblue'
    ax2.plot(df_piv['annee'], df_piv[col], marker='o', color=color)
    last_valid = df_piv[col].dropna()
    if not last_valid.empty:
        last_year = df_piv['annee'].iloc[last_valid.index[-1]]
        ax2.text(last_year + 0.1, last_valid.iloc[-1], col, fontsize=7, color=color, va='center')
ax2.set_xlabel("Année")
ax2.set_ylabel("Tonnage moyen")
ax2.set_xticks(df_piv['annee'])
ax2.set_xticklabels(df_piv['annee'].astype(int), rotation=45)
from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0], [0], color='crimson', marker='o', label='Monopole'),
    Line2D([0], [0], color='steelblue', marker='o', label='Compétition'),
]
ax2.legend(handles=legend_handles, loc='upper left')
ax2.set_title("Filieres REP — monopole vs. compétition")
plt.tight_layout()
plt.savefig('aggregate_monopoly1.png')


