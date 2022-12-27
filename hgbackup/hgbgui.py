import os
import sys
import subprocess
from datetime import datetime
from io import BytesIO as StringIO
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, GLib
from gi.repository import AppIndicator3 as AppIndicator
from gi.repository import Notify

from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QVBoxLayout,
                             QHBoxLayout, QPushButton, QProgressDialog,
                             QTextEdit, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt5.QtGui import QPalette, QFont

try:
    from PyQt5.QtCore import QString
except ImportError:
    QString = str

class ReadOnlyConsole(QTextEdit):
    data = ""
    newdata = False

    def __init__(self, parent=None):
        super(ReadOnlyConsole, self).__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont()
        font.setFamily(u"DejaVu Sans Mono")
        font.setPointSize(10)
        self.setFont(font)
        p = self.palette()
        p.setColor(QPalette.Base, Qt.black)
        p.setColor(QPalette.Text, Qt.white)
        self.setPalette(p)

        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)
        self.timer.setInterval(200)
        self.timer.start()

    def timeout(self):
        if self.newdata:
            self.setText(self.data)
            sb = self.verticalScrollBar()
            sb.setValue(sb.maximum())
            self.newdata = False

    @pyqtSlot(str)
    def write(self, data):
        self.newdata = True
        self.data += data.replace('\r', '')
        self.data = self.data[-5000:]

