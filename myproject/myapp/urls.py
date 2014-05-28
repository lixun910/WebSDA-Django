# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns('myproject.myapp.views',
    url(r'^test/$', 'test', name='test'),
    url(r'^login/$', 'login', name='login'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^spatial_regression/$', 'spatial_regression', name='spatial regression'),
    url(r'^get_fields/$', 'get_fields', name='get field names'),
    url(r'^upload_canvas/$', 'upload_canvas', name='upload canvas'),
    url(r'^upload/$', 'upload', name='upload'),
    url(r'^list/$', 'list', name='list'),
    url(r'^create_weights/$', 'create_weights', name=''),
    url(r'^get_weights_names/$', 'get_weights_names', name=''),
    #url(r'^main/$', TemplateView.as_view(template_name='myapp/main.html')),
    url(r'^main/$','main', name='main'), 
    url(r'^ols/$', TemplateView.as_view(template_name='myapp/ols.html')),
    url(r'^weights/$', TemplateView.as_view(template_name='myapp/weights.html')),
    url(r'^draw/$', TemplateView.as_view(template_name='myapp/draw.html')),
)
