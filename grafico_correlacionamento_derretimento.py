#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Correlações de Pearson entre a extensão de gelo no Mar de Weddell
           e as variáveis do ASAS, com defasagens de 0 a 4 meses.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import pearsonr

pasta_projeto = os.path.dirname(os.path.abspath(__file__))
arquivo_asas = os.path.join(pasta_projeto, 'figuras_asas_isolinha_29', 'dados_anomalia_asas_iso29.csv')
arquivo_gelo = os.path.join(pasta_projeto, 'saida_extensao_gelo_mwd_1980_2025.csv')
pasta_corr = os.path.join(pasta_projeto, 'resultados_correlacao_iso29')
pasta_ondj = os.path.join(pasta_projeto, 'resultados_correlacao_reais_ondj')
os.makedirs(pasta_corr, exist_ok=True)
os.makedirs(pasta_ondj, exist_ok=True)

meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
meses_ondj = [10, 11, 12, 1]
nomes_ondj = ['Out', 'Nov', 'Dez', 'Jan']
variaveis_asas = {
    'anomalia_max': 'Intensidade máxima (gpm)',
    'lat_norte': 'Borda norte (°)',
    'lat_sul': 'Borda sul (°)',
    'lon_leste': 'Borda leste (°)',
    'lon_oeste': 'Borda oeste (°)'
}

print('Iniciando as correlações entre gelo e ASAS...')
df_asas = pd.read_csv(arquivo_asas)
df_asas['data'] = pd.to_datetime(df_asas['data'])
df_asas['ano'] = df_asas['data'].dt.year
df_asas['mes'] = df_asas['data'].dt.month

df_gelo = pd.read_csv(arquivo_gelo).rename(columns={
    'Ano': 'ano', 'Mês': 'mes', 'Extensão de Gelo (km²)': 'gelo',
    'Área de Gelo (km²)': 'gelo'
})
for coluna in ['ano', 'mes', 'gelo']:
    df_gelo[coluna] = pd.to_numeric(df_gelo[coluna], errors='coerce')
df_gelo = df_gelo.dropna(subset=['ano', 'mes', 'gelo']).copy()
df_gelo[['ano', 'mes']] = df_gelo[['ano', 'mes']].astype(int)

# Mantém o período de correlação dos arquivos anteriores (1980 a 2020).
df_asas = df_asas[df_asas['ano'].between(1980, 2020)].copy()
df_base = df_asas.merge(df_gelo[['ano', 'mes', 'gelo']], on=['ano', 'mes'], how='inner')


def calcular_correlacao(variavel, mes, lag):
    inicio = df_base.loc[df_base['mes'] == mes, ['ano', 'gelo']]
    mes_destino = (mes + lag - 1) % 12 + 1
    ajuste_ano = (mes + lag - 1) // 12
    destino = df_asas.loc[df_asas['mes'] == mes_destino, ['ano', variavel]].copy()
    destino['ano'] = destino['ano'] - ajuste_ano
    pares = inicio.merge(destino, on='ano', how='inner').dropna(subset=['gelo', variavel])
    pares = pares[np.isfinite(pares['gelo']) & np.isfinite(pares[variavel])]
    if len(pares) < 6 or pares['gelo'].nunique() < 2 or pares[variavel].nunique() < 2:
        return np.nan, np.nan, len(pares)
    r, p = pearsonr(pares['gelo'], pares[variavel])
    return float(r), float(p), len(pares)


