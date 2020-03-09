import sys
from .hgbcore import HGBCore
from .hgbcli import HGBCLI
from .hgbgui import HGBGUI
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

def main():
    hgbcore = HGBCore()
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == 'hidden'):
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon.fromTheme('task-due'))

        hgbgui = HGBGUI(hgbcore)
        if len(sys.argv) == 1:
            hgbgui.show()

        app.exec_()
    else:
        hgbcli = HGBCLI(hgbcore)
        hgbcli.parse_command_line(sys.argv)

if __name__ == '__main__':
    main()