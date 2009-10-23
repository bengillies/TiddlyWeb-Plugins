"""
TiddlyWebPages

by Ben Gillies
"""
from shorten import shorten
from wikifier import wikifier

TW_PAGES_FILTERS=[
    ('wikified', wikifier),
    ('shorten', shorten)
    ]