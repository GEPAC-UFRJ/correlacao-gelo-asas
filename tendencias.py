#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Autoria: Lorena Aragão
Referência: adaptação dos gráficos de tendência de Neres
Projeto: Influência da Variabilidade do Gelo Marinho Antártico no ASAS
Laboratório: GEPAC/UFRJ
Descrição: Tendências sazonais do ASAS com Theil-Sen e Mann-Kendall.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

try:
    import pymannkendall as mk
except ImportError:
    mk = None


def teste_mann_kendall(valores, alfa=0.05):
    if mk is not None:
        resultado = mk.original_test(valores, alpha=alfa)
        return str(resultado.trend), float(resultado.p)

    n = len(valores)
    s = int(sum(np.sign(valores[i + 1:] - valores[i]).sum() for i in range(n - 1)))
    repetidos = np.unique(valores, return_counts=True)[1]
    variancia = (
        n * (n - 1) * (2 * n + 5)
        - np.sum(repetidos * (repetidos - 1) * (2 * repetidos + 5))
    ) / 18.0
    if variancia <= 0:
        return 'no trend', 1.0
    z = (s - 1 if s > 0 else s + 1 if s < 0 else 0) / np.sqrt(variancia)
    p = float(2 * stats.norm.sf(abs(z)))
    tendencia = 'no trend' if p >= alfa else ('increasing' if s > 0 else 'decreasing')
    return tendencia, p


pasta_projeto = Path(__file__).resolve().parent
arquivo_sazonal = pasta_projeto / 'subseries_sazonais' / 'tabela_sazonal_asas.csv'
pasta_saida = pasta_projeto / 'resultados_tendencias'
pasta_figuras = pasta_saida / 'figuras_para_artigo'
pasta_tabelas = pasta_saida / 'tabelas_para_artigo'
pasta_controle = pasta_saida / 'controle_interno'

estacoes = ['DJF', 'MAM', 'JJA', 'SON', 'ONDJ']
variaveis = [
    ('anomalia_max', 'Intensidade', 'Anomalia do geopotencial (gpm)', 'gpm/década'),
    ('lat_centro', 'Latitude do centro', 'Latitude (°)', 'graus/década'),
    ('lon_centro', 'Longitude do centro', 'Longitude (°)', 'graus/década'),
    ('lat_norte', 'Borda norte', 'Latitude (°)', 'graus/década'),
    ('lat_sul', 'Borda sul', 'Latitude (°)', 'graus/década'),
    ('lon_leste', 'Borda leste', 'Longitude (°)', 'graus/década'),
    ('lon_oeste', 'Borda oeste', 'Longitude (°)', 'graus/década'),
]
rotulos = {coluna: (titulo, eixo, unidade) for coluna, titulo, eixo, unidade in variaveis}

if not arquivo_sazonal.exists():
    raise FileNotFoundError(f'Arquivo não encontrado: {arquivo_sazonal}. Execute subseries_sazonais.py primeiro.')

dados = pd.read_csv(arquivo_sazonal, sep=';', encoding='utf-8-sig')
if dados.empty or 'ano' not in dados.columns:
    raise ValueError('A tabela sazonal está vazia ou não tem a coluna ano.')

dados['ano'] = pd.to_numeric(dados['ano'], errors='raise').astype(int)
if dados['ano'].duplicated().any():
    raise ValueError('Há anos repetidos na tabela sazonal.')

colunas = [f'{coluna}_{estacao}' for estacao in estacoes for coluna, *_ in variaveis]
faltantes = [coluna for coluna in colunas if coluna not in dados.columns]
if faltantes:
    raise ValueError(f'Colunas não encontradas: {faltantes}')

for pasta in [pasta_figuras, pasta_tabelas, pasta_controle]:
    pasta.mkdir(parents=True, exist_ok=True)

# Mantém os anos sem dados como lacunas nos gráficos.
dados = dados.sort_values('ano')
anos = np.arange(int(dados['ano'].min()), int(dados['ano'].max()) + 1)
dados = dados.set_index('ano').reindex(anos)

ajustes = {}
resumo = []
lacunas = []

for estacao in estacoes:
    for coluna, titulo, _, unidade in variaveis:
        nome = f'{coluna}_{estacao}'
        serie = pd.to_numeric(dados[nome], errors='coerce').to_numpy(dtype=float)
        validos = np.isfinite(serie)
        anos_validos = anos[validos]
        valores = serie[validos]
        ausentes = anos[~validos].tolist()
        inclinacao = intercepto = valor_p = np.nan
        tendencia = 'dados insuficientes'

        if len(valores) >= 4:
            resultado = stats.theilslopes(valores, anos_validos, 0.95)
            inclinacao = float(resultado.slope)
            intercepto = float(resultado.intercept)
            tendencia, valor_p = teste_mann_kendall(valores)
            tendencia = {
                'no trend': 'sem tendência',
                'increasing': 'crescente',
                'decreasing': 'decrescente',
            }.get(tendencia, tendencia)

        ajustes[nome] = {
            'serie': serie, 'inclinacao': inclinacao,
            'intercepto': intercepto, 'valor_p': valor_p,
            'anos_validos': len(valores), 'ausentes': ausentes,
        }
        resumo.append({
            'Estacao': estacao,
            'Variavel': titulo,
            'Tendencia': tendencia,
            'Valor_p': valor_p,
            'Inclinacao_Theil_Sen_por_decada': inclinacao * 10,
            'Anos_validos': len(valores),
            'Anos_ausentes': ', '.join(map(str, ausentes)),
            'Unidade': unidade,
        })
        if ausentes:
            lacunas.append({
                'Estacao': estacao, 'Variavel': titulo,
                'Anos_ausentes': ', '.join(map(str, ausentes)),
                'Quantidade_anos_validos': len(valores),
            })

