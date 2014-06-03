# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from myproject.myapp.models import Weights, Geodata, Preference

import logging
import numpy as np
import json, time, os
import multiprocessing as mp
from hashlib import md5
from pysal import W

import GeoDB
from gs_dispatcher import DEFAULT_SPREG_CONFIG, Spmodel
from views_utils import helper_get_W_list

logger = logging.getLogger(__name__)

    
def spatial_regression(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    result = {"success":0}
    # Get param
    layer_uuid = request.POST.get("layer_uuid",None)
    wuuids_model = request.POST.getlist("w[]")
    wuuids_kernel = request.POST.getlist("wk[]")
    model_type = request.POST.get("type",None)
    if model_type: model_type = int(model_type)
    model_method = request.POST.get("method", None) #*
    if model_method: model_method = int(model_method)
    error = request.POST.getlist("error[]")
    if len(error)==0: error = [0,0,0]
    white = int(error[0])
    hac = int(error[1])
    kp_het = int(error[2])
    name_y = request.POST.get("y",None)
    name_x = request.POST.getlist("x[]")
    name_ye = request.POST.getlist("ye[]")
    name_h = request.POST.getlist("h[]")
    name_r = request.POST.get("r",None) # one col
    name_t = request.POST.get("t",None) # one col
   
    print request.POST 
    
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
    w_list = helper_get_W_list(wuuids_model)
    wk_list = helper_get_W_list(wuuids_kernel)
    LM_TEST = False
    if len(w_list) > 0 and model_type in ['Standard', 'Spatial Lag']:
        LM_TEST = True
    request_col_names = name_x
    request_col_names.append(name_y)
    if name_ye: request_col_names += name_ye
    if name_h: request_col_names += name_h
    if name_r: request_col_names.append(name_r)
    if name_t: request_col_names.append(name_t)
    data = GeoDB.GetTableData(str(layer_uuid), request_col_names)
    y = np.array([data[name_y]]).T
    ye = np.array([data[name] for name in name_ye]).T if name_ye else None
    x = np.array([data[name] for name in name_x]).T
    h = np.array([data[name] for name in name_h]).T if name_h else None
    r = np.array(data[name_r]) if name_r else None
    t = np.array(data[name_t]) if name_t else None
    #print y, ye, x, h, r, t 
    layer_name = Geodata.objects.get(uuid=layer_uuid).origfilename
    config = DEFAULT_SPREG_CONFIG
    try:
        preference = Preference.objects.get(userid=userid)
        if preference: 
            config = preference.spreg 
    except:
        pass
    predy_resid = None # not write to file
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
    for i,model in enumerate(models):
        model_id = i
        if len(w_list) == len(models):
            model_id = w_list[i].name
        model_result[model_id] = {'summary':model.summary,'predy':model.predy.T.tolist()}
    result['report'] = model_result
    result['success'] = 1
    return HttpResponse(json.dumps(result))

    