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
from gs_dispatcher import DEFAULT_SPREG_CONFIG, Spmodel

logger = logging.getLogger(__name__)

def test(request):
    return HttpResponse(request.session['userid'])
    
def logout(request):
    request.session['userid'] = None
    return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    
def login(request):
    session_userid = request.session.get('userid', False)
    userid = request.POST.get('userid', None)
    print session_userid, userid
    if session_userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/main/') 
    elif userid: 
        # validate
        request.session['userid'] = userid
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/main/') 
         
    return render_to_response(
        'myapp/login.html',{},
        context_instance=RequestContext(request)
    )

def main(request):
    # check user login
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 

    geodata = Geodata.objects.all().filter( userid=userid )
    geodata_content =  {}
    for i,layer in enumerate(geodata):
        geodata_content[i+1] = layer
    # render main page with userid, shps/tables, weights
    return render_to_response(
        'myapp/main.html',
        {'userid': userid, 'geodata': geodata_content, 'n': len(geodata), 'nn':range(1,len(geodata)+1)},
        context_instance=RequestContext(request)
    )

def list(request):
    # Handle file upload
    if request.method == 'POST' and request.session.get('userid', False):
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            docfile = request.FILES['docfile']
            shpfilename = str(docfile)
            userid = 'test1'
            shpuuid =  md5(userid+shpfilename).hexdigest()
            # if it's a zip file, unzip it, and get real file from it
            # if .shp file already there, there is no need to write db 
            newdoc = Document(uuid = shpuuid, userid = userid,filename=shpfilename, docfile = docfile)
            newdoc.save()

            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('myproject.myapp.views.list'))
    else:
        form = DocumentForm() # A empty, unbound form

    # Load documents for the list page
    documents = Document.objects.all()

    # Render list page with the documents and the form
    return render_to_response(
        'myapp/list.html',
        {'documents': documents, 'form': form},
        context_instance=RequestContext(request)
    )
        
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
