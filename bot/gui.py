#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os
import json
from PyQt5.QtCore import (QSettings, Qt)
from PyQt5.QtGui import (QStandardItemModel, QStandardItem)
from PyQt5.QtWidgets import (QMainWindow, QAction, QWidget, QGridLayout, qApp,
                             QApplication, QTreeView, QTabWidget, QFileDialog,
                             QSplitter)

class PoGoBotManager(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUI()

    def loadBotConfigDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', os.path.expanduser("~"))
        if fname[0]:
            settings = QSettings(QSettings.UserScope, 'PoGoBotManager')
            settings.beginGroup('BotConfigs')
            configs = settings.value('Configs')
            if configs == None:
                configs = {}
            with open(fname[0], 'r') as f:
                configs[fname[0]] = json.loads(f.read())
            settings.setValue('Configs', configs)
            settings.endGroup()

    def initUI(self):
        loadBotAction = QAction('&Load', self)
        loadBotAction.setShortcut('Ctrl+L')
        loadBotAction.setStatusTip('Load bot')
        loadBotAction.triggered.connect(self.loadBotConfigDialog)

        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(loadBotAction)
        fileMenu.addAction(exitAction)

        botTree = QTableView()
        botTreeModel = QStandardItemModel()
        rootNode = botTreeModel.invisibleRootItem()
        settings = QSettings(QSettings.UserScope, 'PoGoBotManager')
        settings.beginGroup('BotConfigs')
        configs = settings.value('Configs')
        for f,d in configs.items():
            item = QStandardItem(f)
            rootNode.appendRow(item)
        settings.endGroup()
        botTree.setModel(botTreeModel)

        botInfoMap = QWidget()
        botInfoPokemon = QWidget()
        botInfoInventory = QWidget()
        botInfoLog = QWidget()
        botInfo = QTabWidget()
        botInfo.addTab(botInfoMap, "Map")
        botInfo.addTab(botInfoPokemon, "Pokemon")
        botInfo.addTab(botInfoInventory, "Inventory")
        botInfo.addTab(botInfoLog, "Log")

        splitter1 = QSplitter(Qt.Horizontal)
        splitter1.addWidget(botTree)
        splitter1.addWidget(botInfo)

        grid = QGridLayout()
        grid.addWidget(splitter1, 0, 0)

        cw = QWidget()
        cw.setLayout(grid)

        self.setCentralWidget(cw)

        self.setGeometry(300, 300, 1200, 400)
        self.setWindowTitle('PoGo Bot Manager')
        self.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    mgr = PoGoBotManager()
    sys.exit(app.exec_())
