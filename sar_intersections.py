if __name__ == '__main__':
    print("\n\rThis file is being run directly\n\r")
    
    
import unit_conversions as uc
import geopandas as gp
import pandas as pd
from misc_func import set_gdf


def intersect_gdfs(gdf1, gdf2, EPSG_LOCAL):
    '''
    Intersects two geodataframes and returns the result

    Args: 
        gdf1 (GeoDataFrame): The first geodataframe
        gdf2 (GeoDataFrame): The second geodataframe
        EPSG_LOCAL (int): The local spatial coordinate reference system
    
    Returns:
        intersections_gdf (GeoDataFrame): The intersected geodataframe
    '''
    intersections = []
    i = 1

    for title1, row1 in gdf1.iterrows():
        j = 1
        for title2, row2 in gdf2.iterrows():
            # Intersect the two geometries and convert to a geodataframe
            intersection = row1['geometry'].intersection(row2['geometry'])
            intersection_gdf = gp.GeoDataFrame({'geometry': [intersection]})
            #intersection_gdf['title'] = f"Int_{int_to_char(i)}{j}"
            #intersection_gdf['description'] = f"Int_{int_to_char(i)}{j}"
            intersection_gdf['title'] = f"dipp {title1} | da {title2}"
            intersection_gdf['di_dp_Area'] = round(intersection.area / 1e6, 2)
            #TODO Change this to generic so it works with any two gdfs
            # di POA = di POA * (intersected portion area / annulus area)
            # i.e. POA = 10 * .44 = 4.4
            intersection_gdf['di_math'] = f"{row1['POA']} * ({round(intersection.area/1e6, 2)} / {round(row1['geometry'].area/1e6, 2)}) = {round(row1['POA'] * (intersection.area / row1['geometry'].area),2)}"
            intersection_gdf['di_POA'] = row1['POA'] * (intersection.area / row1['geometry'].area)
            # da POA = da POA * (intersected portion area / segment area)
            # i.e. POA = 20 * .07 = 1.3
            intersection_gdf['da_math'] = f"{row2['POA']} * ({round(intersection.area/1e6,2)} / {round(row2['geometry'].area/1e6, 2)}) = {round(row2['POA'] * (intersection.area / row2['geometry'].area),2)}"
            intersection_gdf['da_POA'] = row2['POA'] * (intersection.area / row2['geometry'].area)
            # POA = di POA + da POA
            intersection_gdf['POA'] = intersection_gdf['di_POA'] + intersection_gdf['da_POA']
            
            set_gdf(intersection_gdf, EPSG_LOCAL)
            intersections.append(intersection_gdf)
            j += 1
        i += 1
    intersections_gdf = gp.GeoDataFrame(pd.concat(intersections))
    set_gdf(intersections_gdf, EPSG_LOCAL)
       
    return intersections_gdf

def intersect_regions(regions_gdf, intersections_gdf, EPSG_LOCAL):
    """
    Intersects region polygons with statistal area polygons and returns POA values
    as well as the bisected regions.

    Args: 
        regions_gdf (GeoDataFrame): The regions to be intersected
        intersections_gdf (GeoDataFrame): The statistical areas to be intersected
        EPSG_LOCAL (int): The local spatial coordinate reference system

    Returns:
        region_intersections_gdf (GeoDataFrame): The intersected regions
    """
    region_intersections = []
    poa_totals = {}

    for region_idx, region in regions_gdf.iterrows():
        poa_cumulative = 0

        for intersection_idx, intersection in intersections_gdf.iterrows():
            new_intersection = region.geometry.intersection(intersection.geometry)

            if new_intersection.area > 0:
                # Create a new Geodataframe for the intersection
                intersection_gdf = gp.GeoDataFrame({'geometry': [new_intersection]})
                set_gdf(intersection_gdf, EPSG_LOCAL)
                intersection_gdf['title'] = f"{region_idx} | {intersection_idx}"

                # Calculate the portion of this part of the region residing in the intersected area
                region_portion = round(new_intersection.area / region['geometry'].area, 2)

                # Multiply the region portion by the POA of the intersection to get the POA of the region in this intersection
                intersection_gdf['math'] = f"({round(new_intersection.area / 1e6, 2)}km\u00b2 / {round(region['geometry'].area / 1e6, 2)}km\u00b2) * {round(intersection['POA'],2)} = {region_portion}"
                intersect_POA = region_portion * intersection['POA']
                intersection_gdf['Region_Portion_POA'] = round(intersect_POA,2)

                # Append this row to the list
                region_intersections.append(intersection_gdf)

                # Add the intersect POA to the running total for this region
                poa_cumulative = poa_cumulative + intersect_POA

        # Append to the poa_totals dictionary
        poa_totals[region_idx] = round(poa_cumulative,2)
    
    # Convert the list of intersections to a geodataframe
    region_intersections_gdf = gp.GeoDataFrame(pd.concat(region_intersections))
    set_gdf(region_intersections_gdf, EPSG_LOCAL)

    # Add the POA totals to the region_intersections_gdf
    for title, poa in poa_totals.items():
        region_intersections_gdf.loc[region_intersections_gdf.index.str.contains(title), 'Region_POA'] = poa
    
    return region_intersections_gdf
    