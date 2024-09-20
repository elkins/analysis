"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-08-23 19:21:22 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: varioustoxins $"
__date__ = "$Date: 2021-05-06 18:21:23 +0100 (Thu, May 6, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import hjson
import os
from pathlib import Path
import sys
from glob import glob
from operator import itemgetter
import random
from typing import Optional, List

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QBrush, QColor, QPainter
from PyQt5.QtWidgets import QApplication, QWizard, QWizardPage, QCheckBox, QPushButton, QLabel, QGridLayout, \
    QSizePolicy, QFrame, QTextBrowser, QGraphicsScene, QGraphicsView
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Button import Button

from ccpn.framework.PathsAndUrls import tipOfTheDayConfig


HJSON_ERROR = hjson.HjsonDecodeError

RANDOM_TIP_BUTTON = QWizard.CustomButton1
DONT_SHOW_TIPS_BUTTON = QWizard.CustomButton2
HAVE_RANDOM_TIP_BUTTON = QWizard.HaveCustomButton1
HAVE_DONT_SHOW_TIPS_BUTTON = QWizard.HaveCustomButton2

MODE_TIP_OF_THE_DAY = 'TIP_OF_THE_DAY'
MODE_KEY_CONCEPTS = 'KEY_CONCEPTS'

TITLE = 'TITLE'
BUTTONS = 'BUTTONS'
DEFAULT = 'DEFAULT'
MIN_SIZE = 'MIN_SIZE'
LAYOUT = 'LAYOUT'
DIRECTORIES = 'DIRECTORIES'
IDENTIFIERS = 'IDENTIFIERS'
KEY_DEPTH = 'KEY_DEPTH'
EMPTY_TEXT = 'EMPTY_TEXT'
USE_DOTS = 'USE_DOTS'
HAS_DIVIDER = 'HAS_DIVIDER'
DIVIDER_COLOR = 'DIVIDER_COLOR'
DIVIDER_WIDTH = 'DIVIDER_WIDTH'

HEADER = 'header'
ORDER = 'order'
STYLES = 'styles'
TYPE = 'type'
PLACE_HOLDER = '_'
PATH = 'path'
PICTURE = 'picture'
SIMPLE_HTML = 'simple-html'
CONTENTS = 'contents'
COLOR = 'color'
MAX_ORDER = sys.maxsize

STYLE_FILE = 'style_file'

TIPS_SETUP = None
DEFAULT_CONFIG_PATH = 'tipConfig.hjson'


def loadTipsSetup(path: Path, tip_paths: Optional[List[Path]] = None):
    global TIPS_SETUP
    setup = hjson.loads(open(path, 'r').read())
    if tip_paths is None:
        tip_paths = [QApplication.applicationDirPath()]

    for instance in setup.values():
        if not isinstance(instance, dict):
            continue

        new_directories = []
        if DIRECTORIES in instance:
            for path in instance[DIRECTORIES]:
                path = Path(path)
                if not path.is_absolute():
                    for tip_path in tip_paths:
                        new_directories.append(str(Path(tip_path) / path))
                else:
                    new_directories.append(str(path))
            instance[DIRECTORIES] = new_directories

    TIPS_SETUP = setup


def _load_default_setup_if_required():
    global TIPS_SETUP
    if TIPS_SETUP is None:
        TIPS_SETUP = loadTipsSetup(DEFAULT_CONFIG_PATH)


BUTTON_IDS = {
    'Random'      : RANDOM_TIP_BUTTON,
    'Stretch'     : QWizard.Stretch,
    'Dont_show'   : DONT_SHOW_TIPS_BUTTON,
    'BackButton'  : QWizard.BackButton,
    'NextButton'  : QWizard.NextButton,
    'CancelButton': QWizard.CancelButton
    }


