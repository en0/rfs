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
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    response.headers = error.headers
    return response


def get_mode_string(value):
    def _get_mode_part(value):
        _str = 'r' if (value & 0b100) == 0b100 else '-'
        _str += 'w' if (value & 0b010) == 0b010 else '-'
        _str += 'x' if (value & 0b001) == 0b001 else '-'
        return _str

    _user = int(oct(value)[-3])
    _group = int(oct(value)[-2])
    _global = int(oct(value)[-1])
    return _get_mode_part(_user) + _get_mode_part(_group) + _get_mode_part(_global)


class RNode(JsonEndpoint):
    __endpoint__ = "rdir_view"
    __url__ = "/api/v1/node/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @staticmethod
    def as_embedded(full_name, short_name):
        _stat = stat(full_name)

        _links = {
            'node': "{0}{1}".format(RNode.__url__, b64encode(full_name)),
            'delete': None,
        }

        if path.isdir(full_name):
            _links['download'] = "{0}{1}".format(Tar.__url__, b64encode(full_name))
        else:
            _links['download'] = "{0}{1}".format(Content.__url__, b64encode(full_name))

        _mime_type, _ = guess_type(full_name)
        if not _mime_type:
            _mime_type = 'application/octet-stream'
        _mime_group = _mime_type.split('/')[0]

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
        if not node_id:
            node_id = b64encode(path.sep)
        _path = b64decode(node_id)

        if _path == '/':
            _short_path = "ROOT"
        else:
            _short_path = path.basename(_path)

        _ret = RNode.as_embedded(_path, _short_path)

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


    def post(self):
        pass

    def delete(self):
        pass

    def put(self, user_id):
        pass


class Content(StreamEndpoint):
    __endpoint__ = "rcontent_view"
    __url__ = "/api/v1/content/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @login_required
    def get(self, node_id):
        if not node_id:
            node_id = b64encode(path.sep)
        _path = b64decode(node_id)
        if not path.isfile(_path): abort(404)

        return _path, path.basename(_path)
        #return _path


class Tar(StreamEndpoint):
    __endpoint__ = "rtar_view"
    __url__ = "/api/v1/download/"
    __pk__ = "node_id"
    __pk_type__ = "string"

    @login_required
    def get(self, node_id):
        if not node_id: node_id = b64encode(path.sep)
        _path = b64decode(node_id)
        _, _tmp = tempfile.mkstemp(suffix='.tgz')
        fid = tarfile.open(_tmp, mode="w:gz")
        fid.add(_path, arcname=path.basename(_path))
        fid.close()

        def _cleanup():
            remove(_tmp)

        # Return with specific file name and callback for clean-up
        return _tmp, "{0}.tgz".format(path.basename(_path)), _cleanup


class Authority(JsonEndpoint):
    __endpoint__ = "rauthority_view"
    __url__ = "/api/v1/authority/"
    __pk__ = None
    __pk_type__ = None

    def post(self):
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


add_resource(RNode, RNode.__endpoint__, RNode.__url__, pk=RNode.__pk__, pk_type=RNode.__pk_type__)
add_resource(Content, Content.__endpoint__, Content.__url__, pk=Content.__pk__, pk_type=Content.__pk_type__,
             methods=['GET'])
add_resource(Tar, Tar.__endpoint__, Tar.__url__, pk=Tar.__pk__, pk_type=Tar.__pk_type__, methods=['GET'])
add_resource(Authority, Authority.__endpoint__, Authority.__url__, pk=Authority.__pk__, pk_type=Authority.__pk_type__,
             methods=['POST'])

