# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

from sys import argv
from urllib.parse import parse_qsl

from resources.lib.modules import utils, helpers
from resources.lib.indexers import navigator
from resources.lib.modules.constants import SEARCH_HISTORY, PLAYBACK_HISTORY

from tulip.directory import run_builtin
from tulip import kodi, bookmarks as bm

params = dict(parse_qsl(argv[2][1:]))
content = params.get('content_type')
action = params.get('action')
url = params.get('url')
name = params.get('name')
query = params.get('query')


# Indexers are imported on demand: a listing must not pay for the import of
# every other section, and player pulls in resolveurl and the youtube plugin.

def _live():
    from resources.lib.indexers import live
    return live.Indexer()


def _vod():
    from resources.lib.indexers import vod
    return vod.Indexer()


def _music():
    from resources.lib.indexers import music
    return music.Indexer()


def _kids():
    from resources.lib.indexers import kids
    return kids.Indexer()


def _search():
    from resources.lib.indexers import search
    return search.Indexer()


def _settings():
    from resources.lib.indexers import settings
    return settings.Indexer()


def _bookmarks():
    from resources.lib.indexers import bookmarks
    return bookmarks.Indexer()


def _player():
    from resources.lib.modules import player
    return player


def _delete_from_history():
    f = PLAYBACK_HISTORY if query and query.startswith('{') else SEARCH_HISTORY
    utils.process_file(f, query)


ROUTES = {
    'actions': lambda: _settings().actions(),
    'activate_other_addon': lambda: utils.activate_other_addon(url, query=query),
    'addBookmark': lambda: bm.add(url),
    'add_to_playlist': lambda: kodi.add_to_playlist(),
    'add_to_search_history': lambda: _search().search(action, query),
    'album_index': lambda: _music().album_index(url),
    'artist_index': lambda: _music().artist_index(url),
    'bookmarks': lambda: _bookmarks().bookmarks(),
    'cache_clear': lambda: utils.cache_clear(),
    'call_info': lambda: utils.call_info(),
    'cartoon_series': lambda: _vod().cartoons_series(),
    'change_search_term': lambda: utils.process_file(SEARCH_HISTORY, query, mode='change'),
    'changelog': lambda: utils.changelog(),
    'clear_bookmarks': lambda: utils.purge_bookmarks(),
    'clear_playback_history': lambda: utils.clear_playback_history(),
    'clear_playlist': lambda: kodi.clear_playlist(),
    'clear_search_history': lambda: utils.clear_search_history(),
    'deleteBookmark': lambda: bm.delete(url),
    'directory': lambda: _player().directory_picker(url, argv=argv),
    'dmca': lambda: utils.dmca(),
    'episodes': lambda: _vod().episodes(url),
    'events': lambda: _vod().events(url),
    'force': lambda: kodi.update_repositories(),
    'generic_index': lambda: navigator.Indexer().generic(query),
    'global_settings': lambda: kodi.global_settings(),
    'gm_music': lambda: _music().gm_music(),
    'gm_sports': lambda: _vod().gm_sports(),
    'info': lambda: _settings().info(),
    'input_stream_addons': lambda: _settings().input_stream_addons(),
    'isa_enable': lambda: helpers.isa_enable(),
    'kids': lambda: _kids().kids(),
    'kids_live': lambda: _live().modular('30032'),
    'kodi_log_upload': lambda: helpers.log_upload(),
    'lang_choice': lambda: helpers.lang_choice(),
    'listing': lambda: _vod().listing(url),
    'live_m3u': lambda: _live().live_m3u(),
    'live_switcher': lambda: _live().switcher(),
    'live_tv': lambda: _live().live_tv(),
    'movies': lambda: _vod().movies(),
    'music': lambda: _music().menu(),
    'music_live': lambda: _live().modular('30125'),
    'openSettings': lambda: kodi.execute('Addon.OpenSettings({})'.format(kodi.addonInfo('id'))),
    'open_link': lambda: kodi.open_web_browser(url),
    'other_addon_settings': lambda: helpers.other_addon_settings(query),
    'page_selector': lambda: utils.page_selector(query),
    'pin': lambda: utils.pin(query),
    'play': lambda: _player().player(url, params),
    'playback_history': lambda: navigator.Indexer().playback_history(),
    'pp': lambda: utils.pp(),
    'purge_bookmarks': lambda: utils.purge_bookmarks(),
    'quit': lambda: kodi.quit_kodi(),
    'refresh': lambda: kodi.refresh(),
    'refresh_and_clear': lambda: utils.refresh_and_clear(),
    'reload_skin': lambda: kodi.reload_skin(),
    'reset_idx': lambda: utils.reset_idx(forceit=query == 'force'),
    'root': lambda: run_builtin(content_type='video'),
    'rtmp_enable': lambda: helpers.rtmp_enable(),
    'search': lambda: _search().search(action, query),
    'search_index': lambda: _search().search_index(),
    'series': lambda: _vod().series(),
    'settings': lambda: _settings().menu(),
    'setup_various_keymaps': lambda: utils.setup_various_keymaps(query),
    'short_films': lambda: _vod().short_films(),
    'shows': lambda: _vod().shows(),
    'skin_debug': lambda: kodi.skin_debug(),
    'songs_index': lambda: _music().songs_index(url, name),
    'system_info': lambda: kodi.system_info(),
    'techno_choices': lambda: _music().techno_choices(url),
    'theater': lambda: _vod().theater(),
    'toggle_debug': lambda: kodi.toggle_debug(),
    'toggle_watched': lambda: kodi.toggle_watched(),
    'tools_menu': lambda: utils.tools_menu(),
    'unpin': lambda: utils.unpin(query),
    'vod_switcher': lambda: _vod().vod_switcher(url),
    'welcome': lambda: utils.welcome(),
    'delete_from_history': lambda: _delete_from_history(),
}


def route():

    if content == 'video':
        navigator.Indexer().root()
    elif content == 'audio':
        _music().gm_music()
    elif content == 'executable':
        _settings().menu()
    elif action is None:
        navigator.Indexer().root()
    else:
        handler = ROUTES.get(action)
        if handler:
            handler()


if __name__ == '__main__':
    utils.checkpoint()
    route()
