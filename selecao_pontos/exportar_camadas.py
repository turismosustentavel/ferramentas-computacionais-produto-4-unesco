#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SELECAO DOS PONTOS DE AFERICAO | PRODUTO 4
EXPORTACAO DAS CAMADAS VETORIAIS
Projeto UNESCO UNES 2369/2025 | Itaipu Parquetec
================================================================================

Converte os dados da selecao dos pontos em camadas vetoriais:
1. Pontos de Afericao Selecionados (decisoes registradas)
2. Pontos de Sobreposicao de Fluxos (clusters classificados por frequencia)
3. Manchas de Fluxo / Rotas (trajetorias e pontos TomTom)
4. Atrativos Turisticos (classificacao Produto 4)

Formatos gerados:
- ESRI Shapefile (.zip contendo .shp, .shx, .dbf, .prj, .cpg de todas as camadas)
- GeoPackage (.gpkg com todas as 4 camadas em arquivo unico)
- GeoJSON (.geojson individual por camada)

Entradas (caminhos relativos a pasta de trabalho, que e a pasta da selecao
dos pontos: "Entregas/Produto 4/produção/Seleção dos pontos para aferição"):
- pontos_afericao_selecionados*.csv   pontos escolhidos, com justificativa
                                      (MUNICIPIO, ORDEM, NOME, LATITUDE,
                                      LONGITUDE, JUSTIFIC, DATA_HORA)
- ranked_by_frequency.csv ou final/z_top_ranked/top*_clusters_per_city_*.csv
- final/z_rotas_tomtom/tomtom_routes.csv
- atrativos_qualitativo_georeferenciado.csv ou atrativos_georeferenciados_limpo.csv

Saidas: pasta camadas_qgis/ (ou a indicada em --out).

Uso:
    python exportar_camadas.py
    python exportar_camadas.py --csv "caminho/para/pontos_afericao_selecionados.csv"
    python exportar_camadas.py --crs 4674  (para SIRGAS 2000)
