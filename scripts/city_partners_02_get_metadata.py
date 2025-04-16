# -*- coding: utf-8 -*-
"""
Get some data on all graphs
"""

import pandas as pd
import geopandas as gpd
import os
from superblockify.utils import load_graphml_dtypes


if __name__ == "__main__":
    folder_graph_names = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    folder_poly = "./data/raw/city_partners_public/"
    all_arr = []
    # Get all files
    for file_graph in [
        filename
        for filename in os.listdir(folder_graph_names)
        if filename.endswith(".graphml")
    ]:
        city_name = file_graph.split(".")[0]
        folder_sb = folder_graph + city_name
        if not os.path.exists(folder_sb):
            os.makedirs(folder_sb)
        G = load_graphml_dtypes(folder_graph + city_name + "/" + city_name + ".graphml")
        poly = gpd.read_file(folder_poly + city_name + ".gpkg")
        poly = poly.to_crs(G.graph["crs"])
        area = poly.geometry[0].area / 1000000
        roadsum = sum([G.edges[e]["length"] for e in G.edges]) / 1000
        popsum = sum([G.edges[e]["population"] for e in G.edges])
        all_arr.append(
            [
                city_name,
                area,
                len(G.edges),
                roadsum,
                roadsum / area,
                popsum,
                popsum / area,
            ]
        )
    df = pd.DataFrame(
        all_arr,
        columns=[
            "Cities",
            "Area",
            "Number of edges",
            "Total road length",
            "Road density",
            "Total estimated population",
            "Population density",
        ],
    )
    df.to_json("./data/processed/city_partners_public/metadata_cities.json")
