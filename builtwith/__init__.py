from __future__ import print_function

import sys
import os
import re
import json
from six.moves.urllib.request import urlopen, Request


RE_META = re.compile('<meta[^>]*?name=[\'"]([^>]*?)[\'"][^>]*?content=[\'"]([^>]*?)[\'"][^>]*?>', re.IGNORECASE)


def builtwith(url, headers=None, html=None, user_agent='builtwith'):
    """Detect the technology used to build a website

    >>> builtwith('http://wordpress.com')
    {u'blogs': [u'PHP', u'WordPress'], u'font-scripts': [u'Google Font API'], u'web-servers': [u'Nginx'], u'javascript-frameworks': [u'Modernizr'], u'programming-languages': [u'PHP'], u'cms': [u'WordPress']}
    >>> builtwith('http://webscraping.com')
    {u'javascript-frameworks': [u'jQuery', u'Modernizr'], u'web-frameworks': [u'Twitter Bootstrap'], u'web-servers': [u'Nginx']}
    >>> builtwith('http://microsoft.com')
    {u'javascript-frameworks': [u'jQuery'], u'mobile-frameworks': [u'jQuery Mobile'], u'operating-systems': [u'Windows Server'], u'web-servers': [u'IIS']}
    >>> builtwith('http://jquery.com')
    {u'cdn': [u'CloudFlare'], u'web-servers': [u'Nginx'], u'javascript-frameworks': [u'jQuery', u'Modernizr'], u'programming-languages': [u'PHP'], u'cms': [u'WordPress'], u'blogs': [u'PHP', u'WordPress']}
    >>> builtwith('http://joomla.org')
    {u'font-scripts': [u'Google Font API'], u'miscellaneous': [u'Gravatar'], u'web-servers': [u'LiteSpeed'], u'javascript-frameworks': [u'jQuery'], u'programming-languages': [u'PHP'], u'web-frameworks': [u'Twitter Bootstrap'], u'cms': [u'Joomla'], u'video-players': [u'YouTube']}
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
                request.get_method = lambda: 'HEAD'
            response = urlopen(request)
            if headers is None:
                headers = response.headers
            if html is None:
                charset = response.info().get_content_charset() or 'utf-8'
                html = response.read().decode(charset)
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
        for app_name, app_spec in data['apps'].items():
            for key in 'html', 'script':
                snippets = app_spec.get(key, [])
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
        if category not in techs:
            techs[category] = []
        if app_name not in techs[category]:
            techs[category].append(app_name)
            implies = app_spec.get('implies', [])
            if not isinstance(implies, list):
                implies = [implies]
            for app_name in implies:
                add_app(techs, app_name, data['apps'][app_name])


def get_categories(app_spec):
    """Return category names for this app_spec
    """
    return [data['categories'][str(c_id)] for c_id in app_spec['cats']]


def contains(v, regex):
    """Removes meta data from regex then checks for a regex match
    """
    return regex.search(v)


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


def re_compile(regex):
    """
    compile regex from app.json.py in a uniform manner
    """
    return re.compile(regex.split('\\;')[0], flags=re.I)


def rexify(val):
    if isinstance(val, list):
        return '|'.join(r'(?:%s)' % (v.split('\\;')[0], ) for v in val)
    else:
        return val.split('\\;')[0]


def chain_rules(dct, selector):
    """ create combined regexes """
    items = dct.items()
    reverse = {('p_' + str(idx)):item[0] for idx, item in enumerate(items)}
    forward = {v:k for k, v in reverse.items()}
    rules = [r'(?P<%s>%s)' % (forward[k],
                              rexify(v[selector]))
             for k, v in items if selector in v]
    res = re.compile('|'.join(rules))
    return res, reverse


def load_apps(filename='apps.json.py'):
    """Load apps from Wappalyzer JSON (https://github.com/ElbertF/Wappalyzer)
    """
    # get the path of this filename relative to the current script
    # XXX add support to download update
    filename = os.path.join(os.getcwd(), os.path.dirname(__file__), filename)
    json_data = json.load(open(filename))

    # precompile regular expressions for repeated use
    # TODO: built per-type concatenated patterns
    apps = json_data['apps']
    rules = {
        'urls': chain_rules(apps, 'url'),
        'html': chain_rules(apps, 'html'),
        'script': chain_rules(apps, 'script')
    }
    for app_name, app in apps.items():
        for key in ['url', 'html', 'script']:
            if key in app:
                val = app[key]
                if isinstance(val, list):
                    app[key] = [re_compile(v) for v in val]
                else:
                    app[key] = re_compile(val)

        if 'meta' in app:
            app['meta'] = {k: re_compile(v)
                           for k, v in app['meta'].items()}

        if 'headers' in app:
            app['headers'] = {k: re_compile(v)
                              for k, v in app['headers'].items()}
    return json_data, rules

data, rules = load_apps()


if __name__ == '__main__':
    urls = sys.argv[1:]
    if urls:
        for url in urls:
            results = builtwith(url)
            for result in sorted(results.items()):
                print('%s: %s' % result)
    else:
        print('Usage: %s url1 [url2 url3 ...]' % sys.argv[0])