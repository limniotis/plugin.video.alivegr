# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

import json

from xbmcaddon import Addon
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from resolveurl import add_plugin_dirs, resolve as resolve_url
from resolveurl.hmf import HostedMediaFile
from resolveurl.resolver import ResolverError
# noinspection PyUnresolvedReferences
from youtube_plugin.youtube.youtube_exceptions import YouTubeException
from tulip import directory, kodi
from tulip.log import log
from netclient import Net
from urllib.parse import urljoin, parse_qsl, urlencode
from urllib.error import HTTPError
from tulip.utils import percent
from tulip.cleantitle import stripTags
from itertags import iwrapper

from ..indexers.vod import GM_MOVIES, GM_SHORTFILMS, GM_THEATER, GM_BASE, GF_BASE
from .source_makers import gm_source_maker, gf_source_maker
from ..resolvers import youtube
from .constants import (
    YT_URL, separator, PLUGINS_PATH, cache_function, cache_duration, PLAYBACK_HISTORY,
    GFM_GETTER, GFK_GETTER
)
from .utils import add_to_file


def conditionals(url):

    add_plugin_dirs(kodi.transPath(PLUGINS_PATH))

    if not url:
        kodi.close_all()
        return

    if 'youtu' in url or len(url) == 11:

        log('Resolving with youtube addon...')

        if url.startswith('plugin://'):
            return url

        if len(url) == 11:
            url = YT_URL + url

        try:
            return youtube.wrapper(url)
        except YouTubeException as exp:
            log('Youtube resolver failure, reason: ' + repr(exp))
            return

    elif HostedMediaFile(url).valid_url():

        try:
            stream = resolve_url(url)
            log('Resolving with Resolveurl...')
        except ResolverError:
            return None
        except HTTPError:
            return url

        return stream

    elif GM_BASE in url:

        gm_sources = gm_source_maker(url)

        if 'view.php?' in url or 'episode' in url:
            gf = None
        else:
            gf = gf_source_maker(GFM_GETTER, title=gm_sources['title'])

        if gf:
            links = gm_sources['links'] + gf['links']
        else:
            links = gm_sources['links']

        stream = stream_picker(links)

        return conditionals(stream)

    elif GF_BASE in url:

        if 'movie.php' in url:
            sources = gf_source_maker(GFM_GETTER, url=url)
        else:
            sources = gf_source_maker(GFK_GETTER, url=url)
        stream = stream_picker(sources['links'])

        return conditionals(stream)

    else:

        log('Passing direct link...')

        return url


def check_stream(stream_list, start_from=0, show_pd=False):

    if not stream_list:
        return

    for c, (h, stream) in enumerate(stream_list[start_from:]):

        if stream.endswith('blank.mp4'):
            return stream

        if show_pd:
            pd = kodi.progressDialog
            pd.create(kodi.name(), ''.join([kodi.i18n(30459), h.partition(': ')[2]]))

        try:
            resolved = conditionals(stream)
        except Exception:
            resolved = None

        if resolved is not None:
            if show_pd:
                pd.close()
            return resolved
        elif show_pd and pd.iscanceled():
            return
        elif c == len(stream_list[start_from:]) - 1 and not resolved:
            kodi.infoDialog(kodi.i18n(30411))
            if show_pd:
                pd.close()
        elif resolved is None:
            if show_pd:
                _percent = percent(c, len(stream_list[start_from:]))
                pd.update(_percent, ''.join([kodi.i18n(30459), h.partition(': ')[2]]))
            kodi.sleep(100)
            continue


def stream_picker(links):

    if len(links) == 1:

        stream = links[0][1]
        # kodi.infoDialog(links[0][0])

        return stream

    else:

        choice = kodi.selectDialog(heading=kodi.i18n(30064), list=[link[0] for link in links])

        if choice == -1:
            return
        elif Addon().getSetting('check_streams') == 'false':
            return links[choice][1]
        else:
            return check_stream(links, start_from=choice, show_pd=True)


def gf_directory(title):

    sources = gf_source_maker(GFM_GETTER, title=title)

    if not sources:
        sources = gf_source_maker(GFK_GETTER, title=title)

    items = []

    sep = separator()

    for h, l in sources['links']:

        label = title + sep + h

        data = {
            'label': label, 'title': sources['title'], 'url': l, 'image': sources['image'],
            'plot': sources['plot'], 'year': sources['year'], 'genre': [g for g in sources.get('genre', kodi.i18n(30089))],
            'name': sources['label']
        }

        items.append(data)

    return items


