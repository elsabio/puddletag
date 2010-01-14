#!/usr/bin/env python
#puddlesettings.py

#Copyright (C) 2008-2009 concentricpuddle

#This file is part of puddletag, a semi-good music tag editor.

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""In this module, all the dialogs for configuring puddletag are
stored. These are accessed via the Preferences window.

The MainWin class is the important class since it creates,
the dialogs in a stacked widget and calls their methods as needed.

Each dialog must have in its __init__ method an argument called 'cenwid'.
cenwid is puddletag's main window found in puddletag.MainWin.
If cenwid is passed, then the dialog should read all it's values,
apply them (if needed) and return(close). This is done when puddletag starts.

In addition, each dialog should have a saveSettings functions, which
is called when settings pertinent to that dialog need to be saved.

It is not required, that each dialog should also have
an applySettings(self, cenwid) method, which is called when
settings need to be applied while puddletag is running.
"""

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys, resource, os
from copy import copy
from puddleobjects import ListButtons, OKCancel, HeaderSetting, ListBox, PuddleConfig, savewinsize, winsettings
import pdb
import audioinfo.util

class PatternEditor(QFrame):
    def __init__(self, parent = None, cenwid = None):
        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.Box)
        self.listbox = ListBox()
        self.listbox.setSelectionMode(self.listbox.ExtendedSelection)
        buttons = ListButtons()
        cparser = PuddleConfig()
        patterns = cparser.load('editor', 'patterns', ['%artist% - $num(%track%,2) - %title%', '%artist% - %title%', '%artist% - %album%', '%artist% - Track %track%', '%artist% - %title%'])
        if cenwid:
            cenwid.patterncombo.clear()
            cenwid.patterncombo.addItems(patterns)
            return
        self.listbox.addItems(patterns)
        hbox = QHBoxLayout()
        hbox.addWidget(self.listbox)
        hbox.addLayout(buttons)

        self.setLayout(hbox)

        self.connect(buttons, SIGNAL("add"), self.addPattern)
        self.connect(buttons, SIGNAL("edit"), self.editItem)
        self.listbox.connectToListButtons(buttons)
        self.listbox.editButton = buttons.edit
        self.connect(self.listbox, SIGNAL('itemDoubleClicked (QListWidgetItem *)'), self._doubleClicked)

    def saveSettings(self):
        patterns = [unicode(self.listbox.item(row).text()) for row in xrange(self.listbox.count())]
        cparser = PuddleConfig()
        cparser.setSection('editor', 'patterns', patterns)

    def addPattern(self):
        self.listbox.addItem("")
        self.listbox.setCurrentRow(self.listbox.count() - 1)
        self.listbox.clearSelection()
        self.editItem(True)
        self.listbox.setFocus()

    def _doubleClicked(self, item):
        self.editItem()

    def editItem(self, add = False):
        row = self.listbox.currentRow()
        if not add and row < 0:
            return
        l = self.listbox.item
        items = [unicode(l(z).text()) for z in range(self.listbox.count())]
        (text, ok) = QInputDialog().getItem (self, 'puddletag', 'Enter a pattern', items, row)
        if ok:
            item = l(row)
            self.listbox.setItemSelected (item, True)
            item.setText(text)

    def applySettings(self, cenwid):
        patterns = [self.listbox.item(row).text() for row in xrange(self.listbox.count())]
        cenwid.patterncombo.clear()
        cenwid.patterncombo.addItems(patterns)

class Playlist(QFrame):
    def __init__(self, parent = None, cenwid = None):
        QFrame.__init__(self, parent)

        def inttocheck(value):
            if value:
                return Qt.Checked
            return Qt.Unchecked

        cparser = PuddleConfig()
        self.setFrameStyle(QFrame.Box)

        self.extpattern = QLineEdit()
        self.extpattern.setText(cparser.load('playlist', 'extpattern','%artist% - %title%'))
        hbox = QHBoxLayout()
        hbox.addSpacing(10)
        hbox.addWidget(self.extpattern)

        self.extinfo = QCheckBox('&Write extended info', self)
        self.connect(self.extinfo, SIGNAL('stateChanged(int)'), self.extpattern.setEnabled)
        self.extinfo.setCheckState(inttocheck(cparser.load('playlist', 'extinfo',1, True)))
        self.extpattern.setEnabled(self.extinfo.checkState())

        self.reldir = QCheckBox('Entries &relative to working directory')
        self.reldir.setCheckState(inttocheck(cparser.load('playlist', 'reldir',0, True)))


        self.filename = QLineEdit()
        self.filename.setText(cparser.load('playlist', 'filepattern','puddletag.m3u'))
        label = QLabel('&Filename pattern.')
        label.setBuddy(self.filename)

        vbox = QVBoxLayout()
        [vbox.addWidget(z) for z in (self.extinfo, self.reldir,
                                        label, self.filename)]
        vbox.insertLayout(1, hbox)
        vbox.addStretch()
        vbox.insertSpacing(2, 5)
        vbox.insertSpacing(4, 5)
        self.setLayout(vbox)

    def saveSettings(self):
        def checktoint(checkbox):
            if checkbox.checkState() == Qt.Checked:
                return 1
            else:
                return 0
        cparser = PuddleConfig()
        cparser.setSection('playlist', 'extinfo', checktoint(self.extinfo))
        cparser.setSection('playlist', 'extpattern', unicode(self.extpattern.text()))
        cparser.setSection('playlist', 'reldir', checktoint(self.reldir))
        cparser.setSection('playlist', 'filepattern', unicode(self.filename.text()))

class ColumnSettings(HeaderSetting):
    """A dialog that allows you to edit the header of a TagTable widget."""
    def __init__(self, parent = None, cenwid=None, showok = False, showedits = True):
        cparser = PuddleConfig()
        titles = cparser.get('tableheader', 'titles',
                                ['Path', 'Artist', 'Title', 'Album', 'Track',
                                 'Length', 'Year', 'Bitrate', 'Genre',
                                 'Comment', 'Filename'])
        tags = cparser.get('tableheader', 'tags',
                            ['__path', 'artist', 'title',
                             'album', 'track', '__length', 'year', '__bitrate',
                             'genre', 'comment', '__filename'])
        checked = cparser.get('tableheader', 'enabled', range(len(tags)), True)
        headerdata = [z for i, z in enumerate(zip(titles, tags)) if i in checked]

        if cenwid:
            cenwid.cenwid.setNewHeader(headerdata)
            return
        self.tags = zip(titles, tags)

        HeaderSetting.__init__(self, self.tags, parent, showok, showedits)
        if parent:
            self.setWindowFlags(Qt.Widget)
        label = QLabel('Adjust visibility of columns.')
        self.grid.addWidget(label,0,0)
        items = [self.listbox.item(z) for z in range(self.listbox.count())]
        if not checked:
            checked = []
        [z.setCheckState(Qt.Checked) if i in checked else z.setCheckState(Qt.Unchecked)
                                for i,z in enumerate(items)]

    def saveSettings(self):
        row = self.listbox.currentRow()
        if row > -1:
            self.tags[row][0] = unicode(self.textname.text())
            self.tags[row][1] = unicode(self.tag.text())
        checked = [z for z in range(self.listbox.count()) if self.listbox.item(z).checkState()]
        titles = [z[0] for z in self.tags]
        tags = [z[1] for z in self.tags]
        cparser = PuddleConfig()
        cparser.set('tableheader', 'titles', titles)
        cparser.set('tableheader', 'tags', tags)
        cparser.set('tableheader', 'enabled', checked)


    def applySettings(self, cenwid = None):
        checked = [z for z in range(self.listbox.count()) if self.listbox.item(z).checkState()]
        headerdata = [z for i, z in enumerate(self.tags) if i in checked]
        self.emit(SIGNAL("headerChanged"), headerdata)
        if cenwid:
            cenwid.cenwid.setNewHeader(headerdata)

    def add(self):
        row = self.listbox.count()
        self.tags.append(["",""])
        item = QListWidgetItem('')
        item.setCheckState(True)
        self.listbox.addItem(item)
        self.listbox.clearSelection()
        self.listbox.setCurrentRow(row)
        self.textname.setFocus()

    def okClicked(self):
        self.saveSettings()
        self.applySettings()
        self.close()

class ComboSetting(HeaderSetting):
    """Class that sets the type of tag that a combo should display
    and what combos should be in the same row.
    """
    def __init__(self, parent = None, cenwid = None):
        #Default shit
        cparser = PuddleConfig()
        titles = cparser.load('framecombo', 'titles',['&Artist', '&Title', 'Al&bum', 'T&rack', u'&Year', "&Genre", '&Comment'])
        tags = cparser.load('framecombo', 'tags',['artist', 'title', 'album', 'track', u'year', 'genre', 'comment'])
        newtags = [(unicode(title),unicode(tag)) for title, tag in zip(titles, tags)]
        HeaderSetting.__init__(self, newtags, parent, False)
        self.setWindowFlags(Qt.Widget)
        self.grid.addWidget(QLabel("You need to restart puddletag for these settings to be applied."),2,0)
        #Get the number of rows
        try:
            numrows = cparser.load('framecombo','numrows',0, True)
        except ValueError:
            numrows = 0

        rowcolors = {}
        if numrows <= 0:
            numrows = 5
            defaults = [(4294044297,[0]),(4294041729,[1]), (4283560452,[2]),
                        (4294447390,[3,4,5]), (4288440633,[6])]
        else:
            defaults = [(z,[]) for z in range(numrows)]
        for i in range(numrows):
            rowcolor = cparser.load('tageditor' + str(i), 'row' + str(i), defaults[i][0], True)
            rowtags = [z for z in cparser.load('tageditor' + str(i), 'rowtags' + str(i), defaults[i][1], True)]
            rowcolors[rowcolor] = rowtags
            if rowcolor != -1:
                for z in rowtags:
                    newcolor = QColor(rowcolor)
                    self.listbox.item(z).setBackgroundColor(newcolor)
                    textcolor = (255-newcolor.red(),255 - newcolor.green(),255 - newcolor.blue())
                    self.listbox.item(z).setTextColor(QColor(*textcolor))

        if cenwid is not None:
            cenwid.combogroup.setCombos(newtags, rowcolors)
            return

        self.samerow = QPushButton("&Samerow")
        self.vboxgrid.addWidget(self.samerow)
        self.grid.setMargin(0)
        self.connect(self.samerow, SIGNAL("clicked()"), self.sameRow)

    def reject(self):
        pass

    def sameRow(self):
        """Just picks a random color and sets the selected items that that colour"""
        import random
        color = QColor()
        (r, g, b) = int(255*random.random()), int(255*random.random()), int(255*random.random())
        color.setRgb(r, g, b)

        for item in self.listbox.selectedItems():
            item.setBackgroundColor(color)
            textcolor = (255 - color.red(), 255 - color.green(), 255 - color.blue())
            item.setTextColor(QColor(*textcolor))

    def saveSettings(self):
        row = self.listbox.currentRow()
        if row > -1:
            self.tags[row][0] = unicode(self.textname.text())
            self.tags[row][1] = unicode(self.tag.text())

        titles = [z[0] for z in self.tags]
        tags = [z[1] for z in self.tags]
        colors = {}

        for row in xrange(self.listbox.count()):
            color = self.listbox.item(row).backgroundColor().rgb()
            if color not in colors:
                colors[color] = [row]
            else:
                colors[color].append(row)

        cparser = PuddleConfig()
        cparser.setSection('framecombo', 'titles', titles)
        cparser.setSection('framecombo', 'tags', tags)
        cparser.setSection('framecombo', 'numrows', len(colors))
        for i, colour in enumerate(colors):
            cparser.setSection('tageditor' + str(i), 'rowtags' + str(i), colors[colour])
            cparser.setSection('tageditor' + str(i), 'row' + str(i), colour)
        self.colors = colors

    def add(self):
        HeaderSetting.add(self)
        [self.listbox.setItemSelected(item, False) for item in self.listbox.selectedItems()]
        self.listbox.setCurrentRow(self.listbox.count() -1)
        self.sameRow()

class ComboFrame(QFrame):
    def __init__(self, parent = None, cenwid = None):
        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.Box)
        self.combosetting = ComboSetting(parent, cenwid)
        vbox = QVBoxLayout()
        vbox.addWidget(self.combosetting)
        self.setLayout(vbox)
        self.saveSettings = self.combosetting.saveSettings

class GeneralSettings(QFrame):
    def __init__(self, parent = None, cenwid = None):
        def convertstate(setting, defaultval):
            state = int(cparser.load("General", setting, defaultval))
            if not state:
                return Qt.Unchecked
            else:
                return Qt.Checked

        cparser = PuddleConfig()

        vbox = QVBoxLayout()
        self.subfolders = QCheckBox("Su&bfolders")
        self.subfolders.setCheckState(convertstate('subfolders', 0))
        self.pathinbar = QCheckBox("Show &filename in titlebar")
        self.pathinbar.setCheckState(convertstate('pathinbar',1))
        self.gridlines = QCheckBox("Show &gridlines")
        self.gridlines.setCheckState(convertstate('gridlines', 1))
        self.vertheader = QCheckBox("Show &row numbers")
        self.vertheader.setCheckState(convertstate('vertheader',0))
        self.columnresize = QCheckBox("&Resize columns to contents.")
        self.columnresize.setCheckState(convertstate('columnresize',0))
        self.reloaddir = QCheckBox("&Reload last opened directory at startup.")
        self.reloaddir.setCheckState(convertstate('reloaddir',0))
        self.savemod = QCheckBox("&Preserve file modification times.")
        self.savemod.setCheckState(convertstate('savemodification',0))
        self.dragcombo = QComboBox()
        self.dragcombo.addItems(['Ask me each time', 'Move', 'Copy'])
        draglabel = QLabel('When files are dropped on Filesystem:')
        self.dragcombo.setCurrentIndex(cparser.load('General', 'dropaction', 0, True))

        playtext = cparser.load('table', 'playcommand', ['xmms'])
        label = QLabel("Enter the &command to play files with.")
        self.playcommand = QLineEdit()
        label.setBuddy(self.playcommand)
        self.playcommand.setText(" ".join(playtext))

        [vbox.addWidget(z) for z in [self.subfolders, self.pathinbar,
            self.gridlines, self.vertheader, self.columnresize, self.reloaddir,
            self.savemod, label, self.playcommand, draglabel, self.dragcombo]]
        vbox.addStretch()

        if cenwid is not None:
            if self.reloaddir.checkState() == Qt.Checked and os.path.exists(cenwid.lastfolder):
                cenwid.cenwid.table.loadFiles(dirs=[cenwid.lastfolder], append=False)
            cenwid.cenwid.table.setPlayCommand(playtext)
            self.applySettings(cenwid)
            return

        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.Box)
        self.setLayout(vbox)
        self.loadlib = False

    def enablePlay(self):
        if self.enableplay.checkState == QtChecked():
            self.playcommand.setEnabled(True)
        else:
            self.playcommand.setEnabled(False)

    def applySettings(self, cenwid):
        def convertState(checkbox):
            if checkbox.checkState() == Qt.Checked:
                return 1
            else:
                return 0
        cenwid.cenwid.table.subFolders = convertState(self.subfolders)
        cenwid.subfolders = convertState(self.subfolders)
        cenwid.pathinbar = convertState(self.pathinbar)
        cenwid.cenwid.gridvisible = convertState(self.gridlines)

        curindex = self.dragcombo.currentIndex()
        if curindex == 0:
            cenwid.tree.defaultDropAction = None
        elif curindex == 1:
            cenwid.tree.defaultDropAction = Qt.MoveAction
        elif curindex == 2:
            cenwid.tree.defaultDropAction = Qt.CopyAction
        cenwid.cenwid.table.autoresize = convertState(self.columnresize)
        cenwid.cenwid.gridvisible = convertState(self.gridlines)
        cenwid.cenwid.table.model().saveModification = convertState(self.savemod)

        #if convertstate(self.enableplay):
            #cenwid.cenwid.table.playcommand = True
        #else:
        cenwid.cenwid.table.playcommand = [unicode(z) for z in self.playcommand.text().split(" ")]

        if convertState(self.vertheader):
            cenwid.cenwid.table.verticalHeader().show()
        else:
            cenwid.cenwid.table.verticalHeader().hide()

    def saveSettings(self):
        def convertState(state):
            if state == Qt.Checked:
                return 1
            return 0
        cparser = PuddleConfig()
        controls = {'subfolders': convertState(self.subfolders.checkState()),
                    'gridlines': convertState(self.gridlines.checkState()),
                    'pathinbar': convertState(self.pathinbar.checkState()),
                    'vertheader': convertState(self.vertheader.checkState()),
                    'columnresize': convertState(self.columnresize.checkState()),
                    'dropaction': self.dragcombo.currentIndex(),
                    'reloaddir': convertState(self.reloaddir.checkState()),
                    'savemodification': convertState(self.savemod.checkState())}
        for z in controls:
            cparser.setSection('General', z, controls[z])
        cparser.setSection('table', 'playcommand',[unicode(z) for z in self.playcommand.text().split(" ")])

class ListModel(QAbstractListModel):
    def __init__(self, options):
        QAbstractListModel.__init__(self)
        self.options = options

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
            return QVariant(int(Qt.AlignRight|Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(self.headerdata[section])
        return QVariant(int(section + 1))

    def data(self, index, role = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.options)):
            return QVariant()
        if (role == Qt.DisplayRole) or (role == Qt.ToolTipRole):
            try:
                return QVariant(self.options[index.row()][0])
            except IndexError: return QVariant()
        return QVariant()

    def widget(self, row):
        return self.options[row][1]

    def rowCount(self, index = QModelIndex()):
        return len(self.options)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractListModel.flags(self, index))


class SettingsList(QListView):
    """Just want a list that emits a selectionChanged signal, with
    the currently selected row."""
    def __init__(self, parent = None):
        QListView.__init__(self, parent)

    def selectionChanged(self, selected, deselected):
        self.emit(SIGNAL("selectionChanged"), selected.indexes()[0].row())

class TagMappings(QDialog):
    def __init__(self, parent = None, cenwid = None):

        filename = os.path.join(PuddleConfig().savedir, 'mappings')
        try:
            lines = open(filename, 'r').read().split('\n')
            mappings = {}
            for l in lines:
                tags = [z.strip() for z in l.split(' ')]
                if len(tags) == 3: #Tag, Source, Target
                    try:
                        mappings[tags[0]].update({tags[1].lower(): tags[2].lower()})
                    except KeyError:
                        mappings[tags[0]] = ({tags[1].lower(): tags[2].lower()})
        except IOError, OSError:
            mappings = {'VorbisComment': {'tracknumber': 'track'}}
        self._mappings = mappings

        if cenwid:
            self.applySettings(cenwid)
            #if 'puddletag' in mappings:
                #cenwid.cenwid.table.model().setMapping(mappings['puddletag'])
            #else:
                #cenwid.cenwid.table.model().setMapping({})
            return

        QDialog.__init__(self, parent)
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(['Tag', 'Source', 'Target'])
        self._table.horizontalHeader().setVisible(True)
        buttons = ListButtons()
        buttons.connectToWidget(self)
        buttons.moveup.setVisible(False)
        buttons.movedown.setVisible(False)

        hbox = QHBoxLayout()
        hbox.addWidget(self._table, 1)
        hbox.addLayout(buttons, 0)
        self.setLayout(hbox)
        self._setMappings(mappings)

    def _setMappings(self, mappings):
        self._table.clearContents()
        setItem = self._table.setItem
        self._table.setRowCount(1)
        row = 0
        if 'puddletag' in mappings:
            puddletag = mappings['puddletag']
        else:
            puddletag = {}
        for z, v in mappings.items():
            for source, target in v.items():
                if source in puddletag and z != 'puddletag':
                    continue
                setItem(row, 0, QTableWidgetItem(z))
                setItem(row, 1, QTableWidgetItem(source))
                setItem(row, 2, QTableWidgetItem(target))
                row += 1
                self._table.setRowCount(row + 1)
        self._table.removeRow(self._table.rowCount() -1)

    def add(self):
        table = self._table
        row = table.rowCount()
        self._table.insertRow(row)
        for column, v in enumerate(['Tag', 'Source', 'Target']):
            table.setItem(row, column, QTableWidgetItem(v))

    def edit(self):
        self._table.editItem(self._table.currentItem())

    def remove(self):
        self._table.removeRow(self._table.currentRow())

    def applySettings(self, cenwid = None):
        import tagmodel
        audioinfo.setmapping(self._mappings)
        if 'puddletag' in self._mappings:
            tagmodel.mapping = self._mappings['puddletag']
            tagmodel.revmapping = audioinfo.revmapping['puddletag']
            cenwid.combogroup.setMapping(tagmodel.mapping, tagmodel.revmapping)
        else:
            tagmodel.mapping = {}
            tagmodel.revmapping = {}
            cenwid.combogroup.setMapping({}, {})

    def saveSettings(self):
        text = []
        mappings = {}
        item = self._table.item
        itemtext = lambda row, column: unicode(item(row, column).text())
        for row in range(self._table.rowCount()):
            tag = itemtext(row, 0)
            original = itemtext(row, 1).lower()
            other = itemtext(row, 2).lower()
            text.append((tag, original, other))
            if tag in mappings:
                mappings[tag].update({other: original})
            else:
                mappings[tag] = {other: original}
        self._mappings = mappings
        filename = os.path.join(PuddleConfig().savedir, 'mappings')
        f = open(filename, 'w')
        f.write('\n'.join([' '.join(z) for z in text]))
        f.close()

class StatusWidgetItem(QTableWidgetItem):
    def __init__(self, text, color):
        QTableWidgetItem.__init__(self, text)
        self.setBackground(QBrush(color))
        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

class ColorEdit(QDialog):
    def __init__(self, parent = None, cenwid = None):

        if cenwid:
            return
        cparser = PuddleConfig()
        add = QColor.fromRgb(*cparser.get('extendedtags', 'add', [0,255,0], True))
        edit = QColor.fromRgb(*cparser.get('extendedtags', 'edit', [255,255,0], True))
        remove = QColor.fromRgb(*cparser.get('extendedtags', 'remove', [255,0,0], True))
        colors = (add, edit, remove)

        QDialog.__init__(self, parent)

        self.listbox = QTableWidget(0, 2, self)
        header = self.listbox.horizontalHeader()
        self.listbox.setSortingEnabled(True)
        header.setVisible(True)
        header.setSortIndicatorShown (True)
        header.setStretchLastSection (True)
        header.setSortIndicator (0, Qt.AscendingOrder)
        self.listbox.setHorizontalHeaderLabels(['Tag', 'Value'])
        self.listbox.setRowCount(3)

        for i, z in enumerate([('Added', add), ('Edited', edit), ('Removed', remove)]):
            self.listbox.setItem(i, 0, StatusWidgetItem(*z))
            self.listbox.setItem(i, 1, StatusWidgetItem('Double click to edit', z[1]))

        vbox = QVBoxLayout()
        vbox.addWidget(self.listbox)
        self.setLayout(vbox)
        self.connect(self.listbox, SIGNAL('cellDoubleClicked(int,int)'), self.edit)


    def edit(self, row, column):
        self._status = (row, self.listbox.item(row, column).background())
        win = QColorDialog(self)
        win.setCurrentColor(self.listbox.item(row, column).background().color())
        self.connect(win, SIGNAL('currentColorChanged(const QColor&)'), self.intermediateColor)
        self.connect(win, SIGNAL('rejected()'), self.setColor)
        win.open()

    def setColor(self):
        row = self._status[0]
        self.listbox.item(row, 0).setBackground(self._status[1])
        self.listbox.item(row, 1).setBackground(self._status[1])

    def intermediateColor(self, color):
        row = self._status[0]
        if color.isValid():
            self.listbox.item(row, 0).setBackground(QBrush(color))
            self.listbox.item(row, 1).setBackground(QBrush(color))

    def saveSettings(self):
        cparser = PuddleConfig()
        x = lambda c: (c.red(), c.green(), c.blue())
        colors = [x(self.listbox.item(z,0).background().color()) for z in range(self.listbox.rowCount())]
        cparser.set('extendedtags', 'add', colors[0])
        cparser.set('extendedtags', 'edit', colors[1])
        cparser.set('extendedtags', 'remove', colors[2])


class Genres(QDialog):
    def __init__(self, parent = None, cenwid = None):

        cparser = PuddleConfig()

        try:
            genres = open(os.path.join(cparser.savedir, 'genres'), 'r').read().split('\n')
            genres = [z.strip() for z in genres]
        except IOError:
            genres = audioinfo.GENRES[::]
        if cenwid:
            audioinfo.GENRES = genres
            return
        QDialog.__init__(self, parent)
        self.listbox = ListBox()
        self._itemflags = Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        [self.listbox.addItem(self._createItem(z)) for z in genres]

        buttons = ListButtons()
        self.listbox.connectToListButtons(buttons)
        self.listbox.setAutoScroll(False)

        self.connect(buttons, SIGNAL('add'), self.add)
        self.connect(buttons, SIGNAL('edit'), self.edit)

        hbox = QHBoxLayout()
        hbox.addWidget(self.listbox,1)
        hbox.addLayout(buttons, 0)
        self.setLayout(hbox)

    def _createItem(self, text):
        item = QListWidgetItem(text)
        item.setFlags(self._itemflags)
        return item

    def add(self):
        self.listbox.setAutoScroll(True)
        item = self._createItem('')
        self.listbox.addItem(item)
        self.listbox.clearSelection()
        self.listbox.setCurrentItem(item)
        self.listbox.editItem(item)
        self.listbox.setAutoScroll(False)

    def edit(self):
        self.listbox.setAutoScroll(True)
        self.listbox.editItem(self.listbox.currentItem())
        self.listbox.setAutoScroll(False)

    def saveSettings(self):
        cparser = PuddleConfig()
        f = open(os.path.join(cparser.savedir, 'genres'), 'w')
        text = '\n'.join([unicode(self.listbox.item(row).text()) for row in range(self.listbox.count())])
        f.write(text)
        f.close()

    def applySettings(self, cenwid=None):
        audioinfo.GENRES = [unicode(self.listbox.item(row).text()) for row in range(self.listbox.count())]
        #combos = cenwid.cenwid.combogroup.combos
        #if 'genre' in combos:
            #c = combos['genre']
            #text = c.currentText()
            #c.blockSignals(True)
            #c.clear()
            #c.addItems(audioinfo.GENRES)
            #i = c.findText(text)
            #if i > -1:
                #c.setCurrentIndex(i)
            #else:
                #c.setEditText(text)
            #c.blockSignals(False)

class MainWin(QDialog):
    """In order to use a class as an option add it to self.widgets"""
    def __init__(self, cenwid = None, parent = None, readvalues = False):
        QDialog.__init__(self, parent)
        self.setWindowTitle("puddletag settings")
        winsettings('settingswin', self)
        if readvalues:
            self.combosetting = ComboFrame(parent = self, cenwid = cenwid)
            self.gensettings = GeneralSettings(parent = self, cenwid = cenwid)
            self.patterns = PatternEditor(parent = self, cenwid = cenwid)
            self.playlist = Playlist(parent = self, cenwid = cenwid)
            self.columns = ColumnSettings(parent=self, cenwid=cenwid)
            self.mapping = TagMappings(parent=self, cenwid=cenwid)
            self.coloredit = ColorEdit(parent=self, cenwid=cenwid)
            self.genres = Genres(parent=self, cenwid=cenwid)
            return

        self.combosetting = ComboFrame()
        self.gensettings = GeneralSettings()
        self.patterns = PatternEditor()
        self.playlist = Playlist()
        self.columns = ColumnSettings()
        self.coloredit = ColorEdit()
        self.genres = Genres()
        self.mapping = TagMappings()

        self.listbox = SettingsList()

        self.widgets = {0: ["General Settings", self.gensettings],
                        1:["Tag Editor", self.combosetting],
                        2:["Patterns", self.patterns],
                        3:['Playlist', self.playlist],
                        4:['Columns', self.columns],
                        5: ['Extended colors', self.coloredit],
                        6: ['Genres', self.genres],
                        7: ['Mappings', self.mapping]}
        self.model = ListModel(self.widgets)
        self.listbox.setModel(self.model)
        self.cenwid = cenwid

        self.stack = QStackedWidget()

        self.grid = QGridLayout()
        self.grid.addWidget(self.listbox)
        self.grid.addWidget(self.stack,0,1)
        self.grid.setColumnStretch(1,2)
        self.setLayout(self.grid)

        self.connect(self.listbox, SIGNAL("selectionChanged"), self.showOption)

        selection = QItemSelection()
        self.selectionModel= QItemSelectionModel(self.model)
        index = self.model.index(0,0)
        selection.select(index, index)
        self.listbox.setSelectionModel(self.selectionModel)
        self.selectionModel.select(selection, QItemSelectionModel.Select)

        self.okbuttons = OKCancel()
        self.okbuttons.ok.setDefault(True)
        self.grid.addLayout(self.okbuttons, 1,0,1,2)

        self.connect(self.okbuttons,SIGNAL("ok"), self.saveSettings)
        self.connect(self, SIGNAL("accepted"),self.saveSettings)
        self.connect(self.okbuttons,SIGNAL("cancel"), self.close)

    def showOption(self, option):
        widget = self.widgets[option][1]
        stack = self.stack
        if stack.indexOf(widget) == -1:
            stack.addWidget(widget)
        stack.setCurrentWidget(widget)
        if self.width() < self.sizeHint().width():
            self.setMinimumWidth(self.sizeHint().width())

    def saveSettings(self):
        self.cenwid.cenwid.table.saveSelection()
        for i, z in enumerate(self.widgets.values()):
            z[1].saveSettings()
            try:
                z[1].applySettings(self.cenwid)
            except AttributeError:
                pass
                #sys.stderr.write(z[0] + " doesn't have a settings applySettings method.\n")
        self.cenwid.cenwid.table.restoreSelection()
        self.close()

if __name__ == "__main__":
    app=QApplication(sys.argv)
    app.setOrganizationName("Puddle Inc.")
    app.setApplicationName("puddletag")
    qb=MainWin()
    qb.show()
    app.exec_()
