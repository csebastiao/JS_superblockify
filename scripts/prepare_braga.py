# -*- coding: utf-8 -*-
"""
Create a Braga graph ready for superblockify partitioner algorithm.
"""


import shapely
import networkx as nx
import geopandas as gpd
import osmnx as ox
import superblockify as sb
from superblockify.utils import load_graphml_dtypes, extract_attributes
from superblockify.graph_stats import basic_graph_stats
from superblockify.population import add_edge_cells


def make_graph_compatible(G, poly=None, proj_crs=None):
    "Get a graph extracted via OSMnx compatible with Superblockify BasePartitioner."
    G = G.copy()
    ox.add_edge_bearings(G)
    G = ox.project_graph(G, to_crs=proj_crs)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    street_count = ox.stats.count_streets_per_node(G)
    nx.set_node_attributes(G, values=street_count, name="street_count")
    G = extract_attributes(
        G,
        edge_attributes={
            "geometry",
            "osmid",
            "length",
            "highway",
            "speed_kph",
            "travel_time",
            "bearing",
        },
        node_attributes={"y", "x", "lat", "lon", "osmid", "street_count"},
    )
    add_edge_cells(G)
    sb.add_edge_population(G)
    if poly is None:
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        streetgeom = gdf_edges.geometry.unary_union
        bb = streetgeom.bounds
        poly = gpd.GeoDataFrame(
            shapely.Polygon(
                [[bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]], [bb[0], bb[1]]]
            ),
            crs=proj_crs,
        )
    G.graph["boundary_crs"] = poly.crs
    G.graph["boundary"] = poly.geometry[0]
    G.graph["area"] = G.graph["boundary"].area
    G.graph.update(basic_graph_stats(G, area=G.graph["area"]))
    return G


if __name__ == "__main__":
    folder_graph = "./data/processed/braga_private/"
    sb.config.Config.GHSL_DIR = "./data/processed/ghsl"
    graph_name = "Braga_raw"
    G = load_graphml_dtypes(folder_graph + graph_name + ".graphml")
    poly = gpd.read_file(
        "./data/raw/braga_private/SuperblockifyStudy_Limit/SuperblockifyStudy_Limit.shp"
    )
    G = make_graph_compatible(G, poly=poly, proj_crs=poly.crs)
    ox.save_graphml(G, folder_graph + graph_name + "_sbready.graphml")
