__author__ = 'samantha.gibbes'
import os, arcpy
from arcpy import env
from arcpy.sa import *
arcpy.env.overwriteOutput = "True"
arcpy.CheckOutExtension("Spatial")


points = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\data_points_proj.shp'

# aoi = r'C:\Users\samantha.gibbes\Documents\gis\admin_boundaries\wdpa_protected_areas\wdpa_protected_areas.shp'
# aoi = r'C:\Users\samantha.gibbes\Documents\gis\admin_boundaries\ifl_2013\ifl_2013.shp'

buffer_dist = 1784

buffer = str(buffer_dist) + " meters"

#data_points_buff = os.path.join(os.path.dirname(points),os.path.basename(points).split(".")[0]+"_buff.shp")
data_points_buff=r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\datasets\data_points_proj_buff_1784m.shp'

maindir = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance'
# out_table = os.path.join(r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\New File Geodatabase2.gdb',os.path.basename(aoi).split(".")[0]+"_results")

#
# bad = [" ","-",'/', ':', '*', '?', '"', '<', '>', '|']
# for char in bad:
#     basename = basename.replace(char,"_")


globcover = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\NewFileGeodatabase.gdb\global_cover'
hansenareamosaic = r'C:\Users\samantha.gibbes\Documents\gis\mosaics.gdb\hansen_area_worldeckert'
geodatabase = r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\New File Geodatabase2.gdb'
error_text_file = os.path.join(maindir,'errors.txt')
def buffer_points(points):
    print "buffering data points by " + buffer
    arcpy.Buffer_analysis(points,data_points_buff, buffer, "FULL", "ROUND", "NONE", "", "PLANAR")

def project_aoi(aoi):
    print "projecting AOI to world eckert"
    aoi_proj = os.path.join(os.path.dirname(points),os.path.basename(aoi).split(".")[0]+"_proj.shp")
    arcpy.Project_management(aoi, aoi_proj, "PROJCS['World_Eckert_VI',GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Eckert_VI'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',0.0],UNIT['Meter',1.0]]", "", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]]", "NO_PRESERVE_SHAPE", "", "NO_VERTICAL")
    print aoi_proj
    return aoi_proj
def intersect_points(aoi_proj):
    print "intersecting data points buffer with AOI"
    intersected = os.path.join(os.path.dirname(points),os.path.basename(aoi_proj).split(".")[0]+"_intersect_" + str(buffer_dist) +  ".shp")
    arcpy.Intersect_analysis([aoi_proj,data_points_buff], intersected, "ALL", "", "INPUT")
    return intersected
def calculate_area(intersected):
    print "calculating area"
    arcpy.AddField_management(intersected, "area_m2_fi", "DOUBLE")
    exp = "!SHAPE.AREA@SQUAREMETERS!"
    arcpy.CalculateField_management(intersected, "area_m2_fi", exp, "PYTHON_9.3")

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

def zonal_stats(fc_geo,zone_raster,z_stats_tbl,fc_name,raster_name):

    try:
        extraction = ExtractByMask(zone_raster,fc_geo)
        arcpy.gp.ZonalStatisticsAsTable_sa(extraction, "VALUE", hansenareamosaic, z_stats_tbl, "DATA", "SUM")
        arcpy.AddField_management(z_stats_tbl, "ID", "SHORT")
        exp = fc_name.split("_")[1]
        arcpy.CalculateField_management(z_stats_tbl, "ID", "'" + exp + "'", "PYTHON_9.3")

        arcpy.env.workspace = geodatabase
        table_list = arcpy.ListTables(raster_name + "_ID_*")
        final_merge_table = os.path.join(geodatabase,raster_name + '_final')
        arcpy.Merge_management(table_list,final_merge_table)
    except IOError as e:
        arcpy.AddMessage(  "     failed")
        error_text = "I/O error({0}): {1}".format(e.errno, e.strerror)
        errortext = open(error_text_file,'a')
        errortext.write(fc_name + " " + str(error_text) + "\n")
        errortext.close()
        pass
    except ValueError:
        arcpy.AddMessage(  "     failed")
        error_text="Could not convert data to an integer."
        errortext = open(error_text_file,'a')
        errortext.write(fc_name + " " + str(error_text) + "\n")
        errortext.close()
        pass
    except:
        arcpy.AddMessage(  "     failed")
        error_text= "Unexpected error:", sys.exc_info()
        error_text= error_text[1][1]
        errortext = open(error_text_file,'a')
        errortext.write(fc_name + " " + str(error_text) + "\n")
        errortext.close()
        pass

analysis = [r'C:\Users\samantha.gibbes\Documents\gis\gfw_finance\datasets\world_eckert.gdb\idn_primary_forest',"primary_forest"]
def raster_calculation(analysis):
    dataset = analysis[0]
    raster_name = analysis[1]
    with arcpy.da.SearchCursor(data_points_buff, ("Shape@", "point_id")) as cursor:
        feature_count = 0
        for row in cursor:
            feature_count += 1
            fc_geo = row[0]
            fc_name = str(row[1])
            z_stats_tbl = os.path.join(geodatabase,raster_name+"_"+fc_name)
            zonal_stats(fc_geo,dataset,z_stats_tbl,fc_name,raster_name)
    del cursor

def merge_tables(analysis_name):
    arcpy.env.workspace = geodatabase
    table_list = arcpy.ListTables("*_ID_*")
    final_merge_table = os.path.join(geodatabase,analysis_name)
    arcpy.Merge_management(table_list,final_merge_table)
#-----------------------------------
# raster_calculation(analysis)

aoi_proj = project_aoi(r'C:\Users\samantha.gibbes\Documents\gis\admin_boundaries\bra_land_rights\bra_land_rights.shp')
intersected = intersect_points(aoi_proj)
calculate_area(intersected)