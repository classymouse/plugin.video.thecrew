# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file service.py
 * @package plugin.video.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''



# CM - 06/07/2021
# cm - 06/20/2023
# cm - testfile VS without mocking (just useless)
# pylint: disable=import-error
# pylint: disable=no-name-in-module
import os
import re
import traceback
import glob

from threading import Thread
from shutil import rmtree
from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import workers

from resources.lib.modules.crewruntime import c

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

QUARTERLY = 60 * 15
HALF_HOUR = 60 * 30
HOURLY = 60 * 60







def conversion():

    # cm - 10/19/2024 Removed dialogs as being obsolete and not needed
    conversionFile = os.path.join(control.dataPath, 'conversion.v')
    bookmarkFile = control.bookmarksFile
    curVersion = c.moduleversion
    version = c.pluginversion

    if not os.path.exists(conversionFile):
        f_path = 'special://home/addons/script.thecrew.metadata'
        rmtree(f_path, ignore_errors=True)

        if os.path.isfile(bookmarkFile):
            os.remove(bookmarkFile)
            c.log(f'removing {str(bookmarkFile)}')

        if not os.path.isfile(bookmarkFile):
            #write the conversion.v file
            with open(conversionFile, 'w', encoding="utf8") as fh:
                fh.write(curVersion)
            c.log(f'File written, Conversion successful, version = {curVersion}')



def readProviders(scraper_path_fill, msg1, catnr):
    addon_name = c.name
    addon_icon = xbmcaddon.Addon().getAddonInfo('icon')
    addon_path = xbmcvfs.translatePath('special://home/addons/plugin.video.thecrew')
    module_path = xbmcvfs.translatePath('special://home/addons/script.module.thecrew')


    xbmc.log(f"[ plugin.video.thecrew ] service - checking {msg1} providers started", 1)

    if c.has_silent_boot:
        c.log(f"Preparing {msg1} Providers")
    else:
        xbmcgui.Dialog().notification(addon_name, f"Preparing {msg1} Providers", addon_icon)

    settings_xml_path = os.path.join(addon_path, 'resources/settings.xml')
    scraper_path = os.path.join(
        module_path, f'lib/resources/lib/sources/{scraper_path_fill}'
    )
    try:
        xml = openfile(settings_xml_path)
    except Exception as e:
        failure = str(traceback.format_exc())
        c.log(f"The Crew Service - Exception: {e}\n {failure}")
        return

    new_settings = '\n'
    #for file in glob.glob("%s/*.py" % (scraper_path)):
    for file in glob.glob(f"{scraper_path}/*.py"):
        file = os.path.basename(file)
        if '__init__' not in file:
            file = file.replace('.py', '')
            new_settings += f'        <setting id="provider.{file.lower()}" type="bool" label="{file.upper()}" default="true" />\n'
        new_settings += '    '

    #pattern = ('<category label="{}">').format(str(catnr)) + '([\s\S]*?)<\/category>'
    pattern = f'<category label="{str(catnr)}">' + r'([\s\S]*?)<\/category>'
    found = re.findall(pattern, xml, flags=re.DOTALL)
    xml = xml.replace(found[0], new_settings)
    savefile(settings_xml_path, xml)
    if c.has_silent_boot:
        c.log(f"{msg1} Providers Updated")
    else:
        xbmcgui.Dialog().notification(addon_name, f"{msg1} Providers Updated", addon_icon)


def openfile(path_to_the_file):
    try:
        with open(path_to_the_file, 'r', encoding="utf8") as fh:
            contents = fh.read()
        return contents

    except Exception as e:
        failure = str(traceback.format_exc())
        c.log(f"Service Open File Exception - {path_to_the_file} \n {failure} \n {e}")
        return None


def savefile(path_to_the_file, content):
    try:
        with open(path_to_the_file, 'w', encoding="utf8") as fh:
            fh.write(content)
        fh.close()
    except Exception as e:
        failure = str(traceback.format_exc())
        c.log(f"Service Save File Exception - {path_to_the_file} \n {failure}")





