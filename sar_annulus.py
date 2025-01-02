if __name__ == '__main__':
    print("\n\rThis file is being run directly\n\r")

import unit_conversions as uc
import geopandas as gp
import pandas as pd
import numpy as np  
from shapely.geometry import Point, Polygon
from misc_func import set_gdf
   
def create_di_gdfs(ipp, distances, EPSG_LOCAL):
    """
    Creates a geodataframe of annulus buffers around an IPP.
    Also produces a geodataframe of arc buffers around the IPP for programs that 
    can't handle annulus rings with missing centers.
    
    Args:
        ipp (GeoDataFrame): The IPP geodataframe
        distances (list): The distances from the IPP, in km, as they appear in the LPB table
        EPSG_LOCAL (int): The local spatial coordinate reference system

    Returns:
        buffers_gdf (GeoDataFrame): The geodataframe of annulus buffers
        arc_buffers_gdf (GeoDataFrame): The geodataframe of arc buffers
    """

    # Convert the distances from Kilometers to Meters
    distances = uc.km_to_m(distances)

    titles = ['25%', '50%', '75%', '95%', '100%']
    init_poa = [25, 25, 25, 20, 5]

    buffers = []
    arc_buffers = []
    previous_buffer = None
    idx = 0
    # Iterate through the distances from the IPP and create a buffer around each
    for distance in distances:
        # If this is the center buffer, create a circle
        if previous_buffer is None:
            
            buffer = Point(ipp.geometry.x.iloc[0], ipp.geometry.y.iloc[0]).buffer(distance)
            arc_buffer = buffer

        # Otherwise, create an annulus and arc   
        else:
            # Create an annulus
            buffer = (
                Point(ipp.geometry.x.iloc[0], ipp.geometry.y.iloc[0])
                .buffer(distance)
                .difference(Point(ipp.geometry.x.iloc[0], ipp.geometry.y.iloc[0])
                .buffer(previous_buffer))
            )

            # Create an arc
            # Return 100 evenly spaced samples from 0 to 360 degrees
            angles = np.linspace(np.radians(0), np.radians(359.999), 100)
            # Create an outer and inner arc of points
            outer_arc = [Point(distance * np.cos(angle), distance * np.sin(angle)) for angle in angles]
            inner_arc = [Point(previous_buffer * np.cos(angle), previous_buffer * np.sin(angle)) for angle in reversed(angles)]
            arc_points = outer_arc + inner_arc
            # Create a shapely object from the points
            arc_buffer = Polygon([(point.x + ipp.geometry.x.iloc[0], point.y + ipp.geometry.y.iloc[0]) for point in arc_points])

        # Convert the buffer shapely objects to a geodataframe
        buffer_gdf = gp.GeoDataFrame(geometry=[buffer])
        # Set the title, area, and POA columns
        buffer_gdf['title'] = titles[idx]
        buffer_gdf['area'] = buffer.area
        buffer_gdf['POA'] = init_poa[idx]
        buffer_gdf['pDEN'] = round(init_poa[idx] / (buffer.area / 1e6), 2)
        # Validate the CRS and index
        buffer_gdf = set_gdf(buffer_gdf, EPSG_LOCAL)

        # Convert the arc shapely object to a geodataframe
        arc_buffer_gdf = gp.GeoDataFrame(geometry=[arc_buffer])
        # Set the title, area, and POA columns
        arc_buffer_gdf['title'] = titles[idx]
        arc_buffer_gdf['area'] = arc_buffer.area
        arc_buffer_gdf['POA'] = init_poa[idx]
        buffer_gdf['pDEN'] = round(init_poa[idx] / (buffer.area / 1e6), 2)
        # Validate the CRS and index
        arc_buffer_gdf = set_gdf(arc_buffer_gdf, EPSG_LOCAL)

        # Set this buffer as the previous buffer for the next iteration
        previous_buffer = distance
        # Increment the index
        idx += 1

        # Append the buffer and arc to their lists
        buffers.append(buffer_gdf)
        arc_buffers.append(arc_buffer_gdf)

    # Concatenate the buffers and arcs into single geodataframes
    buffers_gdf = gp.GeoDataFrame(pd.concat(buffers))
    buffers_gdf = set_gdf(buffers_gdf, EPSG_LOCAL)

    arc_buffers_gdf = gp.GeoDataFrame(pd.concat(arc_buffers))
    arc_buffers_gdf = set_gdf(arc_buffers_gdf, EPSG_LOCAL)
    
   
    return buffers_gdf, arc_buffers_gdf




