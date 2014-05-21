from pysal import W, w_union, higher_order
from pysal import rook_from_shapefile as rook
from pysal import queen_from_shapefile as queen

def CreateWeights(weights_type, shp_path, weights_name, w_unique_ID, \
                  cont_type = None, cont_order = None, cont_ilo = None, \
                  dist_metric = None, dist_method = None, dist_value = None,\
                  kernel_type = None, kernel_nn = None):
    if weights_type == "contiguity": 
        if cont_type == "rook":
            w = rook( shp_path, w_unique_ID )
        else:
            w = queen( shp_path, w_unique_ID )
        orig_w = w
        w_order = int(cont_order)
        if w_order > 1:
            w = higher_order(w, w_order)
        if cont_ilo == "true":
            for order in xrange(w_order -1, 1, -1):
                lowerOrderW = higher_order(oirg_w, order)
                w = w_union(w, lowerOrderW)
            w = w_union(w, orig_w)
            
    elif weights_type == "distance":
        pass
    
    elif weights_type == "kernel":
        pass