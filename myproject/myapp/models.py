# -*- coding: utf-8 -*-
from django.db import models

class Document(models.Model):
    #md5 [userid, filename]
    uuid = models.CharField(max_length=64, unique=True, db_index=True, primary_key=True)
    userid = models.CharField(max_length=80)
    filename = models.CharField(max_length=255)
    docfile = models.FileField(upload_to='documents/%Y/%m/%d')

class Geodata(models.Model):
    # unique id, that maps to layer name in a sqlite3 spatial database
    uuid = models.CharField(max_length=64, unique=True, db_index=True, primary_key=True)
    # who upload 
    userid = models.CharField(max_length=80)
    # what's its original filename
    origfilename = models.CharField(max_length=255)
    n = models.IntegerField()
    geotype = models.CharField(max_length=10)
    # '[0.0, 0.1, 0.1, 0.0]' javascript evaled
    bbox = models.TextField()
    # fields: {fieldname:type}
    fields = models.TextField()
    thumbnail = models.URLField()

class Weights(models.Model):
    #md5([username,shpfilename,weightsfilename,wtype,details])
    uuid = models.CharField(max_length=64, unique=True, db_index=True, primary_key=True)
    userid = models.CharField(max_length=80)
    shpfilename = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    n = models.IntegerField()
    wid = models.CharField(max_length=32)
    wtype = models.CharField(max_length=50)
    wtypemeta = models.TextField()
    histogram = models.TextField()
    neighbors = models.TextField()
    weights = models.TextField()
