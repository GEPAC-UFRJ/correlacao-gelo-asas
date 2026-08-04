import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np
from scipy.ndimage import label


# 1. DEFINIÇÕES INICIAIS

dominio_lat_min, dominio_lat_max = -70, 10
dominio_lon_min, dominio_lon_max = -70, 40

ano_ini, ano_fim = 1980, 2020
clim_ano_ini, clim_ano_fim = 1991, 2020

valor_borda_anomalia = 22 

lon_caixa = slice(-45, 10)
lat_caixa = slice(0, -45)


# 2. ABRIR E RECORTAR DADOS

nome_arquivo = "Dados_ic.nc"
try:
    ds = xr.open_dataset(nome_arquivo).squeeze(drop=True)
    print(">>> Arquivo carregado com sucesso.")
except FileNotFoundError:
    print("ERRO: Arquivo não encontrado.")
    exit()

# Ajuste de Longitude e Latitude
if ds.longitude.max() > 180:
    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
    ds = ds.sortby('longitude')

if ds.latitude.values[0] > ds.latitude.values[-1]:
    lat_caixa = slice(0, -45)
    ds_asas = ds.sel(latitude=slice(dominio_lat_max, dominio_lat_min), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))
else:
    lat_caixa = slice(-45, 0)
    ds_asas = ds.sel(latitude=slice(dominio_lat_min, dominio_lat_max), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))

ds_asas = ds_asas.sel(valid_time=slice(str(ano_ini), str(ano_fim)))


# 3. CÁLCULO DA CLIMATOLOGIA  (SUN ET AL.)

print(">>> Calculando a Climatologia Média Anual (1991-2020)...")
ds_clim = ds_asas.z.sel(latitude=lat_caixa, longitude=lon_caixa)
ds_clim = ds_clim.sel(valid_time=slice(str(clim_ano_ini), str(clim_ano_fim)))

climatologia_anual = ds_clim.mean('valid_time')
chao_fixo_unico = float(climatologia_anual.mean())

print("="*60)
print(f"VALOR DO CHÃO FIXO (Referência Sun et al.): {chao_fixo_unico / 9.80665:.2f} gpm")
print("="*60)

# GERAR O MAPA DA CLIMATOLOGIA

print(">>> Gerando mapa da climatologia anual...")
pasta_climatologia = 'figuras_climatologia_anual'
os.makedirs(pasta_climatologia, exist_ok=True)

fig_c, ax_c = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})

ax_c.set_extent([-45, 10, -45, 0], crs=ccrs.PlateCarree())

ax_c.add_feature(cfeature.LAND, facecolor='lightgray')
ax_c.coastlines(resolution='50m', color='black', linewidth=1.0)
ax_c.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='gray')

plot_c = (climatologia_anual / 9.80665).plot.contourf(ax=ax_c, transform=ccrs.PlateCarree(),
                                         levels=20, cmap='YlOrRd', add_colorbar=True,
                                         cbar_kwargs={'label': 'Geopotencial 850 hPa (gpm)', 'orientation': 'horizontal', 'pad': 0.08, 'aspect': 40})

ax_c.set_title(f'Climatologia Média Anual ({clim_ano_ini}-{clim_ano_fim})', fontweight='bold')

gl = ax_c.gridlines(draw_labels=True, linestyle='--', color='gray', alpha=0.5)
gl.top_labels = gl.right_labels = False

plt.savefig(f"{pasta_climatologia}/climatologia_anual.png", dpi=100, bbox_inches='tight')
plt.close('all')
print("    [OK] Mapa da climatologia salvo.")

# 4. PROCESSAMENTO MENSAL E BORDAS

pasta_resultados = 'figuras_asas_isolinha_22'
os.makedirs(pasta_resultados, exist_ok=True)
dados_csv_anomalia = []

print(">>> Iniciando processamento dos mapas de anomalia (Isolinha 22)...")

for i, t in enumerate(ds_asas.valid_time):
    mapa_bruto = ds_asas.z.sel(valid_time=t)
    data_str = str(t.values)[:10]

    mapa_anomalia = (mapa_bruto - chao_fixo_unico) / 9.80665
    mapa_recorte = mapa_anomalia.sel(latitude=lat_caixa, longitude=lon_caixa)

    anomalia_max = float(mapa_recorte.max())
    loc_max = mapa_recorte.where(mapa_recorte == anomalia_max, drop=True)

    if loc_max.count() > 0:
        lat_nucleo = float(loc_max.latitude.mean())
        lon_nucleo = float(loc_max.longitude.mean())
    else:
        lat_nucleo, lon_nucleo = np.nan, np.nan

    mascara_binaria = mapa_recorte >= valor_borda_anomalia

    if int(mascara_binaria.sum()) > 0 and not np.isnan(lat_nucleo):
        ilhas_rotuladas, num_ilhas = label(mascara_binaria.values)
        
        distancias = []
        for j in range(1, num_ilhas + 1):
            coords_j = np.where(ilhas_rotuladas == j)
            lat_j = mapa_recorte.latitude.values[coords_j[0]].mean()
            lon_j = mapa_recorte.longitude.values[coords_j[1]].mean()
            dist = np.sqrt((lat_j - lat_nucleo)**2 + (lon_j - lon_nucleo)**2)
            distancias.append(dist)
            
        id_ilha_asas = np.argmin(distancias) + 1
        mask_asas = (ilhas_rotuladas == id_ilha_asas)
        coords_asas = np.where(mask_asas)
        
        lat_norte = float(mapa_recorte.latitude.values[coords_asas[0]].max())
        lat_sul = float(mapa_recorte.latitude.values[coords_asas[0]].min())
        lon_leste = float(mapa_recorte.longitude.values[coords_asas[1]].max())
        lon_oeste = float(mapa_recorte.longitude.values[coords_asas[1]].min())
    else:
        lat_norte, lat_sul, lon_leste, lon_oeste = [np.nan]*4

    # Salvando no CSV 
    dados_csv_anomalia.append([
        data_str, anomalia_max, lat_norte, lat_sul, lon_leste, lon_oeste
    ])

    # Plot do mapa mensal
    fig, ax = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([dominio_lon_min, dominio_lon_max, dominio_lat_min, dominio_lat_max], crs=ccrs.PlateCarree())
    ax.coastlines(resolution='50m', color='black', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='gray')
    gl = ax.gridlines(draw_labels=True, linestyle=':', color='gray', alpha=0.5)
    gl.top_labels = gl.right_labels = False

    if int(mascara_binaria.sum()) > 0:
        cont = mapa_recorte.plot.contour(ax=ax, transform=ccrs.PlateCarree(), levels=[valor_borda_anomalia], colors=['red'], linewidths=2.5)
        ax.clabel(cont, fmt='%d', fontsize=10, colors='red')

    ax.set_title(f'Isolinha {valor_borda_anomalia} gpm - ASAS\n{data_str}', fontweight='bold')
    plt.savefig(f"{pasta_resultados}/mapa_{data_str}.png", dpi=100, bbox_inches='tight')
    plt.close()

    if (i + 1) % 12 == 0:
        print(f"    [OK] Ano {data_str[:4]} processado.")

# 5. SALVAR CSV 

colunas = ["data", "anomalia_max", "lat_norte", "lat_sul", "lon_leste", "lon_oeste"]
df_anomalia = pd.DataFrame(dados_csv_anomalia, columns=colunas)
arquivo_csv = os.path.join(pasta_resultados, "dados_anomalia_asas_iso22.csv")
df_anomalia.to_csv(arquivo_csv, index=False, encoding="utf-8")

print(f">>> CSV limpo salvo em: {arquivo_csv}")