def criar_painel(resultados, nomes, titulo, arquivo_saida, lags):
    colunas = 3 if len(lags) == 5 else 2
    linhas = 2
    fig, eixos = plt.subplots(linhas, colunas,
                              figsize=(18, 10) if colunas == 3 else (14, 10), dpi=300)
    fig.suptitle(titulo, fontsize=17, fontweight='bold', y=0.96)
    eixos = eixos.flatten()

    legenda = [
        mpatches.Patch(color='#D62728', label='Correlação positiva'),
        mpatches.Patch(color='#4C72B0', label='Correlação negativa'),
        mpatches.Patch(facecolor='none', edgecolor='none', label='* p < 0,05')
    ]

    for i, lag in enumerate(lags):
        eixo = eixos[i]
        correlacoes = np.asarray(resultados[lag]['corr'], dtype=float)
        p_valores = resultados[lag]['pval']
        cores = ['#D62728' if r > 0 else '#4C72B0' for r in correlacoes]
        barras = eixo.bar(nomes, correlacoes, width=0.6, color=cores,
                          edgecolor='black', linewidth=1.2)
        eixo.axhline(0, color='black', linewidth=1.2)

        for barra, p in zip(barras, p_valores):
            if np.isfinite(p) and p < 0.05:
                altura = barra.get_height()
                eixo.text(barra.get_x() + barra.get_width() / 2,
                          altura + (0.02 if altura >= 0 else -0.02), '*',
                          ha='center', va='bottom' if altura >= 0 else 'top',
                          fontsize=14, fontweight='bold')

        valores_validos = correlacoes[np.isfinite(correlacoes)]
        maior = np.max(np.abs(valores_validos)) if len(valores_validos) else 0
        limite = max(0.4, float(maior) + 0.15) if maior > 0.4 else 0.4
        eixo.set_ylim(-limite, limite)
        eixo.set_title(f'Defasagem +{lag} mês(es)', fontweight='bold', loc='left')
        eixo.grid(axis='y', linestyle=':', alpha=0.7)
        if i == 0:
            eixo.legend(handles=legenda, loc='upper right', frameon=False, fontsize=9)

    for eixo in eixos[len(lags):]:
        eixo.axis('off')
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(arquivo_saida, bbox_inches='tight')
    plt.close(fig)


resultados_tabela = []
resultado_intensidade_ondj = {}

for variavel, titulo in variaveis_asas.items():
    resultados_geral = {}
    resultados_ondj = {}

    for lag in range(5):
        correlacoes, valores_p = [], []
        for mes in range(1, 13):
            r, p, n = calcular_correlacao(variavel, mes, lag)
            correlacoes.append(r)
            valores_p.append(p)
            resultados_tabela.append({
                'Variavel_ASAS': variavel, 'Mes_gelo': meses_nomes[mes - 1],
                'Defasagem_meses': lag, 'Correlacao_Pearson': r,
                'Valor_p': p, 'Pares_validos': n
            })

        resultados_geral[lag] = {'corr': correlacoes, 'pval': valores_p}
        indices_ondj = [9, 10, 11, 0]
        resultados_ondj[lag] = {
            'corr': [correlacoes[i] for i in indices_ondj],
            'pval': [valores_p[i] for i in indices_ondj]
        }

    criar_painel(resultados_geral, meses_nomes,
                 f'Correlação entre gelo e ASAS — {titulo}',
                 os.path.join(pasta_corr, f'painel_corr_geral_{variavel}.png'), range(5))
    criar_painel(resultados_ondj, nomes_ondj,
                 f'Correlação ONDJ entre gelo e ASAS — {titulo}',
                 os.path.join(pasta_corr, f'painel_corr_ondj_{variavel}.png'), range(5))

    if variavel == 'anomalia_max':
        resultado_intensidade_ondj = resultados_ondj

pd.DataFrame(resultados_tabela).to_csv(
    os.path.join(pasta_corr, 'tabela_correlacoes_gelo_asas.csv'),
    index=False, sep=';', encoding='utf-8-sig', float_format='%.6f'
)

tabela_ondj = pd.DataFrame({'Mes': nomes_ondj})
for lag in range(4):
    tabela_ondj[f'Correlacao_Defasagem_{lag}'] = resultado_intensidade_ondj[lag]['corr']
    tabela_ondj[f'Valor_p_Defasagem_{lag}'] = resultado_intensidade_ondj[lag]['pval']
tabela_ondj.to_csv(os.path.join(pasta_ondj, 'tabela_correlacao_reais_lags0a3.csv'),
                   index=False, encoding='utf-8-sig', float_format='%.6f')

criar_painel(resultado_intensidade_ondj, nomes_ondj,
             'Correlação entre gelo (ONDJ) e intensidade do ASAS',
             os.path.join(pasta_ondj, 'painel_correlacao_ondj_2x2.png'), range(4))

print(f'Painéis e tabela de correlação salvos em: {pasta_corr}')
print(f'Painel específico de ONDJ salvo em: {pasta_ondj}')

# Resumo: relaciona o gelo de cada mês com o ASAS no mesmo mês e nos meses seguintes.
