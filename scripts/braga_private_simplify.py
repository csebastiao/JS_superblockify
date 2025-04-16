# -*- coding: utf-8 -*-
"""
From a list of LineStrings, create a simplified networkx street network of Braga. The list of LineStrings is a manually modified version of the gpkg created by create_graph_braga.py.
"""

import geopandas as gpd
import momepy as mp
import networkx as nx
import osmnx as ox
import shapely
import pandas as pd


if __name__ == "__main__":
    folder_braga = "./data/processed/braga_private/"
    # Read the GeoPackage manually made from QGIS
    gdf = gpd.read_file(folder_braga + "Braga_manual.gpkg")
    # Remove invalid geometry
    gdf_filt = gdf[gdf.geometry.apply(lambda x: True if len(x.geoms) == 1 else False)]
    gdf_ls = gdf_filt.copy()
    # Transform MultiLineString into LineString
    gdf_ls.geometry = gdf_ls.geometry.apply(lambda x: x.geoms[0])
    gdf_ls = gdf_ls.to_crs(epsg=3763)
    # Get a networkx MultiDigraph and add node coordinates
    G = mp.gdf_to_nx(gdf_ls, multigraph=True, directed=True, length="length")
    for n in G:
        G.nodes[n]["x"] = n[0]
        G.nodes[n]["y"] = n[1]
    G = G.to_undirected()
    G = G.to_directed()
    H = G.copy()
    # Segmentize by having all edges being straight edges so osmnx can simplify it
    for e in G.edges:
        coord = G.edges[e]["geometry"].coords[:]
        if len(G.edges[e]["geometry"].coords[:]) > 2:
            # attr = G.edges[e]["attribute"] if completely new
            # else can use the one below
            attr = G.edges[e]
            attr.pop("geometry")
            attr.pop("length")
            attr.pop("osmid")
            for i in range(len(coord) - 1):
                H.add_node(coord[i + 1], x=coord[i + 1][0], y=coord[i + 1][1])
                egeom = shapely.LineString([coord[i], coord[i + 1]])
                H.add_edge(
                    coord[i],
                    coord[i + 1],
                    0,
                    geometry=egeom,
                    length=egeom.length,
                    **attr,
                )
            H.remove_edge(*e)
    G = nx.convert_node_labels_to_integers(H)
    G = ox.simplify_graph(G)
    G = ox.project_graph(G, to_crs="epsg:4326")
    # Flatten list of list and values
    for e in G.edges:
        for attr in G.edges[e]:
            if isinstance(G.edges[e][attr], list):
                output = []
                for val in G.edges[e][attr]:
                    if isinstance(val, str):
                        if "[" in val:
                            vals = val.split(", ")
                            vals[0] = vals[0][1:]
                            vals[-1] = vals[-1][:-1]
                            for single in vals:
                                output.append(single)
                        else:
                            output.append(val)
                    else:
                        output.append(val)
                G.edges[e][attr] = output
    ox.save_graphml(
        G,
        filepath=folder_braga + "Braga_simplified.graphml",
    )
    gdfs = ox.graph_to_gdfs(G)
    geom = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=False))
    geom = geom.drop("fid", axis=1)
    geom.to_file(folder_braga + "Braga_simplified.gpkg")
