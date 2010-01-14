#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Contains objects used throughout puddletag"""

#puddleobjects.py

#Copyright (C) 2008-2009 concentricpuddle

#This file is part of puddletag, a semi-good music tag editor.

#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU 12 Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys, os,pdb,shutil

from itertools import groupby # for unique function.
from bisect import bisect_left, insort_left # for unique function.
from copy import copy
import audioinfo
from audioinfo import IMAGETYPES, DESCRIPTION, DATA, IMAGETYPE
from operator import itemgetter
path = os.path
from configobj import ConfigObj
MSGARGS = (QMessageBox.Warning, QMessageBox.Yes or QMessageBox.Default,
                        QMessageBox.No or QMessageBox.Escape, QMessageBox.YesAll)

def _setupsaves(func):
    #filename = os.path.join(PuddleConfig().savedir, 'windowsizes')
    filename = '/home/keith/Desktop/puddle.conf'
    settings = QSettings(filename, QSettings.IniFormat)
    return lambda x, y: func(x, y, settings)

@_setupsaves
def savewinsize(name, dialog, settings):
    settings.setValue(name, QVariant(dialog.saveGeometry()))

@_setupsaves
def winsettings(name, dialog, settings):
    dialog.restoreGeometry(settings.value(name).toByteArray())
    cevent = dialog.closeEvent
    def closeEvent(e):
        cevent(e)
        savewinsize(name, dialog)
    setattr(dialog, 'closeEvent', closeEvent)

try:
    from Levenshtein import ratio
except ImportError:
    from difflib import SequenceMatcher
    ratio = lambda a,b: SequenceMatcher(None, a,b).ratio()

if sys.version_info[:2] < (2, 5):
    def partial(func, arg):
        def callme():
            return func(arg)
        return callme
else:
    from functools import partial

HORIZONTAL = 1
VERTICAL = 0

def singleerror(parent, msg):
    QMessageBox.warning(parent, 'Error', msg, QMessageBox.Ok, QMessageBox.NoButton)

def errormsg(parent, msg, maximum):
    """Shows a messagebox containing an error message indicating that
    writing to filename has failed and asks the user to continue, stop,
    or continue without interruption.

    error is the error that caused the disruption.
    single is the number of files that are being written. If it is 1, then
    just a warningMessage is shown.

    Returns:
        True if yes to all.
        False if No.
        None if just yes."""
    if maximum > 1:
        mb = QMessageBox('Error', msg + u"<br /> Do you want to continue?",
                                                 *(MSGARGS + (parent, )))
        ret = mb.exec_()
        if ret == QMessageBox.No:
            return False
        elif ret == QMessageBox.YesAll:
            return True
    else:
        singleerror(parent, msg)

def safe_name(name, chars=r'/\*?;"|:', to=None):
    """Make a filename safe for use (remove some special chars)

    If any special chars are found they are replaced by to."""
    if not to:
        to = ""
    else:
        to = unicode(to)
    escaped = ""
    for ch in name:
        if ch not in chars: escaped = escaped + ch
        else: escaped = escaped + to
    if not escaped: return '""'
    return escaped

def unique(seq, stable = False):
    """unique(seq, stable=False): return a list of the elements in seq in arbitrary
    order, but without duplicates.
    If stable=True it keeps the original element order (using slower algorithms)."""
    # Developed from Tim Peters version:
    #   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52560

    #if uniqueDebug and len(str(seq))<50: print "Input:", seq # For debugging.

    # Special case of an empty s:
    if not seq: return []

    # if it's a set:
    if isinstance(seq, set): return list(seq)

    if stable:
        # Try with a set:
        seqSet= set()
        result = []
        try:
            for e in seq:
                if e not in seqSet:
                    result.append(e)
                    seqSet.add(e)
        except TypeError:
            pass # move on to the next method
        else:
            #if uniqueDebug: print "Stable, set."
            return result

        # Since you can't hash all elements, use a bisection on sorted elements
        result = []
        sortedElem = []
        try:
            for elem in seq:
                pos = bisect_left(sortedElem, elem)
                if pos >= len(sortedElem) or sortedElem[pos] != elem:
                    insort_left(sortedElem, elem)
                    result.append(elem)
        except TypeError:
            pass  # Move on to the next method
        else:
            #if uniqueDebug: print "Stable, bisect."
            return result
    else: # Not stable
        # Try using a set first, because it's the fastest and it usually works
        try:
            u = set(seq)
        except TypeError:
            pass # move on to the next method
        else:
            #if uniqueDebug: print "Unstable, set."
            return list(u)

        # Elements can't be hashed, so bring equal items together with a sort and
        # remove them out in a single pass.
        try:
            t = sorted(seq)
        except TypeError:
            pass  # Move on to the next method
        else:
            #if uniqueDebug: print "Unstable, sorted."
            return [elem for elem,group in groupby(t)]

    # Brute force:
    result = []
    for elem in seq:
        if elem not in result:
            result.append(elem)
    #if uniqueDebug: print "Brute force (" + ("Unstable","Stable")[stable] + ")."
    return result

class compare:
    "Natural sorting class."
    def try_int(self, s):
        "Convert to integer if possible."
        try: return int(s)
        except: return s
    def natsort_key(self, s):
        "Used internally to get a tuple by which s is sorted."
        import re
        return map(self.try_int, re.findall(r'(\d+|\D+)', s))
    def natcmp(self, a, b):
        "Natural string comparison, case sensitive."
        return cmp(self.natsort_key(a), self.natsort_key(b))
    def natcasecmp(self, a, b):
        "Natural string comparison, ignores case."
        a = list(a)
        b = list(b)
        return self.natcmp("".join(a).lower(), "".join(b).lower())

