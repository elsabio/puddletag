# -*- coding: utf-8 -*-
#actiondlg.py

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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import QtGui, QtCore
import sys, findfunc, pdb, os, resource, string, functions
from copy import copy
from pyparsing import delimitedList, alphanums, Combine, Word, ZeroOrMore, \
                        QuotedString, Literal, NotAny, nums
import cPickle as pickle
from puddleobjects import ListBox, OKCancel, ListButtons, winsettings, gettaglist, settaglist
from findfunc import Function, runAction
from puddleobjects import PuddleConfig, PuddleCombo
from audioinfo import REVTAGS, INFOTAGS


def displaytags(tags):
    if tags:
        s = "<b>%s</b>: %s<br /> "
        return "".join([s % (z,v) for z,v in tags.items()])[:-2]
    else:
        return '<b>No change.</b>'

class FunctionDialog(QWidget):
    "A dialog that allows you to edit or create a Function class."
    controls = {'text': PuddleCombo, 'combo': QComboBox, 'check': QCheckBox}
    signals = {'text': SIGNAL('editTextChanged(const QString&)'),
                'combo' : SIGNAL('currentIndexChanged(int)'),
                'check': SIGNAL('stateChanged(int)')}
    def __init__(self, funcname, showcombo = False, userargs = None, defaulttags = None, parent = None, example = None, text = None, mapping = None):
        """funcname is name the function you want to use(can be either string, or functions.py function).
        if combotags is true then a combobox with tags that the user can choose from are shown.
        userargs is the default values you want to fill the controls in the dialog with[make sure they don't exceed the number of arguments of funcname]."""
        QWidget.__init__(self,parent)
        identifier = QuotedString('"') | Combine(Word(alphanums + ' !"#$%&\'()*+-./:;<=>?@[\\]^_`{|}~'))
        tags = delimitedList(identifier)
        self.func = Function(funcname)
        docstr = self.func.doc[1:]
        self.vbox = QVBoxLayout()
        self.retval = []
        self._mapping = mapping if mapping else {}
        self._revmapping = dict([(value,key) for key, value in self._mapping.items()])
        self._combotags = []

        if showcombo:
            self.tagcombo = QComboBox()
            self.tagcombo.setEditable(True)
            self.tagcombo.addItems(['__all'] + sorted(INFOTAGS) + showcombo)
            self._combotags = showcombo
            if defaulttags:
                index = self.tagcombo.findText(" | ".join(defaulttags))
                if index != -1:
                    self.tagcombo.setCurrentIndex(index)
                else:
                    self.tagcombo.insertItem(0, " | ".join(defaulttags))
                    self.tagcombo.setCurrentIndex(0)
            self.connect(self.tagcombo, SIGNAL('editTextChanged(const QString&)'), self.showexample)

            self.vbox.addWidget(QLabel("Tags"))
            self.vbox.addWidget(self.tagcombo)
        self.example = example
        self._text =text

        self.textcombos = []
        #Loop that creates all the controls
        for argno, line in enumerate(docstr):
            args = tags.parseString(line)
            #Get the control
            try:
                ctype = args[1]
                if ctype == 'text':
                    control = self.controls['text'](args[0], parent = self)
                else:
                    control = self.controls[ctype](self)
            except IndexError:
                sys.stderr.write("The function isn't defined correctly, I'll continue anyway.")

            defaultarg = args[2:]

            #Create the controls with their default values
            #if default values have been defined, we set them.
            #self.retval contains the method to be called when we get
            #the value of the control
            if ctype == 'combo':
                self.retval.append(control.currentText)
                if defaultarg:
                    control.addItems(defaultarg)
                    if userargs:
                        index = control.findText(userargs[argno])
                        control.setCurrentIndex(index)
            elif ctype == 'text':
                self.textcombos.append(control)
                self.retval.append(control.combo.currentText)
                if defaultarg:
                    control.combo.setEditText(defaultarg[0])
                if userargs:
                    control.combo.setEditText(userargs[argno])
            elif ctype == 'check':
                self.retval.append(control.checkState)
                if defaultarg:
                    if defaultarg[2] == "True":
                        control.setCheckState(Qt.Checked)
                    else:
                        control.setCheckState(Qt.Unchecked)
                if userargs:
                    if userargs[argno] is True:
                        control.setCheckState(Qt.Checked)
                    else:
                        control.setCheckState(Qt.Unchecked)
                control.setText(args[0])

            if ctype != 'check':
                label = QLabel(args[0])
                label.setBuddy(control)
                self.vbox.addWidget(label)

            if self.example is not None:
                control.connect(control, self.signals[ctype], self.showexample)

            self.vbox.addWidget(control)
        self.vbox.addStretch()
        self.setLayout(self.vbox)
        self.setMinimumSize(self.sizeHint())

    def argValues(self):
        """Returns the values in the windows controls.
        The last argument is the tags value.
        Also sets self.func's arg and tag values."""
        newargs = []
        for method in self.retval:
            if method == QtGui.QCheckBox.checkState:
                if method() == Qt.Checked:
                    newargs.append(True)
                elif (method() == Qt.PartiallyChecked) or (method() == Qt.Unchecked):
                    newargs.append(False)
            else:
                if isinstance(method(), (int, long)):
                    newargs.append(method())
                else:
                    newargs.append(unicode(method()))
        [z.save() for z in self.textcombos]
        self.func.setArgs(newargs)
        if hasattr(self, "tagcombo"):
            tags = [x for x in [z.strip().lower() for z in unicode(self.tagcombo.currentText()).split("|")] if z != ""]
            self.func.setTag(tags)
            return newargs + tags
        else:
            return newargs + [""]

    def showexample(self, *args, **kwargs):
        self.argValues()
        if self.example is not None:
            audio = self.example.stringtags()
            if not self._text:
                try:
                    text = audio.get(self.func.tag[0])
                    if self.func.tag == [u'__all']:
                        text = 'Some random text, courtesy of puddletag.'
                    elif self.func.tag[0] in self._mapping:
                        text = audio.get(self._mapping[self.func.tag[0]])
                except IndexError:
                    text = ''
                if not text:
                    text = u''
            else:
                text = self._text

            val = self.func.runFunction(text, audio)
            if val:
                self.emit(SIGNAL('updateExample'), val)
            else:
                self.emit(SIGNAL('updateExample'), '')

