# -*- coding: utf-8 -*-
"""
Create graph for all cities from gpkg file with a polygon in each, see "./data/raw/city_partners_public/00_source.txt" for more information. 
"""


import os
import pandas as pd
import geopandas as gpd
import osmnx as ox
import tqdm
import networkx as nx


if __name__ == "__main__":
    folder_poly = "./data/raw/city_partners_public/"
    folder_graph = "./data/processed/city_partners_public/graphs_OSM/"
    folder_geom = "./data/processed/city_partners_public/geoms/"
    folder_plot = "./plots/city_partners_public/graphs/"
    # Get all polygon files
    for file_poly in tqdm.tqdm(
        sorted(
            [
                filename
                for filename in os.listdir(folder_poly)
                if filename.endswith(".gpkg")
            ]
        )
    ):
        city_name = file_poly.split(".")[0]
        poly = gpd.read_file(folder_poly + file_poly).geometry[0]
        # Extract graph from OSM using OSMnx.
        G = ox.graph_from_polygon(poly, network_type="drive", simplify=False)
        toremove = []
        # Remove forbidden places to drive
        for e in G.edges:
            if "access" in G.edges[e]:
                if G.edges[e]["access"] == "no":
                    toremove.append(e)
            if "area" in G.edges[e]:
                G.edges[e].pop("area")
        G.remove_edges_from(toremove)
        # Keep only the LCC and simplify
        G = G.subgraph(max(nx.weakly_connected_components(G), key=len))
        G = ox.simplify_graph(G)
        ox.save_graphml(G, folder_graph + city_name + ".graphml")
        # Save static figure
        ox.plot_graph(
            G,
            figsize=(32, 32),
            bgcolor="white",
            node_color="black",
            edge_color="#285c52",
            node_size=7.5,
            edge_linewidth=1,
            save=True,
            filepath=folder_plot + city_name + ".png",
            dpi=300,
            close=True,
            show=False,
        )
        # Save geometry of edges and nodes as single gpkg to use GIS software for dynamic visualization and analysis
        gdfs = ox.graph_to_gdfs(G)
        geom = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        geom.to_file(folder_geom + city_name + ".gpkg")
