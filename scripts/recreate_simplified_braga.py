# -*- coding: utf-8 -*-
"""
From a list of LineStrings, create a simplified networkx street network of Braga. The list of LineStrings is a manually modified version of the gpkg created by create_graph_braga.py.
"""

import geopandas as gpd
import momepy as mp
import networkx as nx
import osmnx as ox
import shapely

if __name__ == "__main__":
    folder_braga = "./data/processed/braga_private/"
    # Read the GeoPackage manually made from QGIS
    gdf = gpd.read_file(folder_braga + "Braga_simplified.gpkg")
    # Remove invalid geometry
    gdf_filt = gdf[gdf.geometry.apply(lambda x: True if len(x.geoms) == 1 else False)]
    gdf_ls = gdf_filt.copy()
    # Transform MultiLineString into LineString
    gdf_ls.geometry = gdf_ls.geometry.apply(lambda x: x.geoms[0])
    # Get a networkx MultiDigraph and add node coordinates
    G = mp.gdf_to_nx(gdf_ls, multigraph=True, directed=True, length="length")
    for n in G:
        G.nodes[n]["x"] = n[0]
        G.nodes[n]["y"] = n[1]
    H = G.copy()
    # Segmentize by having all edges being straight edges so osmnx can simplify it
    for e in G.edges:
        coord = G.edges[e]["geometry"].coords[:]
        if len(G.edges[e]["geometry"].coords[:]) > 2:
            attr = G.edges[e]["attribute"]
            for i in range(len(coord) - 1):
                H.add_node(coord[i + 1], x=coord[i + 1][0], y=coord[i + 1][1])
                egeom = shapely.LineString([coord[i], coord[i + 1]])
                H.add_edge(
                    coord[i],
                    coord[i + 1],
                    0,
                    geometry=egeom,
                    length=egeom.length,
                    attribute=attr,
                )
            H.remove_edge(*e)
    G = nx.convert_node_labels_to_integers(H)
    G = ox.simplify_graph(G)
    ox.save_graphml(
        G,
        filepath=folder_braga + "Braga_simplified.graphml",
    )