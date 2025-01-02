import geopandas as gp
import matplotlib.pyplot as plt
from sar_annulus import create_di_gdfs
from sar_dispersions import create_da_gdfs
from misc_func import set_gdf
from sar_intersections import intersect_gdfs, intersect_regions
import os

##### CHANGE THESE VARIABLES #####

# Enter five values, as kilometers, as they appear in LPB Tables
distances_from_ipp = [1.1, 3.1, 5.8, 18.3, 20]

# Enter a single value, as degrees true north, as they appear in LPB Tables.
# Type None if the direction of travel is not known
direction_of_travel = 180

# Enter five values, as degrees, as they appear in LPB Tables.
# Type None if the dispersion angles are not known
dispersion_angles = [2, 23, 64, 132, 360]

# Your local spatial coordinate reference systems
# You can look it up here: https://spatialreference.org/ref/epsg/
EPSG_LOCAL = 32617 

# The default spatial coordinate reference system used by SAR Topo 
# Only change if you have changed it within SAR Topo
EPSG_WGS84 = 4326 

# Enter the path and name of the json file to be used
# The file should contain a single IPP marker and region polygons
# The IPP and regions must have labels
# DO NOT provide any other objects like range rings or sectors.
FILE = "POA-Test1.json"

# Path where this file exists
# Use double backspaces in the path.  i.e. "C:\\Users\\username\\Desktop\\"
PATH = ".\\"

# Do you wish to see the graphic plots when you run this program
# True = Yes, False = No
SHOW_PLOTS = True

# What files do you want returned for import back into SAR Topo?
REGIONS_BISECTED = True
STATISTICAL_INTERSECTS = True
DIPP_ANNULI = True
DIPP_ARCS = True
DA_SECTORS = True


##### DO NOT CHANGE ANYTHING BELOW THIS #####

def set_variables(distances_from_ipp, dispersion_angles, direction_of_travel, file):
    '''
    Properly formats the input variables,loads the json file, 
    and validates/extracts the IPP and regions.
    
    Args:
        distances_from_ipp (list): The distances from the IPP
        dispersion_angles (list): The dispersion angles
        direction_of_travel (int): The direction of travel
        file (str): The path to the json file
    
    Returns:    
        dipp_obj (areas): The distances from the IPP object
        da_obj (areas): The dispersion angles object
        ipp (geopandas.GeoDataFrame): The IPP geodataframe
        regions (geopandas.GeoDataFrame): The regions geodataframe
    '''
    try: 
        # Load the json file
        original_gdf = gp.read_file(file)
    except Exception as e:
        raise ValueError(f"Error loading file: {e}") from e
    
    # Set the CRS to the local zone
    original_gdf = original_gdf.to_crs(epsg=EPSG_LOCAL)

    # Retrieve the user defined IPP and convert to a geodataframe
    ipp = original_gdf[original_gdf['title'] == 'IPP'][['geometry']]
    ipp['title'] = 'IPP'
    ipp = set_gdf(ipp, EPSG_LOCAL)

    # Retrieve the user defined regions and convert them to a geodataframe
    regions = original_gdf[original_gdf.geometry.geom_type == 'Polygon']
    regions = set_gdf(regions, EPSG_LOCAL)

    if regions.empty:
        raise ValueError("No regions found in the file")
    elif ipp.empty:
        raise ValueError("No IPP found in the file")

    # Create the distances from IPP object
    #dipp_obj = dipp(name='Distances from IPP', distances=distances_from_ipp, ipp=ipp, EPSG_LOCAL=EPSG_LOCAL, EPSG_WGS84=EPSG_WGS84)
    
    dipp_gdf, dipp_arcs_gdf = create_di_gdfs(ipp=ipp, distances=distances_from_ipp, EPSG_LOCAL=EPSG_LOCAL)



    # Check if the dispersion angles and direction of travel are known
    if dispersion_angles is None or direction_of_travel is None:
        dispersion_angles = [0, 0, 0, 0, 0]
        direction_of_travel = 0

    # Split the dispersion angles in half (either side from the direction of travel)
    dispersion_angles = [i / 2 for i in dispersion_angles]

    da_gdf = create_da_gdfs(angles=dispersion_angles, ipp=ipp, dot=direction_of_travel, max_distance=max(distances_from_ipp), EPSG_LOCAL=EPSG_LOCAL)
    
    return regions, dipp_gdf, dipp_arcs_gdf, da_gdf 


