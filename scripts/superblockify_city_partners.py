# -*- coding: utf-8 -*-
"""
Run Superblockify on {city_name} private limits.
"""

import os
import superblockify as sb
import shapely
import tqdm


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
        sb.config.Config.GRAPH_DIR = (
            "./data/processed/city_partners_public/graphs_SB/" + city_name
        )
        sb.config.Config.RESULTS_DIR = sb.config.Config.GRAPH_DIR + "/sb_results"
        if not os.path.exists(sb.config.Config.GRAPH_DIR + "/sb_results"):
            part_name = "residential"
            part = sb.ResidentialPartitioner(
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
            part_name = "betweenness"
            part = sb.BetweennessPartitioner(
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
