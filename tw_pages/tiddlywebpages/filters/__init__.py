"""
TiddlyWebPages

by Ben Gillies
"""
from shorten import shorten
from wikifier import wikifier

JINJA_FILTERS=[
    ('wikified', wikifier),
    ('shorten', shorten)
    ]