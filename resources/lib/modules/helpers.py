# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

from tulip import kodi
from os import path


def lang_choice():

    selections = [kodi.i18n(30217), kodi.i18n(30218), kodi.i18n(30312), kodi.i18n(30327)]

    dialog = kodi.selectDialog(selections)

    if dialog == 0:
        kodi.execute('Addon.Default.Set(kodi.resource.language)')
    elif dialog == 1:
        languages = [kodi.i18n(30286), kodi.i18n(30299)]
        layouts = ['English QWERTY', 'Greek QWERTY']
        indices = kodi.dialog.multiselect(kodi.name(), languages)
        kodi.set_gui_setting('locale.keyboardlayouts', [layouts[i] for i in indices])
    elif dialog == 2:
        kodi.set_gui_setting('locale.charset', 'CP1253')
        kodi.set_gui_setting('subtitles.charset', 'CP1253')
    elif dialog == 3:
        kodi.execute('Dialog.Close(all)')
        kodi.execute('ActivateWindow(interfacesettings)')
    else:
        kodi.execute('Dialog.Close(all)')


def inputstream_enable(addon_id, installed_msg, prompt_msg, fail_msg):

    try:

        enabled = kodi.addon_details(addon_id).get('enabled')

    except Exception:

        enabled = False

    try:

        if enabled:

            kodi.infoDialog(kodi.i18n(installed_msg))
            return

        else:

            xbmc_path = kodi.join('special://xbmc', 'addons', addon_id)
            home_path = kodi.join('special://home', 'addons', addon_id)

            if path.exists(kodi.transPath(xbmc_path)) or path.exists(kodi.transPath(home_path)):

                yes = kodi.yesnoDialog(kodi.i18n(prompt_msg))

                if yes:

                    kodi.enable_addon(addon_id)
                    kodi.infoDialog(kodi.i18n(30402))

            else:

                try:

                    kodi.execute('InstallAddon({0})'.format(addon_id))

                except Exception:

                    kodi.okDialog(heading='AliveGR', line1=kodi.i18n(30323))

    except Exception:

        kodi.infoDialog(kodi.i18n(fail_msg))


def isa_enable():

    inputstream_enable('inputstream.adaptive', 30254, 30252, 30278)


def rtmp_enable():

    inputstream_enable('inputstream.rtmp', 30276, 30277, 30279)


def log_upload():

    exists = kodi.condVisibility('System.HasAddon(script.kodi.loguploader)')
    addon_path = kodi.transPath(kodi.join('special://', 'home', 'addons', 'script.kodi.loguploader'))

    if not exists:

        if path.exists(addon_path):
            kodi.enable_addon('script.kodi.loguploader')
        else:
            kodi.execute('InstallAddon(script.kodi.loguploader)')

        while not path.exists(addon_path):
            kodi.sleep(1000)

    kodi.execute('RunScript(script.kodi.loguploader)')


def other_addon_settings(query):

    try:

        if query == 'script.module.resolveurl':

            from resolveurl import display_settings
            display_settings()

        else:

            kodi.openSettings(addon_id=query)

    except Exception:

        pass
