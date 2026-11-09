#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Médias de DJF, MAM, JJA, SON e ONDJ e controle de meses ausentes.
"""

from pathlib import Path
import pandas as pd
import numpy as np

PASTA_PROJETO = Path(__file__).resolve().parent
ARQUIVO_ENTRADA = PASTA_PROJETO / 'figuras_asas_isolinha_29' / 'dados_anomalia_asas_iso29.csv'
PASTA_SAIDA = PASTA_PROJETO / 'subseries_sazonais'
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQUIVO_TABELA = PASTA_SAIDA / 'tabela_sazonal_asas.csv'
ARQUIVO_CONTROLE = PASTA_SAIDA / 'controle_lacunas_sazonais.csv'
ARQUIVO_RESUMO = PASTA_SAIDA / 'relatorio_estacoes_incompletas.csv'

MINIMO_MESES_VALIDOS = 2

VARIAVEIS = [
    'anomalia_max', 'lat_centro', 'lon_centro',
    'lat_norte', 'lat_sul', 'lon_leste', 'lon_oeste'
]

# DJF usa dezembro do ano anterior; ONDJ usa janeiro do ano seguinte.
ESTACOES = {
    'DJF': ((-1, 12), (0, 1), (0, 2)),
    'MAM': ((0, 3), (0, 4), (0, 5)),
    'JJA': ((0, 6), (0, 7), (0, 8)),
    'SON': ((0, 9), (0, 10), (0, 11)),
    'ONDJ': ((0, 10), (0, 11), (0, 12), (1, 1)),
}

COLUNAS_CONTROLE = [
    'Ano', 'Estacao', 'Variavel', 'Quantidade_meses_validos',
    'Quantidade_meses_previstos', 'Meses_previstos', 'Meses_com_valor',
    'Meses_sem_valor', 'Valores_mensais_disponiveis',
    'Valor_se_apenas_um_mes', 'Media_sazonal', 'Situacao',
]
COLUNAS_RESUMO = [
    'Ano', 'Estacao', 'Meses_previstos', 'Meses_sem_registro_no_CSV',
    'Variaveis_com_media_parcial', 'Variaveis_com_apenas_um_mes',
    'Variaveis_sem_nenhum_mes', 'Detalhe',
]


def texto_numero(valor):
    return format(float(valor), '.10g')


def executar():
    if not ARQUIVO_ENTRADA.is_file():
        raise FileNotFoundError(
            f'Arquivo mensal não encontrado: {ARQUIVO_ENTRADA}\n'
            'Execute o rastreamento do ASAS primeiro.'
        )

    df = pd.read_csv(ARQUIVO_ENTRADA, encoding='utf-8-sig')
    colunas_faltantes = [c for c in ['data', *VARIAVEIS] if c not in df.columns]
    if colunas_faltantes:
        raise ValueError(f'Colunas ausentes no CSV mensal: {colunas_faltantes}')
    if df.empty:
        raise ValueError('O CSV mensal está vazio.')

    df['data'] = pd.to_datetime(df['data'], errors='raise')
    df['mes_periodo'] = df['data'].dt.to_period('M')
    if df['mes_periodo'].duplicated().any():
        repetidos = df.loc[df['mes_periodo'].duplicated(keep=False), 'mes_periodo']
        raise ValueError(f'Encontrei meses duplicados: {repetidos.astype(str).tolist()[:10]}')

    for coluna in VARIAVEIS:
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce')

    ano_inicial = int(df['data'].dt.year.min())
    ano_final = int(df['data'].dt.year.max())
    anos = list(range(ano_inicial, ano_final + 1))
    por_mes = df.set_index('mes_periodo')

    linhas_tabela = []
    controle = []
    resumo_estacoes = []

    for ano in anos:
        linha = {'ano': ano}

        for estacao, definicao in ESTACOES.items():
            meses = [pd.Period(year=ano + deslocamento, month=mes, freq='M')
                     for deslocamento, mes in definicao]
            datas = [str(m) for m in meses]
            quantidade_esperada = len(meses)
            ausentes_no_csv = [str(m) for m in meses if m not in por_mes.index]

            parciais = []
            unicos = []
            zerados = []
            detalhes = []

            for nome_mensal in VARIAVEIS:
                valores = [(str(m), float(por_mes.loc[m, nome_mensal]))
                           for m in meses
                           if m in por_mes.index and pd.notna(por_mes.loc[m, nome_mensal])]
                qtd = len(valores)
                nome_coluna = f'{nome_mensal}_{estacao}'

                if qtd >= MINIMO_MESES_VALIDOS:
                    media = round(float(np.mean([v for _, v in valores])), 3)
                else:
                    media = np.nan

                linha[nome_coluna] = media

                if qtd == quantidade_esperada:
                    continue

                presentes = [m for m, _ in valores]
                faltantes = [m for m in datas if m not in presentes]

                if qtd >= MINIMO_MESES_VALIDOS:
                    situacao = 'Média parcial calculada'
                    parciais.append(nome_mensal)
                elif qtd == 1:
                    situacao = 'Somente 1 mês: sem média sazonal'
                    unicos.append(nome_mensal)
                else:
                    situacao = 'Nenhum mês válido: sem média sazonal'
                    zerados.append(nome_mensal)

                detalhes.append(f'{nome_mensal}: {qtd}/{quantidade_esperada}')
                controle.append({
                    'Ano': ano,
                    'Estacao': estacao,
                    'Variavel': nome_mensal,
                    'Quantidade_meses_validos': qtd,
                    'Quantidade_meses_previstos': quantidade_esperada,
                    'Meses_previstos': ', '.join(datas),
                    'Meses_com_valor': ', '.join(presentes),
                    'Meses_sem_valor': ', '.join(faltantes),
                    'Valores_mensais_disponiveis': ' | '.join(
                        f'{mes} = {texto_numero(valor)}' for mes, valor in valores
                    ),
                    'Valor_se_apenas_um_mes': valores[0][1] if qtd == 1 else np.nan,
                    'Media_sazonal': media,
                    'Situacao': situacao,
                })

            if detalhes:
                resumo_estacoes.append({
                    'Ano': ano,
                    'Estacao': estacao,
                    'Meses_previstos': ', '.join(datas),
                    'Meses_sem_registro_no_CSV': ', '.join(ausentes_no_csv),
                    'Variaveis_com_media_parcial': ', '.join(parciais),
                    'Variaveis_com_apenas_um_mes': ', '.join(unicos),
                    'Variaveis_sem_nenhum_mes': ', '.join(zerados),
                    'Detalhe': '; '.join(detalhes),
                })

        linhas_tabela.append(linha)

    tabela = pd.DataFrame(linhas_tabela)
    colunas_tabela = [
        'ano',
        *[f'{nome_mensal}_{estacao}' for estacao in ESTACOES
          for nome_mensal in VARIAVEIS],
    ]
    tabela = tabela.reindex(columns=colunas_tabela)
    relatorio = pd.DataFrame(controle, columns=COLUNAS_CONTROLE)
    resumo = pd.DataFrame(resumo_estacoes, columns=COLUNAS_RESUMO)

    # Esta tabela será usada no cálculo das tendências e correlações.
    tabela.to_csv(ARQUIVO_TABELA, sep=';', index=False, encoding='utf-8-sig')
    relatorio.to_csv(ARQUIVO_CONTROLE, sep=';', index=False, encoding='utf-8-sig')
    resumo.to_csv(ARQUIVO_RESUMO, sep=';', index=False, encoding='utf-8-sig')

    n_parciais = int((relatorio['Situacao'] == 'Média parcial calculada').sum())
    n_unicos = int((relatorio['Situacao'] == 'Somente 1 mês: sem média sazonal').sum())
    n_zero = int((relatorio['Situacao'] == 'Nenhum mês válido: sem média sazonal').sum())

    print('\nSubséries sazonais processadas.')
    print(f'Anos: {ano_inicial} a {ano_final}')
    print(f'Médias parciais (2 ou mais meses): {n_parciais}')
    print(f'Casos com apenas um mês (sem média): {n_unicos}')
    print(f'Casos sem nenhum mês válido: {n_zero}')
    print(f'Estações/anos com alguma lacuna: {len(resumo)}')
    print('\nArquivos gerados:')
    for tipo, arquivo in [
        ('TABELA PRINCIPAL PARA TENDÊNCIAS', ARQUIVO_TABELA),
        ('RELATÓRIO DETALHADO DE VARIÁVEIS', ARQUIVO_CONTROLE),
        ('RESUMO POR ESTAÇÃO E ANO', ARQUIVO_RESUMO),
    ]:
        print(f'  {tipo}\n    {arquivo} (existe: {arquivo.is_file()})')

    caso_1996 = tabela.loc[tabela['ano'] == 1996]
    if not caso_1996.empty:
        print('\nConferência de MAM/1996:')
        print(caso_1996[['ano', 'anomalia_max_MAM', 'lat_sul_MAM']].to_string(index=False))
    print('\nAs tendências usam os anos válidos, sem preencher as lacunas.')


if __name__ == '__main__':
    executar()

# Resumo: faz médias sazonais quando há pelo menos dois meses e registra as lacunas.
