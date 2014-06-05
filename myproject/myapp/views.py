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
from hashlib import md5
from views_utils import get_file_url

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
        'myapp/login.html',{
            'url_prefix': settings.URL_PREFIX,\
            'theme_jquery': settings.THEME_JQUERY,
        },
        context_instance=RequestContext(request)
    )

def main(request):
    # check user login
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 

    geodata = Geodata.objects.all().filter( userid=userid )
    geodata_content =  {}
    first_geodata = ''
    for i,layer in enumerate(geodata):
        geodata_content[i+1] = layer
        if i == 0:
            first_geodata = layer
    # render main page with userid, shps/tables, weights
    return render_to_response(
        'myapp/main.html', {
            'userid': userid, 'geodata': geodata_content, \
            'geodata0': first_geodata,'n': len(geodata), \
            'nn':range(1,len(geodata)+1),\
            'url_prefix': settings.URL_PREFIX,\
            'theme_jquery': settings.THEME_JQUERY,
            },
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
        
def save_pdf(request):
    userid = request.session.get('userid', False)
    if not userid:
        return HttpResponseRedirect(settings.URL_PREFIX+'/myapp/login/') 
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import letter
    
    if request.method == 'POST': 
        layer_uuid = request.POST.get('layer_uuid',None)
        text = request.POST.get('text','')
        print text
        if layer_uuid:
            shp_url = get_file_url(userid, layer_uuid)
            if shp_url:
                shp_location, shp_name = shp_url
                image_location = settings.PROJECT_ROOT + shp_location + ".png"
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment;filename="result.pdf"'
                p = canvas.Canvas(response, pagesize=letter)
                textObject = p.beginText()
                textObject.setTextOrigin(1.3*inch, 7.5*inch)
                textObject.setFont("Times-Roman", 8)
                textObject.textLines(text)
                p.drawText(textObject)
                p.drawImage(image_location, inch, 8*inch, 4*inch, 2.6*inch)
                p.showPage()
                p.save()
                
                return response
                
    return HttpResponse("ERROR")
