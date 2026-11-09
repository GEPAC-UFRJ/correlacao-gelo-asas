#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Identifica os anos com menor e maior extensão de gelo em cada mês.
"""

import os
import pandas as pd

diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_entrada = os.path.join(diretorio_atual, 'saida_extensao_gelo_mwd_1980_2025.csv')
caminho_saida = os.path.join(diretorio_atual, 'extremos_gelo_mes_a_mes.csv')

try:
    df = pd.read_csv(caminho_entrada)
except FileNotFoundError:
    print(f'Arquivo não encontrado: {caminho_entrada}')
    raise SystemExit

if 'Extensão de Gelo (km²)' not in df.columns:
    if 'Área de Gelo (km²)' in df.columns:
        df = df.rename(columns={'Área de Gelo (km²)': 'Extensão de Gelo (km²)'})
    else:
        raise ValueError('A planilha precisa ter a coluna "Extensão de Gelo (km²)".')

nomes_meses = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
    5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
    9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

resultados = []
for mes_num in range(1, 13):
    df_mes = df[df['Mês'] == mes_num].copy()
    q20 = df_mes['Extensão de Gelo (km²)'].quantile(0.20)
    q80 = df_mes['Extensão de Gelo (km²)'].quantile(0.80)

    anos_q20 = (
        df_mes[df_mes['Extensão de Gelo (km²)'] <= q20]['Ano']
        .astype(int).tolist()
    )
    anos_q80 = (
        df_mes[df_mes['Extensão de Gelo (km²)'] >= q80]['Ano']
        .astype(int).tolist()
    )
    anos_q20.sort()
    anos_q80.sort()

    resultados.append({
        'Mes': nomes_meses[mes_num],
        'Anos_Gelo_Minimo (Q20)': anos_q20,
        'Anos_Gelo_Maximo (Q80)': anos_q80,
    })

df_extremos = pd.DataFrame(resultados)
print('\nEXTREMOS DE GELO POR MÊS (Q20 E Q80)')
print(df_extremos.to_string(index=False))

try:
    df_extremos.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
except PermissionError:
    raise PermissionError(f'Feche o arquivo antes de executar o script: {caminho_saida}')

print(f'Arquivo salvo em: {caminho_saida}')

# Resumo: separa os anos com menos gelo (Q20) e mais gelo (Q80) em cada mês.