natcasecmp = compare().natcasecmp

def dupes(l, method = None):
    if method is None:
        method = lambda a,b: int(a==b)
    l = [{'key': z, 'index': i} for i, z in enumerate(l)]
    chars = chars=r'/\*?;"|:\''
    strings = sorted([(safe_name(z['key'].lower(), chars, ''), z['index'])
                            for z in l if z['key'] is not None])
    try:
        last = strings[0][0]
    except IndexError:
        return []
    groups = [[0]]
    for z, i in strings[1:]:
        if z is not None:
            val = method(last, z)
            if val >= 0.85:
                groups[-1].append(i)
            else:
                last = z
                groups.append([i])
    return [z for z in groups if len(z) > 1]

def getfiles(dirs, subfolders = False):
    def recursedir(folder, subfolders):
        if subfolders:
            #TODO: This really fucks up when reading files with malformed
            #unicode filenames.
            files = []
            [[files.append(path.join(z[0], y)) for y in z[2]]
                                            for z in os.walk(folder)]
        else:
            files = os.walk(folder).next()[2]
            files = [path.join(folder, f) for f in files]
        return files

    if isinstance(dirs, basestring):
        files = recursedir(dirs, subfolders)
    else:
        files = []
        if subfolders:
            while dirs and subfolders:
                [files.extend(recursedir(d, True)) for d in dirs]
                dirs = [z for z in files if os.path.isdir(z)]
        else:
            [files.extend(recursedir(d, False)) for d in dirs]
    return [z for z in files if not os.path.isdir(z)]

def gettags(files):
    return (gettag(audio) for audio in files)

def gettag(f):
    try:
        return audioinfo.Tag(f)
    except (IOError, OSError):
        return
    except Exception, e:
        print unicode(e)
        return

def gettaglist():
    cparser = PuddleConfig()
    filename = os.path.join(cparser.savedir, 'usertags')
    try:
        lines = sorted(set([z.strip() for z in open(filename, 'r').read().split('\n')]))
    except (IOError, OSError):
        lines = sorted(audioinfo.REVTAGS)
    return lines

def settaglist(tags):
    cparser = PuddleConfig()
    filename = os.path.join(cparser.savedir, 'usertags')
    f = open(filename, 'w')
    text = '\n'.join(sorted(tags))
    f.write(text)
    f.close()

def progress(func, pstring, maximum, threadfin = None):
    """To be used for functions that need a threaded progressbar.

    Note that this function will only (and is meant to) work on dialogs.

    func is the function that will be run by the thread. It should yield None
    while successful. Otherwise it should yield an errormsg and the number
    of files (this'll be used when calling errormsg).

    pstring is the progress message. This is shown with the number of times
    func yielded a value. For instance, pstring = 'Loading... ', and maximum = 20
    will show 'Loading... 1 of 20', 'Loading... 2 of 20', etc.on the progress
    bar.

    maximum is the maximum value of the progessbar.

    threadfin is the function to run when the thread has finished. Usually
    for cleanup stuff.

    Note that the function returns a function that expects a parent for
    the progess window as the first argument. This with the rest of the arguments
    passed to the returned function are used when calling func (except in the
    case where only the parent argument is passed).
    """
    def s(*args):
        parent = args[0]
        win = ProgressWin(parent, maximum, pstring)
        win.show()
        if len(args) > 1:
            f = func(*args)
        else:
            f = func()
        parent.showmessage = True

        def threadfunc():
            i = 0
            err = False
            while not win.wasCanceled:
                try:
                    temp = f.next()
                    if temp is not None:
                        #temp[0] is the error message, temp[1] the num files
                        parent._t.emit(SIGNAL('error(QString, int)'),
                                                    temp[0], temp[1])
                        err = True
                        break
                    else:
                        parent._t.emit(SIGNAL('win(int)'), i)
                except StopIteration:
                    break
                i += 1

            if not err:
                parent._t.emit(SIGNAL('win(int)'), -1)

        def threadexit(*args):
            if args[0] == -1:
                win.close()
                win.destroy()
                if threadfin:
                    threadfin()
            elif isinstance(args[0], QString):
                if parent.showmessage:
                    ret = errormsg(parent, unicode(args[0]), int(args[1]))
                    if ret is True:
                        parent.showmessage = False
                    elif ret is False:
                        parent._t.emit(SIGNAL('win(int)'), -1)
                        return
                if not win.isVisible():
                    win.show()
                while parent._t.isRunning():
                    pass
                parent._t.start()
            win.setValue(win.value + 1)

        parent._t = PuddleThread(threadfunc)
        parent._threadexit = threadexit
        parent.connect(parent._t, SIGNAL('win(int)'), parent._threadexit)
        parent.connect(parent._t, SIGNAL('error(QString, int)'), parent._threadexit)
        parent._t.start()
    return s

