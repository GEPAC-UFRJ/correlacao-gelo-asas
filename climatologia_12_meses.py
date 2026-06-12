import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np

# 1. DEFINIÇÕES INICIAIS
dominio_lat_min, dominio_lat_max = -70, 10
dominio_lon_min, dominio_lon_max = -70, 40

ano_ini, ano_fim = 1980, 2020
clim_ano_ini, clim_ano_fim = 1991, 2020

# Caixa de monitoramento 
lon_caixa = slice(-45, 10)
lat_caixa = slice(0, -45)

# 2. ABRIR E RECORTAR DADOS
nome_arquivo = r"C:\Users\Looh_\OneDrive\Documentos\GEPAC\correlacao-gelo-asas\Dados_ic.nc"
try:
    ds = xr.open_dataset(nome_arquivo).squeeze(drop=True)
    print(">>> Arquivo carregado com sucesso.")
except FileNotFoundError:
    print("ERRO: Arquivo não encontrado.")
    exit()

# Ajuste de Longitude (0-360 para -180 a 180)
if ds.longitude.max() > 180:
    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
    ds = ds.sortby('longitude')

# Ajuste de Latitude
if ds.latitude.values[0] > ds.latitude.values[-1]:
    lat_caixa = slice(0, -45)
    ds_asas = ds.sel(latitude=slice(dominio_lat_max, dominio_lat_min), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))
else:
    lat_caixa = slice(-45, 0)
    ds_asas = ds.sel(latitude=slice(dominio_lat_min, dominio_lat_max), 
                     longitude=slice(dominio_lon_min, dominio_lon_max))

ds_asas = ds_asas.sel(valid_time=slice(str(ano_ini), str(ano_fim)))

# 3. CÁLCULO DA CLIMATOLOGIA ANUAL (O CHÃO FIXO)
print(">>> Calculando a Climatologia Média Anual (1991-2020)...")
ds_clim = ds_asas.z.sel(latitude=lat_caixa, longitude=lon_caixa)
ds_clim = ds_clim.sel(valid_time=slice(str(clim_ano_ini), str(clim_ano_fim)))

climatologia_anual = ds_clim.mean('valid_time')
chao_fixo_unico = float(climatologia_anual.mean())

print("="*60)
print(f"VALOR DO CHÃO FIXO (Referência): {chao_fixo_unico / 9.80665:.2f} mgp")
print("="*60)

# 4. CÁLCULO DA ANOMALIA MÉDIA DOS 12 MESES
print(">>> Calculando a anomalia média para os 12 meses do ano...")
anomalia_total_mgp = (ds_asas.z - chao_fixo_unico) / 9.80665
anomalia_12_meses = anomalia_total_mgp.groupby('valid_time.month').mean('valid_time')

pasta_resultados = 'figuras_12_meses_isolinhas_20_30'
os.makedirs(pasta_resultados, exist_ok=True)
dados_tabela_meses = []

nomes_meses = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Marco', 4: 'Abril', 
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

# 5. LOOP SOBRE OS 12 MESES MÉDIOS
for mes in range(1, 13):
    mapa_mes_medio = anomalia_12_meses.sel(month=mes)
    mapa_recorte = mapa_mes_medio.sel(latitude=lat_caixa, longitude=lon_caixa)

    # Identificação do Pico Máximo
    anomalia_max = float(mapa_recorte.max())
    loc_max = mapa_recorte.where(mapa_recorte == anomalia_max, drop=True)

    if loc_max.count() > 0:
        lat_nucleo = float(loc_max.latitude.mean())
        lon_nucleo = float(loc_max.longitude.mean())
    else:
        lat_nucleo, lon_nucleo = np.nan, np.nan

    # Salva na lista da tabela
    dados_tabela_meses.append([
        mes, nomes_meses[mes], anomalia_max, lat_nucleo, lon_nucleo, ""
    ])

    # Plot do Mapa 
    fig, ax = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([dominio_lon_min, dominio_lon_max, dominio_lat_min, dominio_lat_max], crs=ccrs.PlateCarree())
    ax.coastlines(resolution='50m', color='black', linewidth=1.0)
    ax.add_feature(cfeature.BORDERS, linestyle=':', edgecolor='gray')
    gl = ax.gridlines(draw_labels=True, linestyle=':', color='gray', alpha=0.5)
    gl.top_labels = gl.right_labels = False

    # Fundo Colorido global
    sun_levels = np.arange(-45, 51, 5)
    fundo = mapa_mes_medio.plot.contourf(ax=ax, transform=ccrs.PlateCarree(), 
                                       levels=sun_levels, cmap='Spectral_r', extend='both',
                                       add_colorbar=False)

    # As Isolinhas de 20 a 30 para a metodologia
    niveis_isolinhas = np.arange(20, 31, 1) # Desenha todas
    niveis_rotulos = np.arange(20, 31, 2)   # Escreve o número só nas pares

    try:
        cont = mapa_mes_medio.plot.contour(ax=ax, transform=ccrs.PlateCarree(), 
                                         levels=niveis_isolinhas, colors='black', linewidths=1.2)
        
        rotulos = ax.clabel(cont, levels=niveis_rotulos, fmt='%d', fontsize=10, inline=True)
        for rotulo in rotulos:
            rotulo.set_fontweight('bold')
            
    except ValueError:
        pass

    plt.colorbar(fundo, ax=ax, orientation='horizontal', pad=0.08, aspect=40, label='Anomalia Geopotencial (mgp)')
    ax.set_title(f'Climatologia Média - {nomes_meses[mes]}\nIsolinhas de 20 a 30 gpm', fontweight='bold')
    
    nome_arquivo_figura = f"{pasta_resultados}/mapa_medio_{mes:02d}_{nomes_meses[mes]}.png"
    plt.savefig(nome_arquivo_figura, dpi=100, bbox_inches='tight')
    plt.close()

    print(f"    [OK] Média de {nomes_meses[mes]} plotada com isolinhas de 20 a 30.")


# 6. SALVAR A TABELA 
colunas = ["mes_numero", "mes_nome", "anomalia_max_media", "lat_nucleo", "lon_nucleo", "isolinha_que_fecha"]
df_meses = pd.DataFrame(dados_tabela_meses, columns=colunas)
arquivo_csv = os.path.join(pasta_resultados, "tabela_medias_mensais_analise.csv")
df_meses.to_csv(arquivo_csv, index=False, encoding="utf-8")

print(f"\n>>> Concluído! CSV e Figuras salvos em: {os.path.abspath(pasta_resultados)}")