class CreateFunction(QDialog):
    """A dialog to allow the creation of functions using only one window and a QStackedWidget.
    For each function in functions, a dialog is created and displayed in the stacked widget."""
    def __init__(self, tags = None, prevfunc = None, showcombo = True, parent = None, example = None, text = None, mapping = None):
        """tags is a list of the tags you want to show in the FunctionDialog.
        Each item should be in the form (DisplayName, tagname) as used in audioinfo.
        prevfunc is a Function object that is to be edited."""
        QDialog.__init__(self,parent)
        winsettings('createfunction', self)
        self.tags = tags
        self._mapping = mapping if mapping else {}
        self._revmapping = dict([(value,key) for key, value in self._mapping.items()])
        self.realfuncs = []
        #Get all the function from the functions module.
        for z in dir(functions):
            funcname = getattr(functions,z)
            if callable(funcname) and (not (funcname.__name__.startswith("__") or (funcname.__doc__ is None))):
                self.realfuncs.append(z)

        funcnames = sorted([(Function(z).funcname, z) for z in  self.realfuncs])
        self.realfuncs = [z[1] for z in funcnames]

        self.vbox = QVBoxLayout()
        self.functions = QComboBox()
        self.functions.addItems([z[0] for z in funcnames])
        self.vbox.addWidget(self.functions)

        self.stack = QStackedWidget()
        self.vbox.addWidget(self.stack)
        self.okcancel = OKCancel()

        self.mydict = {}    #Holds the created windows in the form self.functions.index: window
        self.setLayout(self.vbox)
        self.setMinimumHeight(self.sizeHint().height())
        self.connect(self.okcancel, SIGNAL("ok"), self.okClicked)
        self.connect(self.okcancel, SIGNAL('cancel'), self.close)
        self.setWindowTitle("Format")
        self.example = example
        self._text = text
        if showcombo:
            self.showcombo = gettaglist()
        else:
            self.showcombo = showcombo
        self.exlabel = QLabel('')

        if prevfunc is not None:
            index = self.functions.findText(prevfunc.funcname)
            if index >= 0:
                self.functions.setCurrentIndex(index)
                self.createWindow(index, prevfunc.args, prevfunc.tag)
        else:
            self.createWindow(0)

        self.connect(self.functions, SIGNAL("activated(int)"), self.createWindow)

        self.vbox.addWidget(self.exlabel)
        self.vbox.addLayout(self.okcancel)
        self.setLayout(self.vbox)

    def okClicked(self):
        w = self.stack.currentWidget()
        w.argValues()
        self.close()
        if self.showcombo:
            newtags = [z for z in w.func.tag if z not in self.showcombo]
            if newtags:
                settaglist(sorted(newtags + self.showcombo))
        self.emit(SIGNAL("valschanged"), w.func)

    def createWindow(self, index, defaultargs = None, defaulttags = None):
        """Creates a Function dialog in the stack window
        if it doesn't exist already."""
        self.stack.setFrameStyle(QFrame.Box)
        if index not in self.mydict:
            what = FunctionDialog(self.realfuncs[index], self.showcombo, defaultargs, defaulttags, example = self.example, text=self._text, mapping=self._mapping)
            self.mydict.update({index: what})
            self.stack.addWidget(what)
            if self.example:
                self.connect(what, SIGNAL('updateExample'), self.updateExample)
                what.showexample()
        self.stack.setCurrentWidget(self.mydict[index])
        self.setMinimumHeight(self.sizeHint().height())
        if self.sizeHint().width() > self.width():
            self.setMinimumWidth(self.sizeHint().width())

    def updateExample(self, text):
        if not text:
            self.exlabel.setText('')
        else:
            self.exlabel.setText(text)
        QApplication.processEvents()

