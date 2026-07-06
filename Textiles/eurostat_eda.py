import eurostat
import matplotlib.pyplot as plt

# 1. Pull the data, filtered to France
df = eurostat.get_data_df(
    'cei_pc040030',
    filter_pars={r'geo': ['FR']}
)

# 2. Reshape: keep only year columns, transpose so years are the index
year_cols = [c for c in df.columns if str(c).isdigit()]
series = df[year_cols].iloc[0]        # first (and only) row = France
series.index = series.index.astype(int)
series = series.sort_index().dropna()

# 3. Plot
plt.figure(figsize=(9, 5))
plt.plot(series.index, series.values, marker='o', linewidth=2)
plt.title('Waste generation per capita — France')
plt.xlabel('Year')
plt.ylabel('%')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()