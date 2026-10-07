# -*- coding: utf-8 -*-
"""
================================================================================
SELECAO DOS PONTOS DE AFERICAO | PRODUTO 4
Projeto UNESCO UNES 2369/2025 | Itaipu Parquetec
================================================================================
Esteira que cruza a localizacao dos estabelecimentos das Atividades
Caracteristicas do Turismo (CNPJ) e dos atrativos com as rotas viarias reais
entre eles, para identificar os trechos de maior sobreposicao de fluxos. Os
agrupamentos resultantes foram a base sobre a qual a equipe escolheu, com
justificativa registrada, os pontos aferidos em campo.

As etapas rodam em sequencia, na ordem deste arquivo, e cada uma grava o
arquivo que a seguinte le. Todos os arquivos ficam na pasta de trabalho
(variavel de ambiente P4_SELECAO_PONTOS; sem ela, a pasta corrente).

ETAPAS
    1. Acessos: separa a coordenada em latitude e longitude.
         acessos_inicio.csv -> acessos.csv
    2. CNPJ: une a base dos municipios e a de Dionisio Cerqueira.
         cnpjs_municipios.csv + cnjps_dionisio.csv -> cnpjs.csv
    3. Atrativos e acessos: une as duas bases.
         atrativos.csv + acessos.csv -> atrativos_acessos.csv
    4. Endereco completo de cada CNPJ, para a geocodificacao.
         cnpjs.csv -> cnpjs_enderecos.csv
    5. Amostra de 50% dos CNPJs (identificadores pares).
         cnpjs_enderecos.csv -> cnpjs_enderecos_compressed.csv
    6. Geocodificacao dos enderecos (Google Geocoding API).
         cnpjs_enderecos_compressed.csv -> cnpjs_georreferenciados.csv
    7. Rotas entre os pares origem-destino (TomTom Routing API); de cada rota
       guardam-se os vertices (waypoints).
         partida_chegada.csv -> tomtom_routes.csv
    8. Agrupamento dos vertices por DBSCAN (metrica haversine), por
       municipio, e ordenacao pela frequencia (numero de vertices no grupo).
         tomtom_routes.csv -> top100_clusters_per_city_r100.csv
       Parametros aplicados: EPS_METERS = 100, TOP_N = 100. O arquivo
       top20_clusters_per_city_r50.csv corresponde, pelo nome, a EPS_METERS =
       50 e TOP_N = 20.
    9. Combinacao da frequencia com uma base de pontos de trafego, em raio de
       50 m, com pesos iguais.
         top100_clusters_per_city_r100.csv + traffic.csv -> ranked_points.csv

ENTRADAS (nao distribuidas)
    acessos_inicio.csv, atrativos.csv   cadastro de acessos e atrativos do estudo
    cnpjs_municipios.csv, cnjps_dionisio.csv
                                        estabelecimentos das ACTs (Receita
                                        Federal, Cadastro Nacional da Pessoa
                                        Juridica)
    partida_chegada.csv                 pares origem-destino (atrativo e centro
                                        da mancha de ACTs de cada municipio)
    traffic.csv                         pontos de trafego (lat, lon, traffic)

VARIAVEIS DE AMBIENTE
    GOOGLE_MAPS_API_KEY   etapa 6
    TOMTOM_API_KEY        etapa 7
    P4_SELECAO_PONTOS     pasta de trabalho (opcional)

As respostas da Google e da TomTom nao sao redistribuidas; com chaves
proprias, as etapas 6 e 7 geram novamente os arquivos, com o estado dos
servicos na data da execucao.

COMO EXECUTAR
    python selecao_pontos/selecao_pontos_afericao.py
================================================================================
"""
import os

os.chdir(os.environ.get("P4_SELECAO_PONTOS", "."))

# separate coordinates from ACESSOS

import pandas as pd

# Read CSV
df = pd.read_csv("acessos_inicio.csv", sep=';')

