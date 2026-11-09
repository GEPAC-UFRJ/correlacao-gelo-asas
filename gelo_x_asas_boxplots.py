#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Boxplots das variáveis do ASAS nos anos de menor e maior gelo,
           com defasagens de 0 a 4 meses e teste de Mann-Whitney.
"""

import os
import ast
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu

pasta_projeto = os.path.dirname(os.path.abspath(__file__))
arquivo_asas = os.path.join(pasta_projeto, 'figuras_asas_isolinha_29', 'dados_anomalia_asas_iso29.csv')
arquivo_gelo = os.path.join(pasta_projeto, 'extremos_gelo_mes_a_mes.csv')
pasta_saida = os.path.join(pasta_projeto, 'boxplots_ondj_iso29_sig')
os.makedirs(pasta_saida, exist_ok=True)

print('Iniciando os boxplots de gelo e ASAS...')

df_asas = pd.read_csv(arquivo_asas)
df_asas['data'] = pd.to_datetime(df_asas['data'])
df_asas['ano'] = df_asas['data'].dt.year
df_asas['mes'] = df_asas['data'].dt.month

colunas_asas = ['anomalia_max', 'lat_norte', 'lat_sul', 'lon_leste', 'lon_oeste']
for coluna in colunas_asas:
    df_asas[coluna] = df_asas.groupby('mes')[coluna].transform(lambda x: x - x.mean())

df_gelo = pd.read_csv(arquivo_gelo)
meses = {'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4, 'Mai': 5, 'Jun': 6,
         'Jul': 7, 'Ago': 8, 'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12}
df_gelo['Mes'] = df_gelo['Mes'].map(meses)
df_gelo = df_gelo.melt(id_vars='Mes', var_name='Categoria', value_name='Anos')
df_gelo['Anos'] = df_gelo['Anos'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
df_gelo = df_gelo.explode('Anos').rename(columns={'Mes': 'mes', 'Anos': 'ano'})
df_gelo['categoria'] = df_gelo['Categoria'].map({
    'Anos_Gelo_Minimo (Q20)': 'Q20',
    'Anos_Gelo_Maximo (Q80)': 'Q80'
})
df_gelo = df_gelo.dropna(subset=['ano', 'categoria']).copy()
df_gelo['ano'] = df_gelo['ano'].astype(int)
df_gelo = df_gelo[df_gelo['mes'].isin([10, 11, 12, 1])]

variaveis_asas = {
    'anomalia_max': 'Anomalia da intensidade (gpm)',
    'lat_norte': 'Anomalia da borda norte (°)',
    'lat_sul': 'Anomalia da borda sul (°)',
    'lon_leste': 'Anomalia da borda leste (°)',
    'lon_oeste': 'Anomalia da borda oeste (°)'
}

plt.rcParams['font.family'] = 'DejaVu Serif'
dados_lags = []
resultados_testes = []

for lag in range(5):
    gelo_lag = df_gelo.copy()
    gelo_lag['mes_lag'] = gelo_lag['mes'] + lag
    gelo_lag['ano_lag'] = gelo_lag['ano'] + (gelo_lag['mes_lag'] - 1) // 12
    gelo_lag['mes_lag'] = (gelo_lag['mes_lag'] - 1) % 12 + 1

    dados = pd.merge(df_asas, gelo_lag, left_on=['ano', 'mes'],
                     right_on=['ano_lag', 'mes_lag'], how='inner',
                     suffixes=('_asas', '_gelo'))
    dados['Defasagem'] = lag
    dados_lags.append(dados)

    if dados.empty:
        print(f'Defasagem +{lag}: sem dados para os boxplots.')
        continue

    fig, eixos = plt.subplots(1, 5, figsize=(25, 6))
    fig.suptitle(f'Extremos de gelo (ONDJ) e anomalias do ASAS — defasagem +{lag} mês(es)',
                 fontsize=16, fontweight='bold')

    for eixo, (variavel, titulo) in zip(eixos, variaveis_asas.items()):
        grupo_q20 = dados.loc[dados['categoria'] == 'Q20', variavel].dropna()
        grupo_q80 = dados.loc[dados['categoria'] == 'Q80', variavel].dropna()

        if len(grupo_q20) > 5 and len(grupo_q80) > 5:
            estatistica, p_valor = mannwhitneyu(grupo_q20, grupo_q80, alternative='two-sided')
        else:
            estatistica, p_valor = np.nan, np.nan

        significativo = bool(np.isfinite(p_valor) and p_valor < 0.05)
        resultados_testes.append({
            'Defasagem': lag, 'Variavel': variavel,
            'N_Q20': len(grupo_q20), 'N_Q80': len(grupo_q80),
            'Estatistica_U': estatistica, 'Valor_p': p_valor,
            'Significativo_5porcento': significativo
        })

        sns.boxplot(data=dados, x='categoria', y=variavel, hue='categoria',
                    order=['Q20', 'Q80'], palette={'Q20': '#e28b6d', 'Q80': '#6ab187'},
                    legend=False, ax=eixo)
        sns.stripplot(data=dados, x='categoria', y=variavel, hue='categoria',
                      order=['Q20', 'Q80'], palette={'Q20': 'black', 'Q80': 'black'},
                      alpha=0.5, size=4, legend=False, ax=eixo)
        eixo.set_title(titulo, fontweight='bold')
        eixo.set_xlabel('Extremos de gelo (ONDJ)')
        eixo.set_ylabel(titulo)
        eixo.grid(True, linestyle='--', alpha=0.5, axis='y')
        eixo.axhline(0, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)

        if significativo:
            for borda in eixo.spines.values():
                borda.set_edgecolor('red')
                borda.set_linewidth(2.5)
            eixo.set_title(f'{titulo}\n(p = {p_valor:.3f})*', color='red', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f'boxplot_lag_{lag}_ondj_iso29.png'),
                dpi=300, bbox_inches='tight')
    plt.close(fig)

if dados_lags:
    dados_finais = pd.concat(dados_lags, ignore_index=True)
    colunas = ['Defasagem', 'categoria', 'ano_asas', 'mes_asas', *colunas_asas]
    dados_finais = dados_finais[colunas].copy()
    dados_finais = dados_finais.rename(columns={
        'categoria': 'Categoria', 'ano_asas': 'Ano_ASAS', 'mes_asas': 'Mes_ASAS'
    })
    dados_finais[colunas_asas] = dados_finais[colunas_asas].round(4)
    dados_finais.to_csv(os.path.join(pasta_saida, 'dados_consolidados_gelo_asas_ondj_iso29.csv'),
                        sep=';', index=False, encoding='utf-8-sig')

pd.DataFrame(resultados_testes).to_csv(
    os.path.join(pasta_saida, 'tabela_significancia_boxplots_ondj_iso29.csv'),
    sep=';', index=False, encoding='utf-8-sig', float_format='%.6f'
)
print(f'Boxplots e tabela de significância salvos em: {pasta_saida}')

# Resumo: compara os anos de pouco e muito gelo com o ASAS nos meses seguintes.
