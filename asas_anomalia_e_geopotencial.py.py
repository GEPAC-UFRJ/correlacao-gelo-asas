import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np
import matplotlib.cm as cm

# Projeto PIBIC: VARIABILIDADE DO ASAS

# ---------------------------------------------------------
# TERMINAL DE COMANDOS PARA INSTALAÇÃO DE BIBLIOTECAS
#pip install xarray matplotlib pandas numpy cartopy netCDF4


# 1. DEFINIÇÕES INICIAIS
# ---------------------------------------------------------
dominio_lat_min = -70
dominio_lat_max = 10
dominio_lon_min = -70
dominio_lon_max = 40

ano_ini = 1980
ano_fim = 2020

# Climatologia (1991-2020)
clim_ano_ini = 1991 
clim_ano_fim = 2020

# Limiar de 28
valor_borda_anomalia = 28 

# 2. ABRIR E RECORTAR DADOS

nome_arquivo = 'Dados_ic.nc'
try:
    ds = xr.open_dataset(nome_arquivo)
    print(f">>> Arquivo carregado com sucesso.")
except FileNotFoundError:
    print(f"ERRO: Arquivo não encontrado."); exit()

if ds.latitude.values[0] > ds.latitude.values[-1]:
    
    lat_caixa = slice(0, -45)
    ds_asas = ds.sel(latitude=slice(dominio_lat_max, dominio_lat_min), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))
else:
    
    lat_caixa = slice(-45, 0)
    ds_asas = ds.sel(latitude=slice(dominio_lat_min, dominio_lat_max), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))

lon_caixa = slice(-45, 10)
ds_asas = ds_asas.sel(valid_time=slice(str(ano_ini), str(ano_fim)))


# 3. CÁLCULO DA CLIMATOLOGIA 

print(f">>> Calculando a Climatologia (1991-2020)...")
ds_clim = ds_asas.sel(latitude=lat_caixa, longitude=lon_caixa)
ds_clim = ds_clim.sel(valid_time=slice(str(clim_ano_ini), str(clim_ano_fim)))

climatologia_mensal = ds_clim.groupby('valid_time.month').mean('valid_time')

chao_fixo_por_mes = {}
for mes in range(1, 13):
    media_espacial = float(climatologia_mensal.sel(month=mes).z.mean())
    chao_fixo_por_mes[mes] = media_espacial / 10


# GERAR OS MAPAS DA CLIMATOLOGIA

print(f">>> Gerando mapas da climatologia mensal (12 mapas)...")
pasta_climatologia = 'figuras_climatologia_mensal'
os.makedirs(pasta_climatologia, exist_ok=True)

ds_clim_mapa = ds_asas.sel(valid_time=slice(str(clim_ano_ini), str(clim_ano_fim)))
climatologia_mensal_mapa = ds_clim_mapa.groupby('valid_time.month').mean('valid_time')

for mes in range(1, 13):
    fig_c, ax_c = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})
    ax_c.set_extent([dominio_lon_min, dominio_lon_max, dominio_lat_min, dominio_lat_max], crs=ccrs.PlateCarree())
    ax_c.coastlines(resolution='50m', color='black', linewidth=1.0)

    mapa_clim_mes = (climatologia_mensal_mapa.sel(month=mes).z / 10).squeeze()

    plot_c = mapa_clim_mes.plot.contourf(ax=ax_c, transform=ccrs.PlateCarree(),
                                         levels=20, cmap='YlOrRd', add_colorbar=True,
                                         cbar_kwargs={'label': 'Geopotencial 850 hPa (mgp)', 'orientation': 'horizontal', 'pad': 0.08, 'aspect': 40})

    ax_c.set_title(f'Climatologia Média ({clim_ano_ini}-{clim_ano_fim}) - Mês: {mes:02d}', fontweight='bold')
    plt.savefig(f"{pasta_climatologia}/climatologia_mes_{mes:02d}.png", dpi=100, bbox_inches='tight')

    fig_c.clf()
    plt.close('all')
print(f"    [OK] Mapas da climatologia salvos.")


# 4. PASTAS E LISTAS DOS DADOS

pasta_resultados = 'figuras_metodo_pedro'
os.makedirs(pasta_resultados, exist_ok=True)

dados_csv_anomalia = []
dados_csv_geopotencial = []

print(f">>> Iniciando processamento dos mapas de anomalia e planilhas...")


# 5. LOOP PRINCIPAL