# Split coordenada into latitude and longitude
df[["latitude", "longitude"]] = df["coordenada"].str.split(",", expand=True)

# Remove possible whitespace and convert to numbers
df["latitude"] = pd.to_numeric(df["latitude"].str.strip())
df["longitude"] = pd.to_numeric(df["longitude"].str.strip())

# Keep only the desired columns
df = df[
    ["id", "municipio", "nome", "latitude", "longitude"]
]

# Save new CSV
df.to_csv("acessos.csv", index=False)

print(df.head())

# merge cnpjs_dionisio & cnpjs_municipios

import pandas as pd

file1 = "cnpjs_municipios.csv"
file2 = "cnjps_dionisio.csv"

output_file = "cnpjs.csv"

# Expected headers
expected_headers = [
    "nome_fantasia",
    "tipo_logradouro",
    "logradouro",
    "numero",
    "bairro",
    "cep",
    "uf",
    "codigo_municipio",
    "nome_municipio"
]

df1 = pd.read_csv(file1, dtype=str, sep=';')
df2 = pd.read_csv(file2, dtype=str, sep=';')

df1.columns = df1.columns.str.strip()
df2.columns = df2.columns.str.strip()

headers1 = list(df1.columns)
headers2 = list(df2.columns)

print("File 1 headers:")
print(headers1)

print("\nFile 2 headers:")
print(headers2)

print("\nHeaders are identical:", headers1 == headers2)

print(
    "File 1 has expected headers:",
    headers1 == expected_headers
)

print(
    "File 2 has expected headers:",
    headers2 == expected_headers
)

if headers1 != headers2:

    print("\nHeaders only in file 1:")
    print(set(headers1) - set(headers2))

    print("\nHeaders only in file 2:")
    print(set(headers2) - set(headers1))

    raise ValueError(
        "The two CSV files do not have the same headers."
    )

merged = pd.concat(
    [df1, df2],
    ignore_index=True
)

merged.to_csv(
    output_file,
    index=False
)

print("\n================================")
print("MERGE COMPLETE")
print("================================")

print("Rows in file 1:", len(df1))
print("Rows in file 2:", len(df2))
print("Rows in merged:", len(merged))

print("Output:", output_file)

# merge ACESSOS and ATRATIVOS

import pandas as pd

file1 = "atrativos.csv"
file2 = "acessos.csv"

output_file = "atrativos_acessos.csv"

# Expected headers
expected_headers = [
    "id",
    "municipio",
    "nome",
    "latitude",
    "longitude"
]

df1 = pd.read_csv(file1, dtype=str)
df2 = pd.read_csv(file2, dtype=str)

df1.columns = df1.columns.str.strip()
df2.columns = df2.columns.str.strip()

headers1 = list(df1.columns)
headers2 = list(df2.columns)

print("File 1 headers:")
print(headers1)

print("\nFile 2 headers:")
print(headers2)

print("\nHeaders are identical:", headers1 == headers2)

print(
    "File 1 has expected headers:",
    headers1 == expected_headers
)

print(
    "File 2 has expected headers:",
    headers2 == expected_headers
)

if headers1 != headers2:

    print("\nHeaders only in file 1:")
    print(set(headers1) - set(headers2))

    print("\nHeaders only in file 2:")
    print(set(headers2) - set(headers1))

    raise ValueError(
        "The two CSV files do not have the same headers."
    )

merged = pd.concat(
    [df1, df2],
    ignore_index=True
)

merged.to_csv(
    output_file,
    index=False
)

print("\n================================")
print("MERGE COMPLETE")
print("================================")

print("Rows in file 1:", len(df1))
print("Rows in file 2:", len(df2))
print("Rows in merged:", len(merged))

print("Output:", output_file)

# Produce ADDRESS for CNPJs

import pandas as pd

input_file = "cnpjs.csv"
output_file = "cnpjs_enderecos.csv"

# Read CSV
df = pd.read_csv(input_file, dtype=str)

# Remove whitespace from column names
df.columns = df.columns.str.strip()

