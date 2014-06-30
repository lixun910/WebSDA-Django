jQuery.download = function(url, data, method) {
    //url and data options required
    if (url && data) { 
        //data can be string of parameters or array/object
        data = typeof data == 'string' ? data : jQuery.param(data);
        //split params into form inputs
        var inputs = '';
        jQuery.each(data.split('&'), function() { 
            var pair = this.split('=');
            inputs += '<input type="hidden" name="' + pair[0] +
                '" value="' + pair[1] + '" />'; 
        });
        //send request
        jQuery('<form action="' + url +
            '" method="' + (method || 'post') +'">' + inputs + '</form>')
        .appendTo('body').submit().remove();
    };
}

jQuery.GetTextsFromObjs = function(objs) {
  var texts = [];
  objs.each(function(i, obj){
    if (obj.className != "placeholder") {
      texts.push($(obj).text());
    }
  });
  return texts;
}

jQuery.GetValsFromObjs = function(objs) {
  var vals = [];
  objs.each(function(i, obj){
    if (obj.className != "placeholder") {
      vals.push($(obj).val());
    }
  });
  return vals;
}

function guid() {
  function s4() {
    return Math.floor((1 + Math.random()) * 0x10000)
               .toString(16)
               .substring(1);
  }
  return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
         s4() + '-' + s4() + s4() + s4();
}

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function getFileName(url) {
    return url.substring(url.lastIndexOf('/')+1);
}

function getSuffix(path) {
    return path.substring(path.lastIndexOf('.')+1);
}

function getName(path) {
    return path.substring(0, path.lastIndexOf('.'));
}

function getFileNameNoExt(url) {
    return getName(getFileName(url));
}

function FetchZipResource(url, onSuccess) {
    console.log(url);
    var xhr = new XMLHttpRequest();
    xhr.responseType="blob";
    xhr.open("GET", url, true);
    xhr.onload = function(e) {
        if(this.status == 200) {
            var blob = this.response;
            // use a zip.BlobReader object to read zipped data stored into blob variable
            zip.createReader(new zip.BlobReader(blob), function(zipReader) {
                // get entries from the zip file
                zipReader.getEntries(function(entries) {
                    // get data from the first file
                    console.log(entries[0]);
                    entries[0].getData(new zip.TextWriter("text/plain"), function(content) {
                        console.log("content:",content);
                        content = content.replace(/\n/g, "");
                        //console.log(content);
                        zipReader.close();
                        onSuccess(content);
                    });
                });
            });
        }
    }
    xhr.send();
}

function sortKeys(dict) {
  var field_names = [];
  for ( var key in fields ){
    field_names.push(key); 
  }
  field_names.sort();
}
