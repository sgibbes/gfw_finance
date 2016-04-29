__author__ = 'samantha.gibbes'
import os, arcpy
from arcpy import env
from arcpy.sa import *
arcpy.env.overwriteOutput = "True"
arcpy.CheckOutExtension("Spatial")


points = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\data_points_proj.shp'

# aoi = r'C:\Users\samantha.gibbes\Documents\gis\admin_boundaries\wdpa_protected_areas\wdpa_protected_areas.shp'
aoi = r'C:\Users\samantha.gibbes\Documents\gis\admin_boundaries\ifl_2013\ifl_2013.shp'

buffer_dist = 10

buffer = str(buffer_dist) + " Kilometers"

data_points_buff = os.path.join(os.path.dirname(points),os.path.basename(points).split(".")[0]+"_buff.shp")

aoi_proj = os.path.join(os.path.dirname(points),os.path.basename(aoi).split(".")[0]+"_proj.shp")

out_table = os.path.join(r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\NewFileGeodatabase.gdb',os.path.basename(aoi).split(".")[0]+"_results")

basename = os.path.basename(aoi).split(".")[0]
bad = [" ","-",'/', ':', '*', '?', '"', '<', '>', '|']
for char in bad:
    basename = basename.replace(char,"_")
intersected = os.path.join(os.path.dirname(points),basename+"_intersect.shp")

globcover = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\NewFileGeodatabase.gdb\global_cover'
hansenareamosaic = r'C:\Users\samantha.gibbes\Documents\gis\mosaics.gdb\hansen_area_worldeckert'
geodatabase = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\NewFileGeodatabase.gdb'

def buffer_points(points):
    print "buffering data points by " + buffer
    arcpy.Buffer_analysis(points,data_points_buff, buffer, "FULL", "ROUND", "NONE", "", "PLANAR")

def project_aoi(aoi):
    print "projecting AOI to world eckert"
    arcpy.Project_management(aoi, aoi_proj, "PROJCS['World_Eckert_VI',GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Eckert_VI'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',0.0],UNIT['Meter',1.0]]", "", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]", "NO_PRESERVE_SHAPE", "", "NO_VERTICAL")

def intersect_points(aoi_proj):
    print "intersecting data points buffer with AOI"
    arcpy.Intersect_analysis([aoi_proj,data_points_buff], intersected, "ALL", "", "INPUT")

def calculate_area(intersected):
    print "calculating area"
    arcpy.AddField_management(intersected, "Shape_area", "DOUBLE")
    exp = "!SHAPE.AREA@SQUAREKILOMETERS!"
    arcpy.CalculateField_management(intersected, "Shape_area", exp, "PYTHON_9.3")

def summarize_results(intersected,key_fields,aoi_id):
    print "summarizing results"
    arcpy.Statistics_analysis(intersected, out_table, [["Shape_area","SUM"]],key_fields)
    arcpy.DeleteField_management(out_table,"FREQUENCY")
    arcpy.AlterField_management(out_table, 'SUM_Shape_area', aoi_id+"_sqkm",aoi_id+"_sqkm")

def wdpa_calculation():
    buffer_points(points)
    project_aoi(aoi)
    intersect_points(aoi_proj)
    calculate_area(intersected)
    summarize_results(intersected,["ObjID","iucn_cat"],"wdpa")

def ifl_calculation():
    project_aoi(aoi)
    intersect_points(aoi_proj)
    calculate_area(intersected)
    summarize_results(intersected,["ObjID"],"ifl")

def zonal_stats(fc_geo,z_stats_tbl,fc_name):
    extraction = ExtractByMask(globcover,fc_geo)
    arcpy.gp.ZonalStatisticsAsTable_sa(extraction, "VALUE", hansenareamosaic, z_stats_tbl, "DATA", "SUM")
    arcpy.AddField_management(z_stats_tbl, "ID", "SHORT")
    exp = fc_name.split("_")[1]
    arcpy.CalculateField_management(z_stats_tbl, "ID", "'" + exp + "'", "PYTHON_9.3")

    arcpy.env.workspace = geodatabase
    table_list = arcpy.ListTables("glob_cover_ID_*")
    final_merge_table = os.path.join(geodatabase,'glob_cover_final')
    arcpy.Merge_management(table_list,final_merge_table)

def raster_calculation():
    with arcpy.da.SearchCursor(data_points_buff, ("Shape@", "point_id")) as cursor:
        feature_count = 0
        for row in cursor:
            feature_count += 1
            fc_geo = row[0]
            fc_name = str(row[1])
            z_stats_tbl = os.path.join(geodatabase,"glob_cover_"+fc_name)
            zonal_stats(fc_geo,z_stats_tbl,fc_name)
    del cursor

#-----------------------------------
raster_calculation()