# -*- coding: utf-8 -*-
"""
Create graph for Kozani tailored with the city.
"""

import pandas as pd
import shapely
import networkx as nx
import geopandas as gpd
import osmnx as ox
import superblockify as sb
from superblockify.utils import load_graphml_dtypes, extract_attributes
from superblockify.graph_stats import basic_graph_stats
from superblockify.population import add_edge_cells
from superblockify.partitioning import ResidentialPartitioner, EdgeAttributePartitioner


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
    folder_poly = "./data/raw/kozani_private/"
    folder_results = "./data/processed/kozani_private/"
    city_name = "Kozani"
    gdf_poly = gpd.read_file(folder_poly + "NEIGHBORHOODS.shp")
    # Add a buffer to get surrounding streets
    gdf_poly = gdf_poly.buffer(50)
    gdf_poly_crs = gdf_poly.crs
    gdf_poly = gdf_poly.to_crs(epsg=4326)
    # Extract non-simplified so we can simplify after removing nodes
    G = ox.graph_from_polygon(
        gdf_poly.geometry.union_all(), simplify=False, network_type="drive"
    )
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
    G = ox.simplify_graph(G)
    # Add geometry attribute to non-simplified edges
    for u, v, k in G.edges:
        if "geometry" not in G.edges[u, v, k]:
            G.edges[u, v, k]["geometry"] = shapely.LineString(
                [[G.nodes[u]["x"], G.nodes[u]["y"]], [G.nodes[v]["x"], G.nodes[v]["y"]]]
            )
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
    gdf_poly = gdf_poly.to_crs(gdf_poly_crs)
    G = make_graph_compatible(G, poly=gdf_poly, proj_crs=gdf_poly.crs)
    # Get metadata
    area = gdf_poly.geometry.union_all().area / 1000000
    roadsum = sum([G.edges[e]["length"] for e in G.edges]) / 1000
    popsum = sum([G.edges[e]["population"] for e in G.edges])
    all_arr = [
        city_name,
        area,
        len(G.edges),
        roadsum,
        roadsum / area,
        popsum,
        popsum / area,
    ]
    nr_roadsum = sum(
        [
            G.edges[e]["length"]
            for e in G.edges
            if G.edges[e]["highway"] != "residential"
        ]
    )
    gdf_school = gpd.read_file(
        "./data/raw/kozani_private/SCHOOLS_KOZANI_JUSTSTREETS.shp"
    )
    gdf_school = gdf_school.to_crs(gdf_poly.crs)
    gdf_buffered = gpd.read_file(
        "./data/raw/kozani_private/JustStreets_SchoolsBufferZones.shp"
    )
    gdf_buffered = gdf_buffered.to_crs(gdf_poly.crs)
    edges_removed = []
    for e in G.edges:
        if any(gdf_buffered.intersects(G.edges[e]["geometry"])):
            G.edges[e]["in_buffer"] = True
            G.edges[e]["sparse"] = 0
            if G.edges[e]["highway"] not in ["residential", "living_street"]:
                edges_removed.append(G.edges[e]["length"])
        else:
            G.edges[e]["in_buffer"] = False
            if G.edges[e]["highway"] in ["residential", "living_street"]:
                G.edges[e]["sparse"] = 0
            else:
                G.edges[e]["sparse"] = 1
    all_arr.append(sum(edges_removed) / nr_roadsum)
    all_arr = [all_arr]
    ox.save_graphml(G, folder_results + city_name + ".graphml")
    df = pd.DataFrame(
        all_arr,
        columns=[
            "Name",
            "Area",
            "Number of edges",
            "Total road length",
            "Road density",
            "Total estimated population",
            "Population density",
            "Removed non-residential edges with school buffers",
        ],
    )
    df.to_json(folder_results + "metadata.json")
    sb.config.Config.GRAPH_DIR = folder_results
    sb.config.Config.RESULTS_DIR = folder_results + "/sb_results"
    # Run residential partitioner
    part = ResidentialPartitioner(
        name=city_name + "_residential",
        city_name=city_name,
        search_str=city_name,
        unit="time",
    )
    for e in part.graph.edges:
        part.graph.edges[e]["cell"] = shapely.from_wkt(part.graph.edges[e]["cell"])
    part.run(
        calculate_metrics=True,
        make_plots=False,
        replace_max_speeds=False,
    )
    part.save()
    G_all = G.copy()
    G_filt = G.copy()
    filt_part = []
    all_part = pd.DataFrame(part.partitions)
    for p in part.partitions:
        if (p["area"] > 25600) & (p["area"] < 921600) & (p["n"] > 5):
            filt_part.append(p)
            for e in p["subgraph"].edges:
                for attr in p["subgraph"].edges[e]:
                    G_filt.edges[e][attr] = p["subgraph"].edges[e][attr]
                G_filt.edges[e]["ltn_name"] = p["name"]
                G_filt.edges[e]["in_ltn"] = True
        for e in p["subgraph"].edges:
            if G_all.has_edge(*e):
                for attr in p["subgraph"].edges[e]:
                    G_all.edges[e][attr] = p["subgraph"].edges[e][attr]
                G_all.edges[e]["ltn_name"] = p["name"]
                G_all.edges[e]["in_ltn"] = True
    for H in [G_all, G_filt]:
        for e in part.sparsified.edges:
            if H.has_edge(*e):
                for attr in part.sparsified.edges[e]:
                    H.edges[e][attr] = part.sparsified.edges[e][attr]
                H.edges[e]["ltn_name"] = None
                H.edges[e]["in_ltn"] = False
    filt_part = pd.DataFrame(filt_part)
    filt_part = filt_part.drop("subgraph", axis=1)
    all_part = all_part.drop("subgraph", axis=1)
    all_part.to_json(
        sb.config.Config.RESULTS_DIR + f"/{city_name}_residential/all_partitions.json"
    )
    filt_part.to_json(
        sb.config.Config.RESULTS_DIR + f"/{city_name}_residential/filt_partitions.json"
    )
    ox.save_graphml(
        G_all,
        sb.config.Config.RESULTS_DIR
        + f"/{city_name}_residential/{city_name}_all.graphml",
    )
    ox.save_graphml(
        G_filt,
        sb.config.Config.RESULTS_DIR
        + f"/{city_name}_residential/{city_name}_filt.graphml",
    )
    sb.save_to_gpkg(
        part,
        save_path=sb.config.Config.GRAPH_DIR
        + "/"
        + city_name
        + "_residential"
        + ".gpkg",
        ltn_boundary=True,
    )
    df = gpd.read_file(
        sb.config.Config.GRAPH_DIR + "/" + city_name + "_residential" + ".gpkg",
        layer="ltns",
    )
    df_filt = df[
        (df["geometry"].area < 921600) & (df["geometry"].area > 25600) & (df["n"] > 5)
    ]
    df_filt.to_file(folder_results + f"{city_name}_residential_filt_ltns.gpkg")
    # Run partitioner taking into account buffer around schools
    part_name = "_buffer"
    part = EdgeAttributePartitioner(
        name=city_name + part_name,
        city_name=city_name,
        search_str=city_name,
        unit="time",
    )
    for e in part.graph.edges:
        part.graph.edges[e]["sparse"] = int(part.graph.edges[e]["sparse"])
        part.graph.edges[e]["cell"] = shapely.from_wkt(part.graph.edges[e]["cell"])
    part.run(
        attribute_name="sparse",
        calculate_metrics=True,
        make_plots=False,
        replace_max_speeds=False,
    )
    part.save()
    G_all = G.copy()
    G_filt = G.copy()
    filt_part = []
    all_part = pd.DataFrame(part.partitions)
    for p in part.partitions:
        if (p["area"] > 25600) & (p["area"] < 921600) & (p["n"] > 5):
            filt_part.append(p)
            for e in p["subgraph"].edges:
                for attr in p["subgraph"].edges[e]:
                    G_filt.edges[e][attr] = p["subgraph"].edges[e][attr]
                G_filt.edges[e]["ltn_name"] = p["name"]
                G_filt.edges[e]["in_ltn"] = True
        for e in p["subgraph"].edges:
            if G_all.has_edge(*e):
                for attr in p["subgraph"].edges[e]:
                    G_all.edges[e][attr] = p["subgraph"].edges[e][attr]
                G_all.edges[e]["ltn_name"] = p["name"]
                G_all.edges[e]["in_ltn"] = True
    for H in [G_all, G_filt]:
        for e in part.sparsified.edges:
            if H.has_edge(*e):
                for attr in part.sparsified.edges[e]:
                    H.edges[e][attr] = part.sparsified.edges[e][attr]
                H.edges[e]["ltn_name"] = None
                H.edges[e]["in_ltn"] = False
    filt_part = pd.DataFrame(filt_part)
    filt_part = filt_part.drop("subgraph", axis=1)
    all_part = all_part.drop("subgraph", axis=1)
    all_part.to_json(
        sb.config.Config.RESULTS_DIR + f"/{city_name}{part_name}/all_partitions.json"
    )
    filt_part.to_json(
        sb.config.Config.RESULTS_DIR + f"/{city_name}{part_name}/filt_partitions.json"
    )
    ox.save_graphml(
        G_all,
        sb.config.Config.RESULTS_DIR
        + f"/{city_name}{part_name}/{city_name}_all.graphml",
    )
    ox.save_graphml(
        G_filt,
        sb.config.Config.RESULTS_DIR
        + f"/{city_name}{part_name}/{city_name}_filt.graphml",
    )
    sb.save_to_gpkg(
        part,
        save_path=sb.config.Config.GRAPH_DIR + "/" + city_name + part_name + ".gpkg",
        ltn_boundary=True,
    )
    df = gpd.read_file(
        sb.config.Config.GRAPH_DIR + "/" + city_name + part_name + ".gpkg",
        layer="ltns",
    )
    df_filt = df[
        (df["geometry"].area < 921600) & (df["geometry"].area > 25600) & (df["n"] > 5)
    ]
    df_filt.to_file(folder_results + f"{city_name}{part_name}_filt_ltns.gpkg")
    col_names = [
        "Partitioner",
        "Amount of superblocks",
        "Share of streets within superblocks",
        "Share of the population within superblocks",
        "Area of pacified streets",
        "Schools within a superblock",
        "Superblocks without a school",
    ]
    all_arr = []
    for part_name in ["residential", "buffer"]:
        G = load_graphml_dtypes(
            sb.config.Config.RESULTS_DIR
            + f"/{city_name}_{part_name}/{city_name}_filt.graphml"
        )
        for e in G.edges:
            if "in_ltn" not in G.edges[e]:
                G.edges[e]["in_ltn"] = "False"
        ltn_streets = [e for e in G.edges if G.edges[e]["in_ltn"] == "True"]
        roadsum = round(
            100
            * sum([G.edges[e]["length"] for e in ltn_streets])
            / sum([G.edges[e]["length"] for e in G.edges]),
            1,
        )
        popsum = round(
            100
            * sum([G.edges[e]["population"] for e in ltn_streets])
            / sum([G.edges[e]["population"] for e in G.edges]),
            1,
        )
        areasum = round(
            100
            * sum([shapely.from_wkt(G.edges[e]["cell"]).area for e in ltn_streets])
            / sum([shapely.from_wkt(G.edges[e]["cell"]).area for e in G.edges]),
            1,
        )
        part = gpd.read_file(
            folder_results + f"{city_name}_{part_name}.gpkg", layer="ltns"
        )
        part = part[(part["area"] > 25600) & (part["area"] < 921600) & (part["n"] > 5)]
        all_ltn_geom = part.geometry.union_all()
        all_arr.append(
            [
                part_name,
                len(part["classification"]),
                roadsum,
                popsum,
                areasum,
                round(
                    100
                    * len(gdf_school[gdf_school.geometry.within(all_ltn_geom)].geometry)
                    / len(gdf_school.geometry),
                    1,
                ),
                round(
                    100
                    * len(
                        [
                            ltn
                            for ltn in part.geometry
                            if any(gdf_school.geometry.within(ltn))
                        ]
                    )
                    / len(part["classification"]),
                    1,
                ),
            ]
        )
    df = pd.DataFrame(all_arr, columns=col_names)
    df.to_json(folder_results + "results_Kozani_filtered.json")
