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
    logger.info('login info') 
    logger.debug('login debug') 
    logger.error('login error') 
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


def get_file_url(userid, layer_uuid):
    geodata = Geodata.objects.get(uuid=layer_uuid)
    if geodata:
        file_uuid = md5(geodata.userid + geodata.origfilename).hexdigest()
        document = Document.objects.get(uuid=file_uuid)
        if document:
            return document.docfile.url, document.filename
    return None

def upload_canvas(request):
    import base64, cStringIO, re
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 
    if request.method == 'POST': 
        layer_uuid = request.POST.get('layer_uuid',None)
        if layer_uuid:
            shp_url = get_file_url(userid, layer_uuid)
            if shp_url:
                shp_location, shp_name = shp_url
                image_location = settings.PROJECT_ROOT + shp_location + ".png"
                print image_location
                if not os.path.isfile(image_location):
                    datauri = request.POST['imageData']
                    print datauri
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

def helper_get_W_list(wuuids):
    w_list = []
    for uuid in wuuids:
        w = helper_get_W(uuid)
        if w:
            w_list.append(w)
    return w_list
    
def spatial_regression(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 
    result = {"success":0}
    print request.POST
    # Get param
    layer_uuid = request.POST.get("layer_uuid",None)
    wuuids_model = request.POST.getlist("w[]")
    print wuuids_model
    wuuids_kernel = request.POST.getlist("wk[]")
    model_type = request.POST.get("type",None)
    if model_type: model_type = int(model_type)
    model_method = request.POST.get("method", None) #*
    if model_method: model_method = int(model_method)
    error = request.POST.getlist("error[]")
    if len(error)==0: error = [0,0,0]
    print error
    white = int(error[0])
    hac = int(error[1])
    kp_het = int(error[2])
    name_y = request.POST.get("y",None)
    name_x = request.POST.getlist("x[]")
    name_ye = request.POST.getlist("ye[]")
    name_h = request.POST.getlist("h[]")
    name_r = request.POST.get("r",None) # one col
    name_t = request.POST.get("t",None) # one col
    
    print name_y, name_x, name_ye, name_h, name_r, name_t
    
    if not layer_uuid and not name_y and not name_x and model_type not in [0,1,2,3] and \
       model_method not in [0,1,2]:
        result["message"] = "Parameters are not legal."
        return HttpResponse(json.dumps(result))
    
    # These options are not available yet....
    s = None
    name_s = None
   
    mtypes = {0: 'Standard', 1: 'Spatial Lag', 2: 'Spatial Error', \
              3: 'Spatial Lag+Error'}    
    model_type = mtypes[model_type]
    method_types = {0: 'ols', 1: 'gm', 2: 'ml'}
    method = method_types[model_method]
    
    print wuuids_model
    w_list = helper_get_W_list(wuuids_model)
    wk_list = helper_get_W_list(wuuids_kernel)
   
    print w_list, wk_list 
    LM_TEST = False
    if len(w_list) > 0 and model_type in ['Standard', 'Spatial Lag']:
        LM_TEST = True
    
    request_col_names = name_x
    request_col_names.append(name_y)
    if name_ye: request_col_names += name_ye
    if name_h: request_col_names += name_h
    if name_r: request_col_names.append(name_r)
    if name_t: request_col_names.append(name_t)
    print layer_uuid, request_col_names    
    data = GeoDB.GetTableData(str(layer_uuid), request_col_names)
    print name_y
    y = np.array([data[name_y]]).T
    ye = np.array([data[name] for name in name_ye]).T if name_ye else None
    x = np.array([data[name] for name in name_x]).T
    h = np.array([data[name] for name in name_h]).T if name_h else None
    r = np.array(data[name_r]) if name_r else None
    t = np.array(data[name_t]) if name_t else None
    #print y, ye, x, h, r, t 
    layer_name = Geodata.objects.get(uuid=layer_uuid).origfilename
    print layer_name  
    config = DEFAULT_SPREG_CONFIG
    try:
        preference = Preference.objects.get(userid=userid)
        print preference 
        if preference: 
            config = preference.spreg 
    except:
        pass
    predy_resid = None # not write to file
    print "y.shape", y.shape
    print "x.shape", x.shape
    print w_list
    models = Spmodel(
        name_ds=layer_name,
        w_list=w_list,
        wk_list=wk_list,
        y=y,
        name_y=name_y,
        x=x,
        name_x=name_x,
        ye=ye,
        name_ye=name_ye,
        h=h,
        name_h=name_h,
        r=r,
        name_r=name_r,
        s=s,
        name_s=name_s,
        t=t,
        name_t=name_t,
        model_type=model_type,  # data['modelType']['endogenous'],
        # data['modelType']['spatial_tests']['lm'],
        spat_diag=LM_TEST,
        white=white,
        hac=hac,
        kp_het=kp_het,
        # config.....
        sig2n_k_ols=config['sig2n_k_ols'],
        sig2n_k_tsls=config['sig2n_k_2sls'],
        sig2n_k_gmlag=config['sig2n_k_gmlag'],
        max_iter=config['gmm_max_iter'],
        stop_crit=config['gmm_epsilon'],
        inf_lambda=config['gmm_inferenceOnLambda'],
        comp_inverse=config['gmm_inv_method'],
        step1c=config['gmm_step1c'],
        instrument_lags=config['instruments_w_lags'],
        lag_user_inst=config['instruments_lag_q'],
        vc_matrix=config['output_vm_summary'],
        predy_resid=predy_resid,
        ols_diag=config['other_ols_diagnostics'],
        moran=config['other_residualMoran'],
        white_test=config['white_test'],
        regime_err_sep=config['regimes_regime_error'],
        regime_lag_sep=config['regimes_regime_lag'],
        cores=config['other_numcores'],
        ml_epsilon=config['ml_epsilon'],
        ml_method=config['ml_method'],
        ml_diag=config['ml_diagnostics'],
        method=method
    ).output
    model_result = {} 
    print w_list
    for i,model in enumerate(models):
        model_id = i
        if len(w_list) == len(models):
            model_id = w_list[i].name
        model_result[model_id] = {'summary':model.summary,'predy':model.predy.T.tolist()}
    result['report'] = model_result
    result['success'] = 1
    print result
    return HttpResponse(json.dumps(result))

    
