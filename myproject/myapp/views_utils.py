# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.conf import settings

from myproject.myapp.models import Document, Weights, Geodata, Preference

import logging
import json, time, os
from hashlib import md5
from pysal import W, w_union, higher_order

logger = logging.getLogger(__name__)

RSP_OK = '{"success":1}'
RSP_FAIL = '{"success":0}'

"""
Get reletive url of shape files that user uploaded to server.
"""
def get_file_url(userid, layer_uuid):
    try:
        geodata = Geodata.objects.get(uuid=layer_uuid)
        file_uuid = md5(geodata.userid + geodata.origfilename).hexdigest()
        document = Document.objects.get(uuid=file_uuid)
        return document.docfile.url, document.filename
    except:
        return None

def create_w_uuid(userid, layer_uuid, w_name):
    file_url, shpfilename = get_file_url(userid, layer_uuid) 
    wuuid = md5(userid + shpfilename + w_name).hexdigest()
    return wuuid


def load_from_json(json_str):
    obj = None
    try:
        obj = json.loads(json_str)
    except:
        try:
            obj = eval(json_str)
        except:
            pass
    return obj
        
"""
Get W object from database using weights uuid
"""
def helper_get_W(wuuid):
    w_record = Weights.objects.get(uuid=wuuid)
    if w_record:
        neighbors_dict = {}
        weights_dict = {}
        neighbors = load_from_json(w_record.neighbors)
        for k,v in neighbors.iteritems():
            neighbors_dict[int(k)] = v

        weights = load_from_json(w_record.weights)
        for k,v in weights.iteritems():
            weights_dict[int(k)] = v

        w = W(neighbors_dict, weights_dict)
        w.name = w_record.name
        return w
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


if __name__ == "__main__":
    helper_get_W_list(["7819b820f3d4be9d99d3ea2602c11ad5"])