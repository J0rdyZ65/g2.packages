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
import urlparse

from g2.libraries import client
from g2.providers.api import ProviderBase
from g2.resolvers import ResolvedURL


class Provider(ProviderBase):
    """Netflixlovers provider"""

    netflix_host = 'netflix'

    info = {
        'content': ['movie', 'episode'],
        'language': ['it'],
        'sources': [netflix_host],
    }

    url_base = 'https://www.netflixlovers.it'
    url_search = '/catalogo-netflix-italia'

    headers = {}

    def search(self, content, language, meta):
        if content == 'movie':
            search_term = meta['title']
            search_type = 'Film'
        else:
            search_term = meta['tvshowtitle']
            search_type = 'Series'
        # (fixme) netflixlovers also support: Docs

        url = urlparse.urljoin(self.url_base, self.url_search)
        self.headers['Referer'] = url

        with client.Session(saved_cookies=True) as ses:
            catalogue = ses.get(url).text
            reqtoken = client.parseDOM(catalogue, 'input', attrs={'name': '__RequestVerificationToken'}, ret='value')[0]
            items = ses.post(url,
                             data={
                                 '__RequestVerificationToken': reqtoken,
                                 'Audio': 'Any',
                                 'Genre': 'Any',
                                 'Rating': 'Any',
                                 'Reset': 'False',
                                 'Skip': '0',
                                 'Sub': 'Any',
                                 'Tag': 'Any',
                                 'Take': '10',
                                 'Title': search_term,
                                 'Type': search_type,
                                 # (fixme) year filtering:
                                 #     last - Anno in corso
                                 #     last3 - Ultimi 3 anni
                                 #     2010 - A partire dal 2010
                                 #     2000 - Gli anni 2000
                                 #     1990 - Gli anni '90
                                 #     1980 - Gli anni '80
                                 #     1970 - Gli anni '70
                                 #     before70 - Prima del 1970
                                 'Year': 'Any',
                             }, headers=self.headers).text
            items = client.parseDOM(items, 'div', attrs={'class': 'moviecard'})
            matches = []
            for match in items:
                try:
                    title = client.parseDOM(match, 'h2', attrs={'class': 'title'})[0]
                    # /catalogo-netflix-italia/70142827/limitless
                    netflix_id = re.search(r'/([0-9]+)/', client.parseDOM(title, 'a', ret='href')[0]).group(1)
                    matches.append({
                        'url': netflix_id or 'browse',
                        'title': client.parseDOM(title, 'a')[0],
                        # <div class="rating" title="Punteggio Netflix Lovers: 3.97">4,0</div>
                        'info': client.parseDOM(match, 'div', attrs={'class': 'rating'}, ret='title')[0],
                    })
                    matches[-1].update({k:meta[k] for k in ('season', 'episode') if k in meta})
                except Exception:
                    pass

        return matches

    def sources(self, content, language, match):
        source = {
            'url': urlparse.urlunparse(('extplayer', self.netflix_host, match['url'], '', '', '')),
            'host': self.netflix_host,
        }
        source.update({k:match[k] for k in ('season', 'episode') if k in match})
        return [source]

    def resolve(self, url):
        return (None if not url.startswith('extplayer://' + self.netflix_host) else
                ResolvedURL(url).enrich(meta={'type': self.netflix_host}, size=-1))
