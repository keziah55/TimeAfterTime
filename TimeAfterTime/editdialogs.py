""" 
Dialogs required by Timesheet when adding or removing data.
Supplies AddLineDialog, NewRateDialog, and RemoveLineDialog.
"""

from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QCompleter, QDialog, 
                             QDialogButtonBox, QGridLayout, QGroupBox, 
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout)
from str_to_date import str_to_date
from format_dur import format_duration
from processcsv import get_unique, head_tail
import os
import re
import abc

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
    
    def __init__(self, data, columnLabels):
        """ Add lines to timesheet. 
            
            Parameters
            ----------
            
            data : Data object
                object which holds all the csv data
                
            columnLabels : list
                list of columns headers
        """
        super().__init__()
        
        self.initUI(data, columnLabels)
        
        
    def initUI(self, data, columnLabels):
        
        # 'data' is the csv/config data object
        self.data = data
        
        self.newData = ''
        
        self.rows = []
        
        # message for main window status bar
        self.msg = ''
        
        # get words for QCompleter
        self.uniqact = get_unique(self.data.csv_data, 'Activity', False)
        
        editButtonSize = 65
        
        newButton = QPushButton(QIcon.fromTheme('list-add'), '')
        newButton.setMinimumWidth(editButtonSize)
        newButton.setShortcut("CTRL+N")
        newButton.clicked.connect(self.addLine)
        
        # set labels
        labels = tuple(QLabel(label) for label in columnLabels)
        
        # get number of columns
        self.ncols = len(labels)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.set_new_values)
        buttonBox.rejected.connect(self.reject)

        # make GroupBox for new, ok and cancel buttons
        groupBoxBtn = QGroupBox()
        # don't draw a frame
        groupBoxBtn.setFlat(True)
        
        # make HBoxLayout and add the buttons
        dialogBtnBox = QHBoxLayout()
        dialogBtnBox.addWidget(newButton)
        dialogBtnBox.addWidget(buttonBox)
        
        # put the HBox in the GroupBox
        groupBoxBtn.setLayout(dialogBtnBox)
        groupBoxBtn.setFixedSize(330,50)
        
        # make GroupBox for the line labels and edit boxes
        groupBoxEdit = QGroupBox()
        # don't draw a frame
        groupBoxEdit.setFlat(True)
        
        # make GridLayout and add the labels
        self.editGrid = QGridLayout()
        # have class member for row, so that new rows can be added on the fly
        self.row = 0
        # put labels in Grid
        for n in range(self.ncols):
            self.editGrid.addWidget(labels[n], self.row, n)

        # put the GridLayout in the GroupBox
        groupBoxEdit.setLayout(self.editGrid)

        # overall dialog layout is VBox
        layout = QVBoxLayout()
        # add the GroupBoxes to the VBox
        layout.addWidget(groupBoxBtn)
        layout.addWidget(groupBoxEdit)
        
        # add LineEdit objects
        self.addLine()
        
        # set the VBox as the layout
        self.setLayout(layout)
        
        self.setWindowTitle('Add hours')
        
        
    def makeLine(self):
        """ Make and initialise QLineEdit objects. """
        
        edits = list(QLineEdit(self) for n in range(self.ncols))
        
        # display today's date and default rate
        # set today's set in the Date column
        edits[0].setText(str_to_date('').strftime(datefmt))
        edits[3].setText(self.data.rate)
            
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
        self.completer(self.uniqact, edits[2])

        return tuple(edits)
            
    def addLine(self):
        """ Add new line to Dialog """
        
        # make new row
        fields = self.makeLine()
        # keep all rows in a list, so their contents can be accessed
        self.rows.append(fields)
        
        # increment row
        self.row += 1
        
        for n in range(self.ncols):
            self.editGrid.addWidget(fields[n], self.row, n)
            
        
    def completer(self, lst, edit):
        comp = QCompleter(lst)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        edit.setCompleter(comp)
        
    def update_completer(self, new, lst, edit):
        if new not in lst:
            lst += new
            self.completer(lst, edit)
        
    def set_new_values(self):
        """ Put new csv data into Data object. """
        
        self.newData = ''
        
        error = False
        
        # get text from every QLineEdit
        for row in self.rows:
            
            line = [field.text() for field in row]
            
            # format date and duration
            # catch any exception thrown if the value entered cannot be parsed
            try:
                line[0] = str(str_to_date(line[0]))
            except ValueError:
                self.invalid_value_message(line[0])
                error = True
                
            try:
                line[1] = format_duration(line[1])
            except ValueError:
                self.invalid_value_message(line[1])
                error = True
            
            try:
                line = ','.join(line)
                self.newData += line + '\n'
            except TypeError:
                self.empty_value_message(line)
            
        if not error:
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
    
    __metaclass__ = abc.ABCMeta
    
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
    
    @abc.abstractmethod    
    def customise(self): pass
    
    @abc.abstractmethod
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
        
        self.rateLabel = QLabel('Default rate (£):')
        self.rateEdit = QLineEdit(self)
        self.rateEdit.setText(self.data.rate)
        self.rateEdit.selectAll()
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | 
                                     QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.saveRate)
        buttonBox.rejected.connect(self.reject)

        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        
        row = 0
        layout.addWidget(self.rateLabel, row, 0)
        layout.addWidget(self.rateEdit, row, 1)
        
        row += 1
        layout.addWidget(buttonBox, row, 1)
 
        self.setLayout(layout)
        
        self.setWindowTitle('Set default rate')

        
    def saveRate(self):
        self.data.new_rate(self.rateEdit.text())
        self.accept()
        