class HeaderSetting(QDialog):
    """A dialog that allows you to edit the header of a TagTable widget."""
    def __init__(self, tags = None, parent = None, showok = True, showedits = True):
        QDialog.__init__(self, parent)
        self.listbox = ListBox()
        self.tags = [list(z) for z in tags]
        self.listbox.addItems([z[0] for z in self.tags])

        self.vbox = QVBoxLayout()
        self.vboxgrid = QGridLayout()
        self.textname = QLineEdit()
        self.tag = QLineEdit()
        self.buttonlist = ListButtons()
        self.buttonlist.edit.setVisible(False)
        if showedits:
            self.vboxgrid.addWidget(QLabel("Name"),0,0)
            self.vboxgrid.addWidget(self.textname,0,1)
            self.vboxgrid.addWidget(QLabel("Tag"), 1,0)
            self.vboxgrid.addWidget(self.tag,1,1)
            self.vboxgrid.addLayout(self.buttonlist,2,0)
        else:
            self.vboxgrid.addLayout(self.buttonlist,1,0)
        self.vboxgrid.setColumnStretch(0,0)

        self.vbox.addLayout(self.vboxgrid)
        self.vbox.addStretch()

        self.grid = QGridLayout()
        self.grid.addWidget(self.listbox,1,0)
        self.grid.addLayout(self.vbox,1,1)
        self.grid.setColumnStretch(1,1)
        self.grid.setColumnStretch(0,2)

        self.connect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)
        self.connect(self.listbox, SIGNAL("itemSelectionChanged()"),self.enableEdits)


        self.okbuttons = OKCancel()
        if showok is True:
            self.grid.addLayout(self.okbuttons, 2,0,1,2)
        self.setLayout(self.grid)

        self.connect(self.okbuttons, SIGNAL("ok"), self.okClicked)
        self.connect(self.okbuttons, SIGNAL("cancel"), self.close)
        self.connect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.connect(self.buttonlist, SIGNAL("add"), self.add)
        self.connect(self.buttonlist, SIGNAL("moveup"), self.moveup)
        self.connect(self.buttonlist, SIGNAL("movedown"), self.movedown)
        self.connect(self.buttonlist, SIGNAL("remove"), self.remove)

        self.listbox.setCurrentRow(0)

    def enableEdits(self):
        if len(self.listbox.selectedItems()) > 1:
            self.textname.setEnabled(False)
            self.tag.setEnabled(False)
            return
        self.textname.setEnabled(True)
        self.tag.setEnabled(True)

    def remove(self):
        if len(self.tags) == 1: return
        self.disconnect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.disconnect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)
        self.listbox.removeSelected(self.tags)
        row = self.listbox.currentRow()
        #self.listbox.clear()
        #self.listbox.addItems([z[0] for z in self.tags])

        if row == 0:
            self.listbox.setCurrentRow(0)
        elif row + 1 < self.listbox.count():
            self.listbox.setCurrentRow(row+1)
        else:
            self.listbox.setCurrentRow(self.listbox.count() -1)
        self.fillEdits(self.listbox.currentItem(), None)
        self.connect(self.textname, SIGNAL("textChanged (const QString&)"), self.updateList)
        self.connect(self.listbox, SIGNAL("currentItemChanged (QListWidgetItem *,QListWidgetItem *)"), self.fillEdits)

    def moveup(self):
        self.listbox.moveUp(self.tags)

    def movedown(self):
        self.listbox.moveDown(self.tags)

    def updateList(self, text):
        self.listbox.currentItem().setText(text)

    def fillEdits(self, current, prev):
        row = self.listbox.row(prev)
        try: #An error is raised if the last item has just been removed
            if row > -1:
                self.tags[row][0] = unicode(self.textname.text())
                self.tags[row][1] = unicode(self.tag.text())
        except IndexError:
            pass

        row = self.listbox.row(current)
        if row > -1:
            self.textname.setText(self.tags[row][0])
            self.tag.setText(self.tags[row][1])

    def okClicked(self):
        row = self.listbox.currentRow()
        if row > -1:
            self.tags[row][0] = unicode(self.textname.text())
            self.tags[row][1] = unicode(self.tag.text())
        self.emit(SIGNAL("headerChanged"),[z for z in self.tags])
        self.close()

    def add(self):
        row = self.listbox.count()
        self.tags.append(["",""])
        self.listbox.addItem("")
        self.listbox.clearSelection()
        self.listbox.setCurrentRow(row)
        self.textname.setFocus()

class Label(QLabel):
    """Just a QLabel that sends a clicked() signal
    when left-clicked."""
    def __init__ (self, text = "", parent = None):
        QLabel.__init__ (self, text, parent)

    def mouseReleaseEvent(self, event):
      if event.button() == Qt.LeftButton:
        self.emit(SIGNAL("clicked()"))
      QLabel.mousePressEvent(self, event)

