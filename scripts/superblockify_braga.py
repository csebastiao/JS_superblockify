# -*- coding: utf-8 -*-
"""
Run Superblockify on Braga private limits.
"""


import superblockify as sb
import shapely


if __name__ == "__main__":
    sb.config.Config.GRAPH_DIR = "./data/processed/braga_private"
    sb.config.Config.RESULTS_DIR = "./data/processed/braga_private/sb_results"
    graph_name = "Braga_raw"
    part_name = "shierarchy"
    part = sb.StreetHierarchyPartitioner(
        name=graph_name + "_" + part_name,
        city_name=graph_name + "_sbready",
        search_str="Braga, PT",
        unit="time",
    )
    for e in part.graph.edges:
        part.graph.edges[e]["cell"] = shapely.from_wkt(part.graph.edges[e]["cell"])
    part.run(
        calculate_metrics=True,
        make_plots=True,
        replace_max_speeds=False,
        level=4,
    )
    part.save()
    sb.save_to_gpkg(
        part,
        save_path=sb.config.Config.GRAPH_DIR
        + "/"
        + graph_name
        + "_"
        + part_name
        + ".gpkg",
        ltn_boundary=True,
    )
