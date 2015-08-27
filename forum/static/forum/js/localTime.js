function date(pub_date){
    var date = new Date( Date.parse(pub_date+' UTC'));
    return date.toLocaleString();
    }
