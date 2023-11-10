import pathlib

from PySide6 import QtWidgets, QtCore, QtGui

from module import core
from module.widget.horizontal_divider import HorizontalDivider
from module.recipe import user_settings
from module.recipe import outsource


class DatapathInput(QtWidgets.QWidget):
    def __init__(self, done_event, payload):
        # ■■■■■ the basic ■■■■■

        super().__init__()

        # ■■■■■ full layout ■■■■■

        full_layout = QtWidgets.QHBoxLayout(self)
        cards_layout = QtWidgets.QVBoxLayout()
        full_layout.addLayout(cards_layout)

        # ■■■■■ spacing ■■■■■

        # spacing
        spacer = QtWidgets.QSpacerItem(
            0,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        cards_layout.addItem(spacer)

        # ■■■■■ a card ■■■■■

        # card structure
        card = QtWidgets.QGroupBox()
        card.setFixedWidth(720)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(80, 40, 80, 40)
        cards_layout.addWidget(card)

        # explanation
        detail_text = QtWidgets.QLabel()
        detail_text.setText("All the data that Solie produces will go in this folder.")
        detail_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        detail_text.setWordWrap(True)
        card_layout.addWidget(detail_text)

        # spacing
        spacing_text = QtWidgets.QLabel("")
        spacing_text_font = QtGui.QFont()
        spacing_text_font.setPointSize(3)
        spacing_text.setFont(spacing_text_font)
        card_layout.addWidget(spacing_text)

        # divider
        divider = HorizontalDivider(self)
        card_layout.addWidget(divider)

        # spacing
        spacing_text = QtWidgets.QLabel("")
        spacing_text_font = QtGui.QFont()
        spacing_text_font.setPointSize(3)
        spacing_text.setFont(spacing_text_font)
        card_layout.addWidget(spacing_text)

        # chosen folder label
        folder_label = QtWidgets.QLabel()
        folder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        folder_label.setWordWrap(True)
        card_layout.addWidget(folder_label)

        # spacing
        spacing_text = QtWidgets.QLabel("")
        spacing_text_font = QtGui.QFont()
        spacing_text_font.setPointSize(3)
        spacing_text.setFont(spacing_text_font)
        card_layout.addWidget(spacing_text)

        datapath = ""

        def job_dp():
            nonlocal datapath

            def job_dd():
                nonlocal datapath
                file_dialog = QtWidgets.QFileDialog
                default_path = str(pathlib.Path.home())
                title_bar_text = "Data folder"
                datapath = str(
                    file_dialog.getExistingDirectory(
                        self,
                        title_bar_text,
                        default_path,
                    )
                )

            core.window.undertake(job_dd, True)
            payload = (folder_label.setText, datapath)
            core.window.undertake(lambda p=payload: p[0](p[1]), False)

        # choose button
        this_layout = QtWidgets.QHBoxLayout()
        card_layout.addLayout(this_layout)
        choose_button = QtWidgets.QPushButton("Choose folder", card)
        outsource.do(choose_button.clicked, job_dp)
        choose_button.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        this_layout.addWidget(choose_button)

        # ■■■■■ a card ■■■■■

        def job_ac():
            if datapath == "":
                question = [
                    "Data folder is not chosen",
                    "Choose your data folder first.",
                    ["Okay"],
                ]
                core.window.ask(question)
            else:
                user_settings.apply_app_settings({"datapath": datapath})
                user_settings.load()
                done_event.set()

        # card structure
        card = QtWidgets.QGroupBox()
        card.setFixedWidth(720)
        card_layout = QtWidgets.QHBoxLayout(card)
        card_layout.setContentsMargins(80, 40, 80, 40)
        cards_layout.addWidget(card)

        # confirm button
        confirm_button = QtWidgets.QPushButton("Okay", card)
        outsource.do(confirm_button.clicked, job_ac)
        confirm_button.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        card_layout.addWidget(confirm_button)

        # ■■■■■ spacing ■■■■■

        # spacing
        spacer = QtWidgets.QSpacerItem(
            0,
            0,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        cards_layout.addItem(spacer)