class ListBox(QListWidget):
    """Puddletag's replacement of QListWidget, because
    removing, moving and deleting items in a listbox
    is done a lot.

    First the modifier methods.
    removeSelected, moveUp and moveDown each does as the
    name implies. See docstrings for more info.

    connectToListButtons -> connects removeSelected etc. to
    the respective buttons in a ListButtons object.

    Attributes:
    editButton -> Set this to a button or control which will be enabled only
    when a single item is selected.

    yourlist -> The list that will be used in removeSelected et al, if None
    is passed when calling the function.."""
    def __init__(self, parent = None):
        QListWidget.__init__(self, parent)
        self.yourlist = None
        self.editButton = None
        self.setSelectionMode(self.ExtendedSelection)

    def selectionChanged(self, selected, deselected):
        if self.editButton:
            if len(self.selectedItems()) == 1:
                self.editButton.setEnabled(True)
            else:
                self.editButton.setEnabled(False)
        QListWidget.selectionChanged(self, selected, deselected)

    def connectToListButtons(self, listbuttons, yourlist = None):
        """Connect the moveUp, moveDown and removeSelected to the
        moveup, movedown and remove signals of listbuttons and
        sets the editButton.

        yourlist is used a the argument in these functions if
        no other yourlist is passed."""
        self.editButton = listbuttons.edit
        self.connect(listbuttons, SIGNAL('moveup'), self.moveUp)
        self.connect(listbuttons, SIGNAL('movedown'), self.moveDown)
        self.connect(listbuttons, SIGNAL('remove'), self.removeSelected)
        self.yourlist = yourlist

    def removeSelected(self, yourlist = None, rows = None):
        """Removes the currently selected items.
        If yourlist is not None, then the selected
        items are removed for yourlist also. Note, that
        the indexes of the items in yourlist and the listbox
        have to correspond.

        If you want to remove anything other than the selected,
        just set rows to a list of integers."""
        if not yourlist:
            yourlist = self.yourlist
        if rows:
            rows = sorted(rows)
        else:
            rows = sorted([self.row(item) for item in self.selectedItems()])

        for i in range(len(rows)):
            self.takeItem(rows[i])
            if yourlist:
                try:
                    del(yourlist[rows[i]])
                except (KeyError, IndexError):
                    "The list doesn't have enough items or something"
            rows = [z - 1 for z in rows]

    def moveUp(self, yourlist = None, rows = None):
        """Moves the currently selected items up one place.
        If yourlist is not None, then the indexes of yourlist
        are updated in tandem. Note, that
        the indexes of the items in yourlist and the listbox
        have to correspond."""
        if not rows:
            rows = [self.row(item) for item in self.selectedItems()]
        rows = sorted(rows)
        if not yourlist:
            yourlist = self.yourlist
        currentrow = self.currentRow() - 1
        if 0 in rows:
            return

        [self.setItemSelected(item, False) for item in self.selectedItems()]
        for i in range(len(rows)):
            row = rows[i]
            item = self.takeItem(row)
            self.insertItem(row - 1, item)
            if yourlist:
                temp = copy(yourlist[row - 1])
                yourlist[row - 1] = yourlist[row]
                yourlist[row] = temp
        [self.setItemSelected(self.item(row - 1), True) for row in rows]
        self.setCurrentRow(currentrow)

    def moveDown(self, yourlist = None, rows = None):
        """See moveup. It's exactly the opposite."""
        if rows is None:
            rows = [self.row(item) for item in self.selectedItems()]
        if self.count() - 1 in rows:
            return
        [self.setItemSelected(item, False) for item in self.selectedItems()]
        if not yourlist:
            yourlist = self.yourlist
        rows = sorted(rows)
        lastindex = rows[0]
        groups = {lastindex:[lastindex]}
        lastrow = lastindex
        for row in rows[1:]:
            if row - 1 == lastindex:
                groups[lastrow].append(row)
            else:
                groups[row] = [row]
                lastrow = row
            lastindex = row

        for group in groups:
            item = self.takeItem(group + len(groups[group]))
            if yourlist:
                temp = copy(yourlist[group + len(groups[group])])
                for index in reversed(groups[group]):
                    yourlist[index + 1] = copy(yourlist[index])
                yourlist[group] = temp
            self.insertItem(group, item)

        [self.setItemSelected(self.item(row + 1), True) for row in rows]

class ListButtons(QVBoxLayout):
    """A Layout that contains five buttons usually
    associated with listboxes. They are
    add, edit, movedown, moveup and remove.

    Each button, when clicked sends signal with the
    buttons name. e.g. add sends SIGNAL("add").

    You can find them all in the widgets attribute."""

    def __init__(self, parent = None):
        QVBoxLayout.__init__(self, parent)
        self.add = QToolButton()
        self.add.setIcon(QIcon(':/filenew.png'))
        self.add.setToolTip('Add')
        self.remove = QToolButton()
        self.remove.setIcon(QIcon(':/remove.png'))
        self.remove.setToolTip('Remove')
        self.moveup = QToolButton()
        self.moveup.setArrowType(Qt.UpArrow)
        self.moveup.setToolTip('Move Up')
        self.movedown = QToolButton()
        self.movedown.setArrowType(Qt.DownArrow)
        self.movedown.setToolTip('Move Down')
        self.edit = QToolButton()
        self.edit.setIcon(QIcon(':/edit.png'))
        self.edit.setToolTip('Edit')

        self.widgets = [self.add, self.edit, self.remove, self.moveup, self.movedown]
        [self.addWidget(widget) for widget in self.widgets]
        self.insertStretch(3)
        [z.setIconSize(QSize(16,16)) for z in self.widgets]
        self.addStretch()

        clicked = SIGNAL("clicked()")
        self.connect(self.add, clicked, self.addClicked)
        self.connect(self.remove, clicked, self.removeClicked)
        self.connect(self.moveup, clicked, self.moveupClicked)
        self.connect(self.movedown, clicked, self.movedownClicked)
        self.connect(self.edit, clicked, self.editClicked)

    def connectToWidget(self, widget):
        connect = lambda a: self.connect(self, SIGNAL(a), getattr(widget, a))
        [connect(z) for z in ['add', 'remove', 'edit']]

    def addClicked(self):
        self.emit(SIGNAL("add"))

    def removeClicked(self):
        self.emit(SIGNAL("remove"))

    def moveupClicked(self):
        self.emit(SIGNAL("moveup"))

    def movedownClicked(self):
        self.emit(SIGNAL("movedown"))

    def editClicked(self):
        self.emit(SIGNAL("edit"))

