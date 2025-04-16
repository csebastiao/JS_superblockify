# -*- coding: utf-8 -*-
"""
Run Superblockify on {city_name} private limits.
"""

import os
import superblockify as sb
import shapely
import tqdm
import osmnx as ox
import pandas as pd


if __name__ == "__main__":
    folder_graph_OSM = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    folder_plot = "./plots/city_partners_public/"
    sb.config.Config.GHSL_DIR = "./data/raw"
    # Get all files
    for file_graph in tqdm.tqdm(
        sorted(
            [
                filename
                for filename in os.listdir(folder_graph_OSM)
                if filename.endswith(".graphml")
            ]
        )
    ):
        city_name = file_graph.split(".")[0]
        G = sb.utils.load_graphml_dtypes(
            f"./data/processed/city_partners_public/graphs_SB/{city_name}/{city_name}.graphml"
        )
        sb.config.Config.GRAPH_DIR = (
            "./data/processed/city_partners_public/graphs_SB/" + city_name
        )
        sb.config.Config.RESULTS_DIR = sb.config.Config.GRAPH_DIR + "/sb_results"
        for part_name, func in [
            ["residential", sb.ResidentialPartitioner],
            ["betweenness", sb.BetweennessPartitioner],
        ]:
            part = func(
                name=city_name + "_" + part_name,
                city_name=city_name,
                search_str=city_name,
                unit="time",
            )
            for e in part.graph.edges:
                part.graph.edges[e]["cell"] = shapely.from_wkt(
                    part.graph.edges[e]["cell"]
                )
            part.run(
                calculate_metrics=True,
                make_plots=False,
                replace_max_speeds=False,
            )
            part.save()
            G_all = G.copy()
            G_filt = G.copy()
            filt_part = []
            all_part = pd.DataFrame(part.partitions)
            for p in part.partitions:
                if (p["area"] > 25600) & (p["area"] < 921600) & (p["n"] > 5):
                    filt_part.append(p)
                    for e in p["subgraph"].edges:
                        for attr in p["subgraph"].edges[e]:
                            G_filt.edges[e][attr] = p["subgraph"].edges[e][attr]
                        G_filt.edges[e]["ltn_name"] = p["name"]
                        G_filt.edges[e]["in_ltn"] = True
                for e in p["subgraph"].edges:
                    if G_all.has_edge(*e):
                        for attr in p["subgraph"].edges[e]:
                            G_all.edges[e][attr] = p["subgraph"].edges[e][attr]
                        G_all.edges[e]["ltn_name"] = p["name"]
                        G_all.edges[e]["in_ltn"] = True
            for H in [G_all, G_filt]:
                for e in part.sparsified.edges:
                    if H.has_edge(*e):
                        for attr in part.sparsified.edges[e]:
                            H.edges[e][attr] = part.sparsified.edges[e][attr]
                        H.edges[e]["ltn_name"] = None
                        H.edges[e]["in_ltn"] = False
            # TODO understand how to get the average travel distance increase on the entire graph
            # TODO Solve issue of edges not in partitions and not in sparsified
            filt_part = pd.DataFrame(filt_part)
            filt_part = filt_part.drop("subgraph", axis=1)
            all_part = all_part.drop("subgraph", axis=1)
            all_part.to_json(
                sb.config.Config.RESULTS_DIR
                + f"/{city_name}_{part_name}/all_partitions.json"
            )
            filt_part.to_json(
                sb.config.Config.RESULTS_DIR
                + f"/{city_name}_{part_name}/filt_partitions.json"
            )
            ox.save_graphml(
                G_all,
                sb.config.Config.RESULTS_DIR
                + f"/{city_name}_{part_name}/{city_name}_all.graphml",
            )
            ox.save_graphml(
                G_filt,
                sb.config.Config.RESULTS_DIR
                + f"/{city_name}_{part_name}/{city_name}_filt.graphml",
            )
            sb.save_to_gpkg(
                part,
                save_path=sb.config.Config.GRAPH_DIR
                + "/"
                + city_name
                + "_"
                + part_name
                + ".gpkg",
                ltn_boundary=True,
            )
