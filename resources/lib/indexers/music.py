# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

import json, re
from xbmcaddon import Addon
from tulip import kodi, directory
from itertags import iwrapper
from netclient import Net
from urllib.parse import urljoin
from ..modules.themes import iconname
from ..modules.source_makers import gm_source_maker
from ..modules.constants import cache_method, cache_duration, GM_MUSIC
from ..modules.utils import yt_playlist
from . import vod


# noinspection PyUnboundLocalVariable
class Indexer:

    def __init__(self):

        self.list = []
        if Addon().getSetting('audio_only') == 'true' and kodi.condVisibility('Window.IsVisible(music)'):
            self.content = 'songs'
            self.infotype = 'music'
        else:
            self.content = 'musicvideos'
            self.infotype = 'video'

    def menu(self):

        self.list = [
            {
                'title': kodi.i18n(30170),
                'action': 'music_live',
                'image': iconname('monitor'),
                'fanart': 'https://i.ytimg.com/vi/vtjL9IeowUs/maxresdefault.jpg',
                'isFolder': 'True'
            }
            ,
            {
                'title': kodi.i18n(30124),
                'action': 'gm_music',
                'image': iconname('music'),
                'fanart': 'https://cdn.allwallpaper.in/wallpapers/1280x720/1895/music-hd-1280x720-wallpaper.jpg',
                'isFolder': 'True'
            }
        ]

        if kodi.condVisibility('Window.IsVisible(music)'):
            del self.list[0]

        directory.builder(self.list)

    def gm_music(self):

        html = vod.gm_root(GM_MUSIC)

        options = re.compile(r'(<option  value=.+?</option>)', re.U).findall(html)

        for option in options:

            obj = next(iwrapper(option, 'option'))
            title = obj.text
            link = urljoin(vod.GM_BASE, obj.attributes['value'])

            data = {
                'title': title, 'url': link, 'image': iconname('music'), 'action': 'artist_index',
                'isFolder': 'True'
            }

            self.list.append(data)

        directory.builder(self.list)

    @cache_method(cache_duration(2880))
    def music_list(self, url):

        html = Net().http_GET(url).content

        if isinstance(html, bytes):
            html = html.decode('utf-8')

        if 'albumlist' in html:
            artist = [next(iwrapper(html, 'h4')).text.partition(' <a')[0]]
        else:
            artist = None

        if self.infotype == 'music' and artist is not None:
            # Kodi wants artist as a list for musicvideos, a plain string for music
            artist = ''.join(artist)

        if 'songlist' in html:
            songlist = next(iwrapper(html, 'div', attrs={'class': 'songlist'})).text
            items = iwrapper(songlist, 'li')
        elif 'albumlist' in html:
            albumlist = next(iwrapper(html, 'div', attrs={'class': 'albumlist'})).text
            items = iwrapper(albumlist, 'li')
        else:
            artistlist = next(iwrapper(html, 'div', attrs={'class': 'artistlist'})).text
            items = iwrapper(artistlist, 'li')

        if 'icon/music' in html:
            icon = list(iwrapper(html, 'img', attrs={'class': 'img-responsive'}, ret='src'))[-1]
            icon = urljoin(vod.GM_BASE, icon)
        else:
            icon = iconname('music')

        gm_link = None

        for item in items:

            title = next(iwrapper(item.text, 'a')).text
            link = next(iwrapper(item.text, 'a', ret='href'))
            link = urljoin(vod.GM_BASE, link)

            if 'gapi.client.setApiKey' in html:
                if gm_link is None:
                    gm_link = gm_source_maker(url)['links'][0]
                link = gm_link

            data = {'title': title, 'url': link, 'image': icon}

            if artist:

                data.update({'artist': artist})

            self.list.append(data)

        return self.list

    def artist_index(self, url):

        self.list = self.music_list(url)

        for item in self.list:
            item.update({'action': 'album_index', 'isFolder': 'True'})
            bookmark = {k: v for k, v in item.items() if k != 'next'}
            bookmark['bookmark'] = item['url']
            bookmark_cm = {'title': 30080, 'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}
            item.update({'cm': [bookmark_cm]})

        directory.builder(self.list)

    def album_index(self, url):

        self.list = self.music_list(url)

        for item in self.list:

            try:
                year = int(item['title'].partition(' (')[2][:-1])
            except ValueError:
                year = None

            item.update(
                {
                    'action': 'songs_index', 'name': item['title'].partition(' (')[0], 'isFolder': 'True'
                }
            )

            if year:
                item.update({'year': year})

        directory.builder(self.list, content=self.content, infotype=self.infotype)

    def songs_index(self, url, album):

        self.list = self.music_list(url)

        for count, item in enumerate(self.list, start=1):

            item.update({'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'})
            add_to_playlist = {'title': 30226, 'query': {'action': 'add_to_playlist'}}
            clear_playlist = {'title': 30227, 'query': {'action': 'clear_playlist'}}
            item.update({'cm': [add_to_playlist, clear_playlist], 'album': album, 'tracknumber': count})

        directory.builder(self.list, content=self.content, infotype=self.infotype)

    def techno_choices(self, url):

        self.list = yt_playlist(url)

        if self.list is None:

            return

        for i in self.list:
            i.update(
                {
                    'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'
                }
            )

        directory.builder(self.list)
