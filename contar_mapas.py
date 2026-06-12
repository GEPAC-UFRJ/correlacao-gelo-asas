import pandas as pd

# Carrega a sua planilha gerada
df = pd.read_csv("figuras_metodo_joyce/dados_anomalia_asas.csv")

total_meses = len(df)
print(f"Total de meses na série: {total_meses}\n")
print("Limite (mgp) | Mapas Gerados | Mapas Perdidos | Sucesso (%)")
print("-" * 65)

for limiar in range(18, 31):   
    # Conta quantos meses têm a anomalia máxima maior ou igual ao limiar
    mapas_gerados = (df['anomalia_max'] >= limiar).sum()
    mapas_perdidos = total_meses - mapas_gerados
    porcentagem = (mapas_gerados / total_meses) * 100
    
    print(f"   {limiar:02d} mgp    |      {mapas_gerados:03d}      |      {mapas_perdidos:02d}        |   {porcentagem:.1f}%")