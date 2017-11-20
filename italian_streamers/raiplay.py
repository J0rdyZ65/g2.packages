# -*- coding: utf-8 -*-

"""
    G2 Add-on Package
    Copyright (C) 2016-2017 J0rdyZ65

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import urllib
import urlparse

from unidecode import unidecode

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import client

from g2.providers import title_fuzzy_equal
from g2.providers.api import ProviderBase
from g2.resolvers import ResolvedURL, ResolverError


class Provider(ProviderBase):
    """Raiplay provider"""

    raiplay_id = 'raiplay'

    info = {
        'content': ['movie', 'episode'],
        'sources': [raiplay_id],
    }

    base_url = "http://www.rai.it"
    program_list_url = "/dl/RaiTV/RaiPlayMobile/Prod/Config/programmiAZ-elenco.json"

    def search(self, content, meta):
        if content == 'movie':
            title = unidecode(meta['title'])
            tipology = 'Film'
        elif content == 'episode':
            title = unidecode(meta['tvshowtitle'])
            tipology = 'Programmi Tv'
        year = meta.get('year')

        def _get_raiplay_videos():
            return client.get(self.base_url+self.program_list_url).json()
        try:
            videos = cache.get(_get_raiplay_videos, 24*60)
            items = [{'url': i.get('PathID'),
                      'title': i.get('name'),
                      'year': int(i.get('PLRanno', '0')),
                      'info': '/'.join(i.get('channel', []))}
                     for az in videos.itervalues() for i in az
                     if i.get('tipology') == tipology and i.get('PathID') and title_fuzzy_equal(i.get('name'), title)]
            if year:
                items = [i for i in items if not i['year'] or year-1 <= i['year'] <= year+1]
            return items
        except Exception as ex:
            log.debug('{m}.{f}: %s', repr(ex), trace=True)
            return []

    def sources(self, content, match):
        return [{
            'url': match['url'] if content == 'movie' else
                   urlparse.urlunparse(('extplayer', self.raiplay_id, match['url'], '', '', '')),
            'source': self.raiplay_id,
        }]

    def resolve(self, url):
        log.debug('{m}.{f}: URL: %s', url)

        if url.startswith('extplayer://' + self.raiplay_id):
            return ResolvedURL(url).enrich(meta={'type': self.raiplay_id}, size=-1)

        with client.Session() as session:
            video = session.get(url).json()
            if not video.get('pathFirstItem'):
                return ResolverError('Content not available')
            video = session.get(self.base_url+video['pathFirstItem']).json()
            if not video.get('video'):
                return ResolverError('Content not available')
            url = video['video'].get('contentUrl')
            if not url:
                return ResolverError('Content not available')

        if (url.startswith('http://mediapolis.rai.it/relinker/relinkerServlet.htm') or
                url.startswith('http://mediapolisvod.rai.it/relinker/relinkerServlet.htm') or
                url.startswith('http://mediapolisevent.rai.it/relinker/relinkerServlet.htm')):
            log.debug('{m}.{f}: Relinker URL: %s', url)
            # output=20 url in body
            # output=23 HTTP 302 redirect
            # output=25 url and other parameters in body, space separated
            # output=44 XML (not well formatted) in body
            # output=47 json in body
            # pl=native,flash,silverlight
            # A stream will be returned depending on the UA (and pl parameter?)
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
            query = urlparse.parse_qs(query)
            query['output'] = '20'
            query = urllib.urlencode(query, True)
            url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))
            url = client.get(url).content.strip()

            # Heuristic logic to identify internal errors
            if 'error' in url.lower():
                return ResolverError('URL cannot be resolved')

            # Workaround to normalize URL if the relinker doesn't
            url = urllib.quote(url, safe="%/:=&?~#+!$,;'@()*[]")

        log.debug('{m}.{f}: Resolved URL: %s', url)
        return ResolvedURL(url)
