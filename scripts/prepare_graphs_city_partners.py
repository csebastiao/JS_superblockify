# -*- coding: utf-8 -*-
"""
Create a graph ready for superblockify partitioner algorithm from graph obtained by OSMnx.
"""


import os
import osmnx as ox
import shapely
import superblockify as sb


if __name__ == "__main__":
    folder_graph_OSM = "./data/processed/city_partners_public/graphs_OSM/"
    folder_graph = "./data/processed/city_partners_public/graphs_SB/"
    folder_plot = "./plots/city_partners_public/"
    # Get all polygon files
    for file_graph in [
        filename for filename in os.listdir(folder_graph_OSM) if filename.endswith(".gpkg")
    ]:
        city_name = file_graph.split(".")[0]
        folder_sb = folder_graph + city_name
        if not os.path.exists(folder_sb):
            os.makedirs(folder_sb)
        G = ox.load_graphml(file_graph)
        crs = G.graph["crs"]
        created_date = G.graph["created_date"]
        G = ox.project_graph(G)
        proj_crs = G.graph["crs"]
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        streetgeom = gdf_edges.geometry.unary_union
        bb = streetgeom.bounds
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        sb.add_edge_population(G)
        G = ox.project_graph(G, crs)
        G = ox.routing.add_edge_speeds(G)
        G = ox.routing.add_edge_travel_times(G)
        ox.add_edge_bearings(G)
        G.graph = sb.graph_stats.basic_graph_stats(G, area=area)
        G.graph["crs"] = crs
        G.graph["created_date"] = created_date
        G.graph["area"] = area
        G.graph["edge_population"] = True
        G.graph["boundary"] = shapely.Polygon([[bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]], [bb[0], bb[1]]])
        G.graph["boundary_crs"] = proj_crs
        ox.save_graphml(G, folder_sb + city_name + ".graphml")