#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QAction, QApplication, QDesktopWidget, 
                             QFileDialog, QMainWindow, QMessageBox, QTextEdit)

from editdialogs import (AddLineDialog, NewRateDialog, RemoveLineDialog, 
                         EditLineDialog)
from filedialogs import (NewTimesheetDialog, OpenTimesheetDialog, 
                         DeleteTimesheetDialog)
from processcsv import csv_to_html
from readconfig import ConfigParser

datapath = os.path.join(os.path.expanduser('~'), '.timeaftertime')
conffile = os.path.join(datapath, 'timeaftertime.conf')

# make sure the TimeAfterTime directory and config file exist
def check_path():
    if not os.path.exists(datapath):
        os.mkdir(datapath)
        with open(conffile, 'w') as fileobj:
            fileobj.write('last=None\n')

# type checking decorator
def accepts(t):
    def wrap(func):
        def inner(*args):
            if not isinstance(args[1], t):
                try:
                    len(t)
                    types_str = ', '.join([typ.__name__ for typ in t])
                except TypeError:
                    types_str = t.__name__
                raise TypeError('"{}" takes {}'.format(func.__name__, 
                                types_str))
            else:
                r = func(*args)
            return r
        return inner
    return wrap


class Data:
    # separate class to handle all the data
    
    def __init__(self, project_name):
        """ Object that controls the csv (and config) data. """
        
        self.modified = False
        
        if project_name is None:
            self.csv_data = ''
            self.name = 'None'
            self.rate = ''
            self.currency = ''
                       
        else:
            path = os.path.join(datapath, project_name)
            
            file = 'ts_' + project_name.lower()
            
            self.csvfile, self.conffile = (os.path.join(path, file+ext) 
                                           for ext in ('.csv', '.conf'))
            
            with open(self.csvfile) as fileobj:
                self.csv_data = fileobj.read()
                
                
            self.cfg = ConfigParser(self.conffile)
                
            conf_data = self.cfg.read_conf()
            
            # if conf_data is not empty...
            self.name = conf_data['name']
            self.rate = conf_data['rate']
            # 'currency' is a new feature, so this line will break old versions
            # that don't have currency in the config file
            # In that case, set it to GBP; user can change it, if necessary,
            # and add it to the config file
            try:
                self.currency = conf_data['currency']
            except KeyError:
                self.currency = '£'
                self.cfg.update_conf('currency', self.currency)
            
        
    def add_new(self, new_data):
        """ Add new line to csv. """
        self.csv_data += new_data
        self.modified = True
        
    def save(self):
        # save csv file
        if self.modified:
            with open(self.csvfile, 'w') as fileobj:
                fileobj.write(self.csv_data)
        return True
            
    def new_rate(self, value):
        """ Set new rate of pay. """
        # set new rate and update config file
        self.rate = str(value)
        self.cfg.update_conf('rate', self.value)
        
    def new_currency(self, value):
        """ Set new currency. """
        # set new currency and update config file
        self.currency = str(value)
        self.cfg.update_conf('currency', self.value)
    