@cache_function(cache_duration(660))
def gm_directory(url, params):

    sources = gm_source_maker(url)

    links = sources['links']

    items = []

    try:
        description = sources['plot']
    except KeyError:
        description = params.get('plot')
        if not description:
            description = kodi.i18n(30085)

    try:
        genre = sources['genre']
    except KeyError:
        genre = kodi.i18n(30089)

    sep = separator()

    with ThreadPoolExecutor(max_workers=min(6, len(links)) or 1) as ex:
        htmls = list(ex.map(lambda hl: Net().http_GET(hl[1]).content, links))

    for (h, l), html in zip(links, htmls):

        button = iwrapper(html, 'a', attrs={'role': 'button'}, ret='href').__next__()
        image = iwrapper(html, 'img', attrs={'class': 'thumbnail img-responsive'}, ret='src').__next__()
        image = urljoin(GM_BASE, image)
        title = iwrapper(html, 'h3').__next__().text
        try:
            year = [y.text[-4:] for y in iwrapper(html, 'h4') if str(y.text[-4:]).isdigit()][0]
        except IndexError:
            year = [y.text[-2:] for y in iwrapper(html, 'h4') if str(y.text[-2:]).isdigit()][0]
            numeric_year = int(year)
            if numeric_year < 100:
                if numeric_year >= 40:
                    numeric_year += 1900
                else:
                    numeric_year += 2000
            year = str(numeric_year)
        try:
            episode = stripTags(deque(iwrapper(html, 'h4'), maxlen=1).pop().text)
            if episode[-4:].isdigit():
                raise IndexError
            episode = episode.partition(': ')[2].strip()
            label = title + ' - ' + episode + sep + h
            title = title + ' - ' + episode
        except IndexError:
            label = title + sep + h
        # plot = title + '[CR]' + kodi.i18n(30090) + ': ' + year + '[CR]' + description

        data = {
            'label': label, 'title': title, 'url': button, 'image': image, 'plot': description,
            'year': int(year), 'genre': genre, 'name': title
        }

        items.append(data)

    return items


def directory_picker(url, argv):

    params = dict(parse_qsl(argv[2][1:]))

    gf_merged = False

    if GF_BASE in url:
        items = gf_directory(params.get('title'))
    else:
        try:
            items = gm_directory(url, params) + gf_directory(params.get('title'))
            gf_merged = True
        except TypeError:
            items = gm_directory(url, params)

    if items is None:
        return

    query = None

    if Addon().getSetting('check_streams') == 'true':

        links = [] if GF_BASE in url else gm_source_maker(url)['links']

        if GF_BASE in url or gf_merged:
            gf_sources = gf_source_maker(GFM_GETTER, title=params.get('title')) or gf_source_maker(GFK_GETTER, title=params.get('title'))
            if gf_sources:
                links = links + gf_sources['links']

        query = json.dumps(links)

    for i in items:

        add_to_playlist = {'title': 30226, 'query': {'action': 'add_to_playlist'}}
        clear_playlist = {'title': 30227, 'query': {'action': 'clear_playlist'}}
        i.update({'cm': [add_to_playlist, clear_playlist], 'action': 'play', 'isFolder': 'False', 'isPlayable': 'True'})

        if query:
            i.update({'query': query})

    directory.builder(
        items, content='movies', argv=argv
    )


def dash_conditionals(stream):
    try:

        inputstream_adaptive = kodi.addon_details('inputstream.adaptive').get('enabled')

    except KeyError:

        inputstream_adaptive = False

    m3u8_dash = ('.hls' in stream or '.m3u8' in stream) and Addon().getSetting('m3u8_quality_picker') == '1'

    dash = ('.mpd' in stream or 'dash' in stream or '.ism' in stream or m3u8_dash) and inputstream_adaptive

    mimetype = None
    manifest_type = None

    if dash:

        if '.hls' in stream or '.m3u8' in stream:
            manifest_type = 'hls'
            mimetype = 'application/vnd.apple.mpegurl'
        elif '.ism' in stream:
            manifest_type = 'ism'
        else:
            manifest_type = 'mpd'

        log('Activating adaptive parameters for this url: ' + stream)

    return dash, mimetype, manifest_type


def player(url, params):

    if url is None:
        log('Nothing playable was found')
        return

    url = url.replace('&amp;', '&')

    directory_boolean = any(
        [
            GF_BASE in url, GM_MOVIES in url, GM_SHORTFILMS in url, GM_THEATER in url,
            ('episode' in url and GM_BASE in url)
        ]
    )

    if directory_boolean and Addon().getSetting('action_type') == '1':
        directory.run_builtin(action='directory', url=url, title=params.get('title'))
        return

    log('Attempting to play this url: ' + url)

    if params.get('query') and Addon().getSetting('check_streams') == 'true':
        sl = json.loads(params.get('query'))
        index = int(kodi.infoLabel('Container.CurrentItem')) - 1
        stream = check_stream(sl, start_from=index, show_pd=True)
    else:
        stream = conditionals(url)

    if not stream:

        log('Failed to resolve this url: {0}'.format(url))

        kodi.execute('Dialog.Close(all)')

        return

    elif Addon().getSetting('show_history') == 'true':
        params.update({'isFolder': 'False'})
        add_to_file(PLAYBACK_HISTORY, json.dumps(params))

    plot = params.get('plot')

    if not plot and 'greek-movies.com' in url:
        plot = gm_source_maker(url).get('plot')

    dash, mimetype, manifest_type = dash_conditionals(stream)

    if stream != url:

        log('Stream has been resolved: ' + stream)

    else:

        log('Attempting direct playback: ' + stream)

    licence_type = None
    licence_key = None

    # process headers if necessary:
    if '|' in stream:

        stream, sep, headers = stream.rpartition('|')

        headers = dict(parse_qsl(headers))

        if 'DRM' in headers:
            drm = headers.pop('DRM')
            licence_type = drm[0]
            licence_key = json.dumps(drm[1])

        log('Appending custom headers: ' + repr(headers))

        stream = sep.join([stream, urlencode(headers)])

    image = params.get('image')

    meta = {'title': params.get('name') or params.get('title')}

    if plot:
        meta.update({'plot': plot})

    try:

        directory.resolve(
            stream, meta=meta, icon=image, dash=dash, manifest_type=manifest_type, mimetype=mimetype,
            licence_type=licence_type, licence_key=licence_key
        )

    except:

        kodi.execute('Dialog.Close(all)')
        kodi.infoDialog(kodi.i18n(30112))
