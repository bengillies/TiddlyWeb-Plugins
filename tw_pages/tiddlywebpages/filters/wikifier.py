from tiddlyweb.wikitext import render_wikitext
from tiddlyweb.config import config
from tiddlyweb.model.tiddler import Tiddler

def wikifier(mystr, path):
    """
    Render TiddlyWiki wikitext in the provided
    string to HTML. This function taken and modified
    from wikklytextrender.py
    """
    tiddler = Tiddler('tmp')
    tiddler.text = mystr
    tiddler.recipe = path
    environ={'tiddlyweb.config': config}
    return render_wikitext(tiddler, environ)