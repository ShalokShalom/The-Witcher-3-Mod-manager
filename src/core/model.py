'''Mod management model'''
# pylint: disable=invalid-name,missing-docstring,wildcard-import,unused-wildcard-import

from typing import Dict, List, KeysView, ValuesView
from os import path
import xml.etree.ElementTree as XML

from fasteners import InterProcessLock

from src.domain.mod import Mod
from src.domain.key import Key
from src.globals import data
from src.core.fetcher import *
from src.util.util import *
from src.util.syntax import *


class Model:
    '''Mod management model'''

    def __init__(self, ignorelock=False):
        if not ignorelock:
            self.lock = InterProcessLock(self.lockfile)
            if not self.lock.acquire(False):
                raise IOError('could not lock ' + self.lockfile)
        self.modList: Dict[str, Mod] = {}
        self.reload()

    def reload(self) -> None:
        self.modList = {}
        if path.exists(self.xmlfile):
            tree = XML.parse(self.xmlfile)
            root = tree.getroot()
            for xmlmod in root.findall('mod'):
                mod = self.populateModFromXml(Mod(), xmlmod)
                self.modList[mod.name] = mod

    def write(self) -> None:
        root = XML.ElementTree(XML.Element('installed'))
        for mod in self.all():
            root = self.writeModToXml(mod, root)
        indent(root.getroot())
        print(f"writing mod list to {self.xmlfile}")
        root.write(self.xmlfile)

    def get(self, modname: str) -> Mod:
        return self.modList[modname]

    def list(self) -> KeysView[str]:
        return self.modList.keys()

    def all(self) -> ValuesView[Mod]:
        return self.modList.values()

    def add(self, modname: str, mod: Mod):
        self.modList[modname] = mod
        self.write()

    def remove(self, modname: str):
        if modname in self.modList:
            del self.modList[modname]
        self.write()

    def rename(self, modname: str, newname: str) -> bool:
        if not modname in self.modList:
            return False
        mod = self.modList[modname]
        del self.modList[modname]
        mod.name = newname
        self.modList[newname] = mod
        self.write()
        return True

    def explore(self, modname: str) -> None:
        mod = self.modList[modname]
        for file in mod.files:
            moddir = data.config.mods + \
                ('/~' if not mod.enabled else '/') + file
            openFolder(moddir)

    @property
    def xmlfile(self) -> str:
        return data.config.configuration + '/installed.xml'

    @property
    def lockfile(self) -> str:
        return data.config.configuration + '/installed.lock'

    @staticmethod
    def populateModFromXml(mod: Mod, root: XML.Element) -> Mod:
        mod.date = str(root.get('date'))
        enabled = str(root.get('enabled'))
        if enabled == 'True':
            mod.enabled = True
        else:
            mod.enabled = False
        mod.name = str(root.get('name'))
        prt = str(root.get('priority'))
        if prt != 'Not Set':
            mod.priority = prt
        for elem in root.findall('data'):
            mod.files.append(str(elem.text))
        for elem in root.findall('dlc'):
            mod.dlcs.append(str(elem.text))
        for elem in root.findall('menu'):
            mod.menus.append(str(elem.text))
        for elem in root.findall('xmlkey'):
            mod.xmlkeys.append(str(elem.text))
        for elem in root.findall('hidden'):
            mod.hidden.append(str(elem.text))
        for elem in root.findall('key'):
            key = Key(elem.get('context'), str(elem.text))
            mod.inputsettings.append(key)
        for elem in root.findall('settings'):
            # legacy usersetting storage format
            settings = fetchUserSettings(str(elem.text))
            for setting in iter(settings):
                mod.usersettings.append(setting)
        for elem in root.findall('setting'):
            usersetting = Usersetting(str(elem.get('context')), str(elem.text))
            mod.usersettings.append(usersetting)

        mod.checkPriority()
        return mod

    @staticmethod
    def writeModToXml(mod: Mod, root: XML.ElementTree) -> XML.ElementTree:
        elem = XML.SubElement(root.getroot(), 'mod')
        elem.set('name', mod.name)
        elem.set('enabled', str(mod.enabled))
        elem.set('date', mod.date)
        elem.set('priority', mod.priority)
        if mod.files:
            for file in mod.files:
                XML.SubElement(elem, 'data').text = file
        if mod.dlcs:
            for dlc in mod.dlcs:
                XML.SubElement(elem, 'dlc').text = dlc
        if mod.menus:
            for menu in mod.menus:
                XML.SubElement(elem, 'menu').text = menu
        if mod.xmlkeys:
            for xml in mod.xmlkeys:
                XML.SubElement(elem, 'xmlkey').text = xml
        if mod.hidden:
            for xml in mod.hidden:
                XML.SubElement(elem, 'hidden').text = xml
        if mod.inputsettings:
            for key in mod.inputsettings:
                ky = XML.SubElement(elem, 'key')
                ky.text = str(key)
                ky.set('context', key.context)
        if mod.usersettings:
            for usersetting in mod.usersettings:
                us = XML.SubElement(elem, 'setting')
                us.text = str(usersetting)
                us.set('context', usersetting.context)
        return root
