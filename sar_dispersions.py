if __name__ == '__main__':
    print("\n\rThis file is being run directly\n\r")

import unit_conversions as uc
import geopandas as gp
import pandas as pd
import numpy as np  
from shapely.geometry import Point, Polygon
from misc_func import set_gdf


def create_da_gdfs(ipp, dot, max_distance, angles, EPSG_LOCAL):
    """
    Creates a geodataframe of dispersion angle sectors around an IPP.

    Args:
        ipp (GeoDataFrame): The IPP geodataframe
        dot (int): The direction of travel
        max_distance (int): The maximum distance from the IPP
        angles (list): The dispersion angles, in degrees, as they appear in the LPB table
        EPSG_LOCAL (int): The local spatial coordinate reference system

    Returns:
        gdf (GeoDataFrame): The geodataframe of dispersion angle sectors
    """

    titles = ['25%', '50%', '75%', '95%', '100%']
    init_poa = [25, 25, 25, 20, 5]
    
    # Extending max distance to account for the curved end
    max_distance_ext = max_distance * 3
    
    # Get the IPP coordinates
    ipp_x, ipp_y = ipp.geometry.x.iloc[0], ipp.geometry.y.iloc[0]

    # Get the end coordinates for the Direction of Travel
    dot_x = ipp_x + max_distance_ext * np.cos(np.radians(90 - dot))
    dot_y = ipp_y + max_distance_ext * np.sin(np.radians(90 - dot))
    
    sectors = []
    idx = 0
    previous_coord_pos, previous_coord_neg = (dot_x, dot_y), (dot_x, dot_y)
    
    # Iterate through the dispersion angles and create a sector for each
    for angle in angles:
        # Create a positive half of a sector
        pos_x = ipp_x + max_distance_ext * np.cos(np.radians(90 - (dot + angle)))
        pos_y = ipp_y + max_distance_ext * np.sin(np.radians(90 - (dot + angle)))
        # Create a negative half of a sector
        neg_x = ipp_x + max_distance_ext * np.cos(np.radians(90 - (dot - angle)))
        neg_y = ipp_y + max_distance_ext * np.sin(np.radians(90 - (dot - angle)))

        # Create the polygon using the three points (offset, ipp, previous)
        sector_pos = Polygon([(pos_x, pos_y), (ipp_x, ipp_y), previous_coord_pos])
        sector_neg = Polygon([(neg_x, neg_y), (ipp_x, ipp_y), previous_coord_neg])
        previous_coord_pos, previous_coord_neg = (pos_x, pos_y), (neg_x, neg_y)

        line_gdf = gp.GeoDataFrame({'geometry': [sector_pos, sector_neg]})
        line_gdf['title'] = [titles[idx] + " pos", titles[idx] + " neg"]
        line_gdf['area'] = [sector_pos.area, sector_neg.area]
        line_gdf['POA'] = init_poa[idx]
        line_gdf = set_gdf(line_gdf, EPSG_LOCAL=EPSG_LOCAL)
        idx += 1

        sectors.append(line_gdf)

    # Convert the sectors list into a geodataframe
    sectors_gdf = gp.GeoDataFrame(pd.concat(sectors))
    sectors_gdf = set_gdf(sectors_gdf, EPSG_LOCAL)

    # Create a buffer around the ipp with a radius set to the max distance
    ipp_buffer = Point(ipp_x, ipp_y).buffer(max_distance)
    ipp_buffer = gp.GeoDataFrame({'geometry': [ipp_buffer]})
    ipp_buffer = set_gdf(ipp_buffer, EPSG_LOCAL=EPSG_LOCAL)

    # Intersect the sectors with the buffer to get the curved end
    intersections = []
    for sector_idx, sector in sectors_gdf.iterrows():
        # Intersect the sector with the buffer
        intersection = sector.geometry.intersection(ipp_buffer.geometry.iloc[0])
        
        # Convert the intersection to a geodataframe
        intersection = gp.GeoDataFrame({'geometry': [intersection]})

        # Pull over title and POA values
        intersection['title'] = sector_idx
        poa = sector['POA'] if sector['POA'] == 5 else sector['POA'] / 2
        intersection['POA'] = poa
        intersection['Area'] = round(intersection.geometry.area / 1e6, 2)
        intersection['pDEN'] = round(poa / (intersection.geometry.area / 1e6), 2)
        
        # Append the sector to the list of intersections
        intersections.append(intersection)

    # Concatenate the individual intersections into a single geodataframe
    intersections_gdf = gp.GeoDataFrame(pd.concat(intersections))
    intersections_gdf = set_gdf(intersections_gdf, EPSG_LOCAL)

    # Set the geodataframe to the object
    gdf = intersections_gdf
    return gdf




