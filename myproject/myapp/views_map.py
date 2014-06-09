# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

import numpy as np
import json, time, os, logging
import multiprocessing as mp
from hashlib import md5

from myproject.myapp.models import Document, Geodata

from views_utils import get_file_url
import GeoDB

logger = logging.getLogger(__name__)


"""
Get field names from a map layer. 
The layer_uuid is used to query from Geodata database.
"""
def get_fields(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    if request.method == 'GET': 
        layer_uuid = request.GET.get("layer_uuid","")
        print layer_uuid
        geodata = Geodata.objects.get(uuid = layer_uuid)
        if geodata:
            return HttpResponse(geodata.fields, content_type="application/json")
    return HttpResponse("ERROR")

"""
Upload shape files to server. Write meta data to meta database.
In background, export files to spatial database. 
"""
def upload(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    if request.method == 'POST': 
        # Get data from form
        filelist = request.FILES.getlist('docfile')
        filenames = []
        fileurls = []
        layer_uuid = ""
        print filelist
        # save all files
        for docfile in filelist:
            filename = str(docfile)
            filenames.append(filename)
            shpuuid =  md5(userid+filename).hexdigest()
            if filename[-4:] in [".shp",".json",".geojson"]:
                layer_uuid = shpuuid
            newdoc = Document(uuid = shpuuid, userid = userid,filename=filename, docfile = docfile)
            newdoc.save()
            fileurls.append(newdoc.docfile.url)

        # move files to sqlite db
        if len(filenames) == 0:
            return HttpResponse("ERROR")
        elif len(filenames) == 1:
            pass 
        elif len(filenames) == 3:
            # one time shp/dbf/shx  
            shp_name = ""
            dbf_name = ""
            shx_name = ""
            for name in filenames:
                if name.endswith(".shp"): shp_name = name
                elif name.endswith(".dbf"): dbf_name = name
                elif name.endswith(".shx"): shx_name = name
            if not shp_name and not dbf_name and not shx_name:
                return HttpResponse("ERROR")
            if layer_uuid == "": layer_uuid = md5(userid+shp_name).hexdigest()
            shp_path = settings.PROJECT_ROOT + fileurls[0][:-3] + "shp"
            # save to Geodata table
            meta_data = GeoDB.GetMetaData(layer_uuid,"ESRI shapefile",shp_path)
            print shp_path, meta_data
            new_geodata = Geodata(uuid=layer_uuid, userid=userid, origfilename=shp_name, n=meta_data['n'], geotype=str(meta_data['geom_type']), bbox=str(meta_data['bbox']), fields=json.dumps(meta_data['fields']))
            new_geodata.save()
            # export to sqlite database
            mp.Process(target=GeoDB.ExportToSqlite, args=(shp_path,layer_uuid)).start()

            return HttpResponse('{"layer_uuid":"%s"}'%layer_uuid, content_type="application/json")

        return HttpResponse("OK")

    elif request.method == 'GET':
        # Get data from dropbox or other links
        return HttpResponse("OK")

"""
Upload the image that draw on user's browser in HTML5 canvas.
The image name will just append ".png" to shape file name.
The url of image is stored in related geodatabase under the field
"thumbnail".
"""
def upload_canvas(request):
    import base64, cStringIO, re
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    if request.method == 'POST': 
        layer_uuid = request.POST.get('layer_uuid',None)
        if layer_uuid:
            shp_url = get_file_url(userid, layer_uuid)
            if shp_url:
                shp_location, shp_name = shp_url
                image_location = settings.PROJECT_ROOT + shp_location + ".png"
                #print image_location
                if not os.path.isfile(image_location):
                    datauri = request.POST['imageData']
                    #print datauri
                    imgstr = re.search(r'base64,(.*)', datauri).group(1)
                    o = open(image_location, 'wb')
                    o.write(imgstr.decode('base64'))
                    o.close()
                    # update Geodata table
                    geodata = Geodata.objects.get(uuid=layer_uuid)
                    geodata.thumbnail = shp_location + ".png"
                    geodata.save()
                    return HttpResponse("OK")

    return HttpResponse("ERROR")

    