class MoveButtons(QWidget):
    def __init__(self, arrayname, index = 0, orientation = HORIZONTAL, parent = None):
        QWidget.__init__(self, parent)
        self.next = QPushButton('&>>')
        self.prev = QPushButton('&<<')
        if orientation == VERTICAL:
            box = QVBoxLayout()
            box.addWidget(self.next, 0)
            box.addWidget(self.prev, 0)
        else:
            box = QHBoxLayout()
            box.addWidget(self.prev)
            box.addWidget(self.next)


        self.arrayname = arrayname

        self.setLayout(box)
        self.index = index
        self.connect(self.next, SIGNAL('clicked()'), self.nextClicked)
        self.connect(self.prev, SIGNAL('clicked()'), self.prevClicked)

    def _setCurrentIndex(self, index):
        try:
            if index >= len(self.arrayname) or index < 0:
                return
            else:
                self._currentindex = index
                if self._currentindex >= len(self.arrayname) - 1:
                    self.next.setEnabled(False)
                else:
                    self.next.setEnabled(True)

                if self._currentindex <= 0:
                    self.prev.setEnabled(False)
                else:
                    self.prev.setEnabled(True)
        except TypeError:
            "Probably arrayname is None or something."
            self.prev.setEnabled(False)
            self.next.setEnabled(False)

        if (not self.prev.isEnabled()) and (not self.next.isEnabled()):
            self.prev.hide()
            self.next.hide()
        else:
            self.prev.show()
            self.next.show()

        self.emit(SIGNAL('indexChanged'), index)

    def _getCurrentIndex(self):
        return self._currentindex

    index = property(_getCurrentIndex, _setCurrentIndex)

    def nextClicked(self):
        self.index += 1

    def prevClicked(self):
        self.index -= 1

    def updateButtons(self):
        self.index = self.index

class OKCancel(QHBoxLayout):
    """Yes, I know about QDialogButtonBox, but I'm not using PyQt4.2 here."""
    def __init__(self, parent = None):
        QHBoxLayout.__init__(self, parent)

        self.addStretch()

        self.ok = QPushButton("&OK")
        self.cancel = QPushButton("&Cancel")
        self.ok.setDefault(True)

        self.addWidget(self.ok)
        self.addWidget(self.cancel)

        self.connect(self.ok, SIGNAL("clicked()"), self.yes)
        self.connect(self.cancel, SIGNAL("clicked()"), self.no)

    def yes(self):
        self.emit(SIGNAL("ok"))

    def no(self):
        self.emit(SIGNAL("cancel"))

