import os
import sys
import threading
import time
import logging
import pathlib
import urllib
import math

from PyQt6 import uic, QtGui, QtWidgets, QtCore
import pandas as pd
import pyqtgraph
from apscheduler.schedulers.background import BlockingScheduler
import black

from widget.ask_popup import AskPopup
from widget.setup_area import SetupArea
from widget.guide_frame import GuideFrame
from widget.license_area import LicenseArea
from worker.manager import Manager
from worker.collector import Collector
from worker.transactor import Transactor
from worker.simulator import Simulator
from worker.strategist import Strategiest
from instrument.thread_pool_executor import ThreadPoolExecutor
from instrument.percent_axis_item import PercentAxisItem
from instrument.telephone import Telephone
from instrument.api_streamer import ApiStreamer
from instrument.api_requester import ApiRequester
from instrument.log_handler import LogHandler
from instrument.syntax_highlighter import SyntaxHighlighter
from recipe import outsource
from recipe import check_internet
from recipe import process_toss
from recipe import thread_toss
from recipe import standardize
from recipe import find_goodies


class Window(QtWidgets.QMainWindow, uic.loadUiType("./resource/user_interface.ui")[0]):
    def closeEvent(self, event):  # noqa:N802

        event.ignore()

        def job():

            if not self.should_finalize:
                self.closeEvent = lambda e: e.accept()
                self.undertake(self.close, True)

            if self.should_confirm_closing:

                question = [
                    "정말 종료하시겠어요?",
                    "쏠쏠을 켜 두지 않으면 실시간 데이터 기록이 되지 않습니다. 종료를 선택하면 데이터를 저장하고 통신을 닫는 마무리"
                    " 절차가 수행됩니다.",
                    ["취소", "종료"],
                ]
                answer = self.ask(question)

                if answer in (0, 1):
                    return

            total_steps = len(self.finalize_functions)
            done_steps = 0

            self.undertake(lambda: self.gauge.hide(), True)
            self.undertake(lambda: self.board.hide(), True)
            self.closeEvent = lambda e: e.ignore()

            guide_frame = None

            def job():
                nonlocal guide_frame
                text = "마무리하는 중입니다."
                guide_frame = GuideFrame(text, total_steps)
                self.centralWidget().layout().addWidget(guide_frame)

            self.undertake(job, True)

            def job():
                while True:
                    if done_steps == total_steps:
                        time.sleep(1)
                        text = "완료되었습니다."
                        self.undertake(lambda t=text: guide_frame.change_text(t), True)
                        self.undertake(lambda: guide_frame.change_steps(0), True)
                        time.sleep(1)
                        text = "업데이트 확인 중입니다."
                        self.undertake(lambda t=text: guide_frame.change_text(t), True)
                        time.sleep(1)
                        if find_goodies.check():
                            text = "업데이트가 있습니다."
                            self.undertake(
                                lambda t=text: guide_frame.change_text(t), True
                            )
                            time.sleep(1)
                            text = "업데이트를 준비하고 있습니다."
                            self.undertake(
                                lambda t=text: guide_frame.change_text(t), True
                            )
                            time.sleep(1)
                            find_goodies.apply()
                            text = "업데이트가 준비되었습니다. 종료 후 자동으로 설치됩니다."
                            self.undertake(
                                lambda t=text: guide_frame.change_text(t), True
                            )
                            time.sleep(1)
                        else:
                            text = "업데이트가 없습니다."
                            self.undertake(
                                lambda t=text: guide_frame.change_text(t), True
                            )
                            time.sleep(1)
                        process_toss.terminate_pool()
                        self.closeEvent = lambda e: e.accept()
                        self.undertake(self.close, True)
                    else:
                        time.sleep(0.1)

            thread_toss.apply_async(job)

            self.scheduler.remove_all_jobs()
            self.scheduler.shutdown()
            ApiStreamer.close_all_forever()

            def job(function):
                nonlocal done_steps
                function()
                done_steps += 1
                self.undertake(lambda d=done_steps: guide_frame.progress(d), True)

            thread_toss.map(job, self.finalize_functions)

        thread_toss.apply_async(job)

    def __init__(self):

        super().__init__()
        self.setupUi(self)

        # ■■■■■ package global settings ■■■■■

        os.get_terminal_size = lambda *args: os.terminal_size((72, 80))
        pd.set_option("display.precision", 3)
        pd.set_option("display.min_rows", 20)
        pd.set_option("display.max_rows", 20)
        pyqtgraph.setConfigOptions(antialias=True)

        # ■■■■■ monkey-patching packages ■■■■■

        original_key_press_event = QtWidgets.QPlainTextEdit.keyPressEvent

        def job(self, event):
            should_indent = event.key() == QtCore.Qt.Key.Key_Tab
            should_dedent = event.key() == QtCore.Qt.Key.Key_Backtab
            if should_indent or should_dedent:
                scroll_position = self.verticalScrollBar().value()
                text = self.toPlainText()
                text_cursor = self.textCursor()
                start_character = text_cursor.selectionStart()
                end_character = text_cursor.selectionEnd()
                start_line = text[:start_character].count("\n")
                end_line = text[:end_character].count("\n")
                each_lines = text.split("\n")
                for line_number in range(start_line, end_line + 1):
                    if should_indent:
                        this_line = each_lines[line_number]
                        each_lines[line_number] = "    " + this_line
                    elif should_dedent:
                        for _ in range(4):
                            this_line = each_lines[line_number]
                            if len(this_line) > 0 and this_line[0] == " ":
                                each_lines[line_number] = this_line[1:]
                text = "\n".join(each_lines)
                self.setPlainText(text)
                newline_positions = [
                    turn for turn, char in enumerate(text) if char == "\n"
                ]
                line_start_positions = [item + 1 for item in newline_positions]
                line_start_positions.insert(0, 0)
                line_end_positions = [item - 0 for item in newline_positions]
                line_end_positions.append(len(text))
                if start_line == end_line:
                    text_cursor.setPosition(line_end_positions[end_line])
                else:
                    select_from = line_start_positions[start_line]
                    text_cursor.setPosition(select_from)
                    select_to = line_end_positions[end_line]
                    text_cursor.setPosition(
                        select_to, QtGui.QTextCursor.MoveMode.KeepAnchor
                    )
                self.setTextCursor(text_cursor)
                self.verticalScrollBar().setValue(scroll_position)
                return
            return original_key_press_event(self, event)

        QtWidgets.QPlainTextEdit.keyPressEvent = job

        original_focus_out_event = QtWidgets.QPlainTextEdit.focusOutEvent

        def job(self, event):
            # apply black formatter style
            scroll_position = self.verticalScrollBar().value()
            text = self.toPlainText()
            try:
                text = black.format_str(text, mode=black.FileMode())
                self.setPlainText(text)
            except black.InvalidInput:
                pass
            self.verticalScrollBar().setValue(scroll_position)
            # run original function as well
            return original_focus_out_event(self, event)

        QtWidgets.QPlainTextEdit.focusOutEvent = job

        # ■■■■■ basic display configuration ■■■■■

        self.resize(0, 0)  # to smallest size possible

        fixed_width_font = QtGui.QFont("Consolas", 9)
        self.listWidget.setFont(fixed_width_font)
        self.plainTextEdit.setFont(fixed_width_font)
        self.plainTextEdit_2.setFont(fixed_width_font)
        self.plainTextEdit_3.setFont(fixed_width_font)
        SyntaxHighlighter(self).setDocument(self.plainTextEdit.document())
        SyntaxHighlighter(self).setDocument(self.plainTextEdit_2.document())
        SyntaxHighlighter(self).setDocument(self.plainTextEdit_3.document())

        self.splitter.setSizes([3, 1, 1, 2])
        self.splitter_2.setSizes([3, 1, 1, 2])

        # ■■■■■ app closing settings ■■■■■

        self.should_finalize = False
        self.should_confirm_closing = True

        # ■■■■■ hide the main widgets and go on to boot phase ■■■■■

        self.gauge.hide()
        self.board.hide()
        thread_toss.apply_async(self.boot)

    def boot(self):

        # ■■■■■ start monitoring the internet ■■■■■

        check_internet.start_monitoring()

        # ■■■■■ check system status ■■■■■

        while not check_internet.connected():
            question = [
                "인터넷에 연결되어 있지 않습니다.",
                "쏠쏠이 켜지려면 인터넷 연결이 반드시 필요합니다.",
                ["확인"],
            ]
            self.ask(question)
            time.sleep(1)

        # ■■■■■ check license key ■■■■■

        if standardize.get_license_key() is None:

            license_area = None

            # add temporary widget
            def job():
                nonlocal license_area
                license_area = LicenseArea(self)
                self.centralWidget().layout().addWidget(license_area)

            self.undertake(job, True)

            license_area.done_event.wait()

            # remove temporary widget
            def job():
                license_area.setParent(None)

            self.undertake(job, True)

        # ■■■■■ check data folder ■■■■■

        if standardize.get_datapath() is None:

            datapath = ""

            def job():
                nonlocal datapath
                file_dialog = QtWidgets.QFileDialog
                default_path = str(pathlib.Path.home())
                title_bar_text = "데이터 저장 폴더"
                datapath = str(
                    file_dialog.getExistingDirectory(
                        self,
                        title_bar_text,
                        default_path,
                    )
                )

            while datapath == "":
                question = [
                    "데이터 저장 폴더를 선택하세요.",
                    "앞으로 쏠쏠이 생성하는 모든 데이터는 지금 선택되는 폴더 안에 담기게 됩니다.",
                    ["확인"],
                ]
                self.ask(question)
                self.undertake(job, True)

            standardize.set_datapath(datapath)
            standardize.load()

        # ■■■■■ check basics ■■■■■

        if standardize.get_basics() is None:

            setup_area = None

            # add temporary widget
            def job():
                nonlocal setup_area
                setup_area = SetupArea(self)
                self.centralWidget().layout().addWidget(setup_area)

            self.undertake(job, True)

            setup_area.done_event.wait()

            # remove temporary widget
            def job():
                setup_area.setParent(None)

            self.undertake(job, True)

        # ■■■■■ guide frame ■■■■■

        guide_frame = None

        def job():
            nonlocal guide_frame
            guide_frame = GuideFrame("로딩 중입니다.")
            self.centralWidget().layout().addWidget(guide_frame)

        self.undertake(job, True)

        # ■■■■■ multiprocessing ■■■■■

        process_toss.start_pool()

        # ■■■■■ get information about target symbols ■■■■■

        target_symbols = standardize.get_basics()["target_symbols"]
        response = ApiRequester().coinstats("GET", "/public/v1/coins")
        about_coins = response["coins"]

        coin_names = {}
        coin_icon_urls = {}
        coin_ranks = {}

        for about_coin in about_coins:
            coin_symbol = about_coin["symbol"]
            coin_names[coin_symbol] = about_coin["name"]
            coin_icon_urls[coin_symbol] = about_coin["icon"]
            coin_ranks[coin_symbol] = about_coin["rank"]

        self.alias_to_symbol = {}
        self.symbol_to_alias = {}

        for symbol in target_symbols:
            coin_symbol = symbol.removesuffix("USDT")
            coin_name = coin_names.get(coin_symbol, "")
            if coin_name == "":
                alias = coin_symbol
            else:
                alias = coin_name
            self.alias_to_symbol[alias] = symbol
            self.symbol_to_alias[symbol] = alias

        # ■■■■■ make widgets according to the target symbols list ■■■■■

        name_text_size = 13
        price_text_size = 10
        detail_text_size = 7

        is_long = len(target_symbols) > 5

        symbol_pixmaps = {}
        for symbol in target_symbols:
            coin_symbol = symbol.removesuffix("USDT")
            coin_icon_url = coin_icon_urls.get(coin_symbol, "")
            pixmap = QtGui.QPixmap()
            if coin_icon_url != "":
                image_data = urllib.request.urlopen(coin_icon_url).read()
                pixmap.loadFromData(image_data)
            else:
                pixmap.load("./resource/icon/blank_coin.png")
            symbol_pixmaps[symbol] = pixmap

        def job():
            self.lineEdit.setText(standardize.get_datapath())

            for symbol in target_symbols:
                icon = QtGui.QIcon()
                icon.addPixmap(symbol_pixmaps[symbol])
                alias = self.symbol_to_alias[symbol]
                self.comboBox_4.addItem(icon, alias)
                self.comboBox_6.addItem(icon, alias)

            spacer = QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            self.horizontalLayout_20.addItem(spacer)
            spacer = QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            self.horizontalLayout_17.addItem(spacer)
            self.price_labels = {}
            for turn, symbol in enumerate(target_symbols):
                coin_symbol = symbol.removesuffix("USDT")
                coin_rank = coin_ranks.get(coin_symbol, 0)
                symbol_box = QtWidgets.QGroupBox(objectName="symbol_box")
                if is_long and turn + 1 > math.floor(len(target_symbols) / 2):
                    self.horizontalLayout_17.addWidget(symbol_box)
                else:
                    self.horizontalLayout_20.addWidget(symbol_box)
                inside_layout = QtWidgets.QVBoxLayout(symbol_box)
                spacer = QtWidgets.QSpacerItem(
                    0,
                    0,
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Expanding,
                )
                inside_layout.addItem(spacer)
                icon_label = QtWidgets.QLabel(
                    alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
                )
                this_layout = QtWidgets.QHBoxLayout()
                inside_layout.addLayout(this_layout)
                icon_label.setPixmap(symbol_pixmaps[symbol])
                icon_label.setScaledContents(True)
                icon_label.setFixedSize(70, 70)
                icon_label.setMargin(5)
                this_layout.addWidget(icon_label)
                name_label = QtWidgets.QLabel(
                    self.symbol_to_alias[symbol],
                    alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
                )
                name_font = QtGui.QFont()
                name_font.setPointSize(name_text_size)
                name_font.setWeight(QtGui.QFont.Weight.Bold)
                name_label.setFont(name_font)
                inside_layout.addWidget(name_label)
                price_label = QtWidgets.QLabel(
                    "",
                    alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
                )
                price_font = QtGui.QFont()
                price_font.setPointSize(price_text_size)
                price_font.setWeight(QtGui.QFont.Weight.Bold)
                price_label.setFont(price_font)
                inside_layout.addWidget(price_label)
                if coin_rank == 0:
                    text = coin_symbol
                else:
                    text = f"{coin_rank} - {coin_symbol}"
                detail_label = QtWidgets.QLabel(
                    text,
                    alignment=QtCore.Qt.AlignmentFlag.AlignCenter,
                )
                detail_font = QtGui.QFont()
                detail_font.setPointSize(detail_text_size)
                detail_font.setWeight(QtGui.QFont.Weight.Bold)
                detail_label.setFont(detail_font)
                inside_layout.addWidget(detail_label)
                self.price_labels[symbol] = price_label
                spacer = QtWidgets.QSpacerItem(
                    0,
                    0,
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.Expanding,
                )
                inside_layout.addItem(spacer)
            spacer = QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            self.horizontalLayout_20.addItem(spacer)
            spacer = QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
            self.horizontalLayout_17.addItem(spacer)

        self.undertake(job, True)

        # ■■■■■ graph widgets ■■■■■

        def job():
            self.plot_widget = pyqtgraph.PlotWidget()
            self.plot_widget_1 = pyqtgraph.PlotWidget()
            self.plot_widget_4 = pyqtgraph.PlotWidget()
            self.plot_widget_6 = pyqtgraph.PlotWidget()
            self.plot_widget.setBackground("#FCFCFC")
            self.plot_widget_1.setBackground("#FCFCFC")
            self.plot_widget_4.setBackground("#FCFCFC")
            self.plot_widget_6.setBackground("#FCFCFC")
            self.plot_widget.setMouseEnabled(y=False)
            self.plot_widget_1.setMouseEnabled(y=False)
            self.plot_widget_4.setMouseEnabled(y=False)
            self.plot_widget_6.setMouseEnabled(y=False)
            self.plot_widget.enableAutoRange(y=True)
            self.plot_widget_1.enableAutoRange(y=True)
            self.plot_widget_4.enableAutoRange(y=True)
            self.plot_widget_6.enableAutoRange(y=True)
            self.horizontalLayout_7.addWidget(self.plot_widget)
            self.horizontalLayout_29.addWidget(self.plot_widget_1)
            self.horizontalLayout_16.addWidget(self.plot_widget_4)
            self.horizontalLayout_28.addWidget(self.plot_widget_6)

            plot_item = self.plot_widget.plotItem
            plot_item_1 = self.plot_widget_1.plotItem
            plot_item_4 = self.plot_widget_4.plotItem
            plot_item_6 = self.plot_widget_6.plotItem
            plot_item.vb.setLimits(xMin=0, yMin=0)
            plot_item_1.vb.setLimits(xMin=0, yMin=0)
            plot_item_4.vb.setLimits(xMin=0, yMin=0)
            plot_item_6.vb.setLimits(xMin=0)
            plot_item.setDownsampling(auto=True, mode="subsample")
            plot_item.setClipToView(True)
            plot_item.setAutoVisible(y=True)
            plot_item_1.setDownsampling(auto=True, mode="subsample")
            plot_item_1.setClipToView(True)
            plot_item_1.setAutoVisible(y=True)
            plot_item_4.setDownsampling(auto=True, mode="subsample")
            plot_item_4.setClipToView(True)
            plot_item_4.setAutoVisible(y=True)
            plot_item_6.setDownsampling(auto=True, mode="subsample")
            plot_item_6.setClipToView(True)
            plot_item_6.setAutoVisible(y=True)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": PercentAxisItem(orientation="left"),
                "right": PercentAxisItem(orientation="right"),
            }
            plot_item.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": PercentAxisItem(orientation="left"),
                "right": PercentAxisItem(orientation="right"),
            }
            plot_item_1.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": pyqtgraph.AxisItem(orientation="left"),
                "right": pyqtgraph.AxisItem(orientation="right"),
            }
            plot_item_4.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": pyqtgraph.AxisItem(orientation="left"),
                "right": pyqtgraph.AxisItem(orientation="right"),
            }
            plot_item_6.setAxisItems(axis_items)
            tick_font = QtGui.QFont("Consolas", 7)
            plot_item.getAxis("top").setTickFont(tick_font)
            plot_item.getAxis("bottom").setTickFont(tick_font)
            plot_item.getAxis("left").setTickFont(tick_font)
            plot_item.getAxis("right").setTickFont(tick_font)
            plot_item_1.getAxis("top").setTickFont(tick_font)
            plot_item_1.getAxis("bottom").setTickFont(tick_font)
            plot_item_1.getAxis("left").setTickFont(tick_font)
            plot_item_1.getAxis("right").setTickFont(tick_font)
            plot_item_4.getAxis("top").setTickFont(tick_font)
            plot_item_4.getAxis("bottom").setTickFont(tick_font)
            plot_item_4.getAxis("left").setTickFont(tick_font)
            plot_item_4.getAxis("right").setTickFont(tick_font)
            plot_item_6.getAxis("top").setTickFont(tick_font)
            plot_item_6.getAxis("bottom").setTickFont(tick_font)
            plot_item_6.getAxis("left").setTickFont(tick_font)
            plot_item_6.getAxis("right").setTickFont(tick_font)
            plot_item.getAxis("left").setWidth(40)
            plot_item.getAxis("right").setWidth(40)
            plot_item_1.getAxis("left").setWidth(40)
            plot_item_1.getAxis("right").setWidth(40)
            plot_item_4.getAxis("left").setWidth(40)
            plot_item_4.getAxis("right").setWidth(40)
            plot_item_6.getAxis("left").setWidth(40)
            plot_item_6.getAxis("right").setWidth(40)
            plot_item.getAxis("bottom").setHeight(0)
            plot_item_1.getAxis("top").setHeight(0)
            plot_item_4.getAxis("top").setHeight(0)
            plot_item_4.getAxis("bottom").setHeight(0)
            plot_item_6.getAxis("top").setHeight(0)
            plot_item_6.getAxis("bottom").setHeight(0)
            plot_item.showGrid(x=True, y=True, alpha=0.1)
            plot_item_1.showGrid(x=True, y=True, alpha=0.1)
            plot_item_4.showGrid(x=True, y=True, alpha=0.1)
            plot_item_6.showGrid(x=True, y=True, alpha=0.1)

            self.transaction_lines = {
                "book_tickers": [
                    plot_item.plot(
                        pen=pyqtgraph.mkPen("#CFCFCF"),
                        connect="finite",
                        stepMode="right",
                    )
                    for _ in range(2)
                ],
                "last_price": plot_item.plot(
                    pen=pyqtgraph.mkPen("#D8E461"),
                    connect="finite",
                    stepMode="right",
                ),
                "mark_price": plot_item.plot(
                    pen=pyqtgraph.mkPen("#E2F200"),
                    connect="finite",
                ),
                "price_indicators": [
                    plot_item.plot(connect="finite") for _ in range(20)
                ],
                "entry_price": plot_item.plot(
                    pen=pyqtgraph.mkPen("#FFBB00"),
                    connect="finite",
                ),
                "boundaries": [
                    plot_item.plot(
                        pen=pyqtgraph.mkPen("#D0E200"),
                        connect="finite",
                    )
                    for _ in range(20)
                ],
                "wobbles": [
                    plot_item.plot(
                        pen=pyqtgraph.mkPen("#8AAE31"),
                        connect="finite",
                        stepMode="right",
                    )
                    for _ in range(2)
                ],
                "price_movement": plot_item.plot(
                    pen=pyqtgraph.mkPen("#3C7800"),
                    connect="finite",
                ),
                "close_price": plot_item.plot(
                    pen=pyqtgraph.mkPen("#3C7800"),
                    connect="finite",
                ),
                "sell": plot_item.plot(
                    pen=pyqtgraph.mkPen(None),  # invisible line
                    symbol="o",
                    symbolBrush="#0055FF",
                    symbolPen=pyqtgraph.mkPen("#BBBBBB"),
                    symbolSize=8,
                ),
                "buy": plot_item.plot(
                    pen=pyqtgraph.mkPen(None),  # invisible line
                    symbol="o",
                    symbolBrush="#FF3300",
                    symbolPen=pyqtgraph.mkPen("#BBBBBB"),
                    symbolSize=8,
                ),
                "volume": plot_item_4.plot(
                    pen=pyqtgraph.mkPen("#111111"),
                    connect="all",
                    stepMode="right",
                    fillLevel=0,
                    brush=pyqtgraph.mkBrush(0, 0, 0, 15),
                ),
                "last_volume": plot_item_4.plot(
                    pen=pyqtgraph.mkPen("#111111"),
                    connect="finite",
                ),
                "volume_indicators": [
                    plot_item_4.plot(connect="finite") for _ in range(20)
                ],
                "abstract_indicators": [
                    plot_item_6.plot(connect="finite") for _ in range(20)
                ],
                "asset_with_unrealized_profit": plot_item_1.plot(
                    pen=pyqtgraph.mkPen("#AAAAAA"),
                    connect="finite",
                ),
                "asset": plot_item_1.plot(
                    pen=pyqtgraph.mkPen("#FF8700"),
                    connect="finite",
                    stepMode="right",
                ),
            }

            self.plot_widget_1.setXLink(self.plot_widget)
            self.plot_widget_4.setXLink(self.plot_widget_1)
            self.plot_widget_6.setXLink(self.plot_widget_4)

        self.undertake(job, True)

        def job():

            self.plot_widget_2 = pyqtgraph.PlotWidget()
            self.plot_widget_3 = pyqtgraph.PlotWidget()
            self.plot_widget_5 = pyqtgraph.PlotWidget()
            self.plot_widget_7 = pyqtgraph.PlotWidget()
            self.plot_widget_2.setBackground("#FCFCFC")
            self.plot_widget_3.setBackground("#FCFCFC")
            self.plot_widget_5.setBackground("#FCFCFC")
            self.plot_widget_7.setBackground("#FCFCFC")
            self.plot_widget_2.setMouseEnabled(y=False)
            self.plot_widget_3.setMouseEnabled(y=False)
            self.plot_widget_5.setMouseEnabled(y=False)
            self.plot_widget_7.setMouseEnabled(y=False)
            self.plot_widget_2.enableAutoRange(y=True)
            self.plot_widget_3.enableAutoRange(y=True)
            self.plot_widget_5.enableAutoRange(y=True)
            self.plot_widget_7.enableAutoRange(y=True)
            self.horizontalLayout.addWidget(self.plot_widget_2)
            self.horizontalLayout_30.addWidget(self.plot_widget_3)
            self.horizontalLayout_19.addWidget(self.plot_widget_5)
            self.horizontalLayout_31.addWidget(self.plot_widget_7)

            plot_item_2 = self.plot_widget_2.plotItem
            plot_item_3 = self.plot_widget_3.plotItem
            plot_item_5 = self.plot_widget_5.plotItem
            plot_item_7 = self.plot_widget_7.plotItem
            plot_item_2.vb.setLimits(xMin=0, yMin=0)
            plot_item_3.vb.setLimits(xMin=0, yMin=0)
            plot_item_5.vb.setLimits(xMin=0, yMin=0)
            plot_item_7.vb.setLimits(xMin=0)
            plot_item_2.setDownsampling(auto=True, mode="subsample")
            plot_item_2.setClipToView(True)
            plot_item_2.setAutoVisible(y=True)
            plot_item_3.setDownsampling(auto=True, mode="subsample")
            plot_item_3.setClipToView(True)
            plot_item_3.setAutoVisible(y=True)
            plot_item_5.setDownsampling(auto=True, mode="subsample")
            plot_item_5.setClipToView(True)
            plot_item_5.setAutoVisible(y=True)
            plot_item_7.setDownsampling(auto=True, mode="subsample")
            plot_item_7.setClipToView(True)
            plot_item_7.setAutoVisible(y=True)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": PercentAxisItem(orientation="left"),
                "right": PercentAxisItem(orientation="right"),
            }
            plot_item_2.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": PercentAxisItem(orientation="left"),
                "right": PercentAxisItem(orientation="right"),
            }
            plot_item_3.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": pyqtgraph.AxisItem(orientation="left"),
                "right": pyqtgraph.AxisItem(orientation="right"),
            }
            plot_item_5.setAxisItems(axis_items)
            axis_items = {
                "top": pyqtgraph.DateAxisItem(orientation="top"),
                "bottom": pyqtgraph.DateAxisItem(orientation="bottom"),
                "left": pyqtgraph.AxisItem(orientation="left"),
                "right": pyqtgraph.AxisItem(orientation="right"),
            }
            plot_item_7.setAxisItems(axis_items)
            tick_font = QtGui.QFont("Consolas", 7)
            plot_item_2.getAxis("top").setTickFont(tick_font)
            plot_item_2.getAxis("bottom").setTickFont(tick_font)
            plot_item_2.getAxis("left").setTickFont(tick_font)
            plot_item_2.getAxis("right").setTickFont(tick_font)
            plot_item_3.getAxis("top").setTickFont(tick_font)
            plot_item_3.getAxis("bottom").setTickFont(tick_font)
            plot_item_3.getAxis("left").setTickFont(tick_font)
            plot_item_3.getAxis("right").setTickFont(tick_font)
            plot_item_5.getAxis("top").setTickFont(tick_font)
            plot_item_5.getAxis("bottom").setTickFont(tick_font)
            plot_item_5.getAxis("left").setTickFont(tick_font)
            plot_item_5.getAxis("right").setTickFont(tick_font)
            plot_item_7.getAxis("top").setTickFont(tick_font)
            plot_item_7.getAxis("bottom").setTickFont(tick_font)
            plot_item_7.getAxis("left").setTickFont(tick_font)
            plot_item_7.getAxis("right").setTickFont(tick_font)
            plot_item_2.getAxis("left").setWidth(40)
            plot_item_2.getAxis("right").setWidth(40)
            plot_item_3.getAxis("left").setWidth(40)
            plot_item_3.getAxis("right").setWidth(40)
            plot_item_5.getAxis("left").setWidth(40)
            plot_item_5.getAxis("right").setWidth(40)
            plot_item_7.getAxis("left").setWidth(40)
            plot_item_7.getAxis("right").setWidth(40)
            plot_item_2.getAxis("bottom").setHeight(0)
            plot_item_3.getAxis("top").setHeight(0)
            plot_item_5.getAxis("top").setHeight(0)
            plot_item_5.getAxis("bottom").setHeight(0)
            plot_item_7.getAxis("top").setHeight(0)
            plot_item_7.getAxis("bottom").setHeight(0)
            plot_item_2.showGrid(x=True, y=True, alpha=0.1)
            plot_item_3.showGrid(x=True, y=True, alpha=0.1)
            plot_item_5.showGrid(x=True, y=True, alpha=0.1)
            plot_item_7.showGrid(x=True, y=True, alpha=0.1)

            self.simulation_lines = {
                "book_tickers": [
                    plot_item_2.plot(
                        pen=pyqtgraph.mkPen("#CFCFCF"),
                        connect="finite",
                        stepMode="right",
                    )
                    for _ in range(2)
                ],
                "last_price": plot_item_2.plot(
                    pen=pyqtgraph.mkPen("#D8E461"),
                    connect="finite",
                    stepMode="right",
                ),
                "mark_price": plot_item_2.plot(
                    pen=pyqtgraph.mkPen("#E2F200"),
                    connect="finite",
                ),
                "price_indicators": [
                    plot_item_2.plot(connect="finite") for _ in range(20)
                ],
                "entry_price": plot_item_2.plot(
                    pen=pyqtgraph.mkPen("#FFBB00"),
                    connect="finite",
                ),
                "boundaries": [
                    plot_item_2.plot(
                        pen=pyqtgraph.mkPen("#D0E200"),
                        connect="finite",
                    )
                    for _ in range(20)
                ],
                "wobbles": [
                    plot_item_2.plot(
                        pen=pyqtgraph.mkPen("#8AAE31"),
                        connect="finite",
                        stepMode="right",
                    )
                    for _ in range(2)
                ],
                "price_movement": plot_item_2.plot(
                    pen=pyqtgraph.mkPen("#3C7800"),
                    connect="finite",
                ),
                "close_price": plot_item_2.plot(
                    pen=pyqtgraph.mkPen("#3C7800"),
                    connect="finite",
                ),
                "sell": plot_item_2.plot(
                    pen=pyqtgraph.mkPen(None),  # invisible line
                    symbol="o",
                    symbolBrush="#0055FF",
                    symbolPen=pyqtgraph.mkPen("#BBBBBB"),
                    symbolSize=8,
                ),
                "buy": plot_item_2.plot(
                    pen=pyqtgraph.mkPen(None),  # invisible line
                    symbol="o",
                    symbolBrush="#FF3300",
                    symbolPen=pyqtgraph.mkPen("#BBBBBB"),
                    symbolSize=8,
                ),
                "volume": plot_item_5.plot(
                    pen=pyqtgraph.mkPen("#111111"),
                    connect="all",
                    stepMode="right",
                    fillLevel=0,
                    brush=pyqtgraph.mkBrush(0, 0, 0, 15),
                ),
                "last_volume": plot_item_5.plot(
                    pen=pyqtgraph.mkPen("#111111"),
                    connect="finite",
                ),
                "volume_indicators": [
                    plot_item_5.plot(connect="finite") for _ in range(20)
                ],
                "abstract_indicators": [
                    plot_item_7.plot(connect="finite") for _ in range(20)
                ],
                "asset_with_unrealized_profit": plot_item_3.plot(
                    pen=pyqtgraph.mkPen("#AAAAAA"),
                    connect="finite",
                ),
                "asset": plot_item_3.plot(
                    pen=pyqtgraph.mkPen("#FF8700"),
                    connect="finite",
                    stepMode="right",
                ),
            }

            self.plot_widget_3.setXLink(self.plot_widget_2)
            self.plot_widget_5.setXLink(self.plot_widget_3)
            self.plot_widget_7.setXLink(self.plot_widget_5)

        self.undertake(job, True)

        # ■■■■■ intergrated strategies ■■■■■

        # usability / is parallel calculation / divided unit length / is fast strategy
        self.strategy_tuples = [
            (0, "직접 짜는 나만의 전략"),
            (1, "10초마다 느리게 랜덤으로 주문 넣기", [True, True, 7, False]),
            (2, "0.1초마다 빠르게 랜덤으로 주문 넣기", [True, True, 7, True]),
            (57, "급등락 직후를 바라보기", [False, True, 30, False]),
            (61, "한걸음 한걸음", [False, True, 30, False]),
            (64, "평균 단가로 격차 넘기", [False, True, 30, False]),
            (65, "단순무식한 샌드위치", [True, True, 30, False]),
            (89, "거꾸로 크게 쌓기", [True, False, 30, False]),
            (93, "모두가 한곳을 바라볼 때", [False, True, 30, False]),
            (95, "더 느리게 닿지 않는 곳으로", [True, False, 30, False]),
            (98, "지금의 기울기", [False, True, 30, False]),
            (100, "아빠 일어나", [True, True, 30, False]),
            (107, "거래량이 늘어난 순간 확 낚아채기", [True, True, 30, False]),
            (110, "심해와 하늘에서 조심스레 보물 찾기", [True, True, 30, False]),
        ]

        red_pixmap = QtGui.QPixmap()
        red_pixmap.load("./resource/icon/traffic_light_red.png")
        yellow_pixmap = QtGui.QPixmap()
        yellow_pixmap.load("./resource/icon/traffic_light_yellow.png")
        green_pixmap = QtGui.QPixmap()
        green_pixmap.load("./resource/icon/traffic_light_green.png")

        for strategy_tuple in self.strategy_tuples:
            text = f"{strategy_tuple[0]} - {strategy_tuple[1]}"

            traffic_light_icon = QtGui.QIcon()
            if strategy_tuple[0] == 0:
                traffic_light_icon.addPixmap(yellow_pixmap)
            else:
                if strategy_tuple[2][0]:
                    traffic_light_icon.addPixmap(green_pixmap)
                else:
                    traffic_light_icon.addPixmap(red_pixmap)

            def job(text=text):
                self.comboBox.addItem(traffic_light_icon, text)
                self.comboBox_2.addItem(traffic_light_icon, text)

            self.undertake(job, True)

        # ■■■■■ submenus ■■■■■

        def job():
            action_menu = QtWidgets.QMenu(self)
            self.collector_actions = []
            text = "캔들 데이터 저장하기"
            self.collector_actions.append(action_menu.addAction(text))
            text = "모든 연도의 캔들 데이터 저장하기"
            self.collector_actions.append(action_menu.addAction(text))
            text = "바이낸스 과거 시장 데이터 페이지 열기"
            self.collector_actions.append(action_menu.addAction(text))
            self.pushButton_13.setMenu(action_menu)

            action_menu = QtWidgets.QMenu(self)
            self.transactor_actions = []
            text = "바이낸스 거래소 열기"
            self.transactor_actions.append(action_menu.addAction(text))
            text = "바이낸스 선물 지갑 열기"
            self.transactor_actions.append(action_menu.addAction(text))
            text = "바이낸스 키 관리 페이지 열기"
            self.transactor_actions.append(action_menu.addAction(text))
            text = "바이낸스 테스트넷 거래소 열기"
            self.transactor_actions.append(action_menu.addAction(text))
            text = "해당 시장의 모든 열린 주문 취소하기"
            self.transactor_actions.append(action_menu.addAction(text))
            text = "시뮬레이션 그래프와 같은 범위 보기"
            self.transactor_actions.append(action_menu.addAction(text))
            self.pushButton_12.setMenu(action_menu)

            action_menu = QtWidgets.QMenu(self)
            self.simulator_actions = []
            text = "보이는 범위만 임시로 계산하기"
            self.simulator_actions.append(action_menu.addAction(text))
            text = "계산 멈추기"
            self.simulator_actions.append(action_menu.addAction(text))
            text = "최저 미실현 수익률 지점들 찾기"
            self.simulator_actions.append(action_menu.addAction(text))
            text = "자동 주문 그래프와 같은 범위 보기"
            self.simulator_actions.append(action_menu.addAction(text))
            self.pushButton_11.setMenu(action_menu)

            action_menu = QtWidgets.QMenu(self)
            self.strategist_actions = []
            text = "샘플 전략으로 채우기"
            self.strategist_actions.append(action_menu.addAction(text))
            self.pushButton_9.setMenu(action_menu)

            action_menu = QtWidgets.QMenu(self)
            self.manager_actions = []
            text = "일부러 작은 오류 발생시키기"
            self.manager_actions.append(action_menu.addAction(text))
            text = "시험용 팝업 보이기"
            self.manager_actions.append(action_menu.addAction(text))
            text = "시스템 시각을 바이낸스 서버에 맞추기"
            self.manager_actions.append(action_menu.addAction(text))
            text = "현재 버전 보기"
            self.manager_actions.append(action_menu.addAction(text))
            text = "현재 라이센스 키 보기"
            self.manager_actions.append(action_menu.addAction(text))
            self.pushButton_10.setMenu(action_menu)

        self.undertake(job, True)

        # ■■■■■ prepare auto executions ■■■■■

        self.initialize_functions = []
        self.finalize_functions = []
        self.scheduler = BlockingScheduler(timezone="UTC")
        self.scheduler.add_executor(ThreadPoolExecutor(), "thread_pool_executor")

        # ■■■■■ workers ■■■■■

        self.collector = Collector(self)
        self.transactor = Transactor(self)
        self.simulator = Simulator(self)
        self.strategist = Strategiest(self)
        self.manager = Manager(self)

        # ■■■■■ prepare logging ■■■■■

        log_handler = LogHandler(self.manager.add_log_output)
        log_format = "■ %(asctime)s.%(msecs)03d %(levelname)s\n\n%(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        log_formatter = logging.Formatter(log_format, datefmt=date_format)
        log_formatter.converter = time.gmtime
        log_handler.setFormatter(log_formatter)
        logging.addLevelName(1, "START")
        logging.getLogger().addHandler(log_handler)
        logger = logging.getLogger("solsol")
        logger.setLevel(1)
        logger.log(1, "")

        # ■■■■■ connect events to functions ■■■■■

        def job():

            # 액션
            job = self.collector.save_candle_data
            outsource.do(self.collector_actions[0].triggered, job)
            job = self.collector.save_all_years_history
            outsource.do(self.collector_actions[1].triggered, job)
            job = self.collector.open_binance_data_page
            outsource.do(self.collector_actions[2].triggered, job)
            job = self.transactor.open_exchange
            outsource.do(self.transactor_actions[0].triggered, job)
            job = self.transactor.open_futures_wallet_page
            outsource.do(self.transactor_actions[1].triggered, job)
            job = self.transactor.open_api_management_page
            outsource.do(self.transactor_actions[2].triggered, job)
            job = self.transactor.open_testnet_exchange
            outsource.do(self.transactor_actions[3].triggered, job)
            job = self.transactor.cancel_symbol_orders
            outsource.do(self.transactor_actions[4].triggered, job)
            job = self.transactor.match_graph_range
            outsource.do(self.transactor_actions[5].triggered, job)
            job = self.simulator.simulate_only_visible
            outsource.do(self.simulator_actions[0].triggered, job)
            job = self.simulator.stop_calculation
            outsource.do(self.simulator_actions[1].triggered, job)
            job = self.simulator.analyze_unrealized_peaks
            outsource.do(self.simulator_actions[2].triggered, job)
            job = self.simulator.match_graph_range
            outsource.do(self.simulator_actions[3].triggered, job)
            job = self.strategist.fill_with_sample
            outsource.do(self.strategist_actions[0].triggered, job)
            job = self.manager.make_small_exception
            outsource.do(self.manager_actions[0].triggered, job)
            job = self.manager.open_sample_ask_popup
            outsource.do(self.manager_actions[1].triggered, job)
            job = self.manager.match_system_time
            outsource.do(self.manager_actions[2].triggered, job)
            job = self.manager.show_version
            outsource.do(self.manager_actions[3].triggered, job)
            job = self.manager.show_license_key
            outsource.do(self.manager_actions[4].triggered, job)

            # 특수 위젯
            job = self.transactor.display_range_information
            outsource.do(self.plot_widget.sigRangeChanged, job)
            job = self.simulator.display_range_information
            outsource.do(self.plot_widget_2.sigRangeChanged, job)

            # 일반 위젯
            job = self.simulator.update_calculation_settings
            outsource.do(self.comboBox.activated, job)
            job = self.transactor.update_automation_settings
            outsource.do(self.comboBox_2.activated, job)
            job = self.transactor.update_automation_settings
            outsource.do(self.checkBox.stateChanged, job)
            job = self.simulator.calculate
            outsource.do(self.pushButton_3.clicked, job)
            job = self.manager.open_datapath
            outsource.do(self.pushButton_8.clicked, job)
            job = self.simulator.update_presentation_settings
            outsource.do(self.lineEdit_2.editingFinished, job)
            job = self.simulator.update_presentation_settings
            outsource.do(self.lineEdit_5.editingFinished, job)
            job = self.simulator.erase
            outsource.do(self.pushButton_4.clicked, job)
            job = self.simulator.update_calculation_settings
            outsource.do(self.comboBox_5.activated, job)
            job = self.manager.display_selected_log_output
            outsource.do(self.listWidget.currentItemChanged, job)
            job = self.transactor.update_keys
            outsource.do(self.lineEdit_4.editingFinished, job)
            job = self.transactor.update_keys
            outsource.do(self.lineEdit_6.editingFinished, job)
            job = self.manager.run_script
            outsource.do(self.pushButton.clicked, job)
            job = self.transactor.toggle_vertical_automation
            outsource.do(self.checkBox_2.stateChanged, job)
            job = self.simulator.toggle_vertical_automation
            outsource.do(self.checkBox_3.stateChanged, job)
            job = self.transactor.display_day_range
            outsource.do(self.pushButton_14.clicked, job)
            job = self.simulator.display_year_range
            outsource.do(self.pushButton_15.clicked, job)
            job = self.simulator.delete_calculation_data
            outsource.do(self.pushButton_16.clicked, job)
            job = self.simulator.draw
            outsource.do(self.pushButton_17.clicked, job)
            job = self.collector.download_fill_history_until_last_month
            outsource.do(self.pushButton_18.clicked, job)
            job = self.collector.download_fill_history_this_month
            outsource.do(self.pushButton_5.clicked, job)
            job = self.strategist.revert_scripts
            outsource.do(self.pushButton_19.clicked, job)
            job = self.strategist.save_scripts
            outsource.do(self.pushButton_20.clicked, job)
            job = self.transactor.update_keys
            outsource.do(self.comboBox_3.activated, job)
            job = self.collector.download_fill_history_last_two_days
            outsource.do(self.pushButton_2.clicked, job)
            job = self.transactor.update_leverage_settings
            outsource.do(self.lineEdit_3.editingFinished, job)
            job = self.transactor.update_leverage_settings
            outsource.do(self.checkBox_5.stateChanged, job)
            job = self.manager.deselect_log_output
            outsource.do(self.pushButton_6.clicked, job)
            job = self.manager.reset_datapath
            outsource.do(self.pushButton_22.clicked, job)
            job = self.transactor.update_viewing_symbol
            outsource.do(self.comboBox_4.activated, job)
            job = self.simulator.update_viewing_symbol
            outsource.do(self.comboBox_6.activated, job)
            job = self.manager.open_documentation
            outsource.do(self.pushButton_7.clicked, job)

        self.undertake(job, True)

        # ■■■■■ initialize functions ■■■■■

        def job():
            guide_frame.change_text("초기 실행 중입니다.")
            guide_frame.change_steps(len(self.initialize_functions))

        self.undertake(job, True)

        done_steps = 0

        def job(function):
            nonlocal done_steps
            function()
            done_steps += 1
            self.undertake(lambda d=done_steps: guide_frame.progress(d), True)

        map_result = thread_toss.map_async(job, self.initialize_functions)

        for _ in range(200):
            if map_result.ready() and map_result.successful():
                break
            time.sleep(0.1)

        # ■■■■■ start repetitive timer ■■■■■

        thread_toss.apply_async(lambda: self.scheduler.start())

        # ■■■■■ activate finalization ■■■■■

        self.should_finalize = True

        # ■■■■■ wait until the contents are filled ■■■■■

        time.sleep(1)

        # ■■■■■ show main widgets ■■■■■

        self.undertake(lambda: guide_frame.setParent(None), True)
        self.undertake(lambda: self.board.show(), True)
        self.undertake(lambda: self.gauge.show(), True)

    # takes function and run it on the main thread
    def undertake(self, job, wait_return, called_remotely=False, holder=None):

        if not called_remotely:
            holder = [threading.Event(), None]
            telephone = Telephone()
            telephone.signal.connect(self.undertake)
            telephone.signal.emit(job, False, True, holder)
            if wait_return:
                holder[0].wait()
                return holder[1]

        else:
            returned = job()
            holder[1] = returned
            holder[0].set()

    # show an ask popup and blocks the stack
    def ask(self, question):

        ask_popup = None

        def job():
            nonlocal ask_popup
            ask_popup = AskPopup(self, question)
            ask_popup.show()

        self.undertake(job, True)

        ask_popup.done_event.wait()

        def job():
            ask_popup.setParent(None)

        self.undertake(job, False)

        return ask_popup.answer


# ■■■■■ app ■■■■■

app = QtWidgets.QApplication(sys.argv)

# ■■■■■ theme ■■■■■

# this part should be done after creating the app and before creating the window
QtGui.QFontDatabase.addApplicationFont("./resource/consolas.ttf")
QtGui.QFontDatabase.addApplicationFont("./resource/noto_sans_kr.otf")
default_font = QtGui.QFont("Noto Sans KR", 9)

app.setStyle("Fusion")
app.setFont(default_font)

# ■■■■■ window ■■■■■

window = Window()

# ■■■■■ show ■■■■■

window.show()
sys.exit(getattr(app, "exec")())
