# -*- coding: utf-8 -*-

"""
    G2 Add-on Package
    Copyright (C) 2016-2019 J0rdyZ65

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

from __future__ import unicode_literals

import re
import urllib
import urlparse

from g2.libraries import cache
from g2.libraries import client
from g2.providers.api import ProviderBase
from g2.resolvers import ResolvedURL, ResolverError
from g2.platforms import log


class Provider(ProviderBase):
    """Raiplay provider"""

    raiplay_id = 'raiplay'

    info = {
        'content': ['movie', 'episode'],
        'language': ['it'],
        'sources': [raiplay_id],
    }

    # (fixme) Retrieve dlbase_url from https://www.raiplay.it/mobile/prod/config/RaiPlay_Config.json / "baseUrl"
    dlbase_url = 'https://raidl.rai.it/'
    # (fixme) Retrieve program_list_url from https://www.raiplay.it/mobile/prod/config/RaiPlay_Config.json / "AzTvShow"
    program_list_url = 'https://www.rai.it/dl/RaiTV/RaiPlayMobile/Prod/Config/programmiAZ-elenco.json'
    api_play = 'https://www.raiplay.it/atomatic/raiplay-su-service/api/profiles/play'

    def search(self, content, language, meta):
        if content == 'movie':
            title = meta['title']
            tipology = 'film'
        elif content == 'episode':
            title = meta['tvshowtitle']
            tipology = ('serie tv', 'fiction')
        else:
            raise NotImplementedError

        def _get_raiplay_videos():
            return client.get(self.program_list_url).json()
        try:
            videos = cache.get(_get_raiplay_videos, cacheopt_expire=24*60)
            items = [{'url': i.get('PathID'),
                      'title': i.get('name'),
                      'year': int(i.get('PLRanno', '0')),
                      'info': '/'.join(i.get('channel', [])),
                      'season': meta.get('season'),
                      'episode': meta.get('episode')}
                     for az in videos.itervalues() for i in az
                     if i.get('tipology').lower() in tipology and i.get('PathID')
                     and client.title_fuzzy_equal(title, i.get('name'))]
            return items
        except Exception as ex:
            log.debug('{m}.{f}: %s', repr(ex), trace=True)
            return []

    def sources(self, content, language, match):
        srcs = []
        if content == 'movie':
            try:
                url = re.search(r'(/programmi/[^/]+)/', match['url']).group(1)
                video = client.post(self.api_play, data='{"url": "%s.json"}' % url,
                                    headers={'Content-type': 'application/json'}, ).json()
                srcs.append({
                    'url': video['nextEpisode']['video_url'],
                    'host': self.raiplay_id,
                })
            except Exception:
                pass
        elif content == 'episode':
            with client.Session() as session:
                url = re.search(r'(/programmi/.+)', match['url']).group(1)
                for block in session.get(urlparse.urljoin(self.dlbase_url, url)).json()['Blocks']:
                    if 'episodi' not in block.get('Name', '').lower():
                        continue
                    for blockset in block['Sets']:
                        if 'stagione' not in blockset.get('Name', '').lower():
                            continue
                        url = re.search(r'(/programmi/.+)', blockset['url']).group(1)
                        for episode in session.get(urlparse.urljoin(self.dlbase_url, url)).json()['items']:
                            if episode.get('stagione') and match['season'] and episode['stagione'] != match['season']:
                                continue
                            if episode.get('episodio') and match['episode'] and episode['episodio'] != match['episode']:
                                continue
                            video = session.get(urlparse.urljoin(self.dlbase_url, episode['pathID'])).json()
                            srcs.append({
                                'url': video['video']['contentUrl'],
                                'host': self.raiplay_id
                            })

        return srcs

    def resolve(self, url):
        log.debug('{m}.{f}: URL: %s', url)

        if url.startswith('extplayer://' + self.raiplay_id):
            return ResolvedURL(url).enrich(meta={'type': self.raiplay_id}, size=-1)

        log.debug('{m}.{f}: Content URL: %s', url)

        if (url.startswith('http://mediapolis.rai.it/relinker/relinkerServlet.htm') or
                url.startswith('http://mediapolisvod.rai.it/relinker/relinkerServlet.htm') or
                url.startswith('http://mediapolisevent.rai.it/relinker/relinkerServlet.htm')):
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
            query = urlparse.parse_qs(query)
            query['output'] = '20' # output=20 url in body
            query = urllib.urlencode(query, True)
            url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))
            url = client.get(url).text.strip()

            # Heuristic logic to identify internal errors
            if 'error' in url.lower():
                return ResolverError('URL cannot be resolved')

            # Workaround to normalize URL if the relinker doesn't
            url = urllib.quote(url, safe="%/:=&?~#+!$,;'@()*[]")

        log.debug('{m}.{f}: Media URL: %s', url)

        return ResolvedURL(url)
