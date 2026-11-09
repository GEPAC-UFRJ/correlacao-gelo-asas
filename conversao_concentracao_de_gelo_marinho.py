#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Código original: Catharine
Adaptação: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Calcula a extensão mensal do gelo marinho no Mar de Weddell.
Referência: https://doi.org/10.26848/rbgf.v14.5.p2739-2754
Código de referência: https://drive.google.com/file/d/1p0OF4q_T0XRmLuTcFOII3MbUzWOC501A/view
"""

import os
import glob
import re
import xarray as xr
import pyproj
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def padronizar_variavel(ds):
    if 'F08_ICECON' not in ds.data_vars:
        variaveis = [var for var in ds.data_vars if 'ICECON' in var.upper()]
        if not variaveis:
            raise ValueError('Variável de concentração de gelo não encontrada no NetCDF.')
        ds = ds.rename({variaveis[0]: 'F08_ICECON'})

    if 'time' not in ds.coords:
        nome_arquivo = os.path.basename(ds.encoding.get('source', ''))
        data_arquivo = re.search(r'((?:19|20)\d{2})(0[1-9]|1[0-2])', nome_arquivo)
        if not data_arquivo:
            raise ValueError(f'Não foi possível identificar o ano e mês de {nome_arquivo}.')
        data = pd.Timestamp(int(data_arquivo.group(1)), int(data_arquivo.group(2)), 15)
        if 'time' in ds.dims:
            if ds.sizes['time'] != 1:
                raise ValueError(f'O arquivo {nome_arquivo} tem mais de um mês sem datas.')
            ds = ds.assign_coords(time=[data])
        else:
            ds = ds.expand_dims(time=[data])
    return ds


diretorio_atual = os.path.dirname(os.path.abspath(__file__))
pastas_nsidc = sorted(glob.glob(os.path.join(diretorio_atual, 'NSIDC-0079*')))
pastas_nsidc = [pasta for pasta in pastas_nsidc if os.path.isdir(pasta)]

if not pastas_nsidc:
    raise FileNotFoundError('Coloque a pasta NSIDC-0079 junto deste script.')

pasta_dados = pastas_nsidc[0]
arquivos_nc = sorted(glob.glob(os.path.join(pasta_dados, '**', '*.nc'), recursive=True))
if not arquivos_nc:
    raise FileNotFoundError(f'Nenhum arquivo NetCDF encontrado em {pasta_dados}.')

print(f'Arquivos NetCDF encontrados: {len(arquivos_nc)}')

g = xr.open_mfdataset(
    arquivos_nc,
    preprocess=padronizar_variavel,
    engine='netcdf4',
    combine='nested',
    concat_dim='time',
    coords='minimal',
    data_vars='minimal',
    compat='override'
)

g = g.sortby('time').sel(time=slice('1980-01-01', '2025-12-31'))
if g.sizes.get('time', 0) == 0:
    raise ValueError('Não foram encontrados dados de gelo entre 1980 e 2025.')

# Valores especiais do NSIDC não representam concentração de gelo.
g['F08_ICECON'] = g['F08_ICECON'].where(
    (g['F08_ICECON'] != 1.1) & (g['F08_ICECON'] != 1.2), np.nan
)

transformador = pyproj.Transformer.from_crs('EPSG:3412', 'EPSG:4326', always_xy=True)
x = g['x'].values
y = g['y'].values
xx, yy = np.meshgrid(x, y)
lon, lat = transformador.transform(xx, yy)
g = g.assign_coords(lon=(['y', 'x'], lon), lat=(['y', 'x'], lat))

# Recorte do Mar de Weddell usado nos dados do gelo.
lon_min, lon_max = -60, 0
lat_min, lat_max = -90, -30
g_area = g.where(
    (g.lon >= lon_min) & (g.lon <= lon_max) &
    (g.lat >= lat_min) & (g.lat <= lat_max), drop=True
)

concentracao = g_area['F08_ICECON']
maior_concentracao = float(concentracao.max(skipna=True).compute())
if not np.isfinite(maior_concentracao):
    raise ValueError('Não há concentrações de gelo válidas no recorte.')
if maior_concentracao > 1.01:
    raise ValueError('A concentração não está na escala de 0 a 1. Confira as unidades do NetCDF.')

n = 0.15
pixels_gelo = xr.where(concentracao > n, 1, 0)
numero_pixels = pixels_gelo.sum(dim=('x', 'y'))
meses_com_dados = concentracao.count(dim=('x', 'y')) > 0
extensao_km2 = (numero_pixels * 625).where(meses_com_dados).round()

dados = pd.DataFrame({
    'Ano': g['time'].dt.year.values,
    'Mês': g['time'].dt.month.values,
    'Extensão de Gelo (km²)': extensao_km2.values
})

if dados.duplicated(['Ano', 'Mês']).any():
    raise ValueError('Há meses duplicados nos arquivos NetCDF. Confira os arquivos da pasta NSIDC.')

# Inclui meses sem registro na tabela, deixando a extensão em branco.
meses_esperados = pd.MultiIndex.from_product(
    [range(1980, 2026), range(1, 13)], names=['Ano', 'Mês']
)
dados = dados.set_index(['Ano', 'Mês']).reindex(meses_esperados).reset_index()
media = dados['Extensão de Gelo (km²)'].mean()
dados['Diferença da Média (km²)'] = dados['Extensão de Gelo (km²)'] - media

caminho_saida = os.path.join(diretorio_atual, 'saida_extensao_gelo_mwd_1980_2025.csv')
dados.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
print(f'Tabela mensal salva em: {caminho_saida}')
print(f'Meses sem dados válidos: {dados["Extensão de Gelo (km²)"].isna().sum()}')

primeira_data = pd.to_datetime(g['time'].values[0]).strftime('%m/%Y')
fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.SouthPolarStereo()})
imagem = ax.pcolormesh(
    g_area['lon'], g_area['lat'], concentracao.isel(time=0) * 100,
    transform=ccrs.PlateCarree(), shading='auto', cmap='Blues'
)
plt.colorbar(imagem, ax=ax, orientation='vertical', label='Concentração de gelo (%)')
ax.add_feature(cfeature.LAND, color='lightgray')
ax.coastlines()
ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
ax.set_extent([-180, 180, -90, -39], crs=ccrs.PlateCarree())
ax.set_title(f'Concentração do gelo marinho — {primeira_data}')

caminho_mapa = os.path.join(diretorio_atual, 'concentracao_gelo_primeiro_mes.png')
plt.savefig(caminho_mapa, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'Mapa salvo em: {caminho_mapa}')

# Resumo: lê os arquivos de gelo, calcula a extensão mensal no Mar de Weddell
# e salva a tabela de 1980 a 2025 para as análises de extremos e correlações.
