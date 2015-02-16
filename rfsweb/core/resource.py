from rfsweb import app
from flask import jsonify, Response, session
from flask.views import MethodView
from mimetypes import guess_type
from os import stat


def add_resource(view, endpoint, url, pk='id', pk_type='int', methods=None):
    """ Add a resource to the app.

    This is a short-cut for Flask.add_url_rule. This function will create
    rules following a basic restful service route model.

    Example:
        GET => /path/to/resource
        POST => /path/to/resource
        GET => /path/to/resource/<pk:pk_type>
        PUT => /path/to/resource/<pk:pk_type>
        DELETE => /path/to/resource/<pk:pk_type>

    :type view: MethodView
    :type endpoint: str
    :type url: str
    :type pk: str
    :type pk_type: str

    :param view: Reference to the MethodView class being used.
    :param endpoint: The endpoint name for this class.
    :param url: The URL used to access this endpoint
    :param pk: The primary key used to identify a resource.
    :param pk_type: The primitive type of the primary key.
    """

    if not methods:
        methods = ['GET', 'POST', 'PUT', 'DELETE']

    _uri = "{0}<{2}:{1}>".format(url, pk, pk_type)
    view_fn = view.as_view(endpoint)
    if 'GET' in methods:
        app.add_url_rule(url, defaults={pk: None}, view_func=view_fn, methods=['GET'])
        app.add_url_rule(_uri, view_func=view_fn, methods=['GET'])

    if 'POST' in methods:
        app.add_url_rule(url, view_func=view_fn, methods=['POST'])

    if 'PUT' in methods:
        app.add_url_rule(_uri, view_func=view_fn, methods=['PUT'])

    if 'DELETE' in methods:
        app.add_url_rule(_uri, view_func=view_fn, methods=['DELETE'])

    if 'OPTIONS' in methods:
        app.add_url_rule(url, defaults={pk: None}, view_func=view_fn, methods=['OPTIONS'])
        app.add_url_rule(_uri, view_func=view_fn, methods=['OPTIONS'])


class JsonEndpoint(MethodView):
    def dispatch_request(self, *args, **kwargs):
        """ Dispatch the request to a specific method handler.

        JsonEndpoint captures the resulting object from the dispatch and converts it to json.

        :rtype : str
        :param args: General arguments.
        :param kwargs: Keyword Arguments.
        :return: String
        """
        _ret = super(JsonEndpoint, self).dispatch_request(*args, **kwargs)
        return jsonify(_ret)


class StreamEndpoint(MethodView):
    def dispatch_request(self, *args, **kwargs):
        """ Dispatch the request to a specific method handler.

        StreamEndpoint expects a filename. That file will then be streamed down
        in the response

        :rtype : str
        :param args: General arguments.
        :param kwargs: Keyword Arguments.
        :return: String
        """
        ret = super(StreamEndpoint, self).dispatch_request(*args, **kwargs)
        callback = None

        if type(ret) == tuple:
            if len(ret) == 3:
                path, fname, callback = ret
            else:
                path, fname = ret

            name = "filename={0}".format(fname)
        else:
            path = ret
            name = 'inline'

        mime_type, _ = guess_type(path)
        if not mime_type: mime_type = 'application/octet-stream'
        file_size = stat(path).st_size

        return Response(
            stream_content(path, 512, callback),
            headers={
                "Content-Type": mime_type,
                "Content-Disposition": name,
                "Content-Transfer-Enconding": "binary",
                "Content-Length": file_size
            }
        )


def stream_content(path, chunk_size, callback=None):
    with open(path, 'r') as fid:
        _bytes = fid.read(chunk_size)
        while _bytes:
            yield _bytes
            _bytes = fid.read(chunk_size)
    if callback: callback()