class PicWidget(QWidget):
    """A widget that shows a file's pictures.

    images is a list of mutagen.id3.APIC objects.
    It allows the user to edit, save and delete whichever
    picture the user wants, by right-clicking on it.

    In addition, there are buttons to browse through
    all the pictures.

    Some important attributes are:
    currentImage -> The index of the current image
    maxImage -> Shows the current image fullsized.
    setImages -> Guess
    addImage -> Guess again...but it also shows and open file dialog.
    removeImage -> Removes the current image.
    next and prevImage -> Moves to the next and previous image.
    saveToFile -> Save the current image to file.
    showbuttons -> If True, the >> and << buttons are always shown. If False,
                    they are shown depending on context."""

    def __init__ (self, images = None, imagetags = None, parent = None, readonly = None, buttons = False):
        """Initialises the widget.

        images -> A list of images as described in the classes docstring.
        parent -> Qt parent
        readonly -> indexes of images that are readonly. Can be changed by modifying
                    the readonly attribute.
        buttons -> If True, then the Add, Edit, etc. Buttons are shown.
                   If False, then these functions can be found by right clicking
                   on the picture."""
        QWidget.__init__(self, parent)
        self.lastfilename = u'~'
        #The picture.
        self.label = Label()
        self.label.setFrameStyle(QFrame.Box)
        self.label.setMargin(0)
        self.label.setMinimumSize(150, 130)
        self.label.setMaximumSize(150, 130)
        self.label.setAlignment(Qt.AlignCenter)

        #Description and picture type shit.
        self._image_desc = QLineEdit(self)
        self.connect(self._image_desc, SIGNAL('textEdited (const QString&)'),
                    self.setDescription)
        self._image_type = QComboBox(self)
        self._image_type.addItems(IMAGETYPES)
        self.connect(self._image_type, SIGNAL('currentIndexChanged (int)'),
                        self.setType)
        controls = QVBoxLayout()

        dbox = QVBoxLayout()
        label = QLabel('&Description')
        label.setBuddy(self._image_desc)
        dbox.addWidget(label)
        dbox.addWidget(self._image_desc)
        controls.addLayout(dbox)

        dbox = QVBoxLayout()
        label = QLabel('&Type')
        label.setBuddy(self._image_type)
        dbox.addWidget(label)
        dbox.addWidget(self._image_type)
        controls.addLayout(dbox)

        self.showbuttons = True

        if not readonly:
            readonly = []
        self.readonly = readonly

        self.next = QToolButton()
        self.next.setArrowType(Qt.RightArrow)
        self.prev = QToolButton()
        self.prev.setArrowType(Qt.LeftArrow)
        self.connect(self.next, SIGNAL('clicked()'), self.nextImage)
        self.connect(self.prev, SIGNAL('clicked()'), self.prevImage)

        movebuttons = QHBoxLayout()
        self._contextlabel = QLabel()
        self._contextlabel.setVisible(False)
        movebuttons.addStretch()
        movebuttons.addWidget(self.prev)
        movebuttons.addWidget(self.next)
        movebuttons.addWidget(self._contextlabel)
        movebuttons.addStretch()

        vbox = QVBoxLayout()
        h = QHBoxLayout(); h.addStretch(); h.addWidget(self.label); h.addStretch()
        vbox.addLayout(h)
        vbox.setMargin(0)
        vbox.addLayout(controls)
        vbox.addLayout(movebuttons)
        vbox.setAlignment(Qt.AlignCenter)

        self.connect(self.label, SIGNAL('clicked()'), self.maxImage)

        hbox = QHBoxLayout()
        hbox.addLayout(vbox)
        self.setLayout(hbox)

        if buttons:
            listbuttons = ListButtons()
            self.addpic = listbuttons.add
            self.removepic = listbuttons.remove
            self.editpic = listbuttons.edit
            self.savepic = QToolButton()
            self.savepic.setIcon(QIcon(':/save.png'))
            self.savepic.setIconSize(QSize(16,16))
            listbuttons.insertWidget(3,self.savepic)
            listbuttons.moveup.hide()
            listbuttons.movedown.hide()
            signal = SIGNAL('clicked()')
            hbox.addLayout(listbuttons)

        else:
            self.label.setContextMenuPolicy(Qt.ActionsContextMenu)
            self.savepic = QAction("&Save picture", self)
            self.label.addAction(self.savepic)

            self.addpic = QAction("&Add picture", self)
            self.label.addAction(self.addpic)

            self.removepic = QAction("&Remove picture", self)
            self.label.addAction(self.removepic)

            self.editpic = QAction("&Change picture", self)
            self.label.addAction(self.editpic)
            signal = SIGNAL('triggered()')

        self.connect(self.addpic, signal, self.addImage)
        self.connect(self.removepic, signal, self.removeImage)
        self.edit = partial(self.addImage, True)
        self.connect(self.editpic, signal, self.edit)
        self.connect(self.savepic, signal, self.saveToFile)

        self.win = PicWin(parent = self)
        self._currentImage = -1

        if not images:
            images = []

        if not imagetags:
            imagetags = []

        self.setImages(images, imagetags)

    def _setContext(self, text):
        if not text:
            self._contextlabel.setVisible(False)
            self._contextlabel.setText('')
        else:
            self._contextlabel.setText(text)
            self._contextlabel.setVisible(True)

    def _getContext(self):
        return self._contextlabel.Text()

    context = property(_getContext, _setContext)

    def setDescription(self, text):
        '''Sets the description of the current image to the text in the
            description text box.'''
        self.images[self.currentImage]['description'] = unicode(text)
        self.emit(SIGNAL('imageChanged'))

    def setType(self, index):
        """Like setDescription, but for imagetype"""
        try:
            self.images[self.currentImage]['imagetype'] = index
            self.emit(SIGNAL('imageChanged'))
        except IndexError:
            pass

    def addImage(self, edit = False, filename = None):
        """Adds an image from the given filename to self.images.

        If a filename is not given, then an open file dialog is shown.
        If edit is True, then the current image is changed."""

        if not filename:
            filedlg = QFileDialog()
            filename = unicode(filedlg.getOpenFileName(self,
                    'Select Image...', self.lastfilename, "JPEG Images (*.jpg);;PNG Images (*.png);;All Files(*.*)"))

        if not filename:
            return
        self.lastfilename = os.path.dirname(filename)
        data = open(filename, 'rb').read()
        pic = self.loadPics(filename)
        if pic:
            pic = pic[0]
            if edit and self.images:
                self.images[self.currentImage].update(pic)
                self.currentImage = self.currentImage
            else:
                if not self.images:
                    self.setImages([pic])
                else:
                    self.images.append(pic)
                    self.currentImage = len(self.images) - 1
            self.emit(SIGNAL('imageChanged'))

    def close(self):
        self.win.close()
        QWidget.close(self)

    def enableButtons(self):
        """Enables or disables buttons depending on context.

        With < 1 image in self.images,
        they're hidden unless overidden by self.showbuttons."""
        if not self.images:
            self.next.setEnabled(False)
            self.prev.setEnabled(False)
        else:
            if self.currentImage >= len(self.images) - 1:
                self.next.setEnabled(False)
            else:
                self.next.setEnabled(True)
            if self.currentImage <= 0:
                self.prev.setEnabled(False)
            else:
                self.prev.setEnabled(True)

        if not self.showbuttons and not self.next.isEnabled() and not self.prev.isEnabled():
            self.next.hide()
            self.prev.hide()
        else:
            self.next.show()
            self.prev.show()

    def _getCurrentImage(self):
        return self._currentImage

    def _setCurrentImage(self, num):
        try:
            while True:
                #A lot of files have corrupt picture data. I just want to
                #skip those and not have the user be any wiser.
                image = QImage().fromData(self.images[num]['data'])
                if image.isNull():
                    del(self.images[num])
                else:
                    break
            [action.setEnabled(True) for action in
                    (self.editpic, self.savepic, self.removepic)]
        except IndexError:
            self.setNone()
            return
        if hasattr(self, '_itags'):
            self.setImageTags(self._itags)
        if num in self.readonly:
            self.editpic.setEnabled(False)
            self.removepic.setEnabled(False)
            self._image_desc.setEnabled(False)
            self._image_type.setEnabled(False)
        self.pixmap = QPixmap.fromImage(image)
        self.win.setImage(self.pixmap)
        self.label.setPixmap(self.pixmap.scaled(self.label.size(), Qt.KeepAspectRatio))
        try:
            self._image_desc.blockSignals(True)
            self._image_desc.setText(self.images[num]['description'])
        except KeyError:
            pass
        self._image_desc.blockSignals(False)
        self._image_type.blockSignals(True)
        try:
            self._image_type.setCurrentIndex(self.images[num]['imagetype'])
        except KeyError:
            self._image_type.setCurrentIndex(3)
            pass
        self._image_type.blockSignals(False)
        self._currentImage = num
        self.context = unicode(num + 1) + '/' + unicode(len(self.images))
        self.label.setFrameStyle(QFrame.NoFrame)
        self.enableButtons()

    currentImage = property(_getCurrentImage, _setCurrentImage,"""Get or set the index of
    the current image. If the index isn't valid
    then a blank image is loaded.""")

    def maxImage(self):
        """Shows a window with the picture fullsized."""
        if self.pixmap:
            if self.win.isVisible():
                self.win.hide()
            else:
                self.win = PicWin(self.pixmap, self)
                self.win.show()

    def nextImage(self):
        self.currentImage += 1

    def prevImage(self):
        self.currentImage -= 1

    def saveToFile(self):
        """Opens a dialog that allows the user to save,
        the image in the current file to disk."""
        if self.currentImage > -1:
            filedlg = QFileDialog()
            filename = unicode(filedlg.getSaveFileName(self,
                    'Save as...',self.lastfilename, "PNG (*.png)"))
            if os.path.exists(os.path.dirname(filename)):
                self.pixmap.save(filename, "PNG")

    def setNone(self):
        self.label.setFrameStyle(QFrame.Box)
        self.label.setPixmap(QPixmap())
        self.pixmap = None
        self.images = []
        self._image_desc.setEnabled(False)
        self._image_type.setEnabled(False)
        [action.setEnabled(False) for action in
                    (self.editpic, self.savepic, self.removepic)]


    def setImages(self, images, imagetags = None):
        """Sets images. images are dictionaries as described in the class docstring."""
        if imagetags:
            self.setImageTags(imagetags)
        if images:
            self.images = images
            self.currentImage = 0
        else:
            self.setNone()
        self.enableButtons()


    def removeImage(self):
        """Removes the current image."""
        if len(self.images) >= 1:
            del(self.images[self.currentImage])
            if self.currentImage >= len(self.images) - 1 and self.currentImage > 0:
                self.currentImage = len(self.images) - 1
            else:
                self.currentImage =  self.currentImage
        self.emit(SIGNAL('imageChanged'))

    def loadPics(self, *filenames):
        """Loads pictures from the filenames"""
        images = []
        for filename in filenames:
            image = QImage()
            if image.load(filename):
                try:
                    data = open(filename, 'rb').read()
                except IOError, e:
                    if filename.startswith(u':/'):
                        ba = QByteArray()
                        data = QBuffer(ba)
                        data.open(QIODevice.WriteOnly)
                        image.save(data, "JPG")
                        data = data.data()
                    else:
                        raise e
                pic = {'data': data, 'height': image.height(),
                    'width': image.width(), 'size': len(data),
                    'mime': 'image/jpeg', 'description': 'Enter description',
                    'imagetype': 3}
                images.append(pic)
        return images

    def setImageTags(self, itags):
        tags = {DESCRIPTION: self._image_desc.setEnabled,
                DATA: self.label.setEnabled,
                IMAGETYPE: self._image_type.setEnabled}
        self.enableButtons()
        if not itags:
            self.addpic.setEnabled(False)
        else:
            self.addpic.setEnabled(True)
        for z in itags:
            try:
                tags[z](True)
            except KeyError:
                pass

        others = [z for z in tags if z not in itags]
        if len(others) == len(tags):
            self.next.setEnabled(False)
            self.prev.setEnabled(False)
        for z in others:
            tags[z](False)
        self._itags = itags


