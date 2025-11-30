import h3

print(f"H3 Version: {h3.__version__}")

try:
    # Coords in (lat, lng) or (lng, lat)?
    # H3 usually uses (lat, lng).
    # GeoJSON is (lng, lat).
    
    # Let's try passing h3.LatLngPoly
    # It expects a sequence of (lat, lng) tuples?
    
    coords = [(0,0), (0,1), (1,1), (1,0)] # lat, lng
    
    try:
        poly = h3.LatLngPoly(coords) # type: ignore
        print("Created LatLngPoly")
        cells = h3.polygon_to_cells(poly, 9)
        print(f"Success LatLngPoly: {len(cells)}")
    except Exception as e:
        print(f"Failed LatLngPoly: {e}")
        
    # Try h3.geo_to_cells(geojson_dict) ?
    # It seems `geo_to_cells` is available.
    try:
        geojson = {
            "type": "Polygon",
            "coordinates": [
                [[0,0], [0,1], [1,1], [1,0], [0,0]] # lng, lat
            ]
        }
        cells = h3.geo_to_cells(geojson, 9) # This might be the one!
        print(f"Success geo_to_cells: {len(cells)}")
    except Exception as e:
        print(f"Failed geo_to_cells: {e}")

except Exception as e:
    print(e)
