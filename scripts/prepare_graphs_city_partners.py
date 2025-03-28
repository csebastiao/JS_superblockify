# -*- coding: utf-8 -*-
"""
Create a graph ready for superblockify partitioner algorithm from graph obtained by OSMnx.
"""


import os
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
        folder_sb = folder_graph + city_name
        if not os.path.exists(folder_sb):
            os.makedirs(folder_sb)
        G = load_graphml_dtypes(folder_graph_OSM + file_graph)
        poly = gpd.read_file(f"./data/raw/city_partners_public/{city_name}.gpkg")
        G = make_graph_compatible(G, poly=poly)
        ox.save_graphml(G, folder_sb + "/" + city_name + ".graphml")
