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


def route():

    if content == 'video':

        navigator.Indexer().root()

    elif content == 'audio':

        from resources.lib.indexers import music
        music.Indexer().gm_music()

    elif content == 'executable':

        from resources.lib.indexers import settings
        settings.Indexer().menu()

    elif action is None:

        navigator.Indexer().root()

    elif action == 'root':

        run_builtin(content_type='video')

    elif action == 'generic_index':

        navigator.Indexer().generic(query)

    elif action == 'live_tv':

        from resources.lib.indexers import live
        live.Indexer().live_tv()

    elif action == 'live_m3u':

        from resources.lib.indexers import live
        live.Indexer().live_m3u()

    elif action == 'movies':

        from resources.lib.indexers import vod
        vod.Indexer().movies()

    elif action == 'short_films':

        from resources.lib.indexers import vod
        vod.Indexer().short_films()

    elif action == 'shows':

        from resources.lib.indexers import vod
        vod.Indexer().shows()

    elif action == 'series':

        from resources.lib.indexers import vod
        vod.Indexer().series()

    elif action == 'kids':

        from resources.lib.indexers import kids
        kids.Indexer().kids()

    elif action == 'kids_live':

        from resources.lib.indexers import live
        live.Indexer().modular('30032')

    elif action == 'cartoon_series':

        from resources.lib.indexers import vod
        vod.Indexer().cartoons_series()

    elif action == 'listing':

        from resources.lib.indexers import vod
        vod.Indexer().listing(url)

    elif action == 'episodes':

        from resources.lib.indexers import vod
        vod.Indexer().episodes(url)

    elif action == 'gm_sports':

        from resources.lib.indexers import vod
        vod.Indexer().gm_sports()

    elif action == 'events':

        from resources.lib.indexers import vod
        vod.Indexer().events(url)

    elif action == 'theater':

        from resources.lib.indexers import vod
        vod.Indexer().theater()

    elif action == 'music':

        from resources.lib.indexers import music
        music.Indexer().menu()

    elif action == 'music_live':

        from resources.lib.indexers import live
        live.Indexer().modular('30125')

    elif action == 'gm_music':

        from resources.lib.indexers import music
        music.Indexer().gm_music()

    elif action == 'artist_index':

        from resources.lib.indexers import music
        music.Indexer().artist_index(url)

    elif action == 'album_index':

        from resources.lib.indexers import music
        music.Indexer().album_index(url)

    elif action == 'songs_index':

        from resources.lib.indexers import music
        music.Indexer().songs_index(url, name)

    elif action == 'techno_choices':

        from resources.lib.indexers import music
        music.Indexer().techno_choices(url)

    elif action == 'addBookmark':

        bm.add(url)

    elif action == 'deleteBookmark':

        bm.delete(url)

    elif action == 'pin':

        utils.pin(query)

    elif action == 'unpin':

        utils.unpin(query)

    elif action == 'bookmarks':

        from resources.lib.indexers import bookmarks
        bookmarks.Indexer().bookmarks()

    elif action == 'clear_bookmarks':

        # utils.clear_bookmarks()
        utils.purge_bookmarks()

    elif action == 'playback_history':

        navigator.Indexer().playback_history()

    elif action in ['search', 'add_to_search_history']:

        from resources.lib.indexers import search
        search.Indexer().search(action, query)

    elif action == 'delete_from_history':

        if query and query.startswith('{'):
            f = PLAYBACK_HISTORY
        else:
            f = SEARCH_HISTORY

        utils.process_file(f, query)

    elif action == 'change_search_term':

        utils.process_file(SEARCH_HISTORY, query, mode='change')

    elif action == 'search_index':

        from resources.lib.indexers import search
        search.Indexer().search_index()

    elif action == 'settings':

        from resources.lib.indexers import settings
        settings.Indexer().menu()

    elif action == 'tools_menu':

        utils.tools_menu()

    elif action == 'openSettings':

        kodi.execute('Addon.OpenSettings({})'.format(kodi.addonInfo('id')))

    elif action == 'other_addon_settings':

        helpers.other_addon_settings(query)

    elif action == 'play':

        from resources.lib.modules import player
        player.player(url, params)

    elif action == 'directory':

        from resources.lib.modules import player
        player.directory_picker(url, argv=argv)

    elif action == 'live_switcher':

        from resources.lib.indexers import live
        live.Indexer().switcher()

    elif action == 'vod_switcher':

        from resources.lib.indexers import vod
        vod.Indexer().vod_switcher(url)

    elif action == 'page_selector':

        utils.page_selector(query)

    elif action == 'setup_various_keymaps':

        utils.setup_various_keymaps(query)

    elif action == 'add_to_playlist':

        kodi.add_to_playlist()

    elif action == 'clear_playlist':

        kodi.clear_playlist()

    elif action == 'clear_search_history':

        utils.clear_search_history()

    elif action == 'clear_playback_history':

        utils.clear_playback_history()

    elif action == 'toggle_watched':

        kodi.toggle_watched()

    elif action == 'toggle_debug':

        kodi.toggle_debug()

    elif action == 'skin_debug':

        kodi.skin_debug()

    elif action == 'reload_skin':

        kodi.reload_skin()

    elif action == 'cache_clear':

        utils.cache_clear()

    elif action == 'purge_bookmarks':

        utils.purge_bookmarks()

    elif action == 'refresh':

        kodi.refresh()

    elif action == 'refresh_and_clear':

        utils.refresh_and_clear()

    elif action == 'reset_idx':

        utils.reset_idx(forceit=query == 'force')

    elif action == 'isa_enable':

        helpers.isa_enable()

    elif action == 'rtmp_enable':

        helpers.rtmp_enable()

    elif action == 'changelog':

        utils.changelog()

    elif action == 'info':

        from resources.lib.indexers import settings
        settings.Indexer().info()

    elif action == 'actions':

        from resources.lib.indexers import settings
        settings.Indexer().actions()

    elif action == 'input_stream_addons':

        from resources.lib.indexers import settings
        settings.Indexer().input_stream_addons()

    elif action == 'call_info':

        utils.call_info()

    elif action == 'open_link':

        kodi.open_web_browser(url)

    elif action == 'force':

        kodi.update_repositories()

    elif action == 'dmca':

        utils.dmca()

    elif action == 'pp':

        utils.pp()

    elif action == 'system_info':

        kodi.system_info()

    elif action == 'lang_choice':

        helpers.lang_choice()

    elif action == 'quit':

        kodi.quit_kodi()

    elif action == 'global_settings':

        kodi.global_settings()

    elif action == 'activate_other_addon':

        utils.activate_other_addon(url, query=query)

    elif action == 'welcome':

        utils.welcome()

    elif action == 'kodi_log_upload':

        helpers.log_upload()

if __name__ == '__main__':
    utils.checkpoint()
    route()
