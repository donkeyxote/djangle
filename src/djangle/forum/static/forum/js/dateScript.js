function date_fun(registration) {
        var today = new Date();
        var time = '';
        var diff;
        diff = today.getYear()-registration.getYear();
        if(diff > 0){
            if(diff==1) time= '1 year ago';
            else time = diff.toString()+' years ago';
        }
        else {
            diff = today.getMonth() - registration.getMonth();
            if (diff > 0){
                if(diff == 1) time='1 month ago';
                else diff = diff.toString()+' months ago';
            }
            else{
                diff = today.getDate() - registration.getDate();
                if(diff > 0){
                    if(diff == 1) time='1 day ago';
                    else time = diff.toString()+' days ago';
                }
                else time = 'Less than a day';
            }
        }
        return time;
    }
