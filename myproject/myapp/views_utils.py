# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings

from myproject.myapp.models import Document, Weights, Geodata, Preference

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
Get reletive url of shape files that user uploaded to server.
"""
def get_file_url(userid, layer_uuid):
    geodata = Geodata.objects.get(uuid=layer_uuid)
    if geodata:
        file_uuid = md5(geodata.userid + geodata.origfilename).hexdigest()
        document = Document.objects.get(uuid=file_uuid)
        if document:
            return document.docfile.url, document.filename
    return None

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
