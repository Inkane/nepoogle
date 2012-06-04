#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#***************************************************************************
#*   nepoogle - globals library.                                           *
#*                                                                         *
#*   Copyright (C) 2011-2012 Ignacio Serantes <kde@aynoa.net>              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU General Public License as published by  *
#*   the Free Software Foundation; either version 2 of the License, or     *
#*   (at your option) any later version.                                   *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU General Public License for more details.                          *
#*                                                                         *
#*   You should have received a copy of the GNU General Public License     *
#*   along with this program; if not, write to the                         *
#*   Free Software Foundation, Inc.,                                       *
#*   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.         *
#***************************************************************************

import gettext, os, sys

#BEGIN lglobals.py

PROGRAM_URL = sys.argv[0]
PROGRAM_NAME = os.path.basename(sys.argv[0])
PROGRAM_BASENAME = os.path.splitext(PROGRAM_NAME)[0]
PROGRAM_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
PROGRAM_VERSION_VERSION = 'v0.9.3git'
PROGRAM_VERSION_DATE = '2012-06-xx'
PROGRAM_AUTHOR_NAME = 'Ignacio Serantes'
PROGRAM_AUTHOR_EMAIL = 'kde@aynoa.net'
PROGRAM_HTML_POWERED = "<hr>--<br /><b>Powered by</b> <em>%(name)s</em> <b>%(version)s</b> released (%(date)s)" \
                        % {'name': PROGRAM_NAME, \
                            'version': PROGRAM_VERSION_VERSION, \
                            'date': PROGRAM_VERSION_DATE \
                            }

gettext.bindtextdomain(PROGRAM_NAME, '') #'/path/to/my/language/directory')
gettext.textdomain(PROGRAM_NAME)
_ = gettext.gettext
#gettext.translation(PROGRAM_NAME, languages=['es']).install()

DEFAULT_ENGINE = 1
DO_NOT_USE_NEPOMUK = True
INTERNAL_RESOURCE = (False or DO_NOT_USE_NEPOMUK)
INTERNAL_RESOURCE_IN_RESULTS_LIST = (False or DO_NOT_USE_NEPOMUK)
INTERNAL_RESOURCE_FORCED_IN_CONSOLE = (False or DO_NOT_USE_NEPOMUK)

#END lglobals.py
