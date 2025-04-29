# -*- coding: utf-8 -*-
"""
Filter all LTNs for visualization purposes.
"""


import os
import geopandas as gpd
import tqdm


if __name__ == "__main__":
    folder_graph_names = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    for file_graph in tqdm.tqdm(
        sorted(
            [
                filename
                for filename in os.listdir(folder_graph_names)
                if filename.endswith(".graphml")
            ]
        )
    ):
        city_name = file_graph.split(".")[0]
        for part_name in ["residential", "betweenness"]:
            df = gpd.read_file(
                folder_graph + f"{city_name}/{city_name}_{part_name}.gpkg",
                layer="ltns",
            )
            df_filt = df[
                (df["geometry"].area < 921600)
                & (df["geometry"].area > 25600)
                & (df["n"] > 5)
            ]
            df_filt.to_file(
                folder_graph + f"{city_name}/{city_name}_{part_name}_filt_ltns.gpkg"
            )