def syncTraktLibrary():
    control.execute('RunPlugin(plugin://plugin.video.thecrew/?action=tvshowsToLibrarySilent&url=traktcollection')
    control.execute('RunPlugin(plugin://plugin.video.thecrew/?action=moviesToLibrarySilent&url=traktcollection')

def syncTrakt():
    #control.execute('RunPlugin(plugin://plugin.video.thecrew/?action=syncTrakt')
    trakt.syncTrakt()

def main():

    monitor = xbmc.Monitor()

    try:
        c.log_boot_option()
        hours = control.setting('schedTraktTime')
        _timeout = 3600 * int(hours)

        # cm -conversion check and fix from module v. 1.x to v. > 2.0.0
        c.initialize_all()
        conversion()
        c.log(f"[CM Debug @ 153 in service.py] before syncTrakt")
        syncTrakt()
        c.log(f"[CM Debug @ 155 in service.py] after syncTrakt")

        #monitor.waitForAbort(10)
        control.startupMaintenance()

        #cm - checking the scrapers
        fum_ver = xbmcaddon.Addon('script.module.thecrew').getAddonInfo('version')
        #updated = xbmcaddon.Addon('plugin.video.thecrew').getSetting('module_base') or '0'


        checks = ['en|Free|32345','en_de|Debrid|90004','en_tor|Torrent|90005']
        for check in checks:
            items = check.split('|')
            scraper_path_fill = items[0]
            msg1 = items[1]
            catnr = items[2]
            readProviders(scraper_path_fill, msg1, catnr)

        xbmcaddon.Addon('plugin.video.thecrew').setSetting('module_base', fum_ver)
        c.log('Providers done')

        if control.setting('autoTraktOnStart') == 'true':
            c.log('autoTraktOnStart Enabled: synctraktlib started')
            syncTraktLibrary()

        if int(control.setting('schedTraktTime')) > 0:
            c.log(f"Starting schedTrakTime with setting={hours} hrs")

            #while not monitor.abortRequested():
            #    # Sleep/wait for abort for 10 seconds
            #    if monitor.waitForAbort(timeout=_timeout):
            #        # Abort was requested while waiting. We should exit
            #        break
            #    c.log('Starting trakt scheduling')
            #    c.log(f"Scheduled time frame: {hours} hours")
            #    syncTraktLibrary()

            #while monitor.abortRequested():
                # Sleep/wait for abort for 10 seconds
                #if monitor.waitForAbort(timeout=_timeout):
                    # Abort was requested while waiting. We should exit
                    #break
            while monitor.abortRequested() and not monitor.waitForAbort(timeout=_timeout):
                c.log('Starting trakt scheduling')
                c.log(f"Scheduled time frame: {hours} hours")
                syncTrakt()
                syncTraktLibrary()

    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log(f'[CM Debug @ 204 in service.py]Traceback:: {str(failure)}')
        c.log(f'[CM Debug @ 205 in service.py]Exception raised. Error = {str(e)}')












class TraktMonitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)

    def run(self):
        c.log('\n===========================\nTraktMonitor Service Starting\n===========================\n')
        while not self.abortRequested():
            if self.waitForAbort(QUARTERLY):#seconds
                break
            c.log('\n===========================\nTraktMonitor Service Update Performed\n===========================\n')
            trakt.syncTrakt()
            syncTraktLibrary()
        c.log('\n===========================\nTraktMonitor Service Finished\n===========================\n')

class CrewMonitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.startServices()

    def __del__(self):
        c.log('monitor deleted')
        #stopping threads is highly unrecommended due to the nature. It is better to let the (a) thread(s) die on their own
        del self

    def startServices(self):
        Thread(target=TraktMonitor().run).start()














control.execute('RunPlugin(plugin://%s)' % control.get_plugin_url({'action': 'service'}))

if __name__ == '__main__':
    main()
    CrewMonitor().waitForAbort()
