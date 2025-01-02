def set_gdf(gdf, EPSG_LOCAL):
    '''
    Validates the CRS and index of a geodataframe
    
    Args: 
        gdf (geopandas.GeoDataFrame): The geodataframe to validate
        global: EPSG_LOCAL (int): The local spatial coordinate reference system

    Returns: 
        geopandas.GeoDataFrame: The validated geodataframe
    '''

    # Check the CRS of the geodataframe
    if gdf.crs != f"EPSG:{EPSG_LOCAL}":
        # If not defined, set it
        if gdf.crs is None:
            gdf.set_crs(epsg=EPSG_LOCAL, inplace=True)
        # If not the local CRS, convert it
        else: 
            gdf = gdf.to_crs(epsg=EPSG_LOCAL)

    # Set the index to the title column, if it's not already
    if 'title' in gdf.columns:
        gdf.set_index('title', inplace=True)

    return gdf