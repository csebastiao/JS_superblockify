# -*- coding: utf-8 -*-
"""
Create a graph ready for superblockify partitioner algorithm from graph obtained by OSMnx.
"""


import os
import osmnx as ox
import superblockify as sb


if __name__ == "__main__":
    folder_graph_OSM = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    folder_plot = "./plots/city_partners_public/"
    sb.config.Config.GHSL_DIR = "./data/raw"
    # Get all files
    for file_graph in [
        filename
        for filename in os.listdir(folder_graph_OSM)
        if filename.endswith(".graphml")
    ]:
        city_name = file_graph.split(".")[0]
        if city_name != "Milan_Metropolitan":
            folder_sb = folder_graph + city_name
            if not os.path.exists(folder_sb):
                print(city_name)
                os.makedirs(folder_sb)
                G = ox.load_graphml(folder_graph_OSM + file_graph)
                ## TODO based on Braga example
                ox.save_graphml(G, folder_sb + "/" + city_name + ".graphml")
