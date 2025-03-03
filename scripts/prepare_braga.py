# -*- coding: utf-8 -*-
"""
Create a Braga graph ready for superblockify partitioner algorithm.
"""


import osmnx as ox
import shapely
import superblockify as sb


if __name__ == "__main__":
    folder_graph = "./data/processed/braga_private/"
    sb.config.Config.GHSL_DIR = "./data/processed/ghsl"
    for suffix in ["simplified", "wode"]:
        G = ox.load_graphml(folder_graph + f"Braga_{suffix}.graphml")
        for n in G.nodes:
            G.nodes[n]["street_count"] = len(
                set(list(G.neighbors(n)) + list(G.predecessors(n)))
            )
        crs = G.graph["crs"]
        G = ox.project_graph(G, to_crs="EPSG:3763")
        proj_crs = "EPSG:3763"
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        streetgeom = gdf_edges.geometry.unary_union
        bb = streetgeom.bounds
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        sb.add_edge_population(G)
        G = ox.project_graph(G, to_crs=crs)
        G = ox.routing.add_edge_speeds(G)
        G = ox.routing.add_edge_travel_times(G)
        ox.add_edge_bearings(G)
        G.graph = sb.graph_stats.basic_graph_stats(G, area=area)
        G.graph["crs"] = crs
        G.graph["created_date"] = "03-03-2025"
        G.graph["area"] = area
        G.graph["edge_population"] = True
        G.graph["boundary"] = shapely.Polygon(
            [[bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]], [bb[0], bb[1]]]
        )
        G.graph["boundary_crs"] = proj_crs
        for e in G.edges:
            if "fid" in G.edges[e]:
                G.edges[e].pop("fid")
        ox.save_graphml(G, folder_graph + f"Braga_{suffix}_sbready.graphml")
