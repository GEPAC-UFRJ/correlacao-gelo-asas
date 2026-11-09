
# Variabilidade do gelo marinho antártico e do ASAS

Códigos da iniciação científica desenvolvida no GEPAC/UFRJ para analisar a variabilidade do Anticiclone Subtropical do Atlântico Sul (ASAS) e sua relação com o gelo marinho antártico, com foco no Mar de Weddell.

**Período de análise:** 1980 a 2025. Nas correlações mensais entre gelo e ASAS, foi mantido o período de 1980 a 2020.

## Dados utilizados

- **ASAS:** geopotencial do ERA5 em 850 hPa, no arquivo `Dados_ic.nc`.
- **Gelo marinho:** concentração de gelo dos arquivos NetCDF da pasta `NSIDC-0079/`.
- **Climatologia do ASAS:** 1991–2020.
- **Rastreamento do ASAS:** isolinha de anomalia de 29 gpm; região de 60°W a 10°E e de 45°S a 0° para a análise do núcleo e das bordas.
- **Extensão do gelo:** pixels com concentração acima de 15%, considerando 625 km² por pixel no recorte utilizado para o Mar de Weddell.

Os arquivos NetCDF não estão incluídos neste repositório. Para executar os códigos, coloque `Dados_ic.nc` na pasta principal e os dados de concentração dentro de `NSIDC-0079/`.

## Scripts e ordem de execução

Execute os comandos no terminal, estando na pasta principal do projeto.

### Análise do ASAS

| Script | O que faz |
|---|---|
| `rastreamento_do_ASAS.py` | Localiza o núcleo e as bordas do ASAS, gerando mapas e uma tabela mensal. |
| `subseries_sazonais.py` | Calcula as médias de DJF, MAM, JJA, SON e ONDJ e registra os meses sem dados. |
| `tendencias.py` | Calcula tendências com Theil-Sen e Mann-Kendall e gera os gráficos com escalas padronizadas. |
| `detrend_tendencia_quintis.py` | Retira a tendência das intensidades sazonais e identifica os quintis Q20 e Q80. |
| `correlacao_estacoes.py` | Calcula Pearson para SON do ano anterior × DJF seguinte e MAM × JJA do mesmo ano. |

### Análise do gelo e relação com o ASAS

| Script | O que faz |
|---|---|
| `conversao_concentracao_de_gelo_marinho.py` | Converte a concentração de gelo em extensão mensal e gera o CSV utilizado nas análises. |
| `extremos_gelo_mes_a_mes.py` | Identifica os anos com menor (Q20) e maior (Q80) extensão de gelo para cada mês. |
| `gelo_x_asas_boxplots.py` | Compara os grupos Q20 e Q80 por boxplots, usando defasagens de 0 a 4 meses e Mann-Whitney. |
| `grafico_correlacionamento_derretimento.py` | Calcula correlações mensais entre gelo e ASAS, com defasagens de 0 a 4 meses. |

## Como executar

Instale as bibliotecas com:

```bash
python -m pip install -r requirements.txt
```

Depois execute, nesta ordem:

```bash
python rastreamento_do_ASAS.py
python subseries_sazonais.py
python tendencias.py
python detrend_tendencia_quintis.py
python correlacao_estacoes.py

python conversao_concentracao_de_gelo_marinho.py
python extremos_gelo_mes_a_mes.py
python gelo_x_asas_boxplots.py
python grafico_correlacionamento_derretimento.py
```

As duas primeiras etapas de cada grupo podem exigir mais tempo, dependendo do tamanho dos dados NetCDF. O processamento do gelo e o do ASAS são independentes até a etapa de boxplots e correlações entre eles.

## Observações sobre os cálculos

- **DJF/1990:** dezembro de 1989, janeiro e fevereiro de 1990.
- **ONDJ/1990:** outubro, novembro e dezembro de 1990, mais janeiro de 1991.
- As médias sazonais são calculadas com **pelo menos dois meses válidos**. Períodos com apenas um ou nenhum mês válido ficam sem média, e as lacunas são registradas nos relatórios.
- As tendências são calculadas com os anos disponíveis de cada variável, sem preencher valores ausentes.
- O método **Theil-Sen** estima a tendência. No script de *detrend*, essa tendência é subtraída da intensidade antes do cálculo dos quintis e das correlações entre estações.
- Os gráficos de tendências utilizam escalas iguais para a mesma variável nas diferentes estações.

## Principais arquivos gerados

- `figuras_asas_isolinha_29/dados_anomalia_asas_iso29.csv`
- `subseries_sazonais/tabela_sazonal_asas.csv`
- `resultados_tendencias/`
- `resultados_detrend/` e `resultados_quintis/`
- `resultados_correlacoes_estacoes/`
- `saida_extensao_gelo_mwd_1980_2025.csv`
- `extremos_gelo_mes_a_mes.csv`
- `boxplots_ondj_iso29_sig/`
- `resultados_correlacao_iso29/` e `resultados_correlacao_reais_ondj/`

As tabelas e figuras são geradas ao executar os scripts. Os arquivos de dados e resultados não são enviados ao Git por padrão, conforme o `.gitignore`.

## Créditos

**Adaptação e análises:** Lorena Aragão — GEPAC/UFRJ.

O código de conversão do gelo foi adaptado de um script de **Catharine**. O rastreamento inclui contribuição de **Joyce** na metodologia da isolinha de 29 gpm. Os gráficos de tendências foram adaptados de um código de referência de **Neres**. As referências específicas estão identificadas nos respectivos scripts.