class PicWin(QDialog):
    """A windows that shows an image."""
    def __init__(self, pixmap = None, parent = None):
        """Loads the image specified in QPixmap pixmap.
        If picture is clicked, the window closes.

        If you don't want to load an image when the class
        is created, let pixmap = None and call setImage later."""
        QDialog.__init__(self, parent)
        self.label = Label()

        vbox = QVBoxLayout()
        vbox.setMargin(0)
        vbox.addWidget(self.label)
        self.setLayout(vbox)

        if pixmap is not None:
            self.setImage(pixmap)

        self.connect(self.label, SIGNAL('clicked()'), self.close)

    def setImage(self, pixmap):
        self.label.setPixmap(pixmap)
        self.setMaximumSize(pixmap.size())
        self.setMinimumSize(pixmap.size())
        self.resize(pixmap.size())

class ProgressWin(QDialog):
    def __init__(self, parent=None, maximum = 100, progresstext = '', showcancel = True):
        QDialog.__init__(self, parent)
        self.setModal(True)
        self.setWindowTitle("Please Wait...")

        self.ptext = progresstext

        self.pbar = QProgressBar(self)
        self.pbar.setRange(0, maximum)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignHCenter)

        if maximum <= 0:
            self.pbar.setTextVisible(False)
            self.label.setVisible(False)

        cancel = QPushButton('Cancel')
        cbox = QHBoxLayout()
        cbox.addStretch()
        cbox.addWidget(cancel)
        cancel.setVisible(showcancel)

        vbox = QVBoxLayout()
        vbox.addWidget(self.label)
        vbox.addWidget(self.pbar)
        vbox.addLayout(cbox)
        self.setLayout(vbox)
        self.wasCanceled = False
        self.connect(self, SIGNAL('rejected()'), self.cancel)
        self.connect(cancel, SIGNAL('clicked()'), self.cancel)

        self.setValue(1)

    def setValue(self, value):
        self.blockSignals(True)
        if self.ptext:
            self.pbar.setTextVisible(False)
            self.label.setText(self.ptext + unicode(value) + ' of ' +
                                        unicode(self.pbar.maximum()) + ' ...')
        self.pbar.setValue(value)
        self.blockSignals(False)
        if value >= self.pbar.maximum():
            self.close()

    def cancel(self):
        self.wasCanceled = True
        self.emit(SIGNAL('canceled()'))
        self.close()

    def _value(self):
        return self.pbar.value()

    value = property(_value)

