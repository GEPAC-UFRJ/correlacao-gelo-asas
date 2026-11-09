#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Código complementar (isolinha 29): Joyce
Projeto: Variabilidade do Gelo Marinho Antártico e o ASAS
Laboratório: GEPAC/UFRJ
Descrição: Identificação mensal do ASAS e das suas bordas em 850 hPa.
"""

import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np
from scipy.ndimage import label

# Domínio dos mapas: 70°S a 10°N e 70°W a 40°E
dominio_lat_min, dominio_lat_max = -70, 10
dominio_lon_min, dominio_lon_max = -70, 40

ano_ini, ano_fim = 1980, 2025
clim_ano_ini, clim_ano_fim = 1991, 2020

valor_borda_anomalia = 29

# Região analisada: 45°S a 0° e 60°W a 10°E 
lat_caixa = slice(0, -45)
lon_caixa = slice(-60, 10)

pasta_resultados = "figuras_asas_isolinha_29"
os.makedirs(pasta_resultados, exist_ok=True)
os.makedirs("figuras_climatologia_anual", exist_ok=True)

# Abertura e recorte espacial dos dados
nome_arquivo = "Dados_ic.nc" if os.path.exists("Dados_ic.nc") else "Dados_ic (2).nc"

try:
    ds = xr.open_dataset(nome_arquivo).squeeze(drop=True)
except FileNotFoundError:
    print(f"ERRO: Arquivo {nome_arquivo} não encontrado.")
    raise SystemExit

if ds.longitude.max() > 180:
    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
    ds = ds.sortby("longitude")

ds_asas = ds.sel(
    latitude=slice(dominio_lat_max, dominio_lat_min),
    longitude=slice(dominio_lon_min, dominio_lon_max)
).sel(
    valid_time=slice(f"{ano_ini}-01-01", f"{ano_fim}-12-31")
).load()

# Média de referência de 1991 a 2020
ds_clim = ds_asas.z.sel(latitude=lat_caixa, longitude=lon_caixa)
ds_clim_ref = ds_clim.sel(valid_time=slice(f"{clim_ano_ini}-01-01", f"{clim_ano_fim}-12-31"))

climatologia_anual = ds_clim_ref.mean("valid_time")
chao_fixo_unico = float(climatologia_anual.mean())

print(f">>> Chão fixo único (1991-2020): {chao_fixo_unico / 9.80665:.2f} gpm")

# Salva mapa da climatologia base
fig_c, ax_c = plt.subplots(figsize=(10, 7), subplot_kw={"projection": ccrs.PlateCarree()})
ax_c.set_extent([-60, 10, -45, 0], crs=ccrs.PlateCarree())
ax_c.add_feature(cfeature.LAND, facecolor="lightgray")
ax_c.coastlines(resolution="50m", color="black", linewidth=1.0)
(climatologia_anual / 9.80665).plot.contourf(
    ax=ax_c, transform=ccrs.PlateCarree(), levels=20, cmap="YlOrRd",
    cbar_kwargs={"label": "Geopotencial 850 hPa (gpm)", "orientation": "horizontal", "pad": 0.08}
)
ax_c.set_title(f"Climatologia Média Anual ERA5 ({clim_ano_ini}-{clim_ano_fim})", fontweight="bold")
plt.savefig("figuras_climatologia_anual/climatologia_anual.png", dpi=100, bbox_inches="tight")
plt.close(fig_c)

dados_csv_anomalia = []

for t in ds_asas.valid_time:
    mapa_bruto = ds_asas.z.sel(valid_time=t)
    data_str = str(t.values)[:10]

    # Anomalia em metros geopotenciais
    mapa_anomalia = (mapa_bruto - chao_fixo_unico) / 9.80665
    mapa_recorte = mapa_anomalia.sel(latitude=lat_caixa, longitude=lon_caixa)

    # Identifica o centro pela anomalia máxima
    anomalia_max = float(mapa_recorte.max())
    loc_max = mapa_recorte.where(mapa_recorte == anomalia_max, drop=True)
    lat_nucleo = float(loc_max.latitude.mean()) if loc_max.count() > 0 else np.nan
    lon_nucleo = float(loc_max.longitude.mean()) if loc_max.count() > 0 else np.nan

    mascara_binaria = mapa_recorte >= valor_borda_anomalia

    # Separa as regiões acima de 29 gpm
    if int(mascara_binaria.sum()) > 0 and not np.isnan(lat_nucleo):
        ilhas_rotuladas, num_ilhas = label(mascara_binaria.values)

        distancias = [
            np.sqrt(
                (mapa_recorte.latitude.values[np.where(ilhas_rotuladas == j)[0]].mean() - lat_nucleo) ** 2 +
                (mapa_recorte.longitude.values[np.where(ilhas_rotuladas == j)[1]].mean() - lon_nucleo) ** 2
            )
            for j in range(1, num_ilhas + 1)
        ]

        # Escolhe a região mais próxima do núcleo
        coords_asas = np.where(ilhas_rotuladas == (np.argmin(distancias) + 1))

        # Extrai os limites Norte, Sul, Leste e Oeste
        lat_norte = float(mapa_recorte.latitude.values[coords_asas[0]].max())
        lat_sul = float(mapa_recorte.latitude.values[coords_asas[0]].min())
        lon_leste = float(mapa_recorte.longitude.values[coords_asas[1]].max())
        lon_oeste = float(mapa_recorte.longitude.values[coords_asas[1]].min())
    else:
        lat_norte, lat_sul, lon_leste, lon_oeste = [np.nan] * 4

    dados_csv_anomalia.append([
        data_str, anomalia_max, lat_norte, lat_sul, lon_leste, lon_oeste, lat_nucleo, lon_nucleo
    ])

    fig, ax = plt.subplots(figsize=(10, 7), subplot_kw={"projection": ccrs.PlateCarree()})
    ax.set_extent([dominio_lon_min, dominio_lon_max, dominio_lat_min, dominio_lat_max], crs=ccrs.PlateCarree())
    ax.coastlines(resolution="50m", color="black", linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linestyle=":", edgecolor="gray")

    if int(mascara_binaria.sum()) > 0:
        cont = mapa_recorte.plot.contour(
            ax=ax, transform=ccrs.PlateCarree(), levels=[valor_borda_anomalia],
            colors=["red"], linewidths=2.5
        )
        ax.clabel(cont, fmt="%d", fontsize=10, colors="red")

    if not np.isnan(lat_nucleo):
        ax.plot(
            lon_nucleo, lat_nucleo, marker="X", color="blue", markersize=9,
            markeredgewidth=1.5, transform=ccrs.PlateCarree()
        )

    ax.set_title(f"ASAS (Isolinha {valor_borda_anomalia} gpm) - {data_str}", fontweight="bold")
    plt.savefig(f"{pasta_resultados}/mapa_{data_str}.png", dpi=100, bbox_inches="tight")
    plt.close(fig)

# Salva a tabela mensal
df_anomalia = pd.DataFrame(dados_csv_anomalia, columns=[
    "data", "anomalia_max", "lat_norte", "lat_sul", "lon_leste", "lon_oeste", "lat_centro", "lon_centro"
])
arquivo_csv = os.path.join(pasta_resultados, "dados_anomalia_asas_iso29.csv")
df_anomalia.to_csv(arquivo_csv, index=False, encoding="utf-8")
print(f">>> Rastreamento finalizado. Tabela mensal: {arquivo_csv}")

# Resumo: identifica o núcleo e os limites mensais do ASAS e salva os mapas e o CSV.