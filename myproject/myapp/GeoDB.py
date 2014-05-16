import os
import ogr

GEODB_PATH = os.path.realpath(os.path.dirname(__file__)) + '/../database/geodata.sqlite'

print GEODB_PATH
SQLITE_DRIVER = ogr.GetDriverByName('SQLite')
DS = SQLITE_DRIVER.Open(GEODB_PATH, 0) # readonly

if DS is None:
    print 'Open GeoDB failed'


def GetMetaData(layername):
    lyr = DS.GetLayer(layername)
    if lyr is None:
        return None
    meta_data = dict()
    # shape info
    meta_data['bbox'] = lyr.GetExtent()
    meta_data['geom_type'] = lyr.GetGeomType()
    
    # table info
    lyrDefn = lyr.GetLayerDefn()
    meta_data['n'] = lyrDefn.GetFieldCount()
    
    meta_data['fields'] = []
    for i in range( lyrDefn.GetFieldCount() ):
        fields = dict()
        fields['fieldName'] =  lyrDefn.GetFieldDefn(i).GetName()
        fieldTypeCode = lyrDefn.GetFieldDefn(i).GetType()
        fields['fieldType'] = lyrDefn.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
        #fieldWidth = lyrDefn.GetFieldDefn(i).GetWidth()
        #GetPrecision = lyrDefn.GetFieldDefn(i).GetPrecision()
        #print fieldName, fieldTypeCode, fieldType
        meta_data['fields'].append(fields)
    return meta_data

def GetGeometries(layername):
    pass

# 0 Integer 2 Real 4 String
def GetTableData(layername, column_names):
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