"""

import os
import sys
import glob
import shutil
import zipfile
import argparse
from pathlib import Path

# Configura encoding do terminal para compatibilidade no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


def find_latest_csv():
    """Busca automaticamente o arquivo CSV de pontos mais recente."""
    candidates = []
    
    # Diretorio atual
    candidates.extend(glob.glob("pontos_afericao_selecionados*.csv"))
    candidates.extend(glob.glob("*.csv"))
    
    valid_csvs = []
    for c in set(candidates):
        try:
            p = Path(c)
            if p.is_file() and p.stat().st_size > 0:
                with open(p, "r", encoding="utf-8-sig", errors="ignore") as f:
                    first_line = f.readline().lower()
                    if "municipio" in first_line or "latitude" in first_line or "ponto" in first_line:
                        valid_csvs.append((p.stat().st_mtime, p))
        except Exception:
            continue
            
    if not valid_csvs:
        return None
        
    valid_csvs.sort(key=lambda x: x[0], reverse=True)
    return valid_csvs[0][1]


def load_selected_points(csv_path):
    """Le e padroniza o CSV de pontos de afericao selecionados."""
    if not csv_path or not os.path.exists(csv_path):
        return None
        
    print(f"Lendo pontos selecionados: {csv_path}")
    df = None
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        for sep in [";", ",", "\t"]:
            try:
                temp_df = pd.read_csv(csv_path, sep=sep, encoding=enc, dtype=str)
                cols_lower = [c.lower().strip() for c in temp_df.columns]
                has_lat = any("lat" in c for c in cols_lower)
                has_lon = any("lon" in c or "lng" in c for c in cols_lower)
                if has_lat and has_lon and len(temp_df) > 0:
                    df = temp_df
                    break
            except Exception:
                continue
        if df is not None:
            break
            
    if df is None or len(df) == 0:
        return None
        
    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if "muni" in cl or "cidade" in cl: col_map[col] = "MUNICIPIO"
        elif "ordem" in cl or "seq" in cl: col_map[col] = "ORDEM"
        elif "nome" in cl or "atrativo" in cl or "ponto" in cl and "ordem" not in cl: col_map[col] = "NOME"
        elif "lat" in cl: col_map[col] = "LATITUDE"
        elif "lon" in cl or "lng" in cl: col_map[col] = "LONGITUDE"
        elif "justific" in cl or "obs" in cl or "nota" in cl: col_map[col] = "JUSTIFIC"
        elif "data" in cl or "hora" in cl or "time" in cl: col_map[col] = "DATA_HORA"
            
    df = df.rename(columns=col_map)
    if "MUNICIPIO" not in df.columns: df["MUNICIPIO"] = "Nao informado"
    if "ORDEM" not in df.columns: df["ORDEM"] = [str(i + 1) for i in range(len(df))]
    if "NOME" not in df.columns: df["NOME"] = [f"Ponto #{i+1}" for i in range(len(df))]
    if "JUSTIFIC" not in df.columns: df["JUSTIFIC"] = ""
    if "DATA_HORA" not in df.columns: df["DATA_HORA"] = ""
    
    df["LATITUDE"] = df["LATITUDE"].astype(str).str.replace(",", ".").str.strip()
    df["LONGITUDE"] = df["LONGITUDE"].astype(str).str.replace(",", ".").str.strip()
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
    
    df_valid = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
    df_valid["ORDEM_NUM"] = pd.to_numeric(df_valid["ORDEM"].astype(str).str.extract(r'(\d+)')[0], errors="coerce").fillna(1).astype(int)
    df_valid["ORDEM"] = df_valid["ORDEM_NUM"]
    df_valid = df_valid.drop(columns=["ORDEM_NUM"], errors="ignore")
    
    df_valid["MUNICIPIO"] = df_valid["MUNICIPIO"].astype(str).str[:50]
    df_valid["NOME"] = df_valid["NOME"].astype(str).str[:100]
    df_valid["JUSTIFIC"] = df_valid["JUSTIFIC"].astype(str).str[:254]
    df_valid["DATA_HORA"] = df_valid["DATA_HORA"].astype(str).str[:30]
    
    cols = ["MUNICIPIO", "ORDEM", "NOME", "LATITUDE", "LONGITUDE", "JUSTIFIC", "DATA_HORA"]
    return df_valid[cols]


def load_overlap_clusters():
    """Carrega os pontos de sobreposicao de fluxos (clusters com frequencia e rank)."""
    paths = [
        "ranked_by_frequency.csv",
        "final/z_top_ranked/top100_clusters_per_city_r100.csv",
        "final/z_top_ranked/top20_clusters_per_city_r50.csv"
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"Lendo pontos de sobreposicao: {p}")
            try:
                df = pd.read_csv(p)
                df.columns = [c.lower().strip() for c in df.columns]
                
                col_map = {}
                for c in df.columns:
                    if "muni" in c: col_map[c] = "MUNICIPIO"
                    elif "rank" in c: col_map[c] = "RANK"
                    elif "freq" in c: col_map[c] = "FREQ"
                    elif "lat" in c: col_map[c] = "LATITUDE"
                    elif "lon" in c or "lng" in c: col_map[c] = "LONGITUDE"
                    
                df = df.rename(columns=col_map)
                df["LATITUDE"] = pd.to_numeric(df["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
                df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")
                if "FREQ" in df.columns:
                    df["FREQ"] = pd.to_numeric(df["FREQ"].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
                else:
                    df["FREQ"] = 1.0
                if "RANK" in df.columns:
                    df["RANK"] = pd.to_numeric(df["RANK"], errors="coerce").fillna(1).astype(int)
                else:
                    df["RANK"] = 1
                    
                df_valid = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
                df_valid["MUNICIPIO"] = df_valid["MUNICIPIO"].astype(str).str[:50]
                cols = ["MUNICIPIO", "RANK", "FREQ", "LATITUDE", "LONGITUDE"]
                return df_valid[cols]
            except Exception as e:
                print(f"Aviso ao ler {p}: {e}")
    return None


def load_flow_routes():
    """Carrega os pontos das rotas / manchas de fluxo TomTom."""
    path = "final/z_rotas_tomtom/tomtom_routes.csv"
    if not os.path.exists(path):
        return None
        
    print(f"Lendo manchas e rotas de fluxo: {path}")
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        col_map = {}
        for c in df.columns:
            if "id" in c: col_map[c] = "ID_ROTA"
            elif "muni" in c: col_map[c] = "MUNICIPIO"
            elif "nome" in c: col_map[c] = "NOME_ROTA"
            elif "lat" in c: col_map[c] = "LATITUDE"
            elif "lon" in c or "lng" in c: col_map[c] = "LONGITUDE"
            
        df = df.rename(columns=col_map)
        if "ID_ROTA" not in df.columns: df["ID_ROTA"] = 1
        if "NOME_ROTA" not in df.columns: df["NOME_ROTA"] = "Rota TomTom"
        if "MUNICIPIO" not in df.columns: df["MUNICIPIO"] = "Nao informado"
        
        df["LATITUDE"] = pd.to_numeric(df["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
        df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")
        df["ID_ROTA"] = pd.to_numeric(df["ID_ROTA"], errors="coerce").fillna(1).astype(int)
        
        df_valid = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
        df_valid["MUNICIPIO"] = df_valid["MUNICIPIO"].astype(str).str[:50]
        df_valid["NOME_ROTA"] = df_valid["NOME_ROTA"].astype(str).str[:100]
        
        cols = ["MUNICIPIO", "ID_ROTA", "NOME_ROTA", "LATITUDE", "LONGITUDE"]
        return df_valid[cols]
    except Exception as e:
        print(f"Aviso ao ler rotas: {e}")
        return None


def load_attractions():
    """Carrega a base de atrativos turisticos do estudo."""
    paths = [
        "atrativos_qualitativo_georeferenciado.csv",
        "atrativos_georeferenciados_limpo.csv"
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"Lendo atrativos turisticos: {p}")
            try:
                df = pd.read_csv(p, sep=";") if ";" in open(p, "r", encoding="utf-8-sig", errors="ignore").readline() else pd.read_csv(p)
                df.columns = [c.lower().strip() for c in df.columns]
                col_map = {}
                for c in df.columns:
                    if "id" in c: col_map[c] = "ID_ATRATIV"
                    elif "muni" in c: col_map[c] = "MUNICIPIO"
                    elif "nome" in c: col_map[c] = "NOME"
                    elif "rank" in c: col_map[c] = "RANK_PROD4"
                    elif "lat" in c: col_map[c] = "LATITUDE"
                    elif "lon" in c or "lng" in c: col_map[c] = "LONGITUDE"
                    
                df = df.rename(columns=col_map)
                if "ID_ATRATIV" not in df.columns: df["ID_ATRATIV"] = 1
                if "NOME" not in df.columns: df["NOME"] = "Atrativo"
                if "RANK_PROD4" not in df.columns: df["RANK_PROD4"] = "-"
                
                df["LATITUDE"] = pd.to_numeric(df["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
                df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")
                df["ID_ATRATIV"] = pd.to_numeric(df["ID_ATRATIV"], errors="coerce").fillna(1).astype(int)
                
                df_valid = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
                df_valid["MUNICIPIO"] = df_valid["MUNICIPIO"].astype(str).str[:50]
                df_valid["NOME"] = df_valid["NOME"].astype(str).str[:100]
                df_valid["RANK_PROD4"] = df_valid["RANK_PROD4"].astype(str).str[:50]
                
                cols = ["MUNICIPIO", "ID_ATRATIV", "NOME", "RANK_PROD4", "LATITUDE", "LONGITUDE"]
                return df_valid[cols]
            except Exception as e:
                print(f"Aviso ao ler atrativos {p}: {e}")
    return None


def export_all_qgis_layers(layers_dict, output_dir="camadas_qgis", epsg_code=4326):
    """Exporta todas as camadas para GeoPackage (.gpkg), Shapefiles (.zip) e GeoJSON."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    crs_str = f"EPSG:{epsg_code}"
    crs_name = "SIRGAS 2000 (Geografico)" if epsg_code == 4674 else "WGS 84 (Geografico Padrao GPS)"
    
    print(f"\nConfigurando projecao cartografica: {crs_str} ({crs_name})")
    
    # 1. GeoPackage Unico com todas as camadas
    gpkg_file = out_path / "pontos_afericao_unesco.gpkg"
    print(f"\n[1/3] Gerando GeoPackage multi-camadas: {gpkg_file.name}")
    
    # Remove GPKG antigo se existir para regravar camadas limpas
    if gpkg_file.exists():
        try: os.remove(gpkg_file)
        except Exception: pass
        
    gdfs = {}
    for layer_key, df in layers_dict.items():
        if df is not None and len(df) > 0:
            geometry = [Point(xy) for xy in zip(df["LONGITUDE"], df["LATITUDE"])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs_str)
            gdfs[layer_key] = gdf
            gdf.to_file(gpkg_file, layer=layer_key, driver="GPKG", encoding="utf-8")
            print(f"   + Camada inserida no GeoPackage: {layer_key} ({len(gdf)} feicoes)")

    # 2. GeoJSONs Individuais
    print(f"\n[2/3] Gerando arquivos GeoJSON individuais:")
    for layer_key, gdf in gdfs.items():
        geojson_file = out_path / f"{layer_key}.geojson"
        gdf.to_file(geojson_file, driver="GeoJSON", encoding="utf-8")
        print(f"   + GeoJSON: {geojson_file.name}")

    # 3. Shapefiles Individuais empacotados em ZIP
    print(f"\n[3/3] Gerando pacote Shapefile completo (.zip para QGIS):")
    shp_temp_dir = out_path / "shapefiles_temp"
    if shp_temp_dir.exists():
        shutil.rmtree(shp_temp_dir, ignore_errors=True)
    shp_temp_dir.mkdir(parents=True, exist_ok=True)

    for layer_key, gdf in gdfs.items():
        shp_file = shp_temp_dir / f"{layer_key}.shp"
        gdf.to_file(shp_file, driver="ESRI Shapefile", encoding="utf-8")
        cpg_file = shp_temp_dir / f"{layer_key}.cpg"
        with open(cpg_file, "w", encoding="utf-8") as f:
            f.write("UTF-8\n")
        print(f"   + Shapefile gerado: {layer_key}.shp (.shx, .dbf, .prj, .cpg)")

    # Instrucoes de uso no QGIS
    readme_file = shp_temp_dir / "LEIAME_QGIS.txt"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(f"""================================================================================
CAMADAS VETORIAIS PARA QGIS - PROJETO UNESCO & ITAIPU PARQUETEC
UNES 2369/2025 - Selecao de Pontos para Afericao
================================================================================

COMO ABRIR NO QGIS:
1. Abra o QGIS (versao 3.0 ou superior).
2. Arraste e solte este arquivo .ZIP diretamente para a tela do QGIS.
   O QGIS exibira uma janela para marcar quais camadas deseja carregar:
   - 1_pontos_afericao_selecionados : Pontos de afericao escolhidos no painel
   - 2_pontos_sobreposicao_fluxos  : Pontos de sobreposicao classificados por frequencia
   - 3_manchas_fluxo_rotas          : Trajetorias e pontos de fluxo TomTom
   - 4_atrativos_turisticos         : Atrativos turisticos mapeados
3. Como alternativa, utilize o arquivo 'pontos_afericao_unesco.gpkg' (GeoPackage).

DETALHES DO SISTEMA DE COORDENADAS (CRS):
- Projecao: {crs_name}
- Codigo EPSG: {crs_str}
- Unidade: Graus Decimais

CAMADAS E CAMPOS:
1. pontos_afericao_selecionados:
   - MUNICIPIO, ORDEM, NOME, LATITUDE, LONGITUDE, JUSTIFIC, DATA_HORA

2. pontos_sobreposicao_fluxos:
   - MUNICIPIO, RANK, FREQ, LATITUDE, LONGITUDE

3. manchas_fluxo_rotas:
   - MUNICIPIO, ID_ROTA, NOME_ROTA, LATITUDE, LONGITUDE

4. atrativos_turisticos:
   - MUNICIPIO, ID_ATRATIV, NOME, RANK_PROD4, LATITUDE, LONGITUDE
================================================================================
""")

    zip_dest = out_path / "pontos_afericao_unesco_shapefile.zip"
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in shp_temp_dir.iterdir():
            if f.is_file():
                zf.write(f, arcname=f.name)

    shutil.rmtree(shp_temp_dir, ignore_errors=True)

    print("\n" + "="*70)
    print("EXPORTACAO CONCLUIDA COM SUCESSO!")
    print("="*70)
    print(f"Diretorio de saida: {out_path.resolve()}")
    print(f"1. [Shapefile ZIP] -> {zip_dest.name} (Contem todas as 4 camadas)")
    print(f"2. [GeoPackage]    -> {gpkg_file.name} (Multi-camadas nativo QGIS)")
    print(f"3. [GeoJSONs]      -> {len(gdfs)} arquivos .geojson individuais")
    print("\nResumo das camadas processadas:")
    for k, gdf in gdfs.items():
        print(f"   - {k}: {len(gdf)} feicoes")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="Exportar camadas completas (Pontos Selecionados, Sobreposicao, Manchas de Fluxo e Atrativos) para QGIS.")
    parser.add_argument("--csv", "-c", type=str, default=None, help="Caminho para o arquivo CSV de pontos selecionados.")
    parser.add_argument("--out", "-o", type=str, default="camadas_qgis", help="Diretorio de saida para os arquivos GIS.")
    parser.add_argument("--crs", type=int, default=4326, choices=[4326, 4674], help="Codigo EPSG (4326 = WGS84, 4674 = SIRGAS 2000).")
    
    args = parser.parse_args()
    
    csv_file = args.csv
    if not csv_file:
        csv_file = find_latest_csv()
        if csv_file:
            print(f"Arquivo CSV de pontos selecionados detectado: {csv_file}")
            
    layers = {}
    
    # 1. Pontos Selecionados
    df_sel = load_selected_points(csv_file)
    if df_sel is not None and len(df_sel) > 0:
        layers["1_pontos_afericao_selecionados"] = df_sel
        
    # 2. Pontos de Sobreposicao
    df_sobre = load_overlap_clusters()
    if df_sobre is not None and len(df_sobre) > 0:
        layers["2_pontos_sobreposicao_fluxos"] = df_sobre
        
    # 3. Manchas de Fluxo / Rotas
    df_rotas = load_flow_routes()
    if df_rotas is not None and len(df_rotas) > 0:
        layers["3_manchas_fluxo_rotas"] = df_rotas
        
    # 4. Atrativos Turisticos
    df_att = load_attractions()
    if df_att is not None and len(df_att) > 0:
        layers["4_atrativos_turisticos"] = df_att
        
    if not layers:
        print("Erro: Nenhuma camada valida encontrada para exportacao.")
        sys.exit(1)
        
    try:
        export_all_qgis_layers(layers, output_dir=args.out, epsg_code=args.crs)
    except Exception as e:
        print(f"Erro durante a geracao dos arquivos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
