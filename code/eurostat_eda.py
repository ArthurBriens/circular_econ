import eurostat
import matplotlib.pyplot as plt

# 1. Pull the data, filtered to France
df = eurostat.get_data_df(
    'CEI_PC034',
    filter_pars={'geo': ['FR']}
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
plt.ylabel('kg/hab')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Total waste generation (tonnes) — France
dft = eurostat.get_data_df(
    'env_wasgen',
    filter_pars={'geo': ['FR']}
)

dft_total = dft[
    (dft['unit'] == 'T') &
    (dft['hazard'] == 'HAZ_NHAZ') &
    (dft['nace_r2'] == 'TOTAL_HH') &
    (dft['waste'] == 'TOTAL')
]

year_cols = [c for c in dft_total.columns if str(c).isdigit()]
series_t = dft_total[year_cols].iloc[0]
series_t.index = series_t.index.astype(int)
series_t = series_t.sort_index().dropna()

plt.figure(figsize=(9, 5))
plt.plot(series_t.index, series_t.values / 1e6, marker='o', linewidth=2, color='steelblue')
plt.title('Total waste generation — France')
plt.xlabel('Year')
plt.ylabel('Million tonnes')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()