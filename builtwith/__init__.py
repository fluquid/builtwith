#!/usr/bin/env python
from __future__ import print_function

import sys
import os
import regex as re
import json
from six.moves.urllib.request import urlopen, Request
# from lxml import etree

re._MAXCACHE = 100000

# FIXME: use etree when available?
RE_META = re.compile(r'<meta[^>]*?(name|http-equiv)=[\'"]([^>]*?)[\'"][^>]*?' +
                     r'content=[\'"]([^>]*?)[\'"][^>]*?>',
                     flags=re.I | re.M)
RE_SCRIPTS = re.compile(r'<script[^>]+src=(?:"|\')([^"\']+)',
                        flags=re.I | re.M)
RE_LINKS = re.compile(r'<link[^>]+href=([^>]+)', flags=re.I | re.M)


def _output(dct):
    return json.dumps(dct, sort_keys=True)


def builtwith(url, headers=None, html=None, user_agent='builtwith'):
    """Detect the technology used to build a website

    FIXME: test data (maybe compare against node wappalyzer-cli)?
    """
    techs = {}

    # check URL
    for app_name, app_spec in data['apps'].items():
        if 'url' in app_spec:
            if contains(url, app_spec['url']):
                add_app(techs, app_name, app_spec)

    # download content
    if None in (headers, html):
        try:
            request = Request(url, None, {'User-Agent': user_agent})
            if html:
                # already have HTML so just need to make HEAD request for headers
                request.get_method = lambda : 'HEAD'
            response = urlopen(request)
            if headers is None:
                headers = response.headers
            if html is None:
                html = response.read().decode('utf-8')
        except Exception as e:
            print('Error:', e)
            request = None

    # check headers
    if headers:
        for app_name, app_spec in data['apps'].items():
            if 'headers' in app_spec:
                if contains_dict(headers, app_spec['headers']):
                    add_app(techs, app_name, app_spec)

    # check html
    if html:
        # node version only looks in script tag itself
        script_tags = RE_SCRIPTS.findall(html) + RE_LINKS.findall(html)

        for app_name, app_spec in data['apps'].items():
            for s_tag in script_tags:
                snippets = app_spec.get('script', [])
                if not isinstance(snippets, list):
                    snippets = [snippets]
                for snippet in snippets:
                    if contains(s_tag, snippet):
                        add_app(techs, app_name, app_spec)
                        break

            snippets = app_spec.get('html', [])
            if not isinstance(snippets, list):
                snippets = [snippets]
            for snippet in snippets:
                if contains(html, snippet):
                    add_app(techs, app_name, app_spec)
                    break

        # check meta
        # XXX add proper meta data parsing
        metas = dict(RE_META.findall(html))
        for app_name, app_spec in data['apps'].items():
            for name, content in app_spec.get('meta', {}).items():
                if name in metas:
                    if contains(metas[name], content):
                        add_app(techs, app_name, app_spec)
                        break

    return techs
parse = builtwith



def add_app(techs, app_name, app_spec):
    """Add this app to technology
    """
    for category in get_categories(app_spec):
        category = category.get('name')
        if category not in techs:
            techs[category] = []
        if app_name not in techs[category]:
            techs[category].append(app_name)
            implies = app_spec.get('implies', [])
            if not isinstance(implies, list):
                implies = [implies]
            implies = [im.split('\\;')[0] for im in implies]
            for app_name in implies:
                add_app(techs, app_name, data['apps'][app_name])


def get_categories(app_spec):
    """Return category names for this app_spec
    """
    return [data['categories'][str(c_id)] for c_id in app_spec['cats']]


def contains(v, regex):
    """Removes meta data from regex then checks for a regex match
    """
    return re.search(regex.split('\\;')[0], v, flags=re.IGNORECASE)


def contains_dict(d1, d2):
    """Takes 2 dictionaries

    Returns True if d1 contains all items in d2"""
    for k2, v2 in d2.items():
        v1 = d1.get(k2)
        if v1:
            if not contains(v1, v2):
                return False
        else:
            return False
    return True


def load_apps():
    """Load apps from Wappalyzer JSON (https://github.com/ElbertF/Wappalyzer)

    FIXME: add support to download update
    https://raw.githubusercontent.com/AliasIO/Wappalyzer/master/src/apps.json
    FIXME: pre-split version suffix from all regex
    """
    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'data', 'apps.json')
    return json.load(open(filename))


data = load_apps()


if __name__ == '__main__':
    urls = sys.argv[1:]
    if urls:
        for url in urls:
            results = builtwith(url)
            for result in sorted(results.items()):
                print('%s: %s' % result)
    else:
        print('Usage: %s url1 [url2 url3 ...]' % sys.argv[0])
