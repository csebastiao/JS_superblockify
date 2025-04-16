# -*- coding: utf-8 -*-
"""
Analyze the obtained results from superblockifying cities.
"""


import pandas as pd
import os
from superblockify.utils import load_graphml_dtypes
import json


if __name__ == "__main__":
    folder_graph_names = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    # Get all files
    for part_name in ["betweenness", "residential"]:
        col_names = [
            "Cities",
            "Amount of superblocks",
            "Share of streets within superblocks",
            "Share of the population within superblocks",
        ]
        if part_name == "betweenness":
            col_names.append("Share of non-residential streets in superblocks")
        for filt_val in ["filt", "all"]:
            all_arr = []
            for file_graph in sorted(
                [
                    filename
                    for filename in os.listdir(folder_graph_names)
                    if filename.endswith(".graphml")
                ]
            ):
                city_name = file_graph.split(".")[0]
                folder_sb = (
                    folder_graph + f"{city_name}/sb_results/{city_name}_{part_name}/"
                )
                print(city_name, folder_sb + f"{city_name}_{filt_val}.graphml")
                G = load_graphml_dtypes(folder_sb + f"{city_name}_{filt_val}.graphml")
                # TODO Solve issue of edges not in partitions and not in sparsified
                for e in G.edges:
                    if "in_ltn" not in G.edges[e]:
                        G.edges[e]["in_ltn"] = "False"
                ltn_streets = [e for e in G.edges if G.edges[e]["in_ltn"] == "True"]
                roadsum = round(
                    100
                    * sum([G.edges[e]["length"] for e in ltn_streets])
                    / sum([G.edges[e]["length"] for e in G.edges]),
                    1,
                )
                popsum = round(
                    100
                    * sum([G.edges[e]["population"] for e in ltn_streets])
                    / sum([G.edges[e]["population"] for e in G.edges]),
                    1,
                )
                with open(folder_sb + f"{filt_val}_partitions.json") as f:
                    partitions = json.load(f)
                col_to_add = [
                    city_name,
                    len(partitions["name"]),
                    roadsum,
                    popsum,
                ]
                if part_name == "betweenness":
                    res_streets = [
                        e for e in G.edges if G.edges[e]["highway"] == "residential"
                    ]
                    col_to_add.append(
                        round(
                            100
                            * len([e for e in res_streets if e in ltn_streets])
                            / len(res_streets),
                            1,
                        )
                    )
                all_arr.append(col_to_add)
            df = pd.DataFrame(all_arr, columns=col_names)
            df.to_json(
                f"./data/processed/city_partners_public/results_cities_{part_name}_{filt_val}.json"
            )
