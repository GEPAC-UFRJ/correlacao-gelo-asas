#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Retira a tendência da intensidade do ASAS e identifica os quintis Q20 e Q80.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

pasta_projeto = Path(__file__).resolve().parent
arquivo_entrada = pasta_projeto / 'subseries_sazonais' / 'tabela_sazonal_asas.csv'
pasta_detrend = pasta_projeto / 'resultados_detrend'
pasta_quintis = pasta_projeto / 'resultados_quintis'
estacoes = ['DJF', 'MAM', 'JJA', 'SON', 'ONDJ']


def executar():
    if not arquivo_entrada.exists():
        raise FileNotFoundError(f'Tabela sazonal não encontrada: {arquivo_entrada}')

    dados = pd.read_csv(arquivo_entrada, sep=';', encoding='utf-8-sig')
    colunas = ['ano', *[f'anomalia_max_{estacao}' for estacao in estacoes]]
    faltantes = [col for col in colunas if col not in dados.columns]
    if faltantes:
        raise ValueError(f'Colunas não encontradas: {faltantes}')
    if dados.empty:
        raise ValueError('A tabela sazonal está vazia.')

    dados['ano'] = pd.to_numeric(dados['ano'], errors='raise').astype(int)
    if dados['ano'].duplicated().any():
        raise ValueError('Há anos repetidos na tabela sazonal.')
    dados = dados.sort_values('ano').reset_index(drop=True)

    pasta_detrend.mkdir(parents=True, exist_ok=True)
    pasta_quintis.mkdir(parents=True, exist_ok=True)

    series = pd.DataFrame({'ano': dados['ano']})
    anos_quintis = []
    limites_quintis = []
    controle = []
    linhas_txt = ['ANOS EXTREMOS DA INTENSIDADE DO ASAS — SÉRIES SEM TENDÊNCIA', '']

    for estacao in estacoes:
        intensidade = pd.to_numeric(dados[f'anomalia_max_{estacao}'], errors='coerce')
        validos = np.isfinite(intensidade.to_numpy(dtype=float))
        anos = dados.loc[validos, 'ano'].to_numpy(dtype=float)
        valores = intensidade.loc[validos].to_numpy(dtype=float)
        if len(valores) < 4:
            raise ValueError(f'{estacao}: são necessários pelo menos 4 anos válidos.')

        resultado = stats.theilslopes(valores, anos, 0.95)
        tendencia = resultado.intercept + resultado.slope * anos
        sem_tendencia = valores - tendencia

        series[f'intensidade_original_{estacao}'] = intensidade.to_numpy(dtype=float)
        series[f'tendencia_theil_sen_{estacao}'] = np.nan
        series[f'intensidade_sem_tendencia_{estacao}'] = np.nan
        series.loc[validos, f'tendencia_theil_sen_{estacao}'] = tendencia
        series.loc[validos, f'intensidade_sem_tendencia_{estacao}'] = sem_tendencia

        q20 = float(np.percentile(sem_tendencia, 20))
        q80 = float(np.percentile(sem_tendencia, 80))
        anos_q20 = sorted(int(ano) for ano in anos[sem_tendencia <= q20])
        anos_q80 = sorted(int(ano) for ano in anos[sem_tendencia >= q80])

        linhas_txt.extend([
            f'--- {estacao} ---', f'Mais fortes (Q80): {anos_q80}',
            f'Mais fracos (Q20): {anos_q20}', '',
        ])
        for ano in anos_q20:
            anos_quintis.append({'ano': ano, 'estacao': estacao, 'quintil': 'Q20'})
        for ano in anos_q80:
            anos_quintis.append({'ano': ano, 'estacao': estacao, 'quintil': 'Q80'})

        limites_quintis.append({
            'Estacao': estacao, 'Q20_gpm': q20, 'Q80_gpm': q80,
            'Quantidade_anos_validos': len(valores),
        })
        controle.append({
            'Estacao': estacao,
            'Quantidade_anos_validos': len(valores),
            'Anos_ausentes': ', '.join(map(str, dados.loc[~validos, 'ano'].tolist())),
            'Theil_Sen_gpm_por_ano': float(resultado.slope),
            'Theil_Sen_gpm_por_decada': float(resultado.slope * 10),
            'Limite_inferior_95_por_ano': float(resultado.low_slope),
            'Limite_superior_95_por_ano': float(resultado.high_slope),
        })
        print(f'{estacao}: {len(valores)} anos válidos, Q20={q20:.3f}, Q80={q80:.3f} gpm')

    series.to_csv(pasta_detrend / 'serie_intensidade_sem_tendencia.csv',
                  sep=';', index=False, encoding='utf-8-sig', float_format='%.8f')
    pd.DataFrame(controle).to_csv(pasta_detrend / 'controle_detrend.csv',
                                 sep=';', index=False, encoding='utf-8-sig', float_format='%.8f')
    pd.DataFrame(limites_quintis).to_csv(pasta_quintis / 'limites_quintis_asas.csv',
                                        sep=';', index=False, encoding='utf-8-sig', float_format='%.8f')
    pd.DataFrame(anos_quintis, columns=['ano', 'estacao', 'quintil']).to_csv(
        pasta_quintis / 'anos_extremos_quintis_asas.csv', sep=';', index=False,
        encoding='utf-8-sig')
    (pasta_quintis / 'anos_extremos_quintis_asas.txt').write_text(
        '\n'.join(linhas_txt), encoding='utf-8')

    print(f'Arquivos das séries sem tendência: {pasta_detrend}')
    print(f'Arquivos dos quintis: {pasta_quintis}')


if __name__ == '__main__':
    executar()

# Resumo: retira a tendência pelo Theil-Sen e separa os anos de intensidade mais alta e baixa.
