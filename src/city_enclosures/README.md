# city_enclosures

Scripts to generate enclosed tessellations from all sides of a barrier. Barriers are roads, railways and rivers.

## usage

The main script is called `get_barrier_polygons.py`. It requires an area defined by the GeoJSON polygon and an output filename.
The street barriers can be specified by OSM highway types (motorway, trunk, primary, secondary, tertiary, unclassified, residential). Default types are *motorway*, *trunk*, *primary* and *secondary*.

The railway types can also be specified by the `--railway` argument or skipped completely by the `--no-railyway` argument.
Service railway lines are not required, so the `--excluding-railway-service` is set to *spur*, *yard*, *siding* by default.

There can be rifts inside the enclosures (e.g., a barrier type street that originates from a polygon) that needs to removed as the polygon will have a rift. See dissolve rifts notebook for the details.

These rifts as dissolved using the buffer method by a given threshold (`--buffer` argument, 50 meters by default). As the scripts works in EPSG:4326 projection, the geometries needs to be reprojected. The projection can be defined by the `--buffer-crs` argument (EPSG:23700 by default).

To remove rivers, the river polygon needs to be specified as a GeoJSON containing a single polygon -- in EPSG:4326-- by the `--river` argument.
During the process the river polygon is shrunk, so the buffer and the CRS can be defined by the `--river-shrink` and the `--river-shrink-crs` arguments, respectively.

The algorithm can create very small enclosures, so a threshold can be set to remove them (`--threshold`) with a CRS in which the threshold is defined (`--threshold-crs`). By default, 0.1.

```
usage: get_barrier_polygons.py [-h] -a AREA -o OUTPUT [-s STREET [STREET ...]] [-r [RAILWAY ...]] [--no-railway] [-R EXCLUDING_RAILWAY_SERVICE [EXCLUDING_RAILWAY_SERVICE ...]]
                               [-t THRESHOLD] [-c THRESHOLD_CRS] [-b BUFFER] [-u BUFFER_CRS] [--river RIVER] [--river-shrink RIVER_SHRINK] [--river-shrink-crs RIVER_SHRINK_CRS]

options:
  -h, --help            show this help message and exit
  -a AREA, --area AREA  observation area defined by GeoJSON polygon
  -o OUTPUT, --output OUTPUT
                        output polygons in GeoJSON format
  -s STREET [STREET ...], --street STREET [STREET ...]
                        OSM highway types: motorway trunk primary secondary tertiary unclassified residential
  -r [RAILWAY ...], --railway [RAILWAY ...]
                        OSM railway types
  --no-railway
  -R EXCLUDING_RAILWAY_SERVICE [EXCLUDING_RAILWAY_SERVICE ...], --excluding-railway-service EXCLUDING_RAILWAY_SERVICE [EXCLUDING_RAILWAY_SERVICE ...]
                        without OSM railway service types
  -t THRESHOLD, --threshold THRESHOLD
                        area threshold in square kilometer
  -c THRESHOLD_CRS, --threshold-crs THRESHOLD_CRS
                        CRS in which the threshold is defined
  -b BUFFER, --buffer BUFFER
                        buffer used to dissolve rifts
  -u BUFFER_CRS, --buffer-crs BUFFER_CRS
                        CRS in which the buffer is defined
  --river RIVER         GeoJSON containing a single river polygon
  --river-shrink RIVER_SHRINK
                        buffer used to shrink river for enclosure difference
  --river-shrink-crs RIVER_SHRINK_CRS
                        CRS in which the river shrink buffer is defined
```

## limitations

- the threshold is in square kilometers, so the unit of provided CRS must be meter

## references

- [Generating enclosures from the Urban Grammar AI research project](https://urbangrammarai.xyz/spatial_signatures/spatial_unit/Parallelized_enclosures.html)