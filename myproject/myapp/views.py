# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from myproject.myapp.models import Document, Weights, Geodata
from myproject.myapp.forms import DocumentForm

import numpy as NUM
import json, time
import multiprocessing as mp
from hashlib import md5
from pysal import W, w_union, higher_order
from pysal import rook_from_shapefile as rook
from pysal import queen_from_shapefile as queen
import GeoDB

def login(request):
    pass 

def test(request):
    request.session['userid'] = 'test1'
    
def main(request):
    # check user login
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 

    geodata = Geodata.objects.all().filter( userid=userid )
    # render main page with userid, shps/tables, weights
    return render_to_response(
        'myapp/main.html',
        {'userid': userid, 'geodata': geodata},
        context_instance=RequestContext(request)
    )

def get_fields(request):
    userid = request.session.get('userid', False)
    print userid
    if not userid:
        return HttpResponseRedirect('/myapp/login/') 
    print request
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
        return HttpResponseRedirect('/myapp/login/') 
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


def get_file_url(userid, layer_uuid):
    geodata = Geodata.objects.get(uuid=layer_uuid)
    if geodata:
        file_uuid = md5(geodata.userid + geodata.origfilename).hexdigest()
        document = Document.objects.get(uuid=file_uuid)
        if document:
            return document.docfile.url, document.filename
    return None
        
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
        if w_type == "contiguity":
            cont_type = request.POST.get("cont_type", None)
            cont_order = request.POST.get("cont_order", None)
            cont_ilo = request.POST.get("cont_ilo", None)
            t1 = time.time()
            file_url, shpfilename = get_file_url(userid, layer_uuid)
            file_url = settings.PROJECT_ROOT + file_url
            shp_path = file_url+".shp" if file_url.endswith("json") else file_url
            print shp_path
            t2 = time.time()
            print t2-t1
            w = rook(shp_path) if cont_type == 'rook' else queen(shp_path)
            origWeight = w
            weight_order = int(cont_order)
            print weight_order
            if weight_order > 1:
                w = higher_order(w, weight_order)
            print cont_ilo
            if cont_ilo == "true":
                for order in xrange(weight_order-1,1,-1):
                    lowerOrderW = higher_order(origWeight, order)
                    w = w_union(w, lowerOrderW)
                w = w_union(w, origWeight)
            # save to database
            t3 = time.time()
            print t3 - t2
            wtypemeta = json.dumps({'cont_type':cont_type,'cont_order':cont_order,'cont_ilo':cont_ilo})
            wuuid = md5(userid + shpfilename + w_name).hexdigest()
            histogram = str(w.histogram)
            neighbors = json.dumps(w.neighbors)
            weights = json.dumps(w.weights)
            new_w_item = Weights(uuid=wuuid, userid=userid, shpfilename=shpfilename,name=w_name,n=w.n, wid=w_id, wtype=w_type, wtypemeta=wtypemeta, histogram=histogram, neighbors=neighbors,weights=weights)
            new_w_item.save()
            t4 = time.time()
            print t4 - t3
            return HttpResponse("OK")
        elif w_type == "distance":
            pass
        elif w_type == "kernel":
            pass

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
        w_names = {w.name:w.uuid for w in w_array}
        json_result = json.dumps(w_names)
        return HttpResponse(json_result, content_type="application/json")
    return HttpResponse("ERROR")

FIELDNAMES = ["Estimated", "Residual", "StdResid","PredRes"]

def run_ols(y,x,w,robust,name_y,name_x,layer_name,w_name):
    # robust: white, hac
    if w:
        ols = OLS(y, x, w=w, spat_diag=True, robust=robust,name_y=name_y,
                  name_x = name_x, name_ds = layer_name, name_w = w_name)
    else:
        ols = OLS(y, x, robust=robust,name_y=name_y,name_x = name_x,
                  name_ds = layer_name)
    n = len(y)
    k = len(x) + 1
    dof = n - k - 1
    sdCoeff = NUM.sqrt(1.0 * dof / n)
    resData = sd * ols.u / NUM.std(ols.u)
    
    return {FIELDNAMES[0]:ols.predy,FIELDNAMES[1]:ols.u,FIELDNAMES[2]:resData}
   
def run_lag():
    if model_method == "ML":
        lag = PYSAL.spreg.ML_Lag(y, x, w = w, spat_diag = True, name_y = name_y, name_x = name_x, name_w = w_Name, name_ds = layer_name, name_w = w_name)
    else: # GMM
        lag = PYSAL.spreg.GM_Lag(y, x, w = w, robust = robust, spat_diag = True, name_y = name_y, name_x = name_x, name_w = w_Name, name_ds = layer_name, name_w = w_name)
    n = len(y)
    k = len(x) + 1
    dof = n -k - 1
    sdCoeff = NUM.sqrt(1.0 * dof / n)
    bottom = lag.u.std()
    resData = sdCoeff * lag.u / bottom
    ePredOut = lag.e_pred if lag.e_pred else NUM.ones(n) * NUM.nan
    
    return {FIELDNAMES[0]:ols.predy,FIELDNAMES[1]:ols.u,FIELDNAMES[2]:resData, FIELDNAMES[3]:ePredOut}

