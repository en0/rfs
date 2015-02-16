from os import path, listdir, stat, remove
from base64 import b64encode, b64decode
from functools import wraps
import tempfile
import tarfile
import pwd
import grp

from flask import abort, jsonify, session, request
from rfsweb import app
from rfsweb.core.resource import JsonEndpoint, StreamEndpoint, add_resource
from rfsweb.core.exceptions import ApplicationException
import pam
from mimetypes import guess_type


def login_required(callback):
    """ Decorator used to lock methods to only authenticated users.

    This function will check for a valid session. If one is not found
    the callback will be skipped and the response will be sort-circuited by an exception.

    :param callback: The function being decorated
    :return: Result of callback
    :raise: ApplicationException: If invalid session.
    """

    @wraps(callback)
    def _wrapper(*args, **kwargs):
        if 'user' in session:
            return callback(*args, **kwargs)
        raise ApplicationException(
            message="Authorization Required",
            status_code=401,
            headers={'WWW-Authenticate': Authority.__url__}
        )

    return _wrapper


@app.errorhandler(ApplicationException)
def handle_unathorized_usage(error):
    """ Hook all exceptions and format a json response.
    :type error: ApplicationException
    :param error: The exception that caused this hook to be called
    :return: A valid flask response.
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    response.headers = error.headers
    return response


def get_mode_string(value):
    """ Convert a octal value representing permissions into a unix -rwx------ string.

    The data should be sent in as a integer.

    :type value: int
    :param value: Perms values.
    :return: str representation of the given permissions.
    """

    def _get_mode_part(_value):
        _str = 'r' if (_value & 0b100) == 0b100 else '-'
        _str += 'w' if (_value & 0b010) == 0b010 else '-'
        _str += 'x' if (_value & 0b001) == 0b001 else '-'
        return _str

    # Get each part and concatenate return
    _user = int(oct(value)[-3])
    _group = int(oct(value)[-2])
    _global = int(oct(value)[-1])
    return _get_mode_part(_user) + _get_mode_part(_group) + _get_mode_part(_global)


class RNode(JsonEndpoint):
    """ Metadata about a file or folder on the system.

    This Endpoint returns everything as json. It is expected that all method returns will be json serializable.
    """

    __endpoint__ = "rdir_view"
    __url__ = "/api/v1/node/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @staticmethod
    def as_embedded(full_name, short_name):
        """ Get iNode data and pack into json object.

        :param full_name: The full path of a file.
        :param short_name: The basename of a file.
        :return: Json object repressing iNode data.
        """

        _stat = stat(full_name)

        # A really lame attempt at hypermedia support.
        _links = {
            'node': "{0}{1}".format(RNode.__url__, b64encode(full_name)),
            'delete': None,
        }

        if path.isdir(full_name):
            _links['download'] = "{0}{1}".format(Tar.__url__, b64encode(full_name))
        else:
            _links['download'] = "{0}{1}".format(Content.__url__, b64encode(full_name))

        # Get mime type and default it to application/octet-stream if the type cannot be determined.
        _mime_type, _ = guess_type(full_name)
        if not _mime_type:
            _mime_type = 'application/octet-stream'

        # Get the first part of the mime type for UI reasons.
        _mime_group = _mime_type.split('/')[0]

        # Pack the inode data.
        return {
            '_links_': _links,
            'is_dir': path.isdir(full_name),
            'node_id': b64encode(full_name),
            'full_name': full_name,
            'short_name': short_name,
            'atime': _stat.st_atime,
            'mtime': _stat.st_mtime,
            'ctime': _stat.st_ctime,
            'size': _stat.st_size,
            'mode': {
                'label': get_mode_string(_stat.st_mode),
                'value': int(oct(_stat.st_mode)[-3:]),
            },
            'owner': pwd.getpwuid(_stat.st_uid).pw_name,
            'group': grp.getgrgid(_stat.st_gid).gr_name,
            'mime_type': _mime_type,
            'mime_group': _mime_group,
        }

    @login_required
    def get(self, node_id):
        """ Get the details about the requested path.

        If the target is a directory, the next level of files and folders will also be loaded.

        :param node_id: The base64 encode path being requested.
        :return: iNode (+ some extra stuff) of requested path.
        """

        # Default the path to root if not given.
        if not node_id:
            node_id = b64encode(path.sep)
        _path = b64decode(node_id)

        # Make a fake name for root. (change to C: for windows? - i don't know, i don't care).
        if _path == '/':
            _short_path = "ROOT"
        else:
            _short_path = path.basename(_path)

        # Get the iNode medatadata (+ some extra stuff)
        _ret = RNode.as_embedded(_path, _short_path)

        # If the requested node is a direcotry, Load the next level of nodes.
        if path.isdir(_path):
            _ret['files'] = []
            _ret['dirs'] = []

            for p in listdir(_path):
                _full_name = path.join(_path, p)
                _embedded = RNode.as_embedded(_full_name, p)
                if path.isdir(_full_name):
                    _ret['dirs'].append(_embedded)
                else:
                    _ret['files'].append(_embedded)

        return _ret

    def delete(self, node_id):
        """ Remove the node specified in node_id.

        If the node is a directory, the delete will be recursive.

        :param node_id: Base64 encoded path to remove.
        :return: status
        """
        pass

    def put(self, node_id):
        """ Create or update iNode metadata.

        This function will update or create a iNode at the specified location.
        This is a put because we know the exact name of the new or existing resource.

        :param node_id: Base64 encoded path to remove.
        :return: Status
        :raises ApplicationException: (409) If the target node already exists.
        """
        pass


class Content(StreamEndpoint):
    """ Deal with file data.
    """
    __endpoint__ = "rcontent_view"
    __url__ = "/api/v1/content/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @login_required
    def get(self, node_id):
        """ Stream the content of a file.

        :param node_id: Base64 encoded path to remove.
        :raises ApplicationException: (404) if the path is a folder.
        :return: Stream O' File
        """
        if not node_id:
            node_id = b64encode(path.sep)
        _path = b64decode(node_id)
        if not path.isfile(_path):
            abort(404)

        # Force name of file.
        return _path, path.basename(_path)

    @login_required
    def put(self, node_id):
        """ Create or update the existing file with the given content.

        This is a put because we know the exact name of the new or existing resource.

        :param node_id: base64 encoded path
        :return: status
        """
        pass


class Tar(StreamEndpoint):
    """ Deal with directory data.
    """
    __endpoint__ = "rtar_view"
    __url__ = "/api/v1/download/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @login_required
    def get(self, node_id):
        """ Create a Gzipped Tar file of the given path and stream it back.

        Due to some complication i cannot quite remember, A temp file had to be used for this to work.
        A callback is made after streaming is complete. We use this to remove the temp file.

        :param node_id: Base64 encoded path to remove.
        :return: Stream O' tarfile.
        """
        if not node_id:
            node_id = b64encode(path.sep)
        _path = b64decode(node_id)

        # Create a temp file to hold the tar file.
        _, _tmp = tempfile.mkstemp(suffix='.tgz')
        fid = tarfile.open(_tmp, mode="w:gz")
        fid.add(_path, arcname=path.basename(_path))
        fid.close()

        # callback to cleanup the temp file.
        def _cleanup():
            remove(_tmp)

        # Return with specific file name and callback for clean-up
        return _tmp, "{0}.tgz".format(path.basename(_path)), _cleanup

    @login_required
    def post(self, node_id):
        """ Upload a directory structure from tarball.

        The method will expect a parent directory in node_id. In that path the tar will be extracted.
        This is a post because we don't provide the actual name of the new resource.

        :param node_id: Base64 encoded path
        :return: Status
        """
        pass


class Authority(JsonEndpoint):
    """ Handle logging in and logging out a user.

    I am thinking I should change this to GET a session and use basic authentication header.
    Then DELETE sessionID would be log out but i am not sure that will be very usable in javascript land.
    so for now, you got this.
    """
    __endpoint__ = "rauthority_view"
    __url__ = "/api/v1/authority/"
    __pk__ = None
    __pk_type__ = None

    def post(self):
        """ Authenticate user and write cookie for there session.

        :raises ApplicationException: (401) if bad credentials are given.
        :return: Status
        """
        username = request.json.get('username', '')
        password = request.json.get('password', '')
        print('Authentication Request from: {0}'.format(username))
        if pam.authenticate(username, password):
            session['user'] = dict(name=username)
            return dict(message="OK, here is a cookie.")

        raise ApplicationException(
            message="Wrong username or password",
            status_code=401,
            headers={'WWW-Authenticate': Authority.__url__}
        )


def register_route(view, methods=None):
    """ Helper function to register a route to a MethodView class.

    The method view class must implement the following statics.

    __endpoint__    Name the endpoint
    __url__         The url to register under
    __pk__          The primary key used for methods
    __pk_type__     The type of that primary key

    :param view: Method View with required statics
    :param methods: The supported methods of this method view.
    :return: None
    """
    add_resource(
        view,
        view.__endpoint__,
        view.__url__,
        pk=view.__pk__,
        pk_type=view.__pk_type__,
        methods=methods
    )

# Register all the routes.
register_route(RNode)
register_route(Content, ['GET'])
register_route(Tar, ['GET'])
register_route(Authority, ['POST'])

