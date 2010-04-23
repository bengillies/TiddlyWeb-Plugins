"""
tests to ensure binary tiddlers are uploaded correctly
"""

from setup_test import setup_store, setup_web

from tiddlyweb.config import config
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.store import NoTiddlerError

import httplib2

config['system_plugins'] = ['tiddlywebplugins.form']

def test_upload_binary_file():
    """
    upload a binary file without any meta data
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #set the binary file to upload (NB - this POST data taken from HTTPFox)
    binary_data = open('test/test.bmp').read()
    post_data = [
        '-----------------------------984943658114410893',
        'Content-Disposition: form-data; name="file"; filename="test.bmp"',
        'Content-Type: image/bmp',
        ''
    ]
    post_data.append(binary_data)
    post_data.append('-----------------------------984943658114410893--')
    
    post_body = '\n'.join(post_data)

    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'multipart/form-data; '
            'boundary=---------------------------984943658114410893',
            'Content-Length': '301'
        },
        body=post_body)[0]
    assert response.status == 204
    
    tiddler = Tiddler('test.bmp', 'foo')
    try:
        tiddler = store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler not put into store')
    
    assert tiddler.title == 'test.bmp'
    assert tiddler.text == binary_data

def test_upload_binary_with_meta():
    """
    upload a binary file with some tags and an explicit title
    """
    store = setup_store()
    setup_web()
    http = httplib2.Http()
    
    #set the binary file to upload (NB - this POST data taken from HTTPFox)
    binary_data = open('test/test.bmp').read()
    post_data = [
        '-----------------------------984943658114410893',
        'Content-Disposition: form-data; name="title"',
        '',
        'RGBSquare.bmp',
        '-----------------------------984943658114410893',
        'Content-Disposition: form-data; name="tags"',
        '',
        'image bitmap [[test data]]',
        '-----------------------------984943658114410893',
        'Content-Disposition: form-data; name="file"; filename="test.bmp"',
        'Content-Type: image/bmp',
        ''
    ]
    post_data.append(binary_data)
    post_data.append('-----------------------------984943658114410893--')
    
    post_body = '\n'.join(post_data)

    response = http.request('http://test_domain:8001/bags/foo/tiddlers',
        method='POST', 
        headers={'Content-type': 'multipart/form-data; '
            'boundary=---------------------------984943658114410893',
            'Content-Length': '301'
        },
        body=post_body)[0]
    assert response.status == 204
    
    tiddler = Tiddler('RGBSquare.bmp', 'foo')
    try:
        tiddler = store.get(tiddler)
    except NoTiddlerError:
        raise AssertionError('tiddler not put into store')
    
    assert tiddler.title == 'RGBSquare.bmp'
    assert tiddler.text == binary_data
    assert len(tiddler.tags) == 3
    for tag in ['image', 'bitmap', 'test data']:
        assert tag in tiddler.tags