class CreateAction(QDialog):
    "An action is defined as a collection of functions. This dialog serves the purpose of creating an action"
    def __init__(self, tags = None, parent = None, prevfunctions = None, example = None, mapping = None):
        """tags is a list of the tags you want to show in the FunctionDialog.
        Each item should be in the form (DisplayName, tagname as used in audioinfo).
        prevfunction is the previous function that is to be edited."""
        QDialog.__init__(self, parent)
        self.setWindowTitle("Modify Action")
        winsettings('editaction', self)
        self.tags = tags
        self.grid = QGridLayout()
        self._mapping = mapping if mapping else {}
        self._revmapping = dict([(value,key) for key, value in self._mapping.items()])

        self.listbox = ListBox()
        self.functions = []
        self.buttonlist = ListButtons()
        self.grid.addWidget(self.listbox, 0, 0)
        self.grid.addLayout(self.buttonlist, 0, 1)

        self.okcancel = OKCancel()
        #self.grid.addLayout(self.okcancel,1,0,1,2)
        self.setLayout(self.grid)
        self.example = example

        self.connect(self.okcancel, SIGNAL("cancel"), self.close)
        self.connect(self.okcancel, SIGNAL("ok"), self.okClicked)
        self.connect(self.buttonlist, SIGNAL("add"), self.add)
        self.connect(self.buttonlist, SIGNAL("edit"), self.edit)
        self.connect(self.buttonlist, SIGNAL("moveup"), self.moveUp)
        self.connect(self.buttonlist, SIGNAL("movedown"), self.moveDown)
        self.connect(self.buttonlist, SIGNAL("remove"), self.remove)
        self.connect(self.listbox, SIGNAL("currentRowChanged(int)"), self.enableOK)

        if prevfunctions is not None:
            self.functions = copy(prevfunctions)
            self.listbox.addItems([function.description() for function in self.functions])

        if example:
            self._examplelabel = QLabel('')
            self.grid.addWidget(self._examplelabel,1,0)
            self._example = example
            self.updateExample()
            self.grid.addLayout(self.okcancel,2,0,1,2)
        else:
            self.grid.addLayout(self.okcancel,1,0,1,2)

    def updateExample(self):
        tags = runAction(self.functions, self._example, self._revmapping)
        self._examplelabel.setText(displaytags(tags))


    def enableOK(self, val):
        if val == -1:
            [button.setEnabled(False) for button in self.buttonlist.widgets[1:]]
        else:
            [button.setEnabled(True) for button in self.buttonlist.widgets[1:]]

    def moveDown(self):
        self.listbox.moveDown(self.functions)

    def moveUp(self):
        self.listbox.moveUp(self.functions)

    def remove(self):
        self.listbox.removeSelected(self.functions)

    def add(self):
        self.win = CreateFunction(self.tags, None, parent = self, example = self.example, mapping = self._mapping)
        self.win.setModal(True)
        self.win.show()
        self.connect(self.win, SIGNAL("valschanged"), self.addBuddy)

    def edit(self):
        self.win = CreateFunction(self.tags, self.functions[self.listbox.currentRow()], self, example = self.example, mapping = self._mapping)
        self.win.setModal(True)
        self.win.show()
        self.connect(self.win, SIGNAL("valschanged"), self.editBuddy)

    def editBuddy(self, func):
        self.listbox.currentItem().setText(func.description())
        self.functions[self.listbox.currentRow()] = func
        self.updateExample()

    def addBuddy(self, func):
        self.listbox.addItem(func.description())
        self.functions.append(func)
        self.updateExample()

    def okClicked(self):
        self.close()
        self.emit(SIGNAL("donewithmyshit"), self.functions)


