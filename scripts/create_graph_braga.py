# -*- coding: utf-8 -*-
"""
Create graph for Braga tailored with the city.
"""

import pandas as pd
import geopandas as gpd
import osmnx as ox


if __name__ == "__main__":
    folder_poly = "./data/raw/braga_private/"
    folder_results = "./data/processed/braga_private/"
    city_name = "Braga"
    gdf = gpd.read_file(
        folder_poly + "SuperblockifyStudy_Limit/SuperblockifyStudy_Limit.shp"
    )
    # Add a buffer to get surrounding streets
    gdf = gdf.buffer(50)
    gdf = gdf.to_crs(epsg=4326)
    poly = gdf.geometry[0]
    # Extract non-simplified so we can simplify after removing nodes
    G = ox.graph_from_polygon(poly, simplify=False)
    # Take the rawest version
    G_raw = ox.simplify_graph(G)
    ox.save_graphml(G_raw, folder_results + city_name + "_raw.graphml")
    gdfs = ox.graph_to_gdfs(G_raw)
    geom = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=False))
    geom.to_file(folder_results + city_name + "_raw.gpkg")
    # Remove dead-ends
    keep = True
    while keep is True:
        keep = False
        H = G.copy()
        for n in G.nodes():
            if (
                len(set([m for m in G.successors(n)] + [m for m in G.predecessors(n)]))
                < 2
            ):
                H.remove_node(n)
                keep = True
        G = H
    # Simplify without dead-ends
    G = ox.simplify_graph(G)
    # Remove again dead-ends that were connected by multiple roads
    keep = True
    while keep is True:
        keep = False
        H = G.copy()
        for n in G.nodes():
            if (
                len(set([m for m in G.successors(n)] + [m for m in G.predecessors(n)]))
                < 2
            ):
                H.remove_node(n)
                keep = True
        G = H
    ox.save_graphml(G, folder_results + city_name + "_wode.graphml")
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
        filepath=folder_results + "picture_graph.png",
        dpi=300,
        close=True,
        show=False,
    )
    # Save geometry of edges and nodes as single gpkg to use GIS software for dynamic visualization and analysis
    gdfs = ox.graph_to_gdfs(G)
    geom = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=False))
    geom.to_file(folder_results + city_name + "_wode.gpkg")
