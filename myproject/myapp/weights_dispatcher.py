from pysal import W, w_union, higher_order
from pysal import rook_from_shapefile as rook
from pysal import queen_from_shapefile as queen
import pysal.threshold_binaryW_from_shapefile as thresholdW_from_shapefile

DISTANCE_METRICS = ['Euclidean Distance', 'Arc Distance (miles)', \
                    'Arc Distance (kilometers)']
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
        params = {'idVariable': w_unique_ID, 'radius': radius}
        if dist_method == "threshold":
            w = threshold_binW_from_shapefile( shp_path, cutoff, **params )
        elif dist_method == "knn":
            params['k'] = k
            w = knnW_from_shapefile( shp_path, **params )
        elif dist_method == "inverse_distance":
            params['alpha'] = -1 * power
            w = threshold_contW_from_shapefile( shp_path, cutoff, **params )
    
    elif weights_type == "kernel":
        kerns = ['uniform', 'triangular', 'quadratic', 'quartic', 'gaussian']
        kern = kerns[int(kernel_type)]
        k = int(kernel_nn) 
        w = adaptive_kernelW_from_shapfile( shp_path, k = k, function = kern, \
                                            idVariable = var, radius = radius )
        w = insert_diagnoal( w, wsp = False )
        method_options = [kern, k]
    
    w_object = {'w' : w, 'shapefile' : shp_path, 'id' : w_unique_ID, 'method' : weights_type, 'method options' : method_options}
    
    return w_object