class Dots(QGraphicsView):

    def __init__(self, parent=None):
        super(Dots, self).__init__(parent=parent)
        self._dot_size = 10

        self._pos = 0
        self._length = 0

        self.setFixedHeight(self._dot_size * 2)

        self.setScene(QGraphicsScene())
        self._blackBrush = QBrush(QColor('black'))
        self._whiteBrush = QBrush(QColor('transparent'))

        self.setStyleSheet("border-width: 0px; border-style: solid;")
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.HighQualityAntialiasing)

    def _assure_children(self):
        error = self._length - len(self.items())
        if error != 0:
            if error > 0:
                for i in range(error):
                    ellipse = self.scene().addEllipse(QRectF(0, 0, self._dot_size, self._dot_size))
                    ellipse.setBrush(self._whiteBrush)

        center = self.sceneRect().center()
        items = self.items()
        dot_size_2 = self._dot_size / 2
        for i in range(self._length):
            gaps = self._length / 2
            dots = self._length

            total = dots + gaps
            width = total * self._dot_size
            width_2 = width / 2

            x_center = center.x() - width_2

            items[i].setPos(QPointF(x_center + i * self._dot_size * 2, center.y() - dot_size_2))

    def setLength(self, length):
        self._length = length
        self._assure_children()

    def setIndicatorPos(self, pos):
        self.items()[self._pos].setBrush(self._whiteBrush)
        self._pos = pos
        self.items()[self._pos].setBrush(self._blackBrush)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        our_scene = self.scene()
        if our_scene:
            width = event.size().width()
            height = event.size().height()

            self.scene().setSceneRect(0, 0, width, height)


class TipPage(QWizardPage):

    def __init__(self, data):
        super(TipPage, self).__init__()
        self._data = data

        self.setLayout(QGridLayout())

        if self._data[USE_DOTS]:
            self._dots = Dots(parent=self)
            self._dots.show()

    def setupPage(self):
        divider = ""
        if HAS_DIVIDER in self._data and self._data[HAS_DIVIDER]:

            divider_width = '1px'
            divider_color = '#a9a9a9'
            if DIVIDER_WIDTH in self._data:
                divider_width = self._data[DIVIDER_WIDTH]
            if DIVIDER_COLOR in self._data:
                divider_color = self._data[DIVIDER_COLOR]

            divider = f'border-top: {divider_width} solid {divider_color};'

        if COLOR in self._data:
            if COLOR in self._data:
                stylesheet = f"background-color: {self._data[COLOR]}; {divider}"

                self.parent().setStyleSheet(stylesheet)

        else:
            self.parent().setStyleSheet(f"{divider}")

        self.setStyleSheet("border-top: 0px solid transparent;")

        if self._data[USE_DOTS]:
            self._dots.setLength(len(self.wizard().pageIds()))
            self._dots.setIndicatorPos(self.wizard()._current_page_index())

    def showEvent(self, a0: QtGui.QShowEvent):
        self.setupPage()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self._data[USE_DOTS]:
            self._dots.setGeometry(0, self.height() - self._dots.height(), self.width(), self._dots.height())
            self._dots.raise_()


class PictureTipPage(TipPage):
    def __init__(self, data):
        super(PictureTipPage, self).__init__(data)

        self._label = None
        self._picture = None

    @staticmethod
    def _load_from_path(path):
        return QPixmap(str(path))

    def initializePage(self) -> None:
        super(PictureTipPage, self).initializePage()

        if not self._label:
            self._picture = self._load_from_path(self._data[CONTENTS][0])
            self._label = QLabel(self)
            self._label.setPixmap(self._picture)

            self.layout().setContentsMargins(0, 0, 0, 0)
            self._label.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)

            self.layout().addWidget(self._label, 0, 0)


class SimpleHtmlTipPage(TipPage):
    def __init__(self, data):
        super(SimpleHtmlTipPage, self).__init__(data)
        self._data = data
        self._text_browser = None

    def _load_from_path(self):
        text = None

        if len(self._data) > 0:
            with open(self._data[0], 'r') as file_h:
                text = file_h.read()

        if not text:
            text = f'file {self._data[0]} missing...'

        return text

    def initializePage(self) -> None:
        super(SimpleHtmlTipPage, self).initializePage()

        if not self._text_browser:
            self._text_browser = QTextBrowser(self)
            self.layout().addWidget(self._text_browser, 0, 0)
            self._text_browser.setFrameStyle(QFrame.NoFrame)

            self._text_browser.setOpenExternalLinks(True)
            text = _read_text_from_field_or_file(self._data, CONTENTS)

            self._text_browser.setHtml(text)
        self.layout().setContentsMargins(0, 0, 0, 0)