class ActionWindow(QDialog):
    """Just a dialog that allows you to add, remove and edit actions
    On clicking OK, a signal "donewithmyshit" is emitted.
    It returns a list of lists.
    Each element of a list contains one complete action. While
    the elements of that action are just normal Function objects."""
    def __init__(self, tags, parent = None, example = None, mapping = None):
        """tags are the tags to be shown in the FunctionDialog"""
        QDialog.__init__(self,parent)
        self.setWindowTitle("Actions")
        winsettings('actions', self)
        self.tags = tags
        self._mapping = mapping if mapping else {}
        self._revmapping = dict([(value,key) for key, value in self._mapping.items()])
        self.listbox = ListBox()
        self.listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.example = example

        self.funcs = self.loadActions()
        for z in self.funcs:
            item = QListWidgetItem(self.funcs[z][1])
            item.setCheckState(Qt.Unchecked)
            self.listbox.addItem(item)
        #self.listbox.addItems([self.funcs[z][1] for z in sorted(self.funcs)])

        self.okcancel = OKCancel()
        self.okcancel.ok.setDefault(True)
        self.grid = QGridLayout()

        self.buttonlist = ListButtons()

        self.grid.addWidget(self.listbox,0,0)
        self.grid.addLayout(self.buttonlist, 0,1)


        self.setLayout(self.grid)

        self.connect(self.okcancel, SIGNAL("ok") , self.okClicked)
        self.connect(self.okcancel, SIGNAL("cancel"),self.close)
        self.connect(self.buttonlist, SIGNAL("add"), self.add)
        self.connect(self.buttonlist, SIGNAL("edit"), self.edit)
        self.connect(self.buttonlist, SIGNAL("moveup"), self.moveUp)
        self.connect(self.buttonlist, SIGNAL("movedown"), self.moveDown)
        self.connect(self.buttonlist, SIGNAL("remove"), self.remove)
        self.connect(self.listbox, SIGNAL("itemDoubleClicked (QListWidgetItem *)"), self.edit)
        self.connect(self.listbox, SIGNAL("currentRowChanged(int)"), self.enableOK)

        if example:
            self._examplelabel = QLabel('')
            self.grid.addWidget(self._examplelabel,1,0)
            self._example = example
            self.connect(self.listbox, SIGNAL('itemChanged (QListWidgetItem *)'),
                                self.updateExample)
            self.grid.addLayout(self.okcancel,2,0,1,2)
        else:
            self.grid.addLayout(self.okcancel,1,0,1,2)

    def moveUp(self):
        self.listbox.moveUp(self.funcs)

    def moveDown(self):
        self.listbox.moveDown(self.funcs)

    def remove(self):
        cparser = PuddleConfig()
        filedir = os.path.dirname(cparser.filename)
        listbox = self.listbox
        rows = sorted([listbox.row(item) for item in listbox.selectedItems()])
        for row in rows:
            name = self.funcs[row][1]
            filename = os.path.join(filedir, self.removeSpaces(name) + u'.action')
            os.rename(filename, filename + '.deleted')
        self.listbox.removeSelected(self.funcs)

    def enableOK(self, val):
        if val == -1:
            [button.setEnabled(False) for button in self.buttonlist.widgets[1:]]
            self.okcancel.ok.setEnabled(False)
        else:
            [button.setEnabled(True) for button in self.buttonlist.widgets[1:]]
            self.okcancel.ok.setEnabled(True)

    def loadActions(self):
        funcs = {}

        cparser = PuddleConfig()
        firstrun = cparser.load('puddleactions', 'firstrun', 0, True)
        filedir = os.path.dirname(cparser.filename)
        from glob import glob
        files = glob(os.path.join(filedir, u'*.action'))
        if not firstrun and not files:
            import StringIO
            files = [StringIO.StringIO(QFile(filename).readData(1024**2))
                        for filename in [':/caseconversion.action', ':/standard.action']]
            cparser.setSection('puddleactions', 'firstrun',1)

            for i, f in enumerate(files):
                funcs[i] = findfunc.getAction(f)
                self.saveAction(funcs[i][1], funcs[i][0])
        else:
            order = cparser.load('puddleactions', 'order', [])
            files = [z for z in order if z in files] + [z for z in files if z not in order]
            for i, f in enumerate(files):
                funcs[i] = findfunc.getAction(f)
        return funcs

    def updateExample(self, *args):
        l = self.listbox
        items = [l.item(z) for z in range(l.count())]
        selectedrows = [i for i,z in enumerate(items) if z.checkState() == Qt.Checked]
        if selectedrows:
            tempfuncs = [self.funcs[row][0] for row in selectedrows]
            funcs = []
            [funcs.extend(func) for func in tempfuncs]
            tags = runAction(funcs, self._example, self._revmapping)
            self._examplelabel.setText(displaytags(tags))

    def removeSpaces(self, text):
        for char in string.whitespace:
            text = text.replace(char, '')
        return text.lower()

    def saveAction(self, name, funcs):
        cparser = PuddleConfig()
        filedir = os.path.dirname(cparser.filename)
        filename = os.path.join(filedir, self.removeSpaces(name) + u'.action')
        findfunc.saveAction(filename, name, funcs)

    def add(self):
        (text, ok) = QInputDialog.getText (self, "New Configuration", "Enter a name for the new action.", QLineEdit.Normal)
        if (ok is True) and (text != ""):
            item = QListWidgetItem(text)
            item.setCheckState(Qt.Unchecked)
            self.listbox.addItem(item)
        else:
            return
        win = CreateAction(self.tags, self, example = self.example)
        win.setWindowTitle("Edit Action: " + self.listbox.item(self.listbox.count() - 1).text())
        win.setModal(True)
        win.show()
        self.connect(win, SIGNAL("donewithmyshit"), self.addBuddy)

    def addBuddy(self, funcs):
        name = unicode(self.listbox.item(self.listbox.count() - 1).text())
        self.funcs.update({self.listbox.count() - 1: [funcs, name]})
        self.saveAction(name, funcs)

    def edit(self):
        win = CreateAction(self.tags, self, self.funcs[self.listbox.currentRow()][0], example = self.example, mapping = self._mapping)
        win.setWindowTitle("Edit Action: " + self.listbox.currentItem().text())
        win.show()
        self.connect(win, SIGNAL("donewithmyshit"), self.editBuddy)

    def editBuddy(self, funcs):
        self.saveAction(self.funcs[self.listbox.currentRow()][1], funcs)
        self.funcs[self.listbox.currentRow()][0] = funcs
        self.updateExample()

    def close(self):
        order = [unicode(self.listbox.item(row).text()) for row in
                                                xrange(self.listbox.count())]
        cparser = PuddleConfig()
        filedir = os.path.dirname(cparser.filename)
        filenames = [os.path.join(filedir,self.removeSpaces(z) + u'.action') for z in order]
        cparser.setSection('puddleactions', 'order', filenames)
        QDialog.close(self)

    def okClicked(self):
        """When clicked, save the current contents of the listbox and the associated functions"""
        l = self.listbox
        items = [l.item(z) for z in range(l.count())]
        selectedrows = [i for i,z in enumerate(items) if z.checkState() == Qt.Checked]
        tempfuncs = [self.funcs[row][0] for row in selectedrows]
        funcs = []
        [funcs.extend(func) for func in tempfuncs]
        self.close()
        self.emit(SIGNAL("donewithmyshit"), funcs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOrganizationName("Puddle Inc.")
    app.setApplicationName("puddletag")
    qb = ActionWindow([(u'Path', u'__path'), ('Artist', 'artist'), ('Title', 'title'), ('Album', 'album'), ('Track', 'track'), ('Length', '__length'), (u'Year', u'date')])
    qb.show()
    app.exec_()