# -*- coding: utf-8 -*-

"""
    G2 Add-on Package
    Copyright (C) 2016-2020 J0rdyZ65

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
from six.moves import urllib

from g2.libraries import client
from g2.providers.api import ProviderBase
from g2.resolvers.api import ResolvedURL


class Provider(ProviderBase):
    """Netflixlovers provider"""

    netflix_host = 'netflix'

    info = {
        'content': ['movie', 'episode'],
        'language': ['it'],
        'sources': [netflix_host],
    }

    search_url = 'https://www.netflixlovers.it/catalogo-netflix-italia'

    def search(self, content, language, meta):
        if content == 'movie':
            search_term = meta['title']
            search_type = 'Film'
        else:
            search_term = meta['tvshowtitle']
            search_type = 'Series'

        with client.Session(saved_cookies=True, headers={'Referer': self.search_url}) as ses:
            soup = ses.get(self.search_url).bs4()
            soup = ses.post(self.search_url, data={
                '__RequestVerificationToken': soup.select_one('input[name="__RequestVerificationToken"]')['value'],
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
            }).bs4()

            matches = []
            for div_mcard in soup.select('div.mcard'):
                try:
                    a_title = div_mcard.select_one('h2.title a')
                    matches.append({
                        # /catalogo-netflix-italia/70142827/limitless
                        'url': re.search(r'/([0-9]+)/', a_title['href']).group(1) or 'browse',
                        'title': a_title.get_text(),
                        # <div class="rating" title="Punteggio Netflix Lovers: 3.97">4,0</div>
                        'info': div_mcard.select_one('div.rating')['title'],
                    })
                    matches[-1].update({k: meta[k] for k in ('season', 'episode') if k in meta})
                except Exception:
                    pass

        return matches

    def sources(self, content, language, match):
        source = {
            'url': urllib.parse.urlunparse(('extplayer', self.netflix_host, match['url'], '', '', '')),
            'host': self.netflix_host,
        }
        source.update({k: match[k] for k in ('season', 'episode') if k in match})
        return [source]

    def resolve(self, url):
        if url.startswith('extplayer://' + self.netflix_host):
            return ResolvedURL(url)
        return None