class WorkerThread(QThread):
    new_console_data = pyqtSignal(QString)
    new_progress = pyqtSignal(str, int)
    set_progress = pyqtSignal(int)
    done_progress = pyqtSignal()
    done_backup = pyqtSignal()
    done_verify = pyqtSignal()
    fn = None
    args = None
    kwargs = None

    def __init__(self, console, parent=None):
        super(WorkerThread, self).__init__(parent)
        # set up console
        self.console = console
        self.new_console_data[QString].connect(self.console.write)

    def execute(self, fn, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        std_sav = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = sio = StringIO()
        sio.write = self.new_console_data.emit

        self.fn(*self.args, **self.kwargs)

        sys.stdout, sys.stderr = std_sav
        sio.close()

class HGBGUI(QMainWindow):
    quit = False

    def __init__(self, hgbcore, *args, **kwargs):
        super(HGBGUI, self).__init__(*args, **kwargs)

        self.hgbcore = hgbcore

        self.setWindowTitle("HGBackup")
        self.setGeometry(100, 100, 1024, 768)

        # set up table for targets
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setRowCount(len(self.hgbcore.config['targets']))
        self.table.setColumnCount(6)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["name", "src", "dst", "connected", "last_backup", "last_check"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.currentCellChanged.connect(self.onCellChanged)

        # set up buttons
        self.btnBackup = QPushButton("Backup")
        self.menuBackup = QMenu()
        self.menuBackup.addAction("Backup", self.run_backup)
        self.menuBackup.addAction("Backup (full)", self.runfull_backup)
        self.menuBackup.addAction("Dry run", self.dryrun_backup)
        self.menuBackup.addAction("Dry run (full)", self.dryrunfull_backup)
        self.btnBackup.setMenu(self.menuBackup)
        self.btnCheck = QPushButton("Check verification dictionary")
        self.btnCheck.clicked.connect(self.check_backup)
        self.btnRepair = QPushButton("Repair verification dictionary")
        self.btnRepair.clicked.connect(self.repair_verdict)
        self.btnVerify = QPushButton("Verify")
        self.btnVerify.clicked.connect(self.verify_backup)
        self.btnConfig = QPushButton("Open configuration file")
        self.btnConfig.clicked.connect(self.open_config_file)
        # disable these buttons on startup (in case no targets are defined)
        for btn in [self.btnBackup, self.btnCheck, self.btnRepair, self.btnVerify]:
            btn.setEnabled(False)

        # set up console and worker thread
        self.readonlyconsole = ReadOnlyConsole()
        self.wt = WorkerThread(self.readonlyconsole, parent=self)
        self.hgbcore.thread = self.wt
        self.wt.done_backup.connect(self.done_backup)
        self.wt.done_verify.connect(self.done_verify)
        # make sure that signals from the worker thread are dealt with consecutively
        # (e.g. that the set_progress_handler for 100% and the done_progress_handler
        # are not executed simultaneously, which can lead to undesired behaviour)
        # c.f. https://doc.qt.io/qt-5/threads-qobject.html
        # and  https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html
        t = Qt.BlockingQueuedConnection
        # make connections
        self.wt.new_progress.connect(self.new_progress_handler, type=t)
        self.wt.set_progress.connect(self.set_progress_handler, type=t)
        self.wt.done_progress.connect(self.done_progress_handler, type=t)

        # set up layout
        l2 = QHBoxLayout()
        for w in [self.btnBackup, self.btnCheck, self.btnRepair, self.btnVerify, self.btnConfig]:
            l2.addWidget(w)
        l = QVBoxLayout()
        l.addWidget(self.table)
        l.addLayout(l2)
        l.addWidget(self.readonlyconsole)
        cw = QWidget()
        cw.setLayout(l)
        self.setCentralWidget(cw)                

        # populate table with targets
        for i, (name, target) in enumerate(self.hgbcore.config['targets'].items()):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(target['src']))
            self.table.setItem(i, 2, QTableWidgetItem(target['dst']))
            self.table.setItem(i, 3, QTableWidgetItem(''))
            self.table.setItem(i, 4, QTableWidgetItem(target['last_backup']))
            self.table.setItem(i, 5, QTableWidgetItem(target['last_check']))
            self.table.selectRow(0)
            self.update_target_connection(i, name, target) 

        # set up target watcher
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.folder_watcher)
        self.timer.start()

        # set up periodicity watcher
        self.timer2 = QTimer()
        self.timer2.setInterval(10000)
        self.timer2.timeout.connect(self.periodicity_watcher)
        self.timer2.start()

        # set up notifications
        Notify.init("HGBackup")

        # set up app indicator
        self.ind = AppIndicator.Indicator.new(
                    "indicator-autosync",
                    "task-due",
                    AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
        
        # need to set this for indicator to be shown
        self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        # have to give indicator a menu
        self.menu = Gtk.Menu()

        # build menu
        item = Gtk.MenuItem()
        item.set_label("Show")
        item.connect("activate", self.handler_menu_show)
        item.show()
        self.menu.append(item)

        item = Gtk.MenuItem()
        item.set_label("Quit")
        item.connect("activate", self.handler_menu_exit)
        item.show()
        self.menu.append(item)

        self.menu.show()
        self.ind.set_menu(self.menu)

    def new_progress_handler(self, label, length):
        # set up progress dialog
        self.progress = QProgressDialog(self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setWindowTitle("Working...")
        self.progress.setLabelText(label+"...")
        self.progress.setMinimumDuration(0)
        self.progress.setAutoReset(False)
        # as long as cancelling is not implemented, remove the close button and the cancel button
        self.progress.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.progress.setCancelButton(None)
        self.progress.reset()           # kill the initial 4 second timer (c.f. https://doc.qt.io/qt-5/qprogressdialog.html)

        if length == 1:         # only one element
            self.progress.setMaximum(0)
            self.ind.set_icon(os.path.join(os.path.dirname(__file__), 'pie', 'unknown.png'))
        else:
            self.progress.setMaximum(100)
            self.ind.set_icon(os.path.join(os.path.dirname(__file__), 'pie', '0.png'))
        self.progress.setValue(0)       

    def set_progress_handler(self, value):
        if value not in range(101):
            raise Exception("Invalid progress value")
        self.progress.setValue(value)
        self.ind.set_icon(os.path.join(os.path.dirname(__file__), 'pie', '{}.png'.format(value)))

    def done_progress_handler(self):
        self.progress.reset()
        self.ind.set_icon("task-due")

    def closeEvent(self, evt):
        if not self.quit:
            self.hide()
            evt.ignore()

    def handler_menu_show(self, evt):
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()

    def handler_menu_exit(self, evt):
        self.quit = True
        self.close()

    def onCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        self.update_buttons()

    def get_current_target(self):
        targetname = self.table.item(self.table.currentRow(), 0).text()
        return self.hgbcore.config['targets'][targetname]     

    def run_backup(self):
        self.wt.execute(self.hgbcore.run_backup, self.get_current_target())
    
    def dryrun_backup(self):
        self.wt.execute(self.hgbcore.run_backup, self.get_current_target(), dry=True)

    def runfull_backup(self):
        self.wt.execute(self.hgbcore.run_backup, self.get_current_target(), full=True)
    
    def dryrunfull_backup(self):
        self.wt.execute(self.hgbcore.run_backup, self.get_current_target(), dry=True, full=True)
    
    def done_backup(self):
        self.table.item(self.table.currentRow(), 4).setText(self.get_current_target()['last_backup'])

    def check_backup(self):
        self.wt.execute(self.hgbcore.check_verdict, self.get_current_target())

    def repair_verdict(self):
        self.wt.execute(self.hgbcore.check_verdict, self.get_current_target(), repair=True)

    def verify_backup(self):
        self.wt.execute(self.hgbcore.verify_backup, self.get_current_target())

    def done_verify(self):
        self.table.item(self.table.currentRow(), 5).setText(self.get_current_target()['last_check'])

    def update_buttons(self):
        target = self.get_current_target()
        enable = False
        if target['dst_connected']:
            enable = True
        for btn in [self.btnBackup, self.btnCheck, self.btnRepair, self.btnVerify]:
            btn.setEnabled(enable)

    def update_target_connection(self, i, name, target):
        status, toggle = self.hgbcore.update_target_connection(target)
        if status:
            self.table.item(i, 3).setText('ready')
            self.table.item(i, 3).setBackground(Qt.green)
        else:
            self.table.item(i, 3).setText('N/A')
            self.table.item(i, 3).setBackground(Qt.red)
        self.update_buttons()
        return status, toggle

    def folder_watcher(self):
        for i, (name, target) in enumerate(self.hgbcore.config['targets'].items()):
            status, toggle = self.update_target_connection(i, name, target)
            if not toggle:     # status did not change
                continue
            Notify.Notification.new("HGBackup target {} {}connected.".format(name, "" if status else "dis")).show()

    def periodicity_watcher(self):
        for i, (name, target) in enumerate(self.hgbcore.config['targets'].items()):
            if target['per_backup'] is not None and target['last_backup'] is not None:
                last_backup = datetime.strptime(target['last_backup'], "%Y-%m-%d_%H:%M:%S")
                days = (datetime.now()-last_backup).days
                notified = 'notified_backup' in target and target['notified_backup'] == datetime.now().date()
                if days > target['per_backup'] and not notified:
                    Notify.Notification.new("HGBackup target {} has to be backed up. Last back up {} days ago.".format(name, days)).show()
                    target['notified_backup'] = datetime.now().date()
            if target['per_check'] is not None and target['last_check'] is not None:
                last_check = datetime.strptime(target['last_check'], "%Y-%m-%d_%H:%M:%S")
                days = (datetime.now()-last_check).days
                notified = 'notified_check' in target and target['notified_check'] == datetime.now().date()
                if days > target['per_check'] and not notified:
                    Notify.Notification.new("HGBackup target {} has to be verified. Last verification {} days ago.".format(name, days)).show()
                    target['notified_check'] = datetime.now().date()

    def open_config_file(self):
        subprocess.call(['code', self.hgbcore.config_file])