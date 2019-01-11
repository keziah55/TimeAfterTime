""" 
Dialogs required by Timesheet when adding or removing data.
Supplies AddLineDialog, NewRateDialog, and RemoveLineDialog.
"""

from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QCompleter, QDialog, 
                             QDialogButtonBox, QGridLayout, QLabel, QLineEdit, 
                             QMessageBox, QPushButton, QRadioButton,  
                             QTableWidget, QTableWidgetItem, QVBoxLayout)
from str_to_date import str_to_date
from format_dur import format_duration
from processcsv import get_unique, head_tail
import os
import re
from abc import abstractmethod

datapath = os.path.join(os.path.expanduser('~'), '.timeaftertime')
datefmt = '%d %b %Y'

class QDialog_CTRL_Q(QDialog):
    """ QDialog subclass with CRTL+Q shortcut to close window.
    
        Standard QDialog close shortcut is ESC, which still applies here.
    """
    
    def __init__(self):
        
        super().__init__()
        
        self.exitAct = QAction("E&xit", self, 
                               shortcut="CTRL+Q",
                               statusTip="Exit the application", 
                               triggered=self.close)
        self.addAction(self.exitAct)
        

class AddLineDialog(QDialog_CTRL_Q):
    
    def __init__(self, data):
        """ Add lines to timesheet. 
            
            Parameters
            ----------
            
            data : Data object
                object which holds all the csv data
        """
        super().__init__()
        
        self.initUI(data)
        
        
    def initUI(self, data):
        
        # 'data' is the csv/config data object
        self.data = data
        
        self.newData = ''
        
        self.rows = []
        
        # message for main window status bar
        self.msg = ''
        
        # get words for QCompleter
        self.uniqact = get_unique(self.data.csv_data, 'Activity', False)
        
        self.newButton = QPushButton(QIcon.fromTheme('list-add'), '')
        self.newButton.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_N))
        self.newButton.clicked.connect(self.addLine)
        
        self.dateLabel = QLabel('Date')
        self.durLabel = QLabel('Duration ({})'.format(self.data.timebase+'s'))
        self.actLabel = QLabel('Activity')
        self.rateLabel = QLabel('Rate') 

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.set_new_values)
        buttonBox.rejected.connect(self.reject)

        self.layout = QGridLayout()
        
        self.row = 0
        
        self.layout.addWidget(self.newButton, self.row, 0)
        self.layout.addWidget(buttonBox, self.row, 1)
        
        self.row += 1

        self.layout.addWidget(self.dateLabel, self.row, 0)
        self.layout.addWidget(self.durLabel, self.row, 1)
        self.layout.addWidget(self.actLabel, self.row, 2)
        self.layout.addWidget(self.rateLabel, self.row, 3)
        
        # add lineedit objects
        self.addLine()
        
        self.setLayout(self.layout)
        
        self.setWindowTitle('Add hours')
        
        
    def makeLine(self):
        """ Make and initialise QLineEdit objects. """
        
        self.dateEdit = QLineEdit(self)
        self.durEdit = QLineEdit(self)
        self.actEdit = QLineEdit(self)
        self.rateEdit = QLineEdit(self)
        
        # display today's date and default rate
        self.dateEdit.setText((str_to_date('').strftime(datefmt)))
        self.durEdit.setText('')
        self.actEdit.setText('')
        self.rateEdit.setText(self.data.rate)
            
        # make a QCompleter for 'activity' with up-to-date info
        # if last given value of activity isn't in the completer list, add it
        if self.row > 1:    # make sure there's at least one row of QLineEdits
            # self.rows is the content from the QLineEdits
            # self.row is current row in QGridLayout
            # first entry in self.rows when self.row = 2
            prev_act = self.rows[self.row-2][2].text()
            if prev_act not in self.uniqact:
                self.uniqact.append(prev_act)
                
        # make completer with uniqact for actEdit
        self.completer(self.uniqact, self.actEdit)

        return (self.dateEdit, self.durEdit, self.actEdit, self.rateEdit)
            
    def addLine(self):
        """ Add new line to Dialog """
        
        # make new row
        fields = self.makeLine()
        # keep all rows in a list, so their contents can be accessed
        self.rows.append(fields)
        # unpack QLineEdits
        da, du, a, r = fields
        
        # increment row
        self.row += 1
        
        self.layout.addWidget(da, self.row, 0)
        self.layout.addWidget(du, self.row, 1)
        self.layout.addWidget(a, self.row, 2)
        self.layout.addWidget(r, self.row, 3)
        
    def completer(self, lst, edit):
        comp = QCompleter(lst)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        edit.setCompleter(comp)
        
    def update_completer(self, new, lst, edit):
        if new not in lst:
            lst += new
            print(lst)
            self.completer(lst, edit)
        
    def set_new_values(self):
        """ Put new csv data into Data object. """
        
        self.newData = ''

        # if there's an error anywhere in the entry, it can't be accepted
        valid = True
        
        # get text from every QLineEdit
        for row in self.rows:
            
            line = [field.text() for field in row]
            
            # format date and duration
            # catch any exception thrown if the value entered cannot be parsed
            try:
                line[0] = str(str_to_date(line[0]))
            except ValueError:
                self.invalid_value_message(line[0])
                valid = False
                
            # if time base is hours, format the string accordingly
            if self.data.timebase == 'hour':
                try:
                    line[1] = format_duration(line[1])
                except ValueError:
                    self.invalid_value_message(line[1])
                    valid = False
            # otherwise (time base is days), as long as it can be a float,
            # everything's fine
            else:
                try:
                    float(line[1])
                except ValueError:
                    self.invalid_value_message(line[1])
                    valid = False
            
            try:
                line = ','.join(line)
                self.newData += line + '\n'
            except TypeError:
                self.empty_value_message(line)
            
        if valid:
            self.data.add_new(self.newData)
            self.accept()
        
    def empty_value_message(self, line):
        title = 'Could not add line!'
        message = 'Empty fields in entry. This line will not be added.'
        QMessageBox.warning(self, title, message)
        
    def invalid_value_message(self, value):
        title = 'Could not add line!'
        message = "'{}' contains an invalid value.".format(value)
        QMessageBox.warning(self, title, message)
        
        
