# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

from tulip import kodi
from .constants import ART_ID


def iconname(name):

    base = ('alivegr', 'twilight', 'gemini')[int(kodi.setting('theme'))]

    return kodi.addonmedia(
        addonid=ART_ID, theme=base, path='{0}+{1}.png'.format(name, base)
    )