# Replace missing values with empty strings
df = df.fillna("")

# Create address for geocoding
df["endereco"] = (
    df["tipo_logradouro"].str.strip() + " " +
    df["logradouro"].str.strip() + ", " +
    df["numero"].str.strip() + ", " +
    df["bairro"].str.strip() + ", " +
    df["nome_municipio"].str.strip() + ", " +
    df["uf"].str.strip()
)

# Keep original columns + endereco
df = df[
    [
        "id",
        "nome_fantasia",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "bairro",
        "cep",
        "uf",
        "codigo_municipio",
        "nome_municipio",
        "endereco"
    ]
]

# Save
df.to_csv(
    output_file,
    index=False
)

print("Saved:", output_file)
print(df.head())

# DOWNSAMPLE: keep 50% of the addresses (even ids)

import pandas as pd

input_file = "cnpjs_enderecos.csv"
output_file = "cnpjs_enderecos_compressed.csv"

df = pd.read_csv(input_file)

# Keep only rows where id is even
compressed = df[df["id"] % 2 == 0]

# Save
compressed.to_csv(output_file, index=False)

print("Original rows:", len(df))
print("Compressed rows:", len(compressed))
print("Output:", output_file)

import requests
import pandas as pd

API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
URL = "https://maps.googleapis.com/maps/api/geocode/json?address="

def api_call(place, url=URL):

    full_url = (
        f"{url}"
        f"{place}"
    )

    params = {
        "key": API_KEY
    }

    response = requests.get(
        full_url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("results", [])

    if results:
        location = results[0]["geometry"]["location"]

        lat = location["lat"]
        lon = location["lng"]

        return {
            "lat": lat,
            "lon": lon
        }

    return None

import pandas as pd

df = pd.read_csv(
    "cnpjs_enderecos_compressed.csv")

# Create columns if they don't exist
df["latitude"] = None
df["longitude"] = None

# Iterate over rows
for idx, row in df.iterrows():

    endereco = str(row["endereco"]).strip()
    query = f"{endereco}, Brazil"

    try:

        result = api_call(query)


        if result:

            df.at[idx, "latitude"] = result["lat"]
            df.at[idx, "longitude"] = result["lon"]

            print(f"[OK] {query} -> {result['lat']}, {result['lon']}")

        else:
            print(f"[NOT FOUND] {query}")

    except Exception as e:
        print(f"[ERROR] {query} -> {e}")

# Save CSV
df.to_csv(
    "cnpjs_georreferenciados.csv",
    sep=";",
    index=False,
    encoding="utf-8-sig"
)

print("CSV saved to cnpjs_georreferenciados.csv")

# Generate Routes


import requests
import pandas as pd
import time

# ==========================================================
# CONFIGURATION
# ==========================================================

API_KEY = os.environ["TOMTOM_API_KEY"]
INPUT_CSV = "partida_chegada.csv"
OUTPUT_CSV = "tomtom_routes.csv"

# ==========================================================
# READ CSV
# ==========================================================

df_routes = pd.read_csv(
    INPUT_CSV,
    dtype={
        "id": str,
        "municipio": str,
        "nome": str,
        "latitude_origem": float,
        "longitude_origem": float,
        "latitude_destino": float,
        "longitude_destino": float
    }
)

# Remove whitespace from column names
df_routes.columns = df_routes.columns.str.strip()

required_columns = [
    "id",
    "municipio",
    "nome",
    "latitude_origem",
    "longitude_origem",
    "latitude_destino",
    "longitude_destino"
]

# Check that all required columns exist
missing_columns = [
    col for col in required_columns
    if col not in df_routes.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}"
    )

print("Input CSV loaded.")
print("Number of routes:", len(df_routes))


# ==========================================================
# STORAGE
# ==========================================================

rows = []


# ==========================================================
# PROCESS EACH CSV ROW
# ==========================================================