class PuddleCombo(QWidget):
    def __init__(self, name, default = None, parent = None):
        QWidget.__init__(self, parent)
        hbox = QHBoxLayout()
        hbox.setMargin(0)
        self.combo = QComboBox()

        self.remove = QToolButton()
        self.remove.setIcon(QIcon(':/remove.png'))
        self.remove.setToolTip('Remove current item.')
        self.remove.setIconSize(QSize(13, 13))
        self.connect(self.remove, SIGNAL('clicked()'), (self.removeCurrent))

        hbox.addWidget(self.combo)
        hbox.addWidget(self.remove)
        self.setLayout(hbox)


        self.combo.setEditable(True)
        self.name = name
        cparser = PuddleConfig()
        self.filename = os.path.join(os.path.dirname(cparser.filename), 'combos')
        if not default:
            default = []
        cparser.filename = self.filename
        items = cparser.load(self.name, 'values', default)
        self.combo.addItems(items)
        self.connect(self.combo, SIGNAL('editTextChanged(const QString&)'),
                        self._editTextChanged)

    def load(self, name = None, default = None):
        if name:
            self.name = name
        if not default:
            default = []
        self.combo.clear()
        self.combo.addItems(cparser.load(self.name, 'values', default))

    def save(self):
        values = [unicode(self.combo.itemText(index)) for index in xrange(self.combo.count())]
        cparser = PuddleConfig(self.filename)
        cparser.setSection(self.name, 'values', values)

    def removeCurrent(self):
        self.combo.removeItem(self.combo.currentIndex())

    def _editTextChanged(self, text):
        self.emit(SIGNAL('editTextChanged(const QString&)'), text)

class PuddleConfig(object):
    """Module that allows you to values from INI config files, similar to
    Qt's Settings module (Created it because PyQt4.4.3 has problems with
    saving and loading lists.

    Only two functions of interest:

    load -> load a key from a specified section
    setSection -> save a key section"""
    def __init__(self, filename = None):
        self.settings = ConfigObj(filename, create_empty=True, encoding='utf8')

        if not filename:
            filename = os.path.join(os.getenv('HOME'),'.puddletag', 'puddletag.conf')
        self._setFilename(filename)

        #TODO: backward compatibility, remove all.
        self.setSection = self.set
        self.load = self.get

    def get(self, section, key, default, getint = False):
        settings = self.settings
        try:
            if isinstance(default, bool):
                if self.settings[section][key] == 'True':
                    return True
                return False
            elif getint or isinstance(default, (long,int)):
                try:
                    return int(self.settings[section][key])
                except TypeError:
                    return [int(z) for z in self.settings[section][key]]
            else:
                return self.settings[section][key]
        except KeyError:
            return default

    def set(self, section = None, key = None, value = None):
        settings = self.settings
        if section in self.settings:
            settings[section][key] = value
        else:
            settings[section] = {}
            settings[section][key] = value
        settings.write()

    def _setFilename(self, filename):
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        self.settings.filename = filename
        self.savedir = dirname
        self.settings.reload()

    def _getFilename(self):
        return self.settings.filename

    def sections(self):
        return self.settings.keys()

    filename = property(_getFilename, _setFilename)

class PuddleDock(QDockWidget):
    """A normal QDockWidget that emits a 'visibilitychanged' signal
    when...uhm...it changes visibility."""
    def __init__(self, title = None, parent = None):
        QDockWidget.__init__(self, title, parent)

    def setVisible(self, visible):
        self.emit(SIGNAL('visibilitychanged'), visible)
        QDockWidget.setVisible(self, visible)

class PuddleThread(QThread):
    """puddletag rudimentary threading.
    pass a command to run in another thread. The result
    is stored in retval."""
    def __init__(self, command, parent = None):
        QThread.__init__(self, parent)
        self.connect(self, SIGNAL('finished()'), self._finish)
        self.command = command

    def run(self):
        try:
            self.retval = self.command()
        except StopIteration:
            self.retval = 'STOP'

    def _finish(self):
        if hasattr(self, 'retval'):
            self.emit(SIGNAL('threadfinished'), self.retval)
        else:
            self.emit(SIGNAL('threadfinished'), None)


if __name__ == '__main__':
    class MainWin(QDialog):
        def __init__(self, parent = None):
            QDialog.__init__(self, parent)
            self.combo = PuddleCombo('patterncombo', [u'%artist% - $num(%track%, 2) - %title%', u'%artist% - %title%', u'%artist% - %album%', u'%artist% - Track %track%', u'%artist% - %title%', u'%artist%'])

            hbox = QHBoxLayout()
            hbox.addWidget(self.combo)
            self.setLayout(hbox)

        def closeEvent(self,e):
            self.combo.save()
            QDialog.closeEvent(self, e)

    app = QApplication(sys.argv)
    widget = MainWin()
    widget.show()
    app.exec_()