for i, t in enumerate(ds_asas.valid_time):
    mapa_bruto = ds_asas.sel(valid_time=t).squeeze()
    mes_atual = int(t.dt.month)
    data_str = str(t.values)[:10]

    mapa_geo_mgp = mapa_bruto.z / 10

    mapa_geo_caixa = mapa_geo_mgp.sel(latitude=lat_caixa, longitude=lon_caixa)
    geo_max = float(mapa_geo_caixa.max())
    loc_max_geo = mapa_geo_caixa.where(mapa_geo_caixa == geo_max, drop=True)

    if loc_max_geo.count() > 0:
        lat_nucleo_geo = float(loc_max_geo.latitude.mean())
        lon_nucleo_geo = float(loc_max_geo.longitude.mean())
    else:
        lat_nucleo_geo, lon_nucleo_geo = np.nan, np.nan

    dados_csv_geopotencial.append([data_str, lat_nucleo_geo, lon_nucleo_geo])

    # ANOMALIA E BORDAS
    chao_do_mes = chao_fixo_por_mes[mes_atual]
    mapa_anomalia = mapa_geo_mgp - chao_do_mes

    mapa_para_borda = mapa_anomalia.sel(longitude=slice(-60, dominio_lon_max))
    mascara_borda = mapa_para_borda.where(mapa_para_borda >= valor_borda_anomalia, drop=True)

    if mascara_borda.count() > 0:
        lat_norte = float(mascara_borda.latitude.max())
        lat_sul = float(mascara_borda.latitude.min())
        lon_leste = float(mascara_borda.longitude.max())
        lon_oeste = float(mascara_borda.longitude.min())

        mapa_anom_caixa = mapa_anomalia.sel(latitude=lat_caixa, longitude=lon_caixa)
        anomalia_max = float(mapa_anom_caixa.max())
        loc_max_anom = mapa_anom_caixa.where(mapa_anom_caixa == anomalia_max, drop=True)

        lat_nucleo_anom = float(loc_max_anom.latitude.mean())
        lon_nucleo_anom = float(loc_max_anom.longitude.mean())
    else:
        lat_norte, lat_sul, lon_leste, lon_oeste, lat_nucleo_anom, lon_nucleo_anom, anomalia_max = [np.nan]*7
    
    dados_csv_anomalia.append([data_str, lat_norte, lat_sul, lon_leste, lon_oeste])

    # GERAÇÃO DO MAPA VISUAL

    fig, ax1 = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})

    ax1.set_extent([dominio_lon_min, dominio_lon_max, dominio_lat_min, dominio_lat_max], crs=ccrs.PlateCarree())
    ax1.coastlines(resolution='50m', color='black', linewidth=1.0)
    ax1.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='gray')
    gl = ax1.gridlines(draw_labels=True, linestyle=':', color='gray', alpha=0.5)
    gl.top_labels = gl.right_labels = False

    vmin = float(mapa_anomalia.min())
    vmax = float(mapa_anomalia.max())
    niveis = np.arange(np.floor(vmin/10)*10, np.ceil(vmax/10)*10 + 10, 10)

    estilos_linha = ['dashed' if v < 0 else 'solid' for v in niveis]

    cont_anomalia = mapa_anomalia.plot.contour(ax=ax1, transform=ccrs.PlateCarree(),
                                               levels=niveis, cmap='jet',
                                               linewidths=1.0, linestyles=estilos_linha)

    ax1.clabel(cont_anomalia, inline=True, fontsize=7, fmt='%1.0f')

    norm = plt.Normalize(vmin=niveis.min(), vmax=niveis.max())
    sm = cm.ScalarMappable(norm=norm, cmap='jet')
    sm.set_array([])

    cbar = plt.colorbar(sm, ax=ax1, orientation='horizontal', pad=0.08, aspect=40, ticks=niveis)
    cbar.set_label('Anomalia Geopotencial 850 hPa', fontweight='bold')
    cbar.ax.tick_params(rotation=45)

    ax1.set_title(f'Geopotencial 850 hPa - Anomalia ASAS\nData: {data_str}', fontweight='bold')

    plt.savefig(f"{pasta_resultados}/mapa_{data_str}.png", dpi=100, bbox_inches='tight')

    fig.clf()
    plt.close('all')

    if (i + 1) % 12 == 0:
        print(f"   [OK] Ano {data_str[:4]} finalizado.")

# SALVAR AS DUAS PLANILHAS CSV

print(f"\n>>> Salvando planilhas...")
colunas_anomalia = ["Data", "Borda_Norte", "Borda_Sul", "Borda_Leste", "Borda_Oeste"]
df_anomalia = pd.DataFrame(dados_csv_anomalia, columns=colunas_anomalia)
df_anomalia.to_csv('resultados_anomalia_28.csv', index=False)

colunas_geo = ["Data", "Lat_Nucleo_Geopotencial", "Lon_Nucleo_Geopotencial"]
df_geo = pd.DataFrame(dados_csv_geopotencial, columns=colunas_geo)
df_geo.to_csv('resultados_geopotencial.csv', index=False)

print(f">>> PROCESSAMENTO CONCLUÍDO COM SUCESSO!")