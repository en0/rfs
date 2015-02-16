var app = angular.module('theApp', ['ngRoute','ui.bootstrap']);

app.config(['$routeProvider', '$interpolateProvider', function($routeProvider, $interpolateProvider) {
    $routeProvider
        .when("/", {templateUrl: "partials/home.html", controller: "homeCtrl"})
        .when("/home/", {templateUrl: "partials/home.html", controller: "homeCtrl"})

        .when("/fs/", {templateUrl: "partials/fs.html", controller: "fsCtrl"})
        .when("/fs/:path", {templateUrl: "partials/fs.html", controller: "fsCtrl"})
        /* .when("/fsinfo/:path", {templateUrl: "partials/fsinfo.html", controller: "fsInfoCtrl"}) */
        .when("/fscontent/:type/:path", {templateUrl: "partials/fscontent.html", controller: "fsContentCtrl"})

        .when("/about", {templateUrl: "partials/about.html", controller: "aboutCtrl"})
        .when("/404", {templateUrl: "partials/404.html", controller: "nullCtrl", isPublic: true})
        .otherwise({ redirectTo: '/404' });

    $interpolateProvider
        .startSymbol('[[')
        .endSymbol(']]');
}]);