# Mesma escala para uma variável em todas as estações.
escalas_base = {
    'anomalia_max': (20, 80, 10),
    'lat_centro': (-34, -18, 2),
    'lon_centro': (-40, 0, 5),
    'lat_norte': (-30, 0, 5),
    'lat_sul': (-40, -26, 2),
    'lon_leste': (-15, 15, 5),
    'lon_oeste': (-70, 0, 10),
}

escalas = {}
controle_escalas = []
for coluna, (minimo, maximo, passo) in escalas_base.items():
    valores = []
    for estacao in estacoes:
        info = ajustes[f'{coluna}_{estacao}']
        serie = info['serie']
        valores.extend(serie[np.isfinite(serie)].tolist())
        if np.isfinite(info['inclinacao']):
            linha = info['intercepto'] + info['inclinacao'] * anos
            valores.extend(linha[np.isfinite(linha)].tolist())

    if valores:
        menor, maior = min(valores), max(valores)
        if menor < minimo:
            minimo -= np.ceil((minimo - menor) / passo) * passo
        if maior > maximo:
            maximo += np.ceil((maior - maximo) / passo) * passo

    marcas = np.arange(minimo, maximo + passo / 2, passo)
    escalas[coluna] = (minimo, maximo, marcas)
    controle_escalas.append({
        'Variavel': rotulos[coluna][0],
        'Minimo_eixo': minimo,
        'Maximo_eixo': maximo,
        'Intervalo_marcas': passo,
    })

marcas_anos = np.arange(((anos[0] + 4) // 5) * 5, anos[-1] + 1, 5)


def desenhar_serie(eixo, estacao, coluna):
    info = ajustes[f'{coluna}_{estacao}']
    titulo, nome_eixo, _ = rotulos[coluna]
    eixo.set_title(titulo, fontsize=12, fontweight='bold', loc='left')
    eixo.set_xlabel('Ano', fontsize=10)
    eixo.set_ylabel(nome_eixo, fontsize=10)
    eixo.grid(True, linestyle='--', alpha=0.3)
    eixo.set_xlim(anos[0] - 1, anos[-1] + 1)
    eixo.set_xticks(marcas_anos)
    minimo, maximo, marcas = escalas[coluna]
    eixo.set_ylim(minimo, maximo)
    eixo.set_yticks(marcas)
    eixo.tick_params(axis='both', labelsize=9)
    eixo.plot(anos, info['serie'], 'o-', color='#3267A8',
              linewidth=1.15, markersize=3.3, label='Série original')
    if np.isfinite(info['inclinacao']):
        linha = info['intercepto'] + info['inclinacao'] * anos
        eixo.plot(anos, linha, color='#CC3434', linewidth=1.8,
                  label='Tendência Theil-Sen')
    else:
        eixo.text(0.5, 0.1, 'Dados insuficientes', ha='center',
                  transform=eixo.transAxes, fontsize=9)
    eixo.legend(loc='best', fontsize=8)


def criar_painel(estacao, campos, titulo, nome_arquivo):
    if len(campos) == 3:
        figura, eixos = plt.subplots(1, 3, figsize=(17, 5.4), sharex=True)
        espaco = {'w_pad': 2.3}
    else:
        figura, eixos = plt.subplots(2, 2, figsize=(12.5, 9.2), sharex=True)
        espaco = {'w_pad': 2.1, 'h_pad': 2.2}

    for eixo, campo in zip(np.ravel(eixos), campos):
        desenhar_serie(eixo, estacao, campo)
    figura.suptitle(f'{titulo} — {estacao}', fontsize=15, fontweight='bold')
    figura.tight_layout(rect=(0, 0, 1, 0.93), **espaco)
    destino = pasta_figuras / estacao
    destino.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino / nome_arquivo, dpi=300, bbox_inches='tight')
    plt.close(figura)


for estacao in estacoes:
    criar_painel(estacao,
                 ['anomalia_max', 'lat_centro', 'lon_centro'],
                 'Tendências do ASAS', f'tendencia_geral_{estacao}.png')
    criar_painel(estacao,
                 ['lat_norte', 'lat_sul', 'lon_leste', 'lon_oeste'],
                 'Tendências das bordas do ASAS', f'tendencia_bordas_{estacao}.png')
    print(f'Gráficos de {estacao} concluídos.')

pd.DataFrame(resumo).to_csv(pasta_tabelas / 'resumo_tendencias.csv',
                            sep=';', index=False, encoding='utf-8-sig', float_format='%.5f')
pd.DataFrame([linha for linha in resumo if linha['Estacao'] == 'ONDJ']).to_csv(
    pasta_tabelas / 'resumo_tendencias_ondj.csv', sep=';', index=False,
    encoding='utf-8-sig', float_format='%.5f')
pd.DataFrame(lacunas, columns=[
    'Estacao', 'Variavel', 'Anos_ausentes', 'Quantidade_anos_validos',
]).to_csv(pasta_controle / 'controle_lacunas_tendencias.csv',
          sep=';', index=False, encoding='utf-8-sig')
pd.DataFrame(controle_escalas).to_csv(
    pasta_controle / 'controle_escalas_graficos.csv',
    sep=';', index=False, encoding='utf-8-sig')

print(f'Figuras: {pasta_figuras}')
print(f'Tabelas: {pasta_tabelas}')
print(f'Controles: {pasta_controle}')

# Resumo: calcula as tendências das séries sazonais e faz gráficos com escalas iguais.