for index, route in df_routes.iterrows():

    route_id = route["id"]
    municipio = route["municipio"]
    nome = route["nome"]

    origin_lat = route["latitude_origem"]
    origin_lon = route["longitude_origem"]

    destination_lat = route["latitude_destino"]
    destination_lon = route["longitude_destino"]


    print("\n" + "=" * 70)
    print(
        f"Processing {index + 1}/{len(df_routes)}"
    )
    print("=" * 70)

    print(f"ID:           {route_id}")
    print(f"Municipio:    {municipio}")
    print(f"Nome:         {nome}")

    print(
        f"Origin:       "
        f"{origin_lat}, {origin_lon}"
    )

    print(
        f"Destination:  "
        f"{destination_lat}, {destination_lon}"
    )


    # ======================================================
    # 1. CREATE ROUTE
    # ======================================================

    create_url = (
        "https://api.tomtom.com/routemonitoring/3/routes"
    )

    payload = {
        "name": f"route-{route_id}",
        "pathPoints": [
            {
                "latitude": origin_lat,
                "longitude": origin_lon
            },
            {
                "latitude": destination_lat,
                "longitude": destination_lon
            }
        ]
    }

    response = requests.post(
        create_url,
        params={"key": API_KEY},
        headers={
            "Content-Type": "application/json"
        },
        json=payload
    )

    print(
        "Create route:",
        response.status_code
    )


    if response.status_code not in [200, 201]:

        print("Create failed:")
        print(response.text)

        continue


    data = response.json()

    tomtom_route_id = data["routeId"]

    print(
        "TomTom routeId:",
        tomtom_route_id
    )


    # ======================================================
    # 2. POLL ROUTE DETAILS
    # ======================================================

    details_url = (
        f"https://api.tomtom.com/routemonitoring/3/routes/"
        f"{tomtom_route_id}/details"
    )

    details = None
    detailed_segments = []

    max_attempts = 15
    wait_seconds = 2

    for attempt in range(
        1,
        max_attempts + 1
    ):

        print(
            f"Getting details "
            f"(attempt {attempt}/{max_attempts})..."
        )

        response = requests.get(
            details_url,
            params={"key": API_KEY}
        )

        print(
            "Status:",
            response.status_code
        )


        if response.status_code != 200:

            print(response.text)

            time.sleep(wait_seconds)

            continue


        details = response.json()

        detailed_segments = details.get(
            "detailedSegments",
            []
        )

        print(
            "Number of segments:",
            len(detailed_segments)
        )


        # Route is ready
        if len(detailed_segments) > 0:

            print(
                "Route geometry is ready."
            )

            break


        # Route isn't ready yet
        if attempt < max_attempts:

            print(
                f"No segments yet. "
                f"Waiting {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)


    # ======================================================
    # 3. CHECK ROUTE
    # ======================================================

    if not detailed_segments:

        print(
            f"WARNING: Route {route_id} "
            f"returned no detailed segments."
        )

        # Delete route even if it failed
        delete_url = (
            f"https://api.tomtom.com/routemonitoring/3/routes/"
            f"{tomtom_route_id}"
        )

        delete_response = requests.delete(
            delete_url,
            params={"key": API_KEY}
        )

        print(
            "Delete route:",
            delete_response.status_code
        )

        continue


    # ======================================================
    # 4. EXTRACT COMPLETE SEGMENT SHAPES
    # ======================================================

    route_point_count = 0

    for segment in detailed_segments:

        segment_id = segment.get(
            "segmentId"
        )

        shape = segment.get(
            "shape",
            []
        )

        print(
            f"Segment {segment_id}: "
            f"{len(shape)} points"
        )


        # Save EVERY coordinate
        for point in shape:

            rows.append({

                # Original CSV ID
                "id": route_id,

                # Metadata from original CSV
                "municipio": municipio,
                "nome": nome,

                # Route geometry
                "latitude": point["latitude"],
                "longitude": point["longitude"]
            })

            route_point_count += 1


    print(
        f"Total points extracted: "
        f"{route_point_count}"
    )


    # ======================================================
    # 5. DELETE TOMTOM ROUTE
    # ======================================================

    delete_url = (
        f"https://api.tomtom.com/routemonitoring/3/routes/"
        f"{tomtom_route_id}"
    )

    delete_response = requests.delete(
        delete_url,
        params={"key": API_KEY}
    )

    print(
        "Delete route:",
        delete_response.status_code
    )


    if delete_response.status_code not in [
        200,
        202,
        204
    ]:

        print(
            "WARNING: Could not delete route:"
        )

        print(
            delete_response.text
        )


    # ======================================================
    # DELAY
    # ======================================================

    time.sleep(1)


# ==========================================================
# 6. CREATE OUTPUT DATAFRAME
# ==========================================================

df_output = pd.DataFrame(
    rows,
    columns=[
        "id",
        "municipio",
        "nome",
        "latitude",
        "longitude"
    ]
)


# ==========================================================
# 7. SAVE CSV
# ==========================================================

df_output.to_csv(
    OUTPUT_CSV,
    index=False
)


# ==========================================================
# 8. SUMMARY
# ==========================================================

print("\n")
print("=" * 70)
print("DONE")
print("=" * 70)

print(
    "Total points:",
    len(df_output)
)

if len(df_output) > 0:

    print(
        "Routes with points:",
        df_output["id"].nunique()
    )

    print("\nPoints per route:")

    print(
        df_output.groupby("id").size()
    )

print(
    "\nOutput:",
    OUTPUT_CSV
)

# CLUSTER AND RANK TOP 20 MOST FREQUENT POINTS PER CITY


import pandas as pd
import numpy as np

from sklearn.cluster import DBSCAN
from sklearn.metrics import pairwise_distances


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_CSV = "tomtom_routes.csv"
OUTPUT_CSV = "top100_clusters_per_city_r100.csv"

# Radius used to define a spatial cluster
# 50 meters is a good starting point for street-level data.
EPS_METERS = 100

# Maximum number of clusters/points to retain per municipality
TOP_N = 100


# ============================================================
# READ DATA
# ============================================================

df = pd.read_csv(INPUT_CSV)

required_columns = [
    "id",
    "municipio",
    "nome",
    "latitude",
    "longitude"
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Missing columns: {missing}"
    )


# Remove rows with invalid coordinates
df = df.dropna(
    subset=[
        "municipio",
        "latitude",
        "longitude"
    ]
).copy()


# ============================================================
# DBSCAN PARAMETERS
# ============================================================

EARTH_RADIUS_METERS = 6_371_000

# DBSCAN with haversine expects radians
eps_radians = (
    EPS_METERS /
    EARTH_RADIUS_METERS
)


# ============================================================
# OUTPUT
# ============================================================

results = []


# ============================================================
# PROCESS EACH MUNICIPALITY
# ============================================================

for municipio, city_df in df.groupby(
    "municipio"
):

    print("\n" + "=" * 70)
    print(f"Municipality: {municipio}")
    print(
        f"Input points: {len(city_df)}"
    )
    print("=" * 70)


    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    coordinates = np.radians(
        city_df[
            [
                "latitude",
                "longitude"
            ]
        ].values
    )


    # --------------------------------------------------------
    # DBSCAN
    # --------------------------------------------------------

    clustering = DBSCAN(
        eps=eps_radians,
        min_samples=1,
        metric="haversine"
    )

    labels = clustering.fit_predict(
        coordinates
    )

    city_df = city_df.copy()

    city_df["cluster"] = labels


    # --------------------------------------------------------
    # Count points in each cluster
    # --------------------------------------------------------

    cluster_counts = (
        city_df
        .groupby("cluster")
        .size()
        .reset_index(
            name="frequency"
        )
    )


    # --------------------------------------------------------
    # Rank clusters
    # --------------------------------------------------------

    cluster_counts = (
        cluster_counts
        .sort_values(
            "frequency",
            ascending=False
        )
        .head(TOP_N)
    )


    # --------------------------------------------------------
    # Extract representative coordinate
    # --------------------------------------------------------

    for rank, (_, cluster_row) in enumerate(
        cluster_counts.iterrows(),
        start=1
    ):

        cluster_id = cluster_row[
            "cluster"
        ]

        frequency = int(
            cluster_row[
                "frequency"
            ]
        )


        cluster_points = city_df[
            city_df["cluster"] == cluster_id
        ]


        # ----------------------------------------------------
        # Calculate cluster center
        # ----------------------------------------------------

        latitude = cluster_points[
            "latitude"
        ].mean()

        longitude = cluster_points[
            "longitude"
        ].mean()


        results.append({

            "municipio":
                municipio,

            "rank":
                rank,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "frequency":
                frequency
        })


        print(
            f"Rank {rank:2d}: "
            f"{frequency:6d} points "
            f"→ "
            f"{latitude:.6f}, "
            f"{longitude:.6f}"
        )


# ============================================================
# CREATE OUTPUT DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    results
)