class TableLineDiaolg(QDialog_CTRL_Q):
    
    def __init__(self, data):
        """ Base class for displaying the timesheet as a table for editing.
        
            Implementations of `customise()` and `apply_changes()` will need
            to be provided.
            You may wish to set `self.explain.setText()` and 
            `self.setWindowTitle()` in `customise()`.
        
            Parameters
            ----------
            data : Data object
                object which holds all the csv data
        """
        super().__init__()
        
        self.initUI(data)
        
        self.customise()
        
    def initUI(self, data):
        
        self.data = data
        
        header, self.csv_data = head_tail(self.data.csv_data)
        
        # display most recent csv_data at top
        self.csv_data.reverse()
        
        self.num_rows = len(self.csv_data)
        self.num_cols = len(header)

        # make table
        self.table = QTableWidget(self.num_rows, self.num_cols)
        # remove numbers from rows
        self.table.verticalHeader().setVisible(False)
        # set headers
        self.table.setHorizontalHeaderLabels(header)

        # put data in table
        for row, data in enumerate(self.csv_data):
            
            date, dur, act, rate = data.split(',')
            
            item0 = QTableWidgetItem(date)
            item1 = QTableWidgetItem(dur)
            item2 = QTableWidgetItem(act)
            item3 = QTableWidgetItem(rate)
            self.table.setItem(row, 0, item0)
            self.table.setItem(row, 1, item1)
            self.table.setItem(row, 2, item2)
            self.table.setItem(row, 3, item3)
            
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.apply_changes)
        buttonBox.rejected.connect(self.reject)
        
        for i in range(self.num_rows):
           self.table.setColumnWidth(i, 110)
        
        # for some reason, self.table.width() returns a number larger than
        # it should be
        width = (self.num_cols + 0.1) * self.table.columnWidth(0)
        
        # exaplin how this window works
        # self.explain.setText() should be applied in the derived classes
        self.explain = QLabel(wordWrap=True)
        self.explain.setMinimumWidth(width)
        self.explain.setText('')
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.explain)
        self.layout.addWidget(self.table)
        self.layout.addWidget(buttonBox)

        self.resize(width, 400)
        
        self.setLayout(self.layout)
        
        self.setWindowTitle('Table dialog')
    
    @abstractmethod    
    def customise(self): pass
    
    @abstractmethod
    def apply_changes(self): pass
    

        
