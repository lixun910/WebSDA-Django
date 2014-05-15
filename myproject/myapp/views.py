# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from myproject.myapp.models import Document, Weights
from myproject.myapp.forms import DocumentForm

import json
from hashlib import md5
from pysal import rook_from_shapefile as rook

def login(request):
  

def main(request):
    # check user login
    userid = request.session.get('userid', False):
    if not userid:
        return HttpResponseRedirect('/login/') 


    geodata = Geodata.objects.all().filter( userid=userid )
    # render main page with userid, shps/tables, weights
    return render_to_response(
        'myapp/main.html',
        {'userid': userid, 'geodata': geodata},
        context_instance=RequestContext(request)
    )
    
def list(request):
    # Handle file upload
    if request.method == 'POST' and request.session.get('userid', False):
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            docfile = request.FILES['docfile']
            shpfilename = str(docfile)
            userid = 'test'
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
    if request.method == 'POST' and request.session.get('userid', False):
        userid = request.session['userid']
        shpfilename = request.session['shpfilename']
        w_id = request.POST.get("w_id", None)
        w_name = request.POST.get("w_name", None)
        w_type = request.POST.get("w_type", None)
        cont_type = request.POST.get("cont_type", None)
        cont_order = request.POST.get("cont_order", None)
        cont_ilo = request.POST.get("cont_ilo", None)

        print userid, shpfilename, w_id, w_name, w_type, cont_type, cont_order, cont_ilo
        if userid and shpfilename and w_id and w_name and cont_type and cont_order and cont_ilo:
            shpuuid =  md5(userid+shpfilename).hexdigest()
            print shpuuid
            result = Document.objects.filter(uuid = shpuuid)
            print result
            if len(result) > 0:
              print result[0].docfile
              shp_path = settings.MEDIA_ROOT + "/" + str(result[0].docfile)
              print shp_path
              w = rook(shp_path)
              # save to database
              wtypemeta = json.dumps({'cont_type':cont_type,'cont_order':cont_order,'cont_ilo':cont_ilo})
              wuuid = md5(userid + shpfilename + w_name).hexdigest()
              print w.histogram
              histogram = str(w.histogram)
              neighbors = json.dumps(w.neighbors)
              weights = json.dumps(w.weights)
              new_w_item = Weights(uuid=wuuid, userid=userid, shpfilename=shpfilename,name=w_name,\
                n=w.n, wid=w_id, wtype=w_type, wtypemeta=wtypemeta, histogram=histogram, neighbors=neighbors,weights=weights)
              new_w_item.save()
 
              return HttpResponse("OK")

        return HttpResponse("ERROR")

    # todo: remove 
    request.session['userid'] = 'test'
    request.session['shpfilename'] = 'NAT.shp'
    return HttpResponse("ERROR")

def get_weights_names(request):
    if request.method == 'GET' and request.session.get('userid', False):
        userid = request.session['userid']
        shpfilename = request.session['shpfilename']
        w_array = Weights.objects.filter(userid = userid).filter(shpfilename = shpfilename)
        w_names = [w.name for w in w_array]
        json_result = json.dumps(w_names)
        return HttpResponse(json_result, content_type="application/json")
    return HttpResponse("ERROR")
      
def ols(request):
    request.POST.get("","") 
