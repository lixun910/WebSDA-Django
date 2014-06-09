// Author: xunli at asu.edu
var GeoVizMap = function(geojson, mapcanvas, extent) {
  // members
  this.geojson = geojson;
  this.mapcanvas = mapcanvas;
  this.width = mapcanvas.width;
  this.height = mapcanvas.height;

  this.bbox = [];
  this.extent = extent;
  if ( extent == undefined ) this.extent = this.getExtent();
  this.mapWidth = this.extent[1] - this.extent[0];
  this.mapHeight = this.extent[3] - this.extent[2];

  this.updateTransf();
  
  _self = this;

  this.mapcanvas.addEventListener('mousemove', this.OnMouseMove, false);
  this.mapcanvas.addEventListener('mousedown', this.OnMouseDown, false);
  
  this.draw();
  this.buffer = this.createBuffer(this.mapcanvas);
};

// multi constructors
//GeoVizMap.fromComponents = function(geojson_url, canvas) {};
//GeoVizMap.fromComponents = function(zipfile_url, canvas) {};

// static functions
//GeoVizMap.version = function() {
//  return GeoVizMap.version;
//};

//
GeoVizMap.prototype = {
  // static vars
  //version: "0.1",

  // member functions
  updateTransf: function() {
    var whRatio = this.mapWidth / this.mapHeight,
        xyRatio = this.width / this.height;
    this.offsetX = 0.0;
    this.offsetY = 0.0; 
    if ( xyRatio > whRatio ) {
      this.offsetX = (this.width - this.height * whRatio) / 2.0;
    } else if ( xyRatio < whRatio ) {
      this.offsetY = (this.height - this.width / whRatio) / 2.0;
    }
    this.scaleX = d3.scale.linear()
                    .domain([this.extent[0], this.extent[1]])
                    .range([0, this.width - this.offsetX * 2]);
    this.scaleY = d3.scale.linear()
                  .domain([this.extent[2], this.extent[3]])
                  .range([this.height - this.offsetY * 2, 0]);
    this.scalePX = d3.scale.linear()
                    .domain([0, this.width - this.offsetX * 2])
                    .range([this.extent[0], this.extent[1]]);
    this.scalePY = d3.scale.linear()
                  .domain([this.height - this.offsetY * 2, 0])
                  .range([this.extent[2], this.extent[3]]);
  },
  mapToScreen: function(px,py) {
    var x = this.scaleX(px) + this.offsetX;
    var y = this.scaleY(py) + this.offsetY;
    return [x, y];
  },
  screenToMap: function(x,y) {
    var px = this.scalePX(x - this.offsetX);
    var py = this.scalePY(y - this.offsetY);
    return [px, py];
  },
  getExtent: function() {
    var minX = Number.POSITIVE_INFINITY,
        maxX = Number.NEGATIVE_INFINITY,
        minY = Number.POSITIVE_INFINITY,
        maxY = Number.NEGATIVE_INFINITY;
    this.bbox = [];
    that = this;
    this.geojson.features.forEach(function(feat,i) {
      var bminX = Number.POSITIVE_INFINITY,
          bmaxX = Number.NEGATIVE_INFINITY,
          bminY = Number.POSITIVE_INFINITY,
          bmaxY = Number.NEGATIVE_INFINITY;
      feat.geometry.coordinates.forEach(function(coords,j) {
        coords.forEach( function( xy,k ) {
          x = xy[0], y = xy[1];
          if (x > maxX) {maxX = x;}
          if (x < minX) {minX = x;}
          if (y > maxY) {maxY = y;}
          if (y < minY) {minY = y;}
          if (x > bmaxX) {bmaxX = x;}
          if (x < bminX) {bminX = x;}
          if (y > bmaxY) {bmaxY = y;}
          if (y < bminY) {bminY = y;}
        });
      });
      that.bbox.push([bminX, bmaxX, bminY, bmaxY]);
    });

    return [minX, maxX, minY, maxY];
  },

  // create buffer canvas
  createBuffer: function() {
    var _buffer = document.createElement("canvas");
    _buffer.width = this.mapcanvas.width;
    _buffer.height = this.mapcanvas.height;
    var bufferCtx = _buffer.getContext("2d");
    bufferCtx.drawImage(this.mapcanvas, 0, 0);
    return _buffer;
  },

  highligh: function( id) {
          var context = _self.mapcanvas.getContext("2d");
          context.clearRect(0, 0, _self.mapWidth, _self.mapHeight);
          context.drawImage( _self.buffer, 0, 0);
          context.lineWidth = 1;
          context.strokeStyle = "#00ffff";
          context.fillStyle = "yellow";
          console.log(id);
          _self.geojson.features[id].geometry.coordinates.forEach(
            function( coords, j ) {
              context.beginPath();
              coords.forEach( function(xy,k) {
                var x = xy[0], y = xy[1];
                x = _self.scaleX(x)+ _self.offsetX;
                y = _self.scaleY(y)+ _self.offsetY;
      
                if (k === 0) {
                  context.moveTo(x,y);
                } else {
                  context.lineTo(x,y);
                }
              });
              context.closePath();
              context.stroke();
              context.fill();
            }
          );
          //
          localStorage["highlight"] = id;
          if (window.opener) {
            console.log(window.opener.highlighted);
          }
  },
  // register mouse events of canvas
  OnMouseDown: function(evt) {
    var x = evt.pageX, y = evt.pageY;
    var pt = _self.screenToMap(x,y);
    var px = pt[0], py = pt[1];
    {
      // highlight selected
      _self.bbox.forEach( function( box, i ) {
        if ( px >= box[0] && px <= box[1] && py >= box[2] && py <= box[3] ) {
          _self.highligh(i);
        }
      });
    }
  },
  OnMouseMove: function(evt) {
    var x = evt.pageX, y = evt.pageY;
    pt = _self.screenToMap(x,y);
    //console.log(pt[0], pt[1]);
  },
  // draw map
  draw: function() {
    console.log(this.geojson);
    var context = this.mapcanvas.getContext("2d");
    context.imageSmoothingEnabled= false;
    context.strokeStyle = "#cccccc";
    context.fillStyle = "blue";
    context.lineWidth = 1;

    var that = this;
    this.geojson.features.forEach( function(feat,i) {
      feat.geometry.coordinates.forEach(function(coords,j) {
        context.beginPath();
        coords.forEach( function(xy,k) {
          var x = xy[0], y = xy[1];
          x = that.scaleX(x)+ that.offsetX;
          y = that.scaleY(y)+ that.offsetY;

          if (k === 0) {
            context.moveTo(x,y);
          } else {
            context.lineTo(x,y);
          }
        });
        context.closePath();
        context.stroke();
        context.fill();
      });
    });

  }, // draw()
  
};