# ============================================================
# SAVE
# ============================================================

result_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("DONE")
print("=" * 70)

print(
    "Municipalities:",
    result_df["municipio"].nunique()
)

print(
    "Total selected points:",
    len(result_df)
)

print(
    "Output:",
    OUTPUT_CSV
)

import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree


# ============================================================
# CONFIGURATION
# ============================================================

CANDIDATES_CSV = "top100_clusters_per_city_r100.csv"
TRAFFIC_CSV = "traffic.csv"

OUTPUT_CSV = "ranked_points.csv"

# Radius around each candidate point
RADIUS_METERS = 50

# Equal weights
FREQUENCY_WEIGHT = 0.5
TRAFFIC_WEIGHT = 0.5

EARTH_RADIUS_METERS = 6_371_000


# ============================================================
# READ CSVs
# ============================================================

candidates = pd.read_csv(
    CANDIDATES_CSV
)

traffic = pd.read_csv(
    TRAFFIC_CSV
)


# ============================================================
# CHECK COLUMNS
# ============================================================

required_candidate_columns = [
    "municipio",
    "rank",
    "latitude",
    "longitude",
    "frequency"
]

required_traffic_columns = [
    "lat",
    "lon",
    "traffic"
]

for column in required_candidate_columns:

    if column not in candidates.columns:
        raise ValueError(
            f"Candidate CSV is missing column: {column}"
        )


