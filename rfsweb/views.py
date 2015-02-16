from rfsweb import app
from flask import render_template, abort
from jinja2.exceptions import TemplateNotFound


@app.route('/')
@app.route('/<path:path>')
def webclient(path="index.html"):
    """ Default route.

    This is a catch all. It is locked to the /templates directory.

    Arguments:
        path - The path to the file relative to the /templates directory

    Returns:
        Response Object
    """
    try:
        return render_template(path)
    except TemplateNotFound:
        abort(404)
