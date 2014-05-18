import os
from osgeo import ogr

GEODB_PATH = os.path.realpath(os.path.dirname(__file__)) + '/../database/geodata.sqlite'

print GEODB_PATH
SQLITE_DRIVER = ogr.GetDriverByName('SQLite')
DS = SQLITE_DRIVER.Open(GEODB_PATH, 0) # readonly

if DS is None:
    print 'Open GeoDB failed'

def ExportToSqlite(shp_path,layer_uuid):
    print "export starting..", layer_uuid
    # will be called in subprocess
    import subprocess
    rtn = subprocess.check_call(\
        ["ogr2ogr","-append",GEODB_PATH,shp_path,"-nln",layer_uuid])
    if rtn != 0:
        # write to log
        pass
    if shp_path.endswith(".json") or shp_path.endswith(".geojson"):
        ExportToESRIShape(shp_path) 
    print rtn,"export ends."
    
def ExportToESRIShape(json_path):
    # will be called in subprocess
    import subprocess
    shp_path = json_path + ".shp"
    rtn = subprocess.check_call(\
        ["ogr2ogr","-f \"ESRI Shapefile\"",shp_path,json_path])
    if rtn != 0:
        # write to log
        pass

def IsLayerExist(layer_uuid):
    layer = DS.GetLayer(layer_uuid)
    if layer: 
        return True
    else:
        return False

def GetDataSource(drivername, filepath):
    driver = ogr.GetDriverByName(drivername)
    ds = driver.Open(filepath, 0)
    return ds
    
def GetMetaData(layername, drivername=None, filepath=None):
    lyr = None
    ds = GetDataSource(drivername,filepath) if drivername and filepath else DS 
    lyr = ds.GetLayer(0) if drivername=="ESRI shapefile" else ds.GetLayer(layername)
    if lyr is None:
        return None
    meta_data = dict()
    # shape info
    meta_data['bbox'] = lyr.GetExtent()
    meta_data['geom_type'] = lyr.GetGeomType()
    
    # table info
    lyrDefn = lyr.GetLayerDefn()
    meta_data['n'] = lyrDefn.GetFieldCount()
    
    fields = dict()
    for i in range( lyrDefn.GetFieldCount() ):
        fieldName =  lyrDefn.GetFieldDefn(i).GetName()
        fieldTypeCode = lyrDefn.GetFieldDefn(i).GetType()
        fieldType = lyrDefn.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
        #fieldWidth = lyrDefn.GetFieldDefn(i).GetWidth()
        #GetPrecision = lyrDefn.GetFieldDefn(i).GetPrecision()
        #print fieldName, fieldTypeCode, fieldType
        fields[fieldName] = fieldType
    meta_data['fields'] = fields
    return meta_data

def GetGeometries(layername):
    pass

# 0 Integer 2 Real 4 String
def GetTableData(layername, column_names, drivername=None, filepath=None):
    lyr = DS.GetLayer(layername)
    if lyr is None:
        return None
    lyrDefn = lyr.GetLayerDefn()
    # get position of each query columns
    colum_pos = { col_name:[] for col_name in column_names}
    for i in range( lyrDefn.GetFieldCount() ):
        col_name  =  lyrDefn.GetFieldDefn(i).GetName()
        col_type =  lyrDefn.GetFieldDefn(i).GetType()
        if col_name in colum_pos:
            colum_pos[col_name].append(i)
            colum_pos[col_name].append(col_type)

    column_values = { col_name:[] for col_name in column_names}
    n = lyr.GetFeatureCount()
    feat = lyr.GetNextFeature()
    while feat:
        for col_name, info in colum_pos.iteritems():
            col_pos, col_type = info
            if col_type == 0:
                column_values[col_name].append( feat.GetFieldAsInteger(col_pos) )
            elif col_type == 2:
                column_values[col_name].append( feat.GetFieldAsDouble(col_pos) )
            else:
                column_values[col_name].append( feat.GetField(col_pos) )
                
        feat = lyr.GetNextFeature()
    return column_values

#print GetMetaData("nat")
    
#GetTableData("nat", ["state_fips","hr70","name"])
