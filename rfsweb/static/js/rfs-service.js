'use strict'

angular.module('theApp')

    // Factory for user stuff
    .factory('authority', ['$http', '$q', '$modal', function($http, $q, $modal) {
        var urlBase = '/api/v1/authority/';
        var _ret = {};

        // Spawn login modal
        _ret.showModal = function(callback) {

            // Start modal instance
            var modalInstance = $modal.open({
                templateUrl: 'partials/login_modal.html',
                controller: 'loginCtrl',
                size: ""
            });

            // On complete, execute callback.
            modalInstance.result.then(function (status) {
                callback(status);
            });
        };

        // Log in (sets a cookie)
        _ret.authenticate = function(username, password) {
            var def = $q.defer();

            // Attempt a login
            $http.post(urlBase, {"username":username, "password":password})
            .success(function(data) {
                def.resolve(data);
            })
            .error(function(response, code) {
                def.reject(response);
            });

            return def.promise;
        }

        return _ret;
    }])

    // Factory for node content
    .factory('content', ['$http', '$q', 'authority', function($http, $q, authority) {
        var urlBase = '/api/v1/content/';
        var _ret = {};

        _ret.get = function(path) {
            var def = $q.defer();
            var url = urlBase + path;

            // Request content
            $http.get(url)

            // Success, resolve promise
            .success(function(data) {
                def.resolve(data);
            })

            // On error, check for 401 and spawn login modal.
            .error(function(data,code) {
                if(code == 401) {

                    // After successful login, retry the node request.
                    authority.showModal(function() {

                        // Request a node
                        $http.get(url).success(function(data) {
                            def.resolve(data);
                        });

                    });
                }
            });

            return def.promise;
        };

        return _ret;
    }])

    // Factory for filesystem interaction.
    .factory('node', ['$http', '$q', 'authority', function($http, $q, authority) {
        var urlBase = '/api/v1/node/';
        var _ret = {};

        _ret.get = function(path) {

            /* Get a specific node and it's children                    *
            * This function has all the metadata information about      *
            * a specific node. It will also contain the first level     *
            * of children folders and files.                            */

            var def = $q.defer();
            var url = urlBase + path;

            // Request a node
            $http.get(url)

            // Success, resolve promise
            .success(function(data) {
                def.resolve(data);
            })

            // On error, check for 401 and spawn login modal.
            .error(function(data,code) {
                if(code == 401) {

                    // After successful login, retry the node request.
                    authority.showModal(function() {

                        // Request a node
                        $http.get(url).success(function(data) {
                            def.resolve(data);
                        });

                    });
                }
            });

            return def.promise;
        };

        return _ret;
    }])
