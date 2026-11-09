#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Correlação entre as intensidades sazonais do ASAS após retirar a tendência.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

pasta_projeto = Path(__file__).resolve().parent
arquivo_series = pasta_projeto / 'resultados_detrend' / 'serie_intensidade_sem_tendencia.csv'
pasta_saida = pasta_projeto / 'resultados_correlacoes_estacoes'
pasta_tabelas = pasta_saida / 'tabelas_para_artigo'
pasta_figuras = pasta_saida / 'figuras_para_artigo'
pasta_controle = pasta_saida / 'controle_interno'


def montar_pares(dados, estacao_a, estacao_b, deslocamento=0):
    a = dados[['ano', f'intensidade_sem_tendencia_{estacao_a}']].copy()
    b = dados[['ano', f'intensidade_sem_tendencia_{estacao_b}']].copy()
    a.columns = ['ano_a', 'intensidade_a']
    b.columns = ['ano_b', 'intensidade_b']
    a['ano_referencia'] = a['ano_a'] + deslocamento
    b['ano_referencia'] = b['ano_b']
    pares = a.merge(b, on='ano_referencia', validate='one_to_one')
    pares = pares.dropna(subset=['intensidade_a', 'intensidade_b'])
    return pares.sort_values('ano_referencia').reset_index(drop=True)


def calcular_correlacao(pares):
    x = pares['intensidade_a'].to_numpy(dtype=float)
    y = pares['intensidade_b'].to_numpy(dtype=float)
    if len(pares) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    r, p = pearsonr(x, y)
    return float(r), float(p)


def plotar_correlacao(pares, estacao_a, estacao_b, titulo, destino, r, p):
    x = pares['intensidade_a'].to_numpy(dtype=float)
    y = pares['intensidade_b'].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(7.6, 6.1))
    ax.scatter(x, y, s=44, color='#356B9C', alpha=0.85,
               edgecolors='white', linewidth=0.5)
    if len(x) >= 3 and np.ptp(x) > 0 and np.ptp(y) > 0:
        inclinacao, intercepto = np.polyfit(x, y, 1)
        xx = np.linspace(x.min(), x.max(), 150)
        ax.plot(xx, inclinacao * xx + intercepto, color='#C7473E',
                linewidth=1.8, label='Ajuste linear')
        ax.legend(loc='best', fontsize=9)
    ax.set_xlabel(f'Intensidade de {estacao_a} sem tendência (gpm)')
    ax.set_ylabel(f'Intensidade de {estacao_b} sem tendência (gpm)')
    ax.set_title(titulo, fontsize=12, fontweight='bold')
    ax.text(0.03, 0.97, f'Pearson r = {r:.3f}\np = {p:.4f}\nn = {len(pares)}',
            transform=ax.transAxes, ha='left', va='top', fontsize=10,
            bbox={'facecolor': 'white', 'alpha': 0.9, 'edgecolor': '0.85'})
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(destino, dpi=300, bbox_inches='tight')
    plt.close(fig)


def executar():
    if not arquivo_series.exists():
        raise FileNotFoundError(
            f'Série sem tendência não encontrada: {arquivo_series}\n'
            'Execute primeiro detrend_tendencia_quintis.py.'
        )
    dados = pd.read_csv(arquivo_series, sep=';', encoding='utf-8-sig')
    estacoes = ['DJF', 'MAM', 'JJA', 'SON']
    colunas = ['ano', *[f'intensidade_sem_tendencia_{e}' for e in estacoes]]
    faltantes = [col for col in colunas if col not in dados.columns]
    if faltantes:
        raise ValueError(f'Colunas não encontradas: {faltantes}')
    dados['ano'] = pd.to_numeric(dados['ano'], errors='raise').astype(int)
    if dados['ano'].duplicated().any():
        raise ValueError('Há anos repetidos na série.')
    for coluna in colunas[1:]:
        dados[coluna] = pd.to_numeric(dados[coluna], errors='coerce')
    for pasta in (pasta_tabelas, pasta_figuras, pasta_controle):
        pasta.mkdir(parents=True, exist_ok=True)

    comparacoes = [
        ('SON', 'DJF', 1, 'SON do ano anterior x DJF do ano seguinte', 'son_djf'),
        ('MAM', 'JJA', 0, 'MAM x JJA do mesmo ano', 'mam_jja'),
    ]
    resultados = []
    for estacao_a, estacao_b, deslocamento, titulo, nome in comparacoes:
        pares = montar_pares(dados, estacao_a, estacao_b, deslocamento)
        r, p = calcular_correlacao(pares)
        resultados.append({
            'Comparacao': f'{estacao_a} x {estacao_b}',
            'Periodos_comparados': titulo,
            'Quantidade_pares': len(pares),
            'Correlacao_Pearson_r': r,
            'P_valor': p,
            'Significativo_5_porcento': bool(p < 0.05) if np.isfinite(p) else '',
            'Primeiro_ano_referencia': int(pares.ano_referencia.min()) if len(pares) else '',
            'Ultimo_ano_referencia': int(pares.ano_referencia.max()) if len(pares) else '',
        })
        pares.to_csv(pasta_controle / f'pares_{nome}.csv', sep=';', index=False,
                     encoding='utf-8-sig', float_format='%.8f')
        plotar_correlacao(pares, estacao_a, estacao_b, titulo,
                         pasta_figuras / f'correlacao_{nome}.png', r, p)

    # Comparação adicional para conferir a diferença entre anos consecutivos e iguais.
    pares_alt = montar_pares(dados, 'SON', 'DJF')
    r_alt, p_alt = calcular_correlacao(pares_alt)
    pd.DataFrame([{
        'Comparacao': 'SON x DJF',
        'Periodos_comparados': 'SON e DJF identificados pelo mesmo ano (não consecutivos)',
        'Quantidade_pares': len(pares_alt),
        'Correlacao_Pearson_r': r_alt,
        'P_valor': p_alt,
    }]).to_csv(pasta_controle / 'correlacao_alternativa_mesmo_ano.csv',
              sep=';', index=False, encoding='utf-8-sig', float_format='%.8f')

    tabela = pd.DataFrame(resultados)
    tabela.to_csv(pasta_tabelas / 'correlacoes_intensidade_sem_tendencia.csv',
                  sep=';', index=False, encoding='utf-8-sig', float_format='%.8f')
    print('\nCorrelações das intensidades do ASAS sem tendência:')
    print(tabela.to_string(index=False, float_format=lambda n: f'{n:.4f}'))
    print(f'Gráficos: {pasta_figuras}')
    print(f'Tabelas: {pasta_tabelas}')


if __name__ == '__main__':
    executar()

# Resumo: compara a intensidade entre estações usando Pearson, com a tendência removida.
