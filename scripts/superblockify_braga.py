# -*- coding: utf-8 -*-
"""
Run Superblockify on Braga private limits.
"""


import superblockify as sb


if __name__ == "__main__":
    sb.config.Config.GRAPH_DIR = "./data/processed/braga_private"
    sb.config.Config.RESULTS_DIR = "./data/processed/braga_private/sb_results"
    for suffix in ["simplified", "wode"]:
        part = sb.ResidentialPartitioner(
            name=f"Braga_{suffix}_residential",
            city_name=f"Braga_{suffix}_sbready",
            search_str="Braga, PT",
            unit="time",
        )
        part.run(
            calculate_metrics=True,
            make_plots=True,
            replace_max_speeds=False,
        )
        part.save()
        sb.save_to_gpkg(
            part,
            save_path=f"./data/processed/braga_private/Braga_{suffix}_part_residential.gpkg",
            ltn_boundary=True,
        )
        part = sb.BetweennessPartitioner(
            name=f"Braga_{suffix}_betweenness",
            city_name=f"Braga_{suffix}_sbready",
            search_str="Braga, PT",
            unit="time",
        )
        part.run(
            calculate_metrics=True,
            make_plots=True,
            replace_max_speeds=False,
        )
        part.save()
        sb.save_to_gpkg(
            part,
            save_path=f"./data/processed/braga_private/Braga_{suffix}_part_betweenness.gpkg",
            ltn_boundary=True,
        )
