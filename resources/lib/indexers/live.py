# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

import re
import json
from urllib.parse import urlencode
from datetime import datetime
from tulip import directory, kodi
from netclient import Net
from useragents import get_ua
from tulip.utils import py3_dec
from ..modules.utils import thgiliwt, pinned_from_file
from ..modules.themes import iconname
from ..modules.constants import (
    LIVE_GROUPS, M3U_GROUPS, cache_method, cache_duration, M3U_LINK, PINNED, ALIVEGR,
    ELAREPO_LIVE, ELAREPO_M3U, GITHUB_LIVE, GITHUB_M3U
)


def channel_key(title):

    """
    Normalised channel title, used only to spot the same channel in both lists.

    Deliberately blunt: case, spacing, punctuation and a trailing HD are all noise when the two
    lists are maintained by different people, so 'ERT1 HD' and 'ERT 1' collapse together. Going
    finer than this risks folding two genuinely different regional channels into one, which is
    worse than showing a duplicate.
    """

    key = ''.join(c for c in title.lower() if c.isalnum())

    return key[:-2] if key.endswith('hd') else key


def is_playlist(result):

    if '#EXTM3U' not in result:
        raise ValueError('not a playlist')


class Indexer:

    @staticmethod
    def switcher():

        groups = list(LIVE_GROUPS.values())
        translated = [kodi.i18n(i) for i in groups]
        choice = kodi.selectDialog(heading=kodi.i18n(30049), list=[kodi.i18n(30048)] + translated + [kodi.i18n(30282)])

        if choice != -1:
            kodi.setSetting('live_group', str(choice))
            kodi.idle()
            kodi.sleep(100)
            if str(choice) != kodi.setting('live_group'):
                kodi.refresh()
            else:
                kodi.execute('Dialog.Close(all)')

    @staticmethod
    def fetch_chain(urls, validate, headers=None):

        """
        Return the body of the first url that both answers and passes validate().

        Every tier is validated rather than merely fetched, because a host that answers 200 with
        a holding page would otherwise be served as though it were the channel list. Order is:
        the copy that ships in this repository, then the elarepo.org website copy, then the
        original upstream. If no tier survives, the last exception propagates, exactly as the
        unguarded final fallback used to, so a total outage is never cached as an empty list.
        """

        last = len(urls) - 1

        for index, url in enumerate(urls):

            try:
                if headers:
                    result = Net().http_GET(url, headers=headers).content
                else:
                    result = Net().http_GET(url).content
                validate(result)
                return result
            except Exception:
                if index == last:
                    raise

    def merged_with_m3u(self, live_list):

        """
        Fold the M3U playlist into the JSON channel list.

        The playlist was only reachable through the live_m3u action, which no menu links to, so
        its channels have been invisible. Merging here rather than in live_tv() means every
        consumer - live_tv(), modular(), search - sees one list.

        Best effort by design: the JSON list is the real one, so a playlist that is unreachable
        or malformed must not take Live TV down with it. Channels already in the JSON list are
        skipped and the JSON entry wins, since it carries the info, website, headers and DRM
        fields that the playlist format cannot express.
        """

        try:
            m3u_list = self.cached_live_m3u()
        except Exception:
            return live_list

        seen = {channel_key(item['title']) for item in live_list}
        year = datetime.now().year

        for item in m3u_list:

            key = channel_key(item['title'])

            if not key or key in seen:
                continue

            seen.add(key)
            group = LIVE_GROUPS.get(M3U_GROUPS.get(item['group']), LIVE_GROUPS['Web TV'])

            live_list.append(
                {
                    'title': item['title'], 'image': item['image'], 'group': str(group),
                    'genre': kodi.i18n(group), 'plot': '', 'website': 'None',
                    'year': year, 'url': item['url']
                }
            )

        return live_list

    @cache_method(cache_duration(480))
    def live(self):

        if kodi.setting('debug') == 'false':

            result = self.fetch_chain(
                [GITHUB_LIVE, ELAREPO_LIVE, py3_dec(thgiliwt('=' + ALIVEGR))], json.loads
            )

        else:

            if kodi.setting('local_remote') == '0':
                local = kodi.setting('live_local')
                with open(local, encoding='utf-8') as _json:
                    result = _json.read()
            elif kodi.setting('local_remote') == '1':
                result = Net().http_GET(kodi.setting('live_remote')).content
            else:
                result = Net().http_GET(thgiliwt('=' + ALIVEGR)).content

        try:
            channels = json.loads(result)
        except json.decoder.JSONDecodeError:
            channels = json.loads(result.replace('\'', '"'))
        # channels = [i for i in channel_list['channels'] if i['enable']]
        updated = channels['updated']
        live_list = []

        year = datetime.now().year

        lang_split = kodi.setting('lang_split')
        sys_lang = kodi.infoLabel('System.Language')

        for channel in channels['channels']:

            title = channel['name']
            image = channel['logo']
            group = channel['group']
            # .get(): one channel with an unknown group name must not take the
            # whole Live TV section down. Unknowns land in Web TV.
            group = LIVE_GROUPS.get(group, LIVE_GROUPS['Web TV'])
            url = channel['url']
            website = channel['website']
            info = channel['info']
            headers = channel.get('headers')
            if headers == 'random':
                headers = {'User-Agent': get_ua(), 'Referer': website}
            drm = channel.get('drm')
            if drm:
                if not isinstance(headers, dict):
                    headers = {}
                headers.update({'DRM': json.dumps(drm)})

            if len(info) == 5 and info[:5].isdigit():
                info = kodi.i18n(int(info))

            if ' - ' in info:
                if lang_split == '1' or (lang_split == '0' and 'English' in sys_lang):
                    info = info.partition(' - ')[0]
                elif lang_split == '2' or (lang_split == '0' and 'Greek' in sys_lang):
                    info = info.partition(' - ')[2]

            data = {
                'title': title, 'image': image, 'group': str(group),
                'genre': kodi.i18n(group), 'plot': info, 'website': website, 'year': year,
                'url': '|'.join([url[0], urlencode(headers)]) if headers else url[0]
            }

            live_list.append(data)

        return self.merged_with_m3u(live_list), updated

    def live_tv(self, query=None):

        live_data, updated = self.live()

        live_group_str = kodi.setting('live_group')
        live_group = int(live_group_str) - 1
        switcher_mode = kodi.setting('live_switcher_mode')

        try:
            group = str(list(LIVE_GROUPS.values())[live_group])
        except IndexError:
            group = None

        if live_group_str not in ('0', '10') and query is None:

            live_data = [item for item in live_data if item['group'] == group]

        elif live_group_str == '10' and query is None:

            pinned = set(pinned_from_file(PINNED))
            live_data = [item for item in live_data if item['title'] in pinned]

        for item in live_data:

            item.update({'action': 'play', 'isPlayable': 'True', 'duration': None})

            if live_group_str == '10':
                pin_cm = {'title': 30337, 'query': {'action': 'unpin', 'query': item['title']}}
            else:
                pin_cm = {'title': 30336, 'query': {'action': 'pin', 'query': item['title']}}

            menu = [pin_cm]

            group_changer = {'title': 30034, 'query': {'action': 'live_switcher'}}

            if switcher_mode == '1':
                menu.insert(1, group_changer)

            if item['website'] != 'None':
                web_cm = {'title': 30316, 'query': {'action': 'open_link', 'url': item['website']}}
                menu.insert(2, web_cm)

            item.update({'cm': menu})

        if switcher_mode == '0':

            if live_group_str == '0':
                label = kodi.i18n(30048)
            elif live_group_str == '10':
                label = kodi.i18n(30282)
            else:
                label = kodi.i18n(int(group))

            switch = {
                'title': label,
                'image': iconname('switcher'),
                'action': 'live_switcher',
                'plot': kodi.i18n(30034) + '[CR]' + kodi.i18n(30035) + updated,
                'isFolder': 'False', 'isPlayable': 'False'
            }

            live_data.insert(0, switch)

        if query:

            return [i for i in live_data if query in i['title'].lower()]

        kodi.setsortmethod()
        kodi.setsortmethod('production_code')
        kodi.setsortmethod('title')
        kodi.setsortmethod('genre', mask='%C')

        directory.builder(live_data, content='videos', add_all_at_once=True)

    @cache_method(cache_duration(480))
    def cached_live_m3u(self):

        headers = {'User-Agent': 'AliveGR, version: ' + kodi.version()}

        result = self.fetch_chain([GITHUB_M3U, ELAREPO_M3U, M3U_LINK], is_playlist, headers=headers)

        items = re.findall(r'#EXTINF:.+?\n.+?$', result, re.M)

        m3u_list = []

        for item in items:

            title = re.search(r',(.+)', item).group(1)
            try:
                # Non-greedy: a playlist that puts another attribute after
                # tvg-logo would otherwise capture through to the last quote.
                image = re.search(r'tvg-logo="(.+?)"', item).group(1)
            except AttributeError:
                image = kodi.addonInfo('icon')
            try:
                group = re.search(r'group-title="(.+?)"', item).group(1)
            except AttributeError:
                group = ''
            url = re.search(r'\n(.+)', item).group(1)

            data = {'title': title, 'image': image, 'group': group, 'url': url}

            m3u_list.append(data)

        return m3u_list

    def live_m3u(self):

        m3u_list = self.cached_live_m3u()

        for i in m3u_list:
            i.update({'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'})

        directory.builder(m3u_list, content='videos', as_playlist=kodi.setting('live_tv_mode') == '1')

    def modular(self, group):

        if group == '30125':
            fanart = 'https://i.ytimg.com/vi/vtjL9IeowUs/maxresdefault.jpg'
        elif group == '30032':
            fanart = 'https://cdn.iview.abc.net.au/thumbs/i/ls/LS1604H001S005786f5937ded19.22034349_1280.jpg'
        else:
            fanart = kodi.addonInfo('fanart')

        channel_list, _ = self.live()
        modular_list = [item for item in channel_list if item['group'] == group]

        year = datetime.now().year

        for item in modular_list:
            pin_cm = {'title': 30336, 'query': {'action': 'pin'}}
            item.update(
                {'action': 'play', 'isFolder': 'False', 'isPlayable': 'True',
                 'cm': [pin_cm], 'year': year, 'duration': None, 'fanart': fanart
                 }
            )

        modular_list.sort(key=lambda k: k['title'].lower())

        directory.builder(modular_list, content='videos')