def run_error():
    if model_method == "ML":
        method = preference["spreg"]["ml"]["method"]
        error = PYSAL.spreg.ML_Error(y, x, w, method = method, name_y = name_y, name_x = name_x, name_w = w_Name, name_ds = layer_name, name_w = w_name)
    else: # GMM
        vm = preference["spreg"]["output"]["vm"] 
        if not use_hac:
            error = PYSAL.spreg.GM_Error(y, x, w, vm = vm, name_y = name_y, name_x = name_x, name_w = w_Name, name_ds = layer_name, name_w = w_name)
        else:
            max_iter = preference["spreg"]["gmm"]["max_iter"]  # 1
            epsilon = preference["spreg"]["gmm"]["epsilon"]  # 
            step1c = preference["spreg"]["gmm"]["step1c"]  # 
            error = PYSAL.spreg.GM_Error_Het(y, x, w, max_iter=max_iter, epsilon = epsilon, step1c = step1c, vm = vm, name_y = name_y, name_x = name_x, name_w = w_Name, name_ds = layer_name, name_w = w_name)
        else:
            inv_method = preference["spreg"]["gmm"]["inv_method"]  # 
            error = PYSAL.spreg.GM_Endog_Error_Het(y, x, yend, q, 
            
    n = len(y)
    k = len(x) + 1
    dof = n -k - 1
    sdCoeff = NUM.sqrt(1.0 * dof / n)
    bottom = lag.u.std()
    resData = sdCoeff * lag.u / bottom
    ePredOut = lag.e_pred if lag.e_pred else NUM.ones(n) * NUM.nan
    
    return {FIELDNAMES[0]:ols.predy,FIELDNAMES[1]:ols.u,FIELDNAMES[2]:resData, FIELDNAMES[3]:ePredOut}
        
    
def run_combo():
    if model_method == "ML":
        combo = PYSAL.spreg.GM_Combo(y, x, yend, q, w, w_lags, lag_q, vm)
    else: #GMM
        combo = PYSAL.spreg.GM_Combo(y, x, yend, q, w, w_lags, lag_q, vm)
        # Het
        combo = PYSAL.spreg.GM_Combo(y, x, yend, q, w, w_lags, lag_q, max_iter, epsilon, step1c, inv_method, vm)
        
    
def get_W(wuuid):
    w_record = Weights.objects.get(uuid=wuuid)
    if w_record:
        neighbors = json.loads(w_record.neighbors)
        weights = json.loads(w_record.weights)
        return {w_record.name:W(neighbors, weights)}
        
def spatial_regression(request):
    result = {"success":False}
    # Get data
    name_y = request.POST.get("y_name",None)
    name_x = request.POST.get("x_names",None)
    name_ye = request.POST.get("ye_name",None)
    instruments_col_name = request.POST.get("inst_name",None)
    r_col_name = request.POST.get("r_name",None)
    t_col_name = request.POST.get("t_name",None)
    wuuid_model = request.POST.get("wuuid_model",None)
    wuuid_kernel = request.POST.get("wuuid_kernel",None)
    model_type = request.POST.get("model_type",None)
    model_method = request.POST.get("model_method", None)
    model_stderror = request.POST.get("model_stderror", None)
    
    if not y_col_name and not x_col_names and not model_type and \
       not model_method and not model_stderror:
        result["message"] = "Parameters are not legal."
        return HttpResponse(json.dumps(result))
        
    w_name, w_obj = get_W(wuuid)
    reqeust_col_names = [y_col_name] + x_col_names
    data = GeoDB.GetTableData(layer_uuid, [reqeust_col_names])
    layer_name = Geodata.objects.get(uuid=layer_uuid).origfilename
    
    y = data[y_col_name]
    yvar = NUM.var(y)
    if NUM.isnan(yVar) or yVar <= 0.0:
        result["message"] = "Y Variance should be larger than Zero."
        return HttpResponse(json.dumps(result))
    x = np.array([data[col_name] for col_name in x_col_names])
    # 
    if model_type == "standard":
        result=run_ols(y,x,w,robust,y_col_name,x_col_names,layer_name,w_name)
    elif model_type == "lag":
        pass
    elif model_type == "error":
        pass
    elif model_type == "lagerror":
        
    
    