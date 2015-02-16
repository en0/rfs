'use strict'

app.controller('rootCtrl', ['$rootScope', '$location', function($rootScope, $location) {
    $rootScope.go = function(path) {
        $location.path(path);
    };

    $rootScope.btoa = function (s) {
        return btoa(s);
    }
    /** Root Controller **/
}]);

app.controller('homeCtrl', ['$scope', function($scope) {
    document.title = 'Dashboard';
}]);

app.controller('aboutCtrl', ['$scope', function($scope) {
    document.title = 'About';
}]);

app.controller('fsCtrl', ['$scope', '$routeParams', '$modal', 'node', function($scope, $routeParams, $modal, $node) {

    document.title = 'File Explorer';

    // Default value is /
    if(typeof $routeParams.path === 'undefined')
        $routeParams.path = "Lw==";

    // Get filesystem nodes
    $node.get($routeParams.path).then(function(data) {

        // UI data bindings
        $scope.nodes = data;
        document.title = 'File Explorer - ' + data.short_name;

        console.log($scope.nodes);

        // Reset crumbs and seed data with ROOT link
        $scope.crumbs = [{'link':btoa('/'),'label':'ROOT'}];
        var _link = "";

        // Cycle through each node in path and add crumb back.
        var _path_split = data.full_name.substring(1).split('/');
        angular.forEach(_path_split, function(_label, index) {
                _link += "/" + _label;
                var _meta = { 'link': btoa(_link), 'label': _label };
                $scope.crumbs.push(_meta);
        });
    });

    // Open modal to handle upload requests
    $scope.startUpload = function(path) {
        var modalInstance = $modal.open({
            templateUrl: 'partials/upload_modal.html',
            controller: 'uploadCtrl'
        });
    };

    // Show fs info in a modal
    $scope.fsinfo = function(info_path) {
        $modal.open({
            templateUrl: 'partials/fsinfo_modal.html',
            controller: 'fsInfoCtrl',
            resolve: {
                'path': function() { return info_path; }
            }
        });
    };
}]);

app.controller('fsInfoCtrl', ['$scope', '$routeParams', '$modalInstance', 'node', 'path', function($scope, $routeParams, $modalInstance, $node, path) {

    // Get the node metatdata
    $node.get(path).then(function(data) {
        // Set scope vars
        $scope.node = data;
    });

    $scope.close = function() {
        $modalInstance.close('Close');
    };

}]);

app.controller('fsContentCtrl', ['$scope', '$routeParams', 'node', 'content', function($scope, $routeParams, $node, $content) {

    document.title = 'Loading File';

    // HTML5 (audio, video) will load from the src if the type is correct.
    $scope.type = $routeParams.type;
    $scope.src = '/api/v1/content/' + $routeParams.path;

    // Get node metadata
    $node.get($routeParams.path).then(function(data) {
        console.log(data);
        $scope.node = data;
        document.title = data.short_name;
    });

    // For text docs we are using ACE.
    // This takes a bit more scripting to load
    if($scope.type == 'text') {
        $content.get($routeParams.path)
        .then(function(data) {
            var editor = ace.edit("editor");
            editor.setTheme("ace/theme/monokai");
            editor.getSession().setMode("ace/mode/text");
            editor.getSession().doc.setValue(data);
        });
    }

    // Force presentation type
    $scope.force_type = function(target_type) {
        $scope.go('fscontent/'+target_type+'/'+$routeParams.path);
    };
}]);

app.controller('loginCtrl', ['$scope', '$modalInstance', 'authority', function($scope, $modalInstance, authority){
    $scope.alert = null;

    // The login button.
    $scope.login = function() {

        // Give status update
        $scope.alert = {
            'type': 'primary',
            'msg': 'Verifying Credentials...'
        };

        // Send authentication request
        authority.authenticate($scope.username, $scope.password)

        // Do callback on success. Post alert on error.
        .then(function(data) {
            $modalInstance.close(data);
        }, function(a) {
            $scope.alert = { 'msg': a.message };
        });
    };

    // Close alert click event
    $scope.closeAlert = function(index) {
        $scope.alerts.splice(index, 1);
    };
}]);

app.controller('uploadCtrl', ['$scope', '$modalInstance', function($scope, $modalInstance) {

    $scope.upload_type = "nf";
    $scope.cancel = function() {
        $modalInstance.dismiss('cancel');
    };

    $scope.ok = function() {
        // reference: http://stackoverflow.com/questions/13963022/angularjs-how-to-implement-a-simple-file-upload-with-multipart-form
        $modalInstance.close('Not Implemented');
    };
}]);


