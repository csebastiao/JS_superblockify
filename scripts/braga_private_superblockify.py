# -*- coding: utf-8 -*-
"""
Create graph for Braga tailored with the city.
"""

import pandas as pd
import geopandas as gpd
import osmnx as ox
import shapely
import networkx as nx
import superblockify as sb
from superblockify.utils import extract_attributes
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
    G = ox.graph_from_polygon(poly, simplify=False, network_type="all")
    # Take the rawest version
    G_raw = ox.simplify_graph(G, edge_attrs_differ=["highway"])
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
    G = ox.simplify_graph(G, edge_attrs_differ=["highway"])
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
    folder_graph = "./data/processed/braga_private/"
    sb.config.Config.GHSL_DIR = "./data/processed/ghsl"
    graph_name = "Braga_raw"
    poly = gpd.read_file(
        "./data/raw/braga_private/SuperblockifyStudy_Limit/SuperblockifyStudy_Limit.shp"
    )
    G = make_graph_compatible(G, poly=poly, proj_crs=poly.crs)
    ox.save_graphml(G, folder_graph + graph_name + "_sbready.graphml")
    sb.config.Config.GRAPH_DIR = "./data/processed/braga_private"
    sb.config.Config.RESULTS_DIR = "./data/processed/braga_private/sb_results"
    part_name = "residential"
    part = sb.ResidentialPartitioner(
        name=graph_name + "_" + part_name,
        city_name=graph_name + "_sbready",
        search_str="Braga, PT",
        unit="time",
    )
    for e in part.graph.edges:
        part.graph.edges[e]["cell"] = shapely.from_wkt(part.graph.edges[e]["cell"])
    part.run(
        calculate_metrics=True,
        make_plots=True,
        replace_max_speeds=False,
        level=4,
    )
    part.save()
    sb.save_to_gpkg(
        part,
        save_path=sb.config.Config.GRAPH_DIR
        + "/"
        + graph_name
        + "_"
        + part_name
        + ".gpkg",
        ltn_boundary=True,
    )