TIP_PAGE_TYPE_TO_HANDLER = {
    SIMPLE_HTML: SimpleHtmlTipPage,
    PICTURE    : PictureTipPage
    }


# wizard pages: picture, html, movie (not implemented yet)
def _read_text_from_field_or_file(data, field):
    result = ""

    if field in data:
        result = data[field]
        if isinstance(result, list):
            result = '\n'.join(result)

        try:
            if PATH in data:
                text_file_name = data[PATH].parents[0] / result
                if text_file_name.exists() and text_file_name.is_file():
                    with open(text_file_name, 'r') as file_h:
                        result = file_h.read()
        except OSError:
            pass
    return result


class TipOfTheDayWindow(QWizard):
    dont_show = pyqtSignal(bool)
    seen_tips = pyqtSignal(list)

    def __init__(self, parent=None, seen_perma_ids=(), dont_show_tips=False, standalone=False,
                 mode=MODE_TIP_OF_THE_DAY):

        _load_default_setup_if_required()

        super(TipOfTheDayWindow, self).__init__(parent=parent)

        self._page_list = []
        self._id_path = {}
        self._visited_pages = set()
        self._id_page = {}
        self._page_path_to_perma_id = {}
        self._seen_perma_ids = set(seen_perma_ids)
        self._standalone = standalone

        self._mode = mode

        self.setWizardStyle(QWizard.ModernStyle)

        if not standalone:
            self._dont_show_tips_button = CheckBox(PLACE_HOLDER)
        self._random_tip_button = Button(PLACE_HOLDER)

        self.setOption(HAVE_RANDOM_TIP_BUTTON, True)
        self.setOption(HAVE_DONT_SHOW_TIPS_BUTTON, not standalone)

        self.setOption(QWizard.HaveNextButtonOnLastPage, True)

        if not standalone:
            self.setButton(DONT_SHOW_TIPS_BUTTON, self._dont_show_tips_button)
            if dont_show_tips:
                self._dont_show_tips_button.setCheckState(Qt.Checked)
            self._dont_show_tips_button.stateChanged.connect(self._dont_show_clicked)

        self.setButton(RANDOM_TIP_BUTTON, self._random_tip_button)

        self.button(BUTTON_IDS[TIPS_SETUP[DEFAULT]]).setAutoDefault(True)

        self.setOption(QWizard.NoCancelButton, False)

        for button, text in TIPS_SETUP[self._mode][BUTTONS].items():
            button = BUTTON_IDS[button]
            self.setButtonText(button, text)

        layout = [BUTTON_IDS[button] for button in TIPS_SETUP[self._mode][LAYOUT]]

        if standalone:
            position = layout.index(DONT_SHOW_TIPS_BUTTON)
            if position >= 0:
                del layout[position]

        self.setButtonLayout(layout)

        self.setWindowTitle(TIPS_SETUP[self._mode][TITLE])

        self.customButtonClicked.connect(self._button_clicked)
        self.currentIdChanged.connect(self._page_visited)

        self._load_pages()

        self.setTitleFormat(Qt.RichText)

        random.seed(1)

        self._centre_window()

        self._setStyle()

    def _setStyle(self):
        _style = """QPushButton { padding: 2px 5px 2px 5px; }
                    QPushButton:focus {
                        padding: 0px;
                        border-color: palette(highlight);
                        border-style: solid;
                        border-width: 1px;
                        border-radius: 2px;
                    }
                    QPushButton:disabled {
                        color: palette(dark);
                        background-color: palette(midlight);
                    }
                    """
        self.setStyleSheet(_style)
        for button in TIPS_SETUP[self._mode][BUTTONS]:
            button = BUTTON_IDS[button]
            self.button(button).setStyleSheet(_style)

    def isStandalone(self):
        return self._standalone

    def _dont_show_clicked(self, state):
        if state == Qt.Checked:
            self.dont_show.emit(True)
        else:
            self.dont_show.emit(False)

    def _current_page_index(self):
        return self._page_list.index(self.currentId())

    @staticmethod
    def _load_tip_dict(path):
        result = None
        try:
            with open(path, 'r') as file_h:
                result = hjson.loads(file_h.read())
        except (EnvironmentError, HJSON_ERROR) as e:
            print(f"WARNING: couldn't load tip file {path} because {e}")

        return result

    def _load_tip_file_data(self):
        files = []
        for directory_name in TIPS_SETUP[self._mode][DIRECTORIES]:
            identifiers = [identifier.split('/') for identifier in TIPS_SETUP[self._mode][IDENTIFIERS]]
            for identifier_parts in identifiers:
                identifier_pattern = os.path.join(directory_name, *identifier_parts)

                tip_file_list = glob(identifier_pattern)

                file_parts = dict(
                        [(Path(file_path), file_path[len(directory_name) + 1:]) for file_path in tip_file_list])

                file_parts = self._filter_dict_by_values(file_parts, self._seen_perma_ids)

                self._page_path_to_perma_id.update(file_parts)

                files.extend(file_parts.keys())

        results = []

        for file in files:
            tip_data = self._load_tip_dict(file)
            if ORDER not in tip_data:
                tip_data[ORDER] = MAX_ORDER

            for i, data_file in enumerate(tip_data[CONTENTS]):
                tip_data[CONTENTS][i] = str(file.parent / tip_data[CONTENTS][i])

            tip_data[PATH] = file
            results.append(tip_data)

        results.sort(key=itemgetter(ORDER))

        return results

    def _filter_dict_by_values(self, in_dict, filter_values):
        filtered_file_parts = {}
        for file_path, perma_id in in_dict.items():
            if not perma_id in filter_values:
                filtered_file_parts[file_path] = perma_id
        return filtered_file_parts

    def setup_page_from_tip_file(self, tip_file):
        tip_type = tip_file[TYPE]
        handler = TIP_PAGE_TYPE_TO_HANDLER[tip_type]

        copy_attributes = HAS_DIVIDER, DIVIDER_WIDTH, DIVIDER_COLOR

        for attribute in copy_attributes:
            if attribute in TIPS_SETUP[self._mode]:
                tip_file[attribute] = TIPS_SETUP[self._mode][attribute]

        if USE_DOTS not in tip_file:
            tip_file[USE_DOTS] = TIPS_SETUP[self._mode][USE_DOTS]

        if handler is not None:

            styles = {}
            if STYLES in tip_file:
                styles_data = tip_file[STYLES]
                if isinstance(styles_data, str):
                    styles.update(self._load_styles_from_file(styles, tip_file))
                elif isinstance(styles_data, dict):
                    for style, value in styles_data.items():
                        if style == STYLE_FILE:
                            styles.update(self._load_styles_from_file(value, tip_file))
                        else:
                            styles[style] = value

            title = _read_text_from_field_or_file(tip_file, HEADER)

            try:
                title = title % styles
            except Exception as e:
                print(f'WARNING: failed to apply style because of {e}')

            page = handler(tip_file)

            page.setTitle(title)

            page.setMinimumSize(*TIPS_SETUP[self._mode][MIN_SIZE])

            return page

    @staticmethod
    def _load_styles_from_file(styles, tip_file):
        try:
            style_path = tip_file[PATH].parents[0] / styles
            with open(style_path, 'r') as file_h:
                styles = hjson.loads(file_h.read())
        except IOError:
            pass
        if not isinstance(styles, dict):
            print(f"WARNING: styles field in file {tip_file[PATH]} is not a dict!")
        return styles

    def _load_pages(self):
        tip_files = self._load_tip_file_data()

        for tip_file in tip_files:
            page = self.setup_page_from_tip_file(tip_file)

            tip_id = self.addPage(page)
            self._id_path[tip_id] = tip_file
            self._page_list.append(tip_id)
            self._id_page[tip_id] = page

        if len(self._page_list) == 1:
            self._disable_random_tips()

        if len(self._page_list) == 0:

            if self._mode == MODE_KEY_CONCEPTS:
                header = "Note: the key concept viewer is not correctly configured..."
            else:
                header = "All Tips viewed: no more tips to show..."

            info_page = {
                HEADER  : header,
                TYPE    : "simple-html",
                CONTENTS: TIPS_SETUP[self._mode][EMPTY_TEXT],
                PATH    : Path(os.path.realpath(__file__)),
                USE_DOTS: False
                }

            page = self.setup_page_from_tip_file(info_page)
            tip_id = self.addPage(page)
            self._page_list.append(tip_id)

    def nextId(self) -> int:
        current_id = self.currentId()
        if len(self._page_list) and current_id in self._page_list:
            index = self._page_list.index(current_id)
        else:
            index = -1

        result = -1
        if index >= 0:
            if index < len(self._page_list) - 1:
                result = self._page_list[index + 1]
            else:
                result = -1
        elif index == -1 and len(self._page_list) > 0:
            result = self._page_list[0]

        if not self._have_more_pages():
            self._disable_random_tips()

        return result

    def _have_more_pages(self):
        return len(self._visited_page_ids()) != len(self._page_list) - 1

    def setMode(self, mode):
        self._mode = mode

    # https://stackoverflow.com/questions/42324399/how-to-center-a-qdialog-in-qt
    def _centre_window(self):
        host = self.parentWidget()

        if host:
            hostRect = host.geometry()
            self.move(hostRect.center() - self.rect().center())

        else:
            screenGeometry = QApplication.desktop().screenGeometry()
            x = int((screenGeometry.width() - self.width()) / 2)
            y = int((screenGeometry.height() - self.height()) / 2)
            self.move(x, y)

    def _visited_page_ids(self):
        return set(self._visited_pages)

    def _all_page_ids(self):
        return set(self.pageIds())

    def _unvisited_page_ids(self):
        return self._all_page_ids() - self._visited_page_ids()

    def _button_clicked(self, button_clicked):
        if button_clicked == RANDOM_TIP_BUTTON:
            self._random_tip()

    def _random_tip(self):
        available_ids = list(self._unvisited_page_ids())
        next_id = random.choice(available_ids)

        current_index = self._page_list.index(self.currentId())
        self._page_list.remove(next_id)
        self._page_list.insert(current_index + 1, next_id)

        if len(available_ids) <= 1:
            self._disable_random_tips()

        self.next()

    def _disable_random_tips(self):
        self.button(RANDOM_TIP_BUTTON).setEnabled(False)

    def done(self, result):
        super(TipOfTheDayWindow, self).done(result)

        self.seen_tips.emit(self._get_seen_tips_perma_ids())

    def _get_seen_tips_perma_ids(self):
        seen_tips = self._get_seen_tips()
        perma_ids = [self._page_path_to_perma_id[tip_path] for tip_path in seen_tips]
        return perma_ids

    def _get_seen_tips(self):
        seen_tips = []
        for page_id in self._visited_pages:
            if page_id in self._id_path:
                seen_tips.append(self._id_path[page_id][PATH])
        return seen_tips

    def _page_visited(self, page_id):
        self.adjustSize()
        if page_id != -1:
            self._visited_pages.add(page_id)
            self.seen_tips.emit(self._get_seen_tips_perma_ids())

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self.adjustSize()
        self._centre_window()
        super(TipOfTheDayWindow, self).showEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # wizard = TipOfTheDayWindow(mode=MODE_KEY_CONCEPTS)
    wizard = TipOfTheDayWindow(mode=MODE_TIP_OF_THE_DAY)

    wizard.show()
    wizard.exec_()

    sys.exit(app.exec())
