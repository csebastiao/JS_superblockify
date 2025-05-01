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
import numpy as np


def avoid_zerodiv_matrix(num_mat, den_mat):
    """
    Divide one matrix by another while replacing numerator divided by 0 by 0.
    Example: [[1, 2],   divided by [[1, 0],    will give out [[1, 0],
              [3, 4]]               [6, 0]]                   [0.5, 0]]
    """
    return np.divide(
        num_mat,
        den_mat,
        out=np.zeros_like(num_mat),
        where=((den_mat != 0) & (den_mat != np.inf) & (num_mat != np.inf)),
    )


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
            G = part.graph.copy()
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
                else:
                    for e in p["subgraph"].edges:
                        for attr in p["subgraph"].edges[e]:
                            G_filt.edges[e][attr] = p["subgraph"].edges[e][attr]
                        G_filt.edges[e]["ltn_name"] = None
                        G_filt.edges[e]["in_ltn"] = False
                for e in p["subgraph"].edges:
                    for attr in p["subgraph"].edges[e]:
                        G_all.edges[e][attr] = p["subgraph"].edges[e][attr]
                    G_all.edges[e]["ltn_name"] = p["name"]
                    G_all.edges[e]["in_ltn"] = True
            for H in [G_all, G_filt]:
                for e in part.sparsified.edges:
                    for attr in part.sparsified.edges[e]:
                        H.edges[e][attr] = part.sparsified.edges[e][attr]
                    H.edges[e]["ltn_name"] = None
                    H.edges[e]["in_ltn"] = False
            filt_part = pd.DataFrame(filt_part)
            partitions_travel = part.get_partition_nodes()
            partitions_travel_filt = {
                partition["name"]: {
                    "subgraph": partition["subgraph"],
                    "nodes": list(
                        partition["nodes"]
                    ),  # exclusive nodes inside the subgraph
                    "nodelist": list(
                        partition["subgraph"]
                    ),  # also nodes shared with the
                    # sparsified graph or on partition boundaries
                }
                for partition in partitions_travel
                if partition["name"] in list(filt_part["name"])
            }
            filt_sparsified = G.edge_subgraph(
                [e for e in G_filt.edges if G_filt.edges[e]["in_ltn"] is False]
            )
            partitions_travel_filt["sparsified"] = {
                "subgraph": filt_sparsified,
                "nodes": list(filt_sparsified.nodes),
                "nodelist": list(filt_sparsified.nodes),
            }
            dg, _ = sb.metrics.distances.calculate_path_distance_matrix(
                G, weight="length"
            )
            dgr, _ = sb.metrics.distances.shortest_paths_restricted(
                G, partitions_travel_filt, "length", list(G.nodes)
            )
            rel_travel = avoid_zerodiv_matrix(dgr, dg)
            G_filt.graph["avg_rel_travel"] = np.sum(rel_travel) / np.count_nonzero(
                rel_travel
            )
            max_detour = np.where(rel_travel == np.max(rel_travel))
            G_filt.graph["max_detour"] = (
                dgr[max_detour[0][0]][max_detour[1][0]]
                - dg[max_detour[0][0]][max_detour[1][0]]
            )
            partitions_travel_all = {
                partition["name"]: {
                    "subgraph": partition["subgraph"],
                    "nodes": list(
                        partition["nodes"]
                    ),  # exclusive nodes inside the subgraph
                    "nodelist": list(
                        partition["subgraph"]
                    ),  # also nodes shared with the
                    # sparsified graph or on partition boundaries
                }
                for partition in partitions_travel
            }
            all_sparsified = G.edge_subgraph(
                [e for e in G_all.edges if G_all.edges[e]["in_ltn"] is False]
            )
            partitions_travel_all["sparsified"] = {
                "subgraph": all_sparsified,
                "nodes": list(all_sparsified.nodes),
                "nodelist": list(all_sparsified.nodes),
            }
            dgr, _ = sb.metrics.distances.shortest_paths_restricted(
                G, partitions_travel_all, "length", list(G.nodes)
            )
            rel_travel = avoid_zerodiv_matrix(dgr, dg)
            G_all.graph["avg_rel_travel"] = np.sum(rel_travel) / np.count_nonzero(
                rel_travel
            )
            max_detour = np.where(rel_travel == np.max(rel_travel))
            G_all.graph["max_detour"] = (
                dgr[max_detour[0][0]][max_detour[1][0]]
                - dg[max_detour[0][0]][max_detour[1][0]]
            )
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