for column in required_traffic_columns:

    if column not in traffic.columns:
        raise ValueError(
            f"Traffic CSV is missing column: {column}"
        )


# ============================================================
# CLEAN NUMERIC COLUMNS
# ============================================================

candidates["latitude"] = pd.to_numeric(
    candidates["latitude"],
    errors="coerce"
)

candidates["longitude"] = pd.to_numeric(
    candidates["longitude"],
    errors="coerce"
)

candidates["frequency"] = pd.to_numeric(
    candidates["frequency"],
    errors="coerce"
)

traffic["lat"] = pd.to_numeric(
    traffic["lat"],
    errors="coerce"
)

traffic["lon"] = pd.to_numeric(
    traffic["lon"],
    errors="coerce"
)

traffic["traffic"] = pd.to_numeric(
    traffic["traffic"],
    errors="coerce"
)


# Remove invalid rows

candidates = candidates.dropna(
    subset=[
        "municipio",
        "latitude",
        "longitude",
        "frequency"
    ]
).copy()

traffic = traffic.dropna(
    subset=[
        "lat",
        "lon",
        "traffic"
    ]
).copy()


# ============================================================
# NORMALIZE FREQUENCY WITHIN EACH MUNICIPIO
# ============================================================

def normalize_frequency(group):

    min_freq = group["frequency"].min()
    max_freq = group["frequency"].max()

    if max_freq == min_freq:

        # If all points in this municipality
        # have exactly the same frequency

        group["frequency_norm"] = 1.0

    else:

        group["frequency_norm"] = (
            (group["frequency"] - min_freq)
            /
            (max_freq - min_freq)
        )

    return group