class RemoveLineDialog(TableLineDiaolg):
    
    def __init__(self, data):
        """ Remove lines from the timesheet.
        
            Parameters
            ----------
            data : Data object
                object which holds all the csv data
        """
        super().__init__(data)

    def customise(self):
        # only select rows
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        self.explain.setText('Select rows and click "OK" to remove them from '
                             'the timesheet.\nThis cannot be undone, so please '
                             'be careful!')
        
        self.setWindowTitle('Remove entries')
        
    def apply_changes(self):
        """ Remove selected rows from the timesheet. """
        self.selected = self.table.selectedItems()
        
        rows = set(item.row() for item in self.selected)
        
        for idx in rows:
            row = self.csv_data[idx]
            self.data.csv_data = re.sub(row, '', self.data.csv_data)
            self.data.modified = True

        self.accept()
        
        
class EditLineDialog(TableLineDiaolg):
    
    def __init__(self, data):
        """ Edit lines in the timesheet.
        
            Parameters
            ----------
            data : Data object
                object which holds all the csv data
        """
        super().__init__(data)
        
    def customise(self):
        
        self.explain.setText('Edit rows in the timesheet.')
        self.setWindowTitle('Edit entries')

    def apply_changes(self):
        # check every row in the table against the csv data 
        # if different, overwrite the csv row
        
        for row in range(self.num_rows):
            
            trow = ','.join([self.table.item(row, col).text() 
                             for col in range(self.num_cols)])
    
            drow = self.csv_data[row]
            
            if trow != drow:
                self.data.csv_data = re.sub(drow, trow, self.data.csv_data)
                self.data.modified = True
            
        self.accept()
        

class NewRateDialog(QDialog_CTRL_Q):
    
    def __init__(self, data):
        """ Change the default rate of pay.
        
            Parameters
            ----------
            data : Data object
                object which holds all the csv data
        """
        super().__init__()
        
        self.initUI(data)
        
    def initUI(self, data):
        
        self.data = data
        
        # rate of pay
        rateLabel = QLabel('Default rate of pay:')
        rateLabel.setAlignment(Qt.AlignRight)
        self.rateEdit = QLineEdit(self)
        self.rateEdit.setText(self.data.rate)
        self.rateEdit.selectAll()
        
        # time base
        timeLabel = QLabel('per')
        self.dayButton = QRadioButton('day')
        self.hourButton = QRadioButton('hour')
        
        # if timebase is already set, check the right button
        if self.data.timebase == 'hour':
            self.hourButton.setChecked(True)
        # else, default to day
        else:
            self.dayButton.setChecked(True)
            
        radioLayout = QVBoxLayout()
        radioLayout.addWidget(self.dayButton)
        radioLayout.addWidget(self.hourButton)
        
        # currency
        currencyLabel = QLabel('Currency:')
        currencyLabel.setAlignment(Qt.AlignRight)
        self.currencyEdit = QLineEdit(self)
        self.currencyEdit.setText(self.data.currency)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.saveChanges)
        buttonBox.rejected.connect(self.reject)

        editLayout = QGridLayout()
        
        row = 0
        editLayout.addWidget(rateLabel, row, 0)
        editLayout.addWidget(self.rateEdit, row, 1)
        editLayout.addWidget(timeLabel, row, 2)
        editLayout.addLayout(radioLayout, row, 3)
        
        row += 1
        editLayout.addWidget(currencyLabel, row, 0)
        editLayout.addWidget(self.currencyEdit, row, 1)
        
        layout = QVBoxLayout()
        layout.addLayout(editLayout)
        layout.addWidget(buttonBox)
 
        self.setLayout(layout)
        
        self.setWindowTitle('Set default rate of pay')

        
    def saveChanges(self):
        # apply changes to Data object; raise error message if there is invalid
        # data in 'rate' or 'currency'
        
        valid = True
        
        # set rate
        rate = self.rateEdit.text().strip()
        if rate:
            self.data.new_rate(rate)
        else:
            self.error_message('rate of pay')
            valid = False
            
        # set time base
        if self.dayButton.isChecked():
            self.data.new_timebase('day')
        else:
            self.data.new_timebase('hour')
            
        # set currency
        curr = self.currencyEdit.text().strip()
        if curr:
            self.data.new_currency(curr)
        else:
            self.error_message('currency')
            valid = False
            
        if valid:
            self.accept()
            
        
    def error_message(self, which):
        title = 'No {} provided!'.format(which)
        message = 'Please provide a {} for the new timesheet.'.format(which)
        QMessageBox.warning(self, title, message)
        