def  assign_POA_colors(gdf):
    '''
    Normalizes the 'POA' column to a range of 0-1 and assigns a color
    to each based on the autumn heatmap
    '''
    # Normalize the POA values to a range of 0-1
    if ('Region_Portion_POA' in gdf.columns):
        gdf['fill'] = (gdf['Region_Portion_POA'] - gdf['Region_Portion_POA'].min()) / (gdf['Region_Portion_POA'].max() - gdf['Region_Portion_POA'].min())
    
    # Assign a color to each POA value based on the autumn colormap
    gdf['fill'] = gdf['fill'].apply(lambda x: plt.cm.autumn(x))
    # Convert the color to a hex value
    gdf['fill'] = gdf['fill'].apply(lambda x: f"#{int(x[0]*255):02x}{int(x[1]*255):02x}{int(x[2]*255):02x}")
    # Set the stroke, stroke-width, and fill-opacity columns
    gdf['stroke'] = '#000000'
    gdf['stroke-width'] = 1
    gdf['fill-opacity'] = 0.3
    
    return gdf




def main():
    # Read the input variables and set the geodataframes
    regions, dipp_gdf, dipp_arcs_gdf, da_gdf = set_variables(distances_from_ipp, dispersion_angles, direction_of_travel, FILE)

    # Intersect the DIPP annuli with the DA sectors
    intersects_gdf = intersect_gdfs(gdf1=dipp_gdf, gdf2=da_gdf, EPSG_LOCAL=EPSG_LOCAL)

    # Intersect the regions with the DIPP annuli
    region_intersections_gdf = intersect_regions(regions, intersects_gdf, EPSG_LOCAL)

    # Output the results to the console
    print(region_intersections_gdf[['Region_Portion_POA', 'Region_POA']])
    
    # If the user wants to see the plots, display them
    if SHOW_PLOTS:
        region_intersections_gdf = assign_POA_colors(region_intersections_gdf)
        region_intersections_gdf.plot(color=region_intersections_gdf['fill'], edgecolor=region_intersections_gdf['stroke'], linewidth=region_intersections_gdf['stroke-width'], alpha=region_intersections_gdf['fill-opacity'])
        for idx, row in region_intersections_gdf.iterrows():
            plt.text(row.geometry.centroid.x, row.geometry.centroid.y, idx + " \n POA: " + str(row['Region_Portion_POA']), fontsize=8, ha='center', va='center')
        plt.show()

    # Create a subdirectory 'output' if it doesn't exist
    outpath = PATH + "output\\"    
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    # Save the geodataframes to a json files based on user input
    if REGIONS_BISECTED:
        region_intersections_gdf.to_crs(epsg=EPSG_WGS84).to_file(outpath + "Regions_Bisected.json", driver='GeoJSON')
    if STATISTICAL_INTERSECTS:
        intersects_gdf.to_crs(epsg=EPSG_WGS84).to_file(outpath + "Statistical_Intersects.json", driver='GeoJSON')
    if DIPP_ANNULI:
        dipp_gdf.to_crs(epsg=EPSG_WGS84).to_file(outpath + "DIPP_Annuli.json", driver='GeoJSON')
    if DIPP_ARCS:
        dipp_arcs_gdf.to_crs(epsg=EPSG_WGS84).to_file(outpath + "DIPP_Arcs.json", driver='GeoJSON')
    if DA_SECTORS:
        da_gdf.to_crs(epsg=EPSG_WGS84).to_file(outpath + "DA_Sectors.json", driver='GeoJSON')
    
    
    
if __name__ == '__main__':

    main()