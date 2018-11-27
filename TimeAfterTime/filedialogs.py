""" 
Supplies NewTimesheetDialog and TimesheetsFileDialog (the super class for 
OpenTimesheetDialog and DeleteTimesheetDialog).
"""

from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, 
                             QGridLayout, QLabel, QLineEdit,  QListWidget, 
                             QListWidgetItem, QMessageBox, QVBoxLayout)

import os
import re
from abc import abstractmethod
import subprocess

datapath = os.path.join(os.path.expanduser('~'), '.timeaftertime')

class NewTimesheetDialog(QDialog):
    
    def __init__(self):
        """ Make a new timesheet. """
        super().__init__()
        
        self.initUI()
        
        
    def initUI(self):
        
        # get name and default rate for the new timesheet        
        self.nameLabel = QLabel('Timesheet name:')
        self.nameEdit = QLineEdit(self)
        
        self.rateLabel = QLabel('Default rate:')
        self.rateEdit = QLineEdit(self)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.make_new)
        buttonBox.rejected.connect(self.reject)

        self.nameEdit.textChanged[str].connect(self.setName)
        self.rateEdit.textChanged[str].connect(self.setRate)

        layout = QGridLayout()
        layout.setColumnStretch(1, 1)

        row = 0
        layout.addWidget(self.nameLabel, row, 0)
        layout.addWidget(self.nameEdit, row, 1)
        
        row += 1
        layout.addWidget(self.rateLabel, row, 0)
        layout.addWidget(self.rateEdit, row, 1)
        
        row += 1
        layout.addWidget(buttonBox, row, 1)
 
        self.setLayout(layout)
        
        self.setWindowTitle('New timesheet')
        
        self.name = None
        self.rate = None
        
        
    def setName(self, text):
        self.name = text
        
    def setRate(self, text):
        self.rate = text
        
    def name_message(self):
        title = 'No name provided!'
        message = 'Please provide a name for the new timesheet.'
        QMessageBox.warning(self, title, message)
        
    def rate_message(self):
        title = 'No rate provided!'
        message = 'Please provide a default pay rate for the new timesheet.'
        QMessageBox.warning(self, title, message)
        
    def name_error(self):
        title = 'Timesheet already exists!'
        message = '''There is already a timesheet called "{}". Please provide 
another name.'''.format(self.name)
        QMessageBox.critical(self, title, message)
        
        
    def make_new(self):
        """ Make new timesheet."""
        
        # if no name has been entered, prompt the user to do so
        if self.name is None:
            self.name_message()
            
        # if no rate has been entered, prompt the user to do so
        elif self.rate is None:
            self.rate_message()
            
        else:
            self.name = re.sub('\s', '_', self.name)
            path = os.path.join(datapath, self.name)
            
            try:
                # if name does not already exist, make csv and config files
                os.mkdir(path)
                
                base = 'ts_'+self.name.lower()
                
                self.new_csv  = os.path.join(path, base+'.csv')
                self.new_conf = os.path.join(path, base+'.conf')
                
                with open(self.new_csv, 'w') as fileobj:
                    fileobj.write('Date,Duration,Activity,Rate\n')
                    
                with open(self.new_conf, 'w') as fileobj:
                    text = 'name={}\nrate={}\n'.format(self.name, self.rate)
                    fileobj.write(text)
            
                self.accept()
                
            except FileExistsError:
                # if name is already taken, get user to enter another one
                self.name_error()
                # and reset dialog
                self.initUI()

    # din't think these are actually used - now part of Data
    @property 
    def csvname(self):
        return self.new_csv
    
    @property 
    def confname(self):
        return self.new_conf
    
    
class TimesheetsFileDialog(QDialog):
    
    def __init__(self):
        """ Dialog to select timesheet(s). """
        super().__init__()
        
        self.initUI()
        
    def initUI(self):
        
        # get list of timesheets from names of directories
        timesheets = list(file for file in os.listdir(datapath) 
                     if os.path.isdir(os.path.join(datapath, file)))
        
        if len(timesheets) == 0:
            self.none_message()
            self.reject()
            self.close()
            
        else:
            # make list where only one thing can be selected
            self.timesheetList = QListWidget()
#            self.timesheetList.setSelectionMode(QAbstractItemView.SingleSelection)
            # double click or 'OK' button select that timesheet
            self.timesheetList.itemDoubleClicked.connect(self.get_selected)
            
            listWidgetItems = []
            
            # set the text in the list
            for timesheet in timesheets:
                item = QListWidgetItem(self.timesheetList)
                item.setText(timesheet)
                listWidgetItems.append(item)
                
            buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                         QDialogButtonBox.Cancel)
    
            buttonBox.accepted.connect(self.get_selected)
            buttonBox.rejected.connect(self.reject)
                
            layout = QVBoxLayout()
            layout.addWidget(self.timesheetList)
            layout.addWidget(buttonBox)
            
            self.setLayout(layout)
            
    @abstractmethod
    def get_selected(self): pass
        
    def none_message(self):
        title = 'No timesheets available!'
        message = 'There are no timesheets to show! Go and make one!'
        QMessageBox.warning(self, title, message)
        
        
class OpenTimesheetDialog(TimesheetsFileDialog):
    
    def __init__(self):
        """ Dialog to open a timesheet. """
        super().__init__()
        self.setWindowTitle('Open a timesheet')
        
        self.timesheetList.setSelectionMode(QAbstractItemView.SingleSelection)
    
    def get_selected(self):
        self.selected = self.timesheetList.selectedItems()[0].text()
        self.accept()
        
    
class DeleteTimesheetDialog(TimesheetsFileDialog):
    
    def __init__(self):
        """ Dialog to delete timesheet(s). """
        super().__init__()
        self.setWindowTitle('Delete timesheet(s)')
        self.timesheetList.setSelectionMode(QAbstractItemView.ExtendedSelection)
    
    def get_selected(self):
        self.selected = self.timesheetList.selectedItems()
        self.selected = list(item.text() for item in self.selected)
        self.confirm_message()
            
    def confirm_message(self):
        
        title = 'Confirm delete'
        message = 'This action will irreversibly delete:\n'
        for item in self.selected:
            message += '    - ' + item + '\n'
        message += 'Confirm deletion?'
        
        ret = QMessageBox.question(self, title, message)
        
        if ret == QMessageBox.Yes:
            # delete the directory for each
            for item in self.selected:
                # escape any spaces in name
                item = re.sub(' ', '\ ', item)
                path = os.path.join(datapath, item)
                subprocess.run(["rm", "-r", path])
                self.accept()

        if ret == QMessageBox.No:
            self.reject()
            
