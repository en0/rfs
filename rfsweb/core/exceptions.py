class ApplicationException(Exception):
    status_code = 401

    def __init__(self, message, status_code=None, payload=None, headers=None):
        self.message = message
        self.headers = headers or {}
        if status_code:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