candidates = (
    candidates
    .groupby(
        "municipio",
        group_keys=False
    )
    .apply(
        normalize_frequency
    )
)


# ============================================================
# PREPARE COORDINATES FOR BALLTREE
# ============================================================

candidate_coords = np.radians(
    candidates[
        [
            "latitude",
            "longitude"
        ]
    ].values
)

traffic_coords = np.radians(
    traffic[
        [
            "lat",
            "lon"
        ]
    ].values
)


# ============================================================
# BUILD BALLTREE
# ============================================================

tree = BallTree(
    traffic_coords,
    metric="haversine"
)


# ============================================================
# CONVERT RADIUS TO RADIANS
# ============================================================

radius_radians = (
    RADIUS_METERS
    /
    EARTH_RADIUS_METERS
)


# ============================================================
# FIND TRAFFIC POINTS WITHIN RADIUS
# ============================================================

indices, distances = tree.query_radius(
    candidate_coords,
    r=radius_radians,
    return_distance=True
)


# ============================================================
# CALCULATE TRAFFIC SCORE
# ============================================================

traffic_scores = []


for i in range(len(candidates)):

    nearby_indices = indices[i]

    nearby_distances = distances[i]


    # --------------------------------------------------------
    # No traffic points nearby
    # --------------------------------------------------------

    if len(nearby_indices) == 0:

        traffic_scores.append(0.0)

        continue


    # --------------------------------------------------------
    # Convert distance from radians to meters
    # --------------------------------------------------------

    distances_m = (
        nearby_distances
        *
        EARTH_RADIUS_METERS
    )


    # --------------------------------------------------------
    # Distance weighting
    # --------------------------------------------------------

    # Avoid division by zero when a traffic point
    # is exactly coincident with the candidate.

    distances_m = np.maximum(
        distances_m,
        1.0
    )

    weights = 1 / distances_m


    # --------------------------------------------------------
    # Get traffic values
    # --------------------------------------------------------

    traffic_values = (
        traffic.iloc[
            nearby_indices
        ]["traffic"].values
    )


    # --------------------------------------------------------
    # Weighted traffic average
    # --------------------------------------------------------

    weighted_traffic = (
        np.sum(
            weights *
            traffic_values
        )
        /
        np.sum(weights)
    )


    traffic_scores.append(
        weighted_traffic
    )


candidates["traffic_score"] = (
    traffic_scores
)


# ============================================================
# FINAL SCORE
# ============================================================

candidates["score"] = (

    FREQUENCY_WEIGHT
    *
    candidates["frequency_norm"]

    +

    TRAFFIC_WEIGHT
    *
    candidates["traffic_score"]

)


# ============================================================
# FINAL RANK WITHIN EACH MUNICIPIO
# ============================================================

candidates["final_rank"] = (
    candidates
    .groupby("municipio")["score"]
    .rank(
        ascending=False,
        method="first"
    )
    .astype(int)
)


# ============================================================
# SORT
# ============================================================

candidates = candidates.sort_values(
    [
        "municipio",
        "final_rank"
    ],
    ascending=[
        True,
        True
    ]
)


# ============================================================
# SAVE
# ============================================================

candidates.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# PRINT RESULTS
# ============================================================

print("\n============================================")
print("DONE")
print("============================================")

print(
    f"Output: {OUTPUT_CSV}"
)

print(
    f"Total candidate points: {len(candidates)}"
)

print(
    f"Municipalities: {candidates['municipio'].nunique()}"
)


print("\nTop 20 points per municipality:")

print(
    candidates[
        candidates["final_rank"] <= 20
    ][
        [
            "municipio",
            "rank",
            "latitude",
            "longitude",
            "frequency",
            "frequency_norm",
            "traffic_score",
            "score",
            "final_rank"
        ]
    ].to_string(index=False)
)