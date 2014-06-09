var User = function(name, age) {
    this.name = name;
    this.age = age;
}

User.prototype = {
    getName: function() {
        return this.name;
    },

    setName: function(name) {
        this.name = name;
    }
}

var GeoVizMap = function(geojson, mapcanvas, extent) {
  // members
  this.geojson = geojson;
  this.mapcanvas = mapcanvas;
  this.width = mapcanvas.width;
  this.height = mapcanvas.height;

  this.extent = extent;
  if ( extent == undefined ) this.extent = this.getExtent();
  this.mapWidth = extent[1] - extent[0];
  this.mapHeight = extent[3] - extent[2];

  var whRatio = this.mapWidth / this.mapHeight,
      xyRatio = this.width / this.height;
 
  this.offsetX = 0.0;
  this.offsetY = 0.0; 

  if ( xyRatio > whRatio ) {
    this.offsetX = (this.width - this.height * whRatio) / 2.0;
  } else if ( xyRatio < whRatio ) {
    this.offsetY = (this.height - this.width / whRatio) / 2.0;
  }
  this.buffer = this.createBuffer(this.mapcanvas);
  this.scaleX = d3.scale.linear()
                  .domain([this.extent[0], this.extent[1]])
                  .range([0, this.width - this.offsetX * 2]);
  this.scaleY = d3.scale.linear()
                  .domain([this.extent[2], this.extent[3]])
                  .range([this.height - this.offsetY * 2, 0]);

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
  getExtent: function() {
    var minX = Number.POSITIVE_INFINITY,
        maxX = Number.NEGATIVE_INFINITY,
        minY = Number.POSITIVE_INFINITY,
        maxY = Number.NEGATIVE_INFINITY;

    this.geojson.features.forEach(function(feat,i) {
      feat.geometry.coordinates.forEach(function(coords,j) {
        coords.forEach( function( xy,k ) {
          x = xy[0], y = xy[1];
          if (x > maxX) {maxX = x;}
          if (x < minX) {minX = x;}
          if (y > maxY) {maxY = y;}
          if (y < minY) {minY = y;}
        });
      });
    });

    this.extent = [minX, maxX, minY, maxY];
  },

  // create buffer canvas
  createBuffer: function() {
    var _buffer = document.createElement("canvas");
    _buffer.width = this.mapcanvas.width;
    _buffer.height = this.mapcanvas.height;
    return _buffer;
  },

  // register mouse events of canvas

  // draw map
  draw: function() {
    console.log(this.geojson);
    var context = this.mapcanvas.getContext("2d");
    context.fillStyle = 'blue';
    context.fillRect(100, 100, 100, 100);
    
    context.strokeStyle = "#cccccc";
    context.fillStyle = "#ffffff";

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
      });
    });

  }, // draw()
  
};