class TimeAfterTime(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):
        
        # make sure the TimeAfterTime directory and config file exist
        check_path()

        # display last opened file
        self.get_last_opened()
            
        # get timesheet name
        self.name = self.data.name

        self.textEdit = QTextEdit(readOnly=True)
        
        # display text (as html)
        self.update_display()

        self.setCentralWidget(self.textEdit)

        self.createActions()
        self.createMenus()
        self.createToolBars()
        
        self.statusBar()
        self.statTimeout = 1000
        
        self.setWindowIcon(QIcon(''))  
        self.resize(400, 500)
        self.centre()
        
        self.show()
        
        
    def centre(self):
        """ Centre window on screen. """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        
    def get_last_opened(self):
        """ Get name of last timesheet worked on. """
        
        self.cfg_last = ConfigParser(conffile)
        
        try:
            conf_data = self.cfg_last.read_conf()
            previous = conf_data['last']
            if previous == 'None':
                previous = None
            
        except FileNotFoundError:
            previous = None
            self.cfg_last.make_conf()
        
        self.data = Data(previous)
            
        
    def update_display(self):
        """ Update text and window title """
        self.textEdit.setHtml(csv_to_html(self.data.csv_data, self.data.currency))
        self.setWindowTitle('TimeAfterTime - ' + self.name)
        if self.data.modified:
            self.statusBar().showMessage('Updated', self.statTimeout)

    def newTimesheet(self):
        """ Make a new timesheet. """
        
        # prompt save
        self.maybeSave()
        
        self.ntd = NewTimesheetDialog()
        self.ntd.show()
        self.ntd.accepted.connect(self.setTimesheet)
        
    def setTimesheet(self):
        """ Set name (internally), make new Data object and display data. """
        self.name = self.ntd.name
        self.data = Data(self.name)
        self.update_display()
        
    def addLine(self):
        """ Add line(s) to timesheet. """
        self.ald = AddLineDialog(self.data)
        self.ald.show()
        self.ald.accepted.connect(self.update_display)
        
    def removeLine(self):
        """ Remove line(s) from timesheet. """
        self.rld = RemoveLineDialog(self.data)
        self.rld.show()
        self.rld.accepted.connect(self.update_display)
            
    def editEntries(self):
        self.ed = EditLineDialog(self.data)
        self.ed.show()
        self.ed.accepted.connect(self.update_display)
        
    def open(self):
        """ Open another timesheet. """
        self.otd = OpenTimesheetDialog()
        self.otd.show()
        self.otd.accepted.connect(self.setOpenVars)
        
    def setOpenVars(self):
        """ Set parameters for this timesheet. """
        
        # this is basically the same as setTimesheet, but with different object
        # to get name from
        self.name = self.otd.selected
        self.data = Data(self.name)
        self.update_display()


    def save(self):
        # use Data's save method
        if self.data.save():
            self.statusBar().showMessage('Saved', self.statTimeout)
            
    def closeEvent(self, event):
        # save the timesheet, save the name of this timesheet to the cache and
        # close the window
        self.save()
        self.cfg_last.update_conf('last', self.name)
        event.accept()

    def export(self):
        """ Write the csv data to a file of the user's choice. """
        filename, _ = QFileDialog.getSaveFileName(self, 
                     'Export timesheet as csv', os.getcwd(), 
                     'CSV Files (*.csv);;Text Files (*.txt);;All Files (*)')
        if filename:
            self.save()
            with open(filename, 'w') as fileobj:
                fileobj.write(self.data.csv_data)
                
    def deleteTimesheet(self):
        """ Delete a timesheet """
        self.dtd = DeleteTimesheetDialog()
        self.dtd.show()
        self.dtd.accepted.connect(self.reset)
        
    def reset(self):
        if self.name in self.dtd.selected:
            self.data = Data(None)
            self.name = self.data.name
            self.cfg_last.update_conf('last', self.name)
            self.update_display()

    def about(self):
        QMessageBox.about(self, "About TimeAfterTime",
                          "Create and manage timesheets.\n"
                          "See README for more details. ")
           
    def setRate(self):
        """ Set the default rate of pay. """
        # rate is saved to Data in NewRateDialog
        self.nrd = NewRateDialog(self.data)
        self.nrd.show()
    
    def createActions(self):
                    
        self.newAct = QAction(QIcon.fromTheme('document-new'), "New", self,
                shortcut=QKeySequence.New, statusTip="Create a new timesheet",
                triggered=self.newTimesheet)

        self.openAct = QAction(QIcon.fromTheme('document-open'), "&Open...",
                self, shortcut=QKeySequence.Open,
                statusTip="Open an existing timesheet", triggered=self.open)

        self.saveAct = QAction(QIcon.fromTheme('document-save'), "&Save", self,
                shortcut=QKeySequence.Save,
                statusTip="Save the timesheet", triggered=self.save)

        self.exportAct = QAction("&Export csv", self, shortcut="Ctrl+E",
                statusTip="Export the timesheet as csv",
                triggered=self.export)

        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q",
                statusTip="Exit the application", triggered=self.close)

        self.aboutAct = QAction("&About", self,
                statusTip="Show the application's About box",
                triggered=self.about)
        
        self.addAct = QAction(QIcon.fromTheme('list-add'), "Add", self,
                shortcut=QKeySequence("N"), statusTip="Add new entries",
                triggered=self.addLine)
        
        self.removeAct = QAction(QIcon.fromTheme('list-remove'), 
                "Remove", self, shortcut=QKeySequence("C"), 
                statusTip="Remove entries", triggered=self.removeLine)
        
        self.editAct = QAction(QIcon.fromTheme(''), "Edit", self,
                shortcut=QKeySequence("E"), statusTip="Edit entries",
                triggered=self.editEntries)
        
        self.setRateAct = QAction(QIcon.fromTheme('preferences-system'), 
                "Set rate", self, shortcut=QKeySequence("R"), 
                statusTip="Set hourly rate", triggered=self.setRate)
        
        self.deleteAct = QAction("Delete", self,
                shortcut="Ctrl+D", statusTip="Delete timesheet",
                triggered=self.deleteTimesheet)


    def createMenus(self):
        
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.newAct)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.exportAct)
        self.fileMenu.addAction(self.deleteAct)
        self.fileMenu.addSeparator();
        self.fileMenu.addAction(self.exitAct)
        
        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.addAct)
        self.editMenu.addAction(self.removeAct)
        self.editMenu.addAction(self.editAct)
        self.editMenu.addAction(self.setRateAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)

    def createToolBars(self):
        
        self.fileToolBar = self.addToolBar("File")
        self.fileToolBar.addAction(self.newAct)
        self.fileToolBar.addAction(self.openAct)
        self.fileToolBar.addAction(self.saveAct)
        
        self.editToolBar = self.addToolBar("Edit")
        self.editToolBar.addAction(self.addAct)
        self.editToolBar.addAction(self.setRateAct)


    def maybeSave(self):
        if self.data.modified:
            ret = QMessageBox.warning(self, "Application",
                    "This timesheet has been modified.\nDo you want to save "
                    "your changes?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
    
            if ret == QMessageBox.Save:
                return self.save()
    
            if ret == QMessageBox.Cancel:
                return False

        return True
    

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    window = TimeAfterTime()
    sys.exit(app.exec_())
