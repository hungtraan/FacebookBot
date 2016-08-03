function facebookInit() {
    FB.Event.subscribe('auth.login', function(response) {
        var uid = response.authResponse.userID;
        console.log(uid);
    });
    
    FB.getLoginStatus(function(response) {
    if (response.status === 'connected') {
            var uid = response.authResponse.userID;
            var accessToken = response.authResponse.accessToken;
            console.log(uid);
        } else if (response.status === 'not_authorized') {
            alert("Please login to Facebook");
        }
    });
}
