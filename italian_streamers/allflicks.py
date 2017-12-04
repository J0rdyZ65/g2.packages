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


import re
import time
import urlparse
import datetime
from cookielib import Cookie

from g2.libraries import log
from g2.libraries import client
from g2.providers.api import ProviderBase
from g2.resolvers import ResolvedURL


class Provider(ProviderBase):
    """Allflicks provider"""

    netflix_id = 'netflix'

    info = {
        'content': ['movie', 'episode'],
        # NOTE: when adding languages, please add also the corresponding base url below
        #   Here language actually means country where 'en' is 'us'. We might to add
        #   other pseudo-language such as en-uk to actually identify the country.
        'language': ['en', 'it'],
        'sources': [netflix_id],
    }

    url_base = {
        'en': 'https://www.allflicks.net/',
        'it': 'https://it.allflicks.net/',
    }

    url_search = {
        'en': 'wp-content/themes/responsive/processing/processing_us.php',
        'it': 'wp-content/themes/responsive/processing/processing.php',
    }

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def search(self, content, language, meta):
        with self._session(language) as ses:
            search_term = meta['title'] if content == 'movie' else meta['tvshowtitle']
            self.headers['Referer'] = self.url_base[language]
            res = ses.post(self.url_base[language] + self.url_search[language], headers=self.headers,
                           data=self.payload(content, search_term, meta.get('year')))
            return [{
                'url': r.get('id') or 'browse',
                'title': r.get('title'),
                'year': r.get('year'),
                'info': 'Rating %s'%r.get('rating') if 'rating' in r else '',
            } for r in res.json()['data']]

    def sources(self, content, language, match):
        return [{
            'url': urlparse.urlunparse(('extplayer', self.netflix_id, match['url'], '', '', '')),
            'source': self.netflix_id,
        }]

    def resolve(self, url):
        return (None if not url.startswith('extplayer://' + self.netflix_id) else
                ResolvedURL(url).enrich(meta={'type': self.netflix_id}, size=-1))

    def _session(self, language):
        ses = client.Session(saved_cookies=True)

        for cookie in ses.cookies:
            if cookie.name == 'identifier' and cookie.domain in self.url_base[language]:
                return ses

        res = ses.get(self.url_base[language])
        if res.cookies:
            for cke, val in res.cookies.iteritems():
                log.debug('{m}.{f}: GET cookie: %s=%s', cke, val)

        # var date=new Date();date.setTime(date.getTime()+864e5);var expires="; expires="+date.toGMTString();
        #  document.cookie="identifier=76ce113abb15bef069c93a0b60467081"+expires+"; path=/; domain=.allflicks.net";
        try:
            identifier, path, domain = re.search(r'identifier=([0-9a-fA-F]+).*path=([^;]+).*domain=([^"]+)', res.content).groups()
            def makeCookie(name, value, path, domain, expire):
                return Cookie(
                    version=0, 
                    name=name, 
                    value=value,
                    port=None, 
                    port_specified=False,
                    domain=domain, 
                    domain_specified=True, 
                    domain_initial_dot=path.startswith('.'),
                    path=path,
                    path_specified=True,
                    secure=False,
                    expires=expire,
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest={}
                )
            identifier = makeCookie('identifier', identifier, path, domain, time.time() + 86400)
            ses.cookies.set_cookie(identifier)
            log.debug('{m}.{f}: captured identifier cookie: %s', identifier)
        except Exception as ex:
            log.notice('{m}.{f}: session identifier not found or properly formatted in the GET response (%s)', repr(ex))

        return ses

    @staticmethod
    def payload(content, search_term, search_year):
        this_year = datetime.date.today().year
        return {
            "draw": '1',
            "columns[0][data]": "box_art",
            "columns[0][name]": "",
            "columns[0][searchable]": "true",
            "columns[0][orderable]": "false",
            "columns[0][search][value]": "",
            "columns[0][search][regex]": "false",
            "columns[1][data]": "title",
            "columns[1][name]": "",
            "columns[1][searchable]": "true",
            "columns[1][orderable]": "true",
            "columns[1][search][value]": "",
            "columns[1][search][regex]": "false",
            "columns[2][data]": "year",
            "columns[2][name]": "",
            "columns[2][searchable]": "true",
            "columns[2][orderable]": "true",
            "columns[2][search][value]": "",
            "columns[2][search][regex]": "false",
            "columns[3][data]": "genre",
            "columns[3][name]": "",
            "columns[3][searchable]": "true",
            "columns[3][orderable]": "true",
            "columns[3][search][value]": "",
            "columns[3][search][regex]": "false",
            "columns[4][data]": "rating",
            "columns[4][name]": "",
            "columns[4][searchable]": "true",
            "columns[4][orderable]": "true",
            "columns[4][search][value]": "",
            "columns[4][search][regex]": "false",
            "columns[5][data]": "available",
            "columns[5][name]": "",
            "columns[5][searchable]": "true",
            "columns[5][orderable]": "true",
            "columns[5][search][value]": "",
            "columns[5][search][regex]": "false",
            "columns[6][data]": "director",
            "columns[6][name]": "",
            "columns[6][searchable]": "true",
            "columns[6][orderable]": "true",
            "columns[6][search][value]": "",
            "columns[6][search][regex]": "false",
            "columns[7][data]": "cast",
            "columns[7][name]": "",
            "columns[7][searchable]": "true",
            "columns[7][orderable]": "true",
            "columns[7][search][value]": "",
            "columns[7][search][regex]": "false",
            "order[0][column]": "5",
            "order[0][dir]": "desc",
            "start": "0",
            "length": "25",
            "search[value]": search_term,
            "search[regex]": "false",
            "movies": "true" if content == 'movie' else "false",
            "shows": "true" if content == 'episode' else "false",
            "documentaries":  "true" if content == 'doc' else "false",
            "min": '%d' % max(1900, search_year-1) if search_year else 1900,
            "max": '%d' % min(this_year, search_year+1) if search_year else this_year}
