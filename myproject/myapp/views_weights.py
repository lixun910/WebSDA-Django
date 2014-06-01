# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from myproject.myapp.models import Document, Weights, Geodata, Preference
from myproject.myapp.forms import DocumentForm

import logging
import numpy as np
import json, time, os
import multiprocessing as mp
from hashlib import md5
from pysal import W, w_union, higher_order
from pysal import rook_from_shapefile as rook
from pysal import queen_from_shapefile as queen
import GeoDB

logger = logging.getLogger(__name__)

"""
Create weights file from a shape file using PySAL.
Note: weights are now stored in database as a JSON string, which
needs more discussion about, e.g. big size weights file.
"""
def create_weights(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 
    if request.method == 'POST':
        userid = request.session['userid']
        layer_uuid = request.POST.get("layer_uuid",None)
        w_id = request.POST.get("w_id", None)
        w_name = request.POST.get("w_name", None)
        w_type = request.POST.get("w_type", None)
        # detect w_id is unique ID
        print w_id
        if w_type == "contiguity":
            cont_type = request.POST.get("cont_type", None)
            cont_order = request.POST.get("cont_order", None)
            cont_ilo = request.POST.get("cont_ilo", None)
            t1 = time.time()
            file_url, shpfilename = get_file_url(userid, layer_uuid)
            file_url = settings.PROJECT_ROOT + file_url
            shp_path = file_url+".shp" if file_url.endswith("json") else file_url
            w = rook(shp_path, w_id) if cont_type == 'rook' \
                else queen(shp_path, w_id)
            origWeight = w
            weight_order = int(cont_order)
            if weight_order > 1:
                w = higher_order(w, weight_order)
            if cont_ilo == "true":
                for order in xrange(weight_order-1,1,-1):
                    lowerOrderW = higher_order(origWeight, order)
                    w = w_union(w, lowerOrderW)
                w = w_union(w, origWeight)
            # save to database
            wtypemeta = json.dumps({'cont_type':cont_type,'cont_order':cont_order,'cont_ilo':cont_ilo})
            wuuid = md5(userid + shpfilename + w_name).hexdigest()
            histogram = str(w.histogram)
            neighbors = json.dumps(w.neighbors)
            weights = json.dumps(w.weights)
            new_w_item = Weights(uuid=wuuid, userid=userid, shpfilename=shpfilename,name=w_name,n=w.n, wid=w_id, wtype=w_type, wtypemeta=wtypemeta, histogram=histogram, neighbors=neighbors,weights=weights)
            new_w_item.save()
            return HttpResponse("OK")
        elif w_type == "distance":
            dist_metric = request.POST.get("dist_metric", None)
            dist_method = request.POST.get("dist_method", None)
            dist_value = request.POST.get("dist_value", None)
        elif w_type == "kernel":
            kernel_type = request.POST.get("kernel_type", None)
            kernel_nn = request.POST.get("kernel_nn", None)

        return HttpResponse("ERROR")
    return HttpResponse("ERROR")

"""
Get all weights file names that created based on one map layer.
"""
def get_weights_names(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 
    if request.method == 'GET': 
        layer_uuid = request.GET.get('layer_uuid','')
        file_url, shpfilename = get_file_url(userid, layer_uuid)
        w_array = Weights.objects.filter(userid = userid).filter(shpfilename = shpfilename)
        w_names = {}
        for w in w_array:
            w_names[w.name] = w.uuid
        json_result = json.dumps(w_names)
        return HttpResponse(json_result, content_type="application/json")
    return HttpResponse("ERROR")

"""
Get W object from database using weights uuid
"""
def helper_get_W(wuuid):
    print "get_w"
    try:
        w_record = Weights.objects.get(uuid=wuuid)
        if w_record:
            neighbors = json.loads(w_record.neighbors)
            for k,v in neighbors.iteritems():
                neighbors_dict[int(k)] = v

            weights = json.loads(w_record.weights)
            for k,v in weights.iteritems():
                weights_dict[int(k)] = v

            w = W(neighbors_dict, weights_idct)
            print w.sparse
            w.name = w_record.name
            return w
    except:
        pass
    return None

"""
Get W object list using weights uuid.
"""
def helper_get_W_list(wuuids):
    w_list = []
    for uuid in wuuids:
        w = helper_get_W(uuid)
        if w:
            w_list.append(w)
    return w_list
