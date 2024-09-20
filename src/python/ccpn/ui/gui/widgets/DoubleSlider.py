import sys

from PyQt5 import QtGui
from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, QObject, QRect, QPoint, pyqtProperty
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPainterPath, QPainter, QPen, QColor, QLinearGradient, QBrush, QFont, QFontMetrics, QCursor, \
    QGuiApplication, QIcon, QScreen
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsItem, QGraphicsItemGroup, QGraphicsRectItem, QLabel, \
    QWidget, QGraphicsObject, QCheckBox, QLineEdit, QFormLayout, QTextEdit, QToolButton, QDialog, \
    QComboBox, QStyle
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon, DoubleLabel, Side


# class MyGraphicsScene(QGraphicsScene):
#     def drawBackground(self, painter, rect):
#         myBrush = QBrush('red')
#         painter.setBrush(myBrush)
#         self.setBackgroundBrush(brush)
#
#
#         super(MyGraphicsScene, self).drawBackground(painter, rect)
#         painter.fillRect(rect, myBrush)

# TODO disabled state centre widget line wrong color
# * TODO cleanup code - done
# * TODO set values - done
# * TODO set ranges - done
# * TODO dragging handles specialise bubble code - done
# * TODO bubble should display formatted value - done
# * TODO system should broadcast converted values - done
# - TODO adapt balloon to size of children
# TODO remove 'arbitrary' fudge factors
# TODO off by 1 error on handle balloon position
# - TODO when dragging handles balloon position overruns - done
# TODO support for mouse wheel
# TODO add timer to display balloon window
# * TODO pull request - done
# * done TODO signals not firing on value changes from properties
# TODO demo values should update on typing
# * TODO setting left and right values wrong way round via text controls swaps handles! - done
# * TODO setting left and right values wrong way round via text controls gives negative gap! -done

CCPN_PURPLE = '#686dbe'
OFF_LINE_COLOUR = '#dbdbdb'

LEFT = 0
RIGHT = 1
BOTH = 2

OPPOSITE_SIDES = {
    Side.TOP   : Side.BOTTOM,
    Side.BOTTOM: Side.TOP,
    Side.LEFT  : Side.RIGHT,
    Side.RIGHT : Side.LEFT
    }


class DoubleRangeView(QGraphicsView):
    # signals
    valuesChanged = pyqtSignal(int, int, name='valuesChanged')
    displayValues = pyqtSignal(object, object, name='displayValues')
    rangeChanged = pyqtSignal(int, int, name='rangeChanged')
    sliderPressed = pyqtSignal(int, name='sliderPressed')
    sliderReleased = pyqtSignal(int, name='sliderReleased')

    def __init__(self):

        super(DoubleRangeView, self).__init__()

        self._slider = Slider()
        self._slider.setName('slider')

        self._balloon = SpeechBalloon(owner=self, on_top=True)

        label = DoubleLabel(parent=self._balloon)
        self._balloon.setCentralWidget(label)
        self._balloon.setAttribute(Qt.WA_ShowWithoutActivating)

        self._single_unit_move = 10
        self._repeat_time = 100
        self._repeat_timer = None

        self._enabled = True

        self._min_value = 1
        self._max_value = 100

        self._value_formatter = None
        self._value_converter = None

        self._values = self._min_value, self._min_value

        self.setBackgroundBrush(QBrush(QColor('#e9e9e9')))

        self.setScene(QGraphicsScene())
        scene_width = self.frameSize().width()
        scene_height = self.frameSize().height()
        self.setSceneRect(0, 0, scene_width, scene_height)

        self._track = Track(x_radius=3, y_radius=3)
        self._track.setName('track')
        self._track.setPen(QPen(QColor('#9f9f9f')))
        self._track.setBrush(QBrush(QColor('white')))

        self.scene().addItem(self._track)

        self.scene().addItem(self._slider)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.HighQualityAntialiasing)

        QApplication.instance().applicationStateChanged.connect(self._change_activation)

        self.setMouseTracking(True)

    def setValueConverter(self, converter):
        """
        takes a value an converts it for display
        :param converter: function taking a single value and returning a single value
        :return:
        """
        self._value_converter = converter

    def setValueFormatter(self, formatter):
        """
        takes a value and formats it to a string for display

        :param formatter:  function taking a single value and returning a single string
        """
        self._value_formatter = formatter

    def _swapMinMaxIfRequired(self):
        if self._min_value > self._max_value:
            self._max_value, self._min_value = self._min_value, self._max_value

        print('WARNING: min and max values inverted in double slider: correcting ')

    @pyqtProperty(float)
    def minValue(self):
        return self._min_value

    @minValue.setter
    def setMinValue(self, value):
        self._min_value = value

        self._swapMinMaxIfRequired()

        #TODO: update controls

    @pyqtProperty(float)
    def maxValue(self):
        return self._max_value

    @maxValue.setter
    def setMaxValue(self, value):
        self._max_value = value

        self._swapMinMaxIfRequired()

        # TODO: update controls

    @pyqtProperty(float)
    def pageStep(self):
        return self._single_unit_move

    @pageStep.setter
    def pageStep(self, page_step):
        self._single_unit_move = page_step

        # pageStep: int
        # TODO: single step

    @pyqtProperty(tuple)
    def values(self):
        return tuple(self._values)

    @values.setter
    def values(self, values):
        self.setValues(values)

    def _calculate_min_max_handle_centre_positions(self, global_system=True):
        scene_rect = self.sceneRect()
        if global_system:
            global_pos = self.mapToGlobal(scene_rect.topLeft().toPoint())
            scene_rect = QRect(global_pos, scene_rect.size().toSize())

        min_x = scene_rect.left() + self._slider._handle_left.width() / 2
        max_x = scene_rect.right() - self._slider._handle_right.width() / 2

        return min_x, max_x

    def setValues(self, values):
        left_value, right_value = values
        if left_value > right_value:
            left_value, right_value = right_value, left_value

        self._values = [left_value, right_value]

        self._calculate_min_max_pixel_ranges()
        min_position, max_position = self._min_max_handle_positions()

        proportions = self._proportions_from_values((left_value, right_value))

        position_range = max_position - min_position
        positions = []
        for proportion in proportions:
            positions.append(min_position + (proportion * position_range))

        self._slider.removeFromGroup(self._slider._handle_left)
        self._slider.removeFromGroup(self._slider._handle_right)

        centre_min_width_2 = self._slider._centre.min_width() / 2

        # TODO WHY A FACTOR OF 0.5..
        left_slider_position = positions[LEFT] - centre_min_width_2 - (self._slider._handle_left.width() / 2) + 0.5
        right_slider_position = positions[RIGHT] + centre_min_width_2 + (self._slider._handle_right.width() / 2) + 0.5

        self._slider._handle_left.setPos(QPointF(left_slider_position, self._slider._handle_left.pos().y()))
        self._slider._handle_right.setPos(right_slider_position, self._slider._handle_right.pos().y())

        self._slider.addToGroup(self._slider._handle_left)
        self._slider.addToGroup(self._slider._handle_right)

        self._slider._centre.setText('%i' % ((right_value - left_value) + 1))

        self._slider._expand_centre()

    @pyqtProperty(int, int)
    def range(self):
        return self._min_value, self._max_value

    @range.setter
    def setRange(self, min_value, max_value):
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        self._min_value = min_value
        self._max_value = max_value

        self.rangeChanged.emit(self._min_value, self._max_value)

        orig_values = list(self._values)
        updated_values = list(self._values)

        if self._values[LEFT] < min_value:
            updated_values[LEFT] = min_value
        if self.values[LEFT] > max_value:
            updated_values[LEFT] = max_value

        if self._values[RIGHT] < min_value:
            updated_values[RIGHT] = min_value
        if self.values[RIGHT] > max_value:
            updated_values[RIGHT] = max_value

        if orig_values != updated_values:
            self.setValues(*updated_values)

    def _handle_rects_from_positions(self, positions):

        centre_min_width_2 = self._slider._centre.min_width()

        left_handle = self._slider._handle_left
        left_rect = left_handle.rect().translated(0, 0)
        left_rect.setLeft(positions[0] - left_handle.width() - centre_min_width_2)
        left_rect.setRight(left_rect.left() + left_handle.width())

        right_handle = self._slider._handle_right
        right_rect = right_handle.rect().translated(0, 0)
        right_rect.setRight(positions[1] + right_handle.width() - centre_min_width_2)
        right_rect.setLeft(right_rect.right() - right_handle.width())

        return left_rect, right_rect

    def _proportions_from_values(self, values):
        value_range = self._max_value - self._min_value

        result = []
        for value in values:
            result.append((value - self._min_value) / value_range)
        return result

    # not implemented
    # sliderDown: bool
    # sliderPosition: int
    # tracking: bool

    def _change_activation(self, state):
        if state != Qt.ApplicationActive:
            self._balloon.hide()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super(DoubleRangeView, self).showEvent(event)
        self.rangeChanged.emit(self._min_value, self._max_value)
        self.valuesChanged.emit(*self._values)
        display_values = self._calculate_display_values(self._values)
        self.displayValues.emit(*display_values)

    def _calculate_min_max_pixel_ranges(self):
        """
            Calculate the pixels between the min and max values
            of the positions of the handles

            :return:
        """
        width = self.sceneRect().width()

        slider_min_width = self._slider.min_width()
        slider_min_width_2 = slider_min_width / 2.0

        range_min = slider_min_width_2
        range_max = width - slider_min_width_2

        return range_min, range_max

    def _calculate_handle_scene_positions(self):
        """
            calculates handle positions in pixels in the scene coordinate space
            handles positions are calculated as left edge + 1/2 min width of centre
            :return: float,float positions
        """
        centre_min_width_2 = self._slider._centre.min_width() / 2

        left_position = self._slider._handle_left.reference_position_scene() + centre_min_width_2
        right_position = self._slider._handle_right.reference_position_scene() - centre_min_width_2

        return left_position, right_position

    def _update_value(self):
        """
            after moving a slider re-calculate values, set them and emit them, also update center text

            :return: None
        """
        values = self._calculate_values()

        size = values[RIGHT] - values[LEFT]

        self._slider._centre.setText(str(int(size + 1)))

        self._values = values

        self.valuesChanged.emit(int(values[LEFT]), int(values[RIGHT]))
        display_values = self._calculate_display_values(values)
        self.displayValues.emit(*display_values)

    def _calculate_values(self):
        """
            calculate the left and right slider values from the current slider positions

            :return: int, int left and right values
        """

        positions = self._calculate_handle_scene_positions()

        proportions = self._calculate_proportions_from_positions(positions)

        # range is inclusive
        value_range = (self._max_value - self._min_value)

        result = []
        for proportion in proportions:
            result.append(self._min_value + (proportion * value_range))

        return result

    def _calculate_proportions_from_positions(self, positions):

        """
            given left and right positions calculate their fractional proportions [0.0...1.0] across the controls range

            :param positions: positions of the two sliders in scene space
            :return: fractional positions
        """
        range_min, range_max = self._calculate_min_max_pixel_ranges()

        raw_range = range_max - range_min

        result = []
        for raw_value in positions:
            result.append((raw_value - range_min) / raw_range)

        return result

    def _calculate_positions_from_proportions(self, proportions):
        range_min, range_max = self._calculate_min_max_pixel_ranges()

        raw_range = range_max - range_min

        result = []

        for proportion in proportions:
            result.append(range_min + (proportion * raw_range))

        return result

    def resizeEvent(self, event):
        our_scene = self.scene()
        if our_scene:
            width = event.size().width()
            height = event.size().height()

            # this makes ure the anti aliasing fits in...
            self.setSceneRect(0, 0, width, height)
            self.scene().setSceneRect(0, 0, width, height)

        self._update_controls()

        super(DoubleRangeView, self).resizeEvent(event)

    def _update_controls(self):
        # this just ensures the control is mapped into the track for now
        # but will screw up positioning so we would need something more
        # sophisticated here it may also have to vary the controller width
        # and track size...
        self._slider.move_into_scene()
        track_rect = self.sceneRect()
        track_rect.setWidth(self.sceneRect().width() - self._slider.width())
        track_rect.setHeight(6)
        self._track.setRect(track_rect)
        self._track.setPos(self._slider.width() / 2.0, (self.sceneRect().height() / 2.0) - 4)

    def mouseDoubleClickEvent(self, event):

        if self._enabled:
            x_offset = (event.pos() - self._slider.sceneBoundingRect().center()).x()

            item_at = self.itemAt(event.pos())
            if item_at not in self._slider.childItems():
                self._slider._offset_slider(x_offset, self._slider.pos(), self._slider.sceneRect())

            self._update_value()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        item_at = self.itemAt(event.pos())
        child_items = self._slider.childItems()
        item_at_in_slider = item_at in child_items

        if self._enabled and not item_at_in_slider:

            self._repeat_timer = QTimer(self)
            self._repeat_timer.setSingleShot(False)
            self._repeat_timer.timeout.connect(self._single_click_move)
            self._repeat_timer.start(self._repeat_time)
            self._update_value()
        else:
            event.ignore()

        super(DoubleRangeView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):

        if self._enabled:
            # if not self._ignore_release:
            super(DoubleRangeView, self).mouseReleaseEvent(event)
            if not event.isAccepted():
                self.single_click_move(event)

            if self._repeat_timer:
                self._repeat_timer.stop()
                self._repeat_timer = None
            # self._ignore_release = False
        else:
            event.ignore()

    def _min_max_handle_positions(self, global_system=False):
        """
            Calculate the minimum and maximum positions of the handles
            either in the scene or global coordinate system

            :param global_system: if True use global coordinate system other scene
            :return: float,float min_position, maximum_position
        """
        centre_width_2 = self._slider._centre.min_width() / 2

        slider_width_left = self._slider._handle_left.width()
        slider_width_right = self._slider._handle_right.width()

        scene_top_left = self.sceneRect().topLeft().toPoint()
        scene_bottom_right = self.sceneRect().bottomRight().toPoint()

        if global_system:
            scene_top_left = self.mapToGlobal(scene_top_left)
            scene_bottom_right = self.mapToGlobal(scene_bottom_right)

        scene_left = scene_top_left.x()
        scene_right = scene_bottom_right.x()

        min_width = scene_left + slider_width_left + centre_width_2 - 0.5
        max_width = scene_right - slider_width_right - centre_width_2 - 0.5
        return min_width, max_width

    def _position_to_value(self, pos):
        """
            calculate the value of a position given in in pixels in global coordinates

            :param pos: the position in the global coordinate system
            :return: float the value
        """

        min_pos, max_pos = self._min_max_handle_positions(global_system=True)

        slider_range = max_pos - min_pos
        proportion = (pos - min_pos) / slider_range

        return (proportion * (self._max_value - self._min_value)) + 1

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:

        if self._enabled:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            item_pos = self._track.mapFromScene(scene_pos)
            slider_scene_rect = self._slider.sceneRect()

            self._track._line_pos = item_pos.x()
            self._track.update()

            slider_state = self._slider._long_click_state
            last_click_widget = self._slider._last_click_widget

            control_rect = self.geometry()
            control_rect = QRect(self.mapToGlobal(control_rect.topLeft()), control_rect.size())

            if slider_state == self._slider.INSIDE:
                min_x, max_x = self._calculate_min_max_handle_centre_positions(global_system=True)
            else:
                # TODO: needs limiting by position of handles...
                min_x, max_x = self._min_max_handle_positions(global_system=True)

            event_x = event.globalPos().x()
            if event_x < min_x:
                event_x = min_x
            elif event_x > max_x:
                event_x = max_x

            balloon_pos = QPoint(int(event_x), int(control_rect.top() - 4))

            self._balloon.show()
            self._balloon.move_pointer_to(balloon_pos)

            if slider_state == self._slider.INSIDE:
                if last_click_widget == self._slider._handle_left:
                    values = [self._values[LEFT]]
                elif last_click_widget == self._slider._handle_right:
                    values = [self._values[RIGHT]]
            elif slider_scene_rect.contains(scene_pos) and slider_state == self._slider.OUTSIDE:
                values = list(self._values)
            elif slider_state == self._slider.SINGLE:
                values = list(self._values)
            else:
                values = [self._position_to_value(event_x)]

            if len(values) == 2 and (values[0] == values[1]):
                values = [values[0]]

            display_values = self._calculate_display_values(values)
            display_strings = ['%4.1f' % value for value in display_values]

            self._balloon.centralWidget().setLabels(display_strings)

        return super(DoubleRangeView, self).mouseMoveEvent(event)

    def _calculate_display_values(self, values):
        result = list(values)

        if self._value_converter:
            for i, value in enumerate(values):
                result[i] = self._value_converter(value)
        return result

    def leaveEvent(self, event):
        super(DoubleRangeView, self).leaveEvent(event)
        self._track._line_pos = None
        self._track.update()
        self._balloon.hide()

    def _single_click_move(self):
        pos = self.mapFromGlobal(QCursor.pos())
        pos = self.mapToScene(pos)
        self.single_click_move(pos)

    def single_click_move(self, pos):

        x_offset = 0

        if (QGuiApplication.keyboardModifiers() & Qt.ShiftModifier) == Qt.ShiftModifier:
            move = 1
        else:
            move = self._single_unit_move

        if pos.x() < self._slider.sceneBoundingRect().center().x():
            x_offset = -move
        elif pos.x() > self._slider.sceneBoundingRect().center().x():
            x_offset = move

        slider_rect = self._slider.sceneBoundingRect().translated(0, 0)
        slider_rect.translate(QPointF(x_offset, 0))

        dist = pos.x() - slider_rect.center().x()

        if abs(dist) < self._single_unit_move:
            x_offset = dist
        self._slider._offset_slider(x_offset, self._slider.scenePos(), self._slider.sceneRect())

    def setEnabled(self, enabled):
        self._enabled = enabled
        self._slider.setEnabled(enabled)
        self._track.setEnabled(enabled)
        if not enabled:
            self._balloon.hide()


class Named:
    def __init__(self):
        self._name = ''

    def setName(self, name):
        self._name = name

    def name(self):
        return self._name


class GraphicsRoundedRectItem(QGraphicsRectItem, Named):

    def __init__(self, *args, x_radius=0, y_radius=0, **kwargs):
        super(GraphicsRoundedRectItem, self).__init__(*args, **kwargs)

        self._x_radius = x_radius
        self._y_radius = y_radius

    def paint(self, painter, option, target_widget):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawRoundedRect(self.rect(), self._x_radius, self._y_radius)
        # if (option->state & QStyle::State_Selected)
        #     qt_graphicsItem_highlightSelected(this, painter, option);

    def shape(self) -> QtGui.QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self.rect(), self._x_radius, self._y_radius)

        return path


class Track(GraphicsRoundedRectItem, Named):

    def __init__(self, *args, **kwargs):
        super(Track, self).__init__(*args, **kwargs)

        self._line_pos = None

        self._marker_color = QColor(CCPN_PURPLE)
        self._marker_pen = QPen(self._marker_color)
        self._marker_pen.setWidth(2)

    def setEnabled(self, enabled: bool) -> None:
        super(Track, self).setEnabled(enabled)

        if enabled:
            self.setBrush(QColor('white'))
        else:
            self.setBrush(QColor('#e9e9e9'))
            self.setPen(QPen(QColor(OFF_LINE_COLOUR)))

    def paint(self, painter, option, target_widget):

        super(Track, self).paint(painter, option, target_widget)

        if self._line_pos and self.isEnabled():

            if self._marker_is_visible():
                painter.setPen(self._marker_pen)
                painter.setClipping(True)
                painter.setClipPath(self.shape())

                bottom = self.rect().bottom()
                top = self.rect().top()

                painter.drawLine(QPointF(self._line_pos, bottom), QPointF(self._line_pos, top))

    def _marker_is_visible(self):
        return (self.rect().left() + self._x_radius) < self._line_pos < (self.rect().right() - self._x_radius)


class Slider(QGraphicsItemGroup, Named):
    OUTSIDE = 'outside'
    INSIDE = 'inside'
    SINGLE = 'single'
    WAIT = 'wait'

    def __init__(self):

        super(Slider, self).__init__()
        self._centre = Centre(None, parent=self)
        self._handle_left = HandleItem(orientation=LEFT, parent=self)
        self._handle_right = HandleItem(orientation=RIGHT, parent=self)

        self._centre.setName('center')
        self._handle_left.setName('handle left')
        self._handle_right.setName('handle right')

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)

        self._update_layout()

        self._group_all()

        self._long_click_timer = None
        self._last_click_widget = None
        self._long_click_pos = None
        self._long_click_state = self.OUTSIDE
        self._long_click_widget_pos = None
        # self._widget_pos = {}
        self._widget_rect = None
        self._widget_pos = None

        self._last_mouse = None

        self._enabled = True

        self._last_mouse_scene = None
        self._long_click_rect = None

    def setHighlighted(self, highlighted):
        self._handle_left.setHighlighted(highlighted)
        self._handle_right.setHighlighted(highlighted)

    def rect(self):
        result = QRectF()
        for child in self.childItems():
            if isinstance(child, HandleItem):
                child_rect = child.rect()
                result = result.united(self.mapRectFromItem(child, child_rect))
        return result

    def min_width(self):
        return self._handle_left.rect().width() + self._centre.min_width() + self._handle_right.rect().width()

    def sceneRect(self):
        return self.mapRectToScene(self.rect())

    def setPos(self, *args):

        super(Slider, self).setPos(*args)

    def width(self):
        return self._handle_left.width() + self._centre.width() + self._handle_right.width()

    def _group_all(self):
        self.addToGroup(self._centre)
        self.addToGroup(self._handle_left)
        self.addToGroup(self._handle_right)

    def _update_layout(self):
        self._handle_left.setX(-(self._handle_left.width() / 2.0 + self._centre.width() / 2.0))
        self._handle_right.setX(self._handle_right.width() / 2.0 + self._centre.width() / 2.0)

    def _get_slider_y(self):
        return (self.rect().height() / 2) + 1

    def move_into_scene(self):
        view_rect = self.scene().sceneRect()
        control_rect = self.mapRectToScene(self.rect())

        x_offset_change = self.get_offset_to_inside(control_rect, view_rect)
        x_pos = self.pos().x()
        x_pos += x_offset_change
        self.setPos(x_pos, self._get_slider_y())

    # def itemChange(self, change, value):
    #
    #     if self.scene() and change == QGraphicsItem.ItemPositionChange:
    #         print('item change value', value)
    #         view_rect = self.scene().sceneRect()
    #         control_rect = self.mapRectToScene(self.boundingRect())
    #
    #
    #         # print(value, )            print(self.name())
    #         raw_range_min, raw_range_max = self._get_view()._calculate_raw_range()
    #         if value.x() < raw_range_min:
    #             value.setX(raw_range_min)
    #         if value.x() > raw_range_max:
    #             value.setX(raw_range_max)
    #
    #         # change = value - self.pos()
    #         #
    #         # control_rect.adjust(change.x(), 0, change.x(), 0)
    #         #
    #         # offset_change = self.get_offset_to_inside(control_rect, view_rect)
    #         # offset = value.x()
    #         # offset += offset_change
    #         # value.setX(offset)
    #
    #         y_offset = 0
    #         if view_rect.height() > control_rect.height():
    #             y_offset = (view_rect.height() - control_rect.height()) / 2
    #
    #         value.setY((self.rect().height() / 2) + y_offset)
    #
    #         result = value
    #
    #         # print('item change', self._last_click_widget, self._long_click_state)
    #     else:
    #         result = super(Slider, self).itemChange(change, value)
    #
    #     # print('item change', result)
    #     return result

    @staticmethod
    def get_offset_to_inside(control_rect, view_rect):
        offset_change = 0
        if control_rect.left() < 0:
            offset_change = - control_rect.left()
        if control_rect.right() > view_rect.right():
            offset_change = - (control_rect.right() - view_rect.right())
        return offset_change

    # def view_rect_in_scene(self):
    #     result = None
    #     our_scene = self.scene()
    #     if our_scene is not None:
    #         our_view = our_scene.views()[0]
    #         # print(our_view.transform().dx(), our_view.transform().dy())
    #         result = our_view.mapToScene(our_view.viewport().geometry()).boundingRect()
    #
    #     return result

    def mousePressEvent(self, event):
        handle_click = False

        self._last_mouse = event.pos()
        self._last_mouse_scene = event.scenePos()

        if self._enabled:

            for child in self.childItems():
                child_pos = child.mapFromScene(event.scenePos())

                self._last_click_widget = self
                if child.rect().contains(child_pos):
                    if child in (self._handle_left, self._handle_right):
                        handle_click = True
                        self._last_click_widget = child
                        self._long_click_rect = child.sceneRect()
                        self._long_click_widget_pos = child.pos()
                        break

                    if child == self._handle_left:
                        self.parent().sliderPressed.emit(LEFT)

            self._widget_rect = self.sceneRect()
            self._widget_pos = self.scenePos()
            self._long_click_pos = event.scenePos()

            if handle_click:
                event.accept()
                self._long_click_timer = QTimer()
                self._long_click_timer.setSingleShot(True)
                self._long_click_timer.timeout.connect(self._long_clicked)
                self._long_click_timer.start(1000)

                self._long_click_state = self.WAIT

                super(Slider, self).mousePressEvent(event)

            else:
                event.accept()
                self._long_click_state = self.SINGLE

                super(Slider, self).mousePressEvent(event)

        else:
            event.ignore()

        super(Slider, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._enabled:
            if self._long_click_timer is not None:
                self._cancel_long_click()
            if self._last_click_widget:
                self._last_click_widget.setHighlighted(False)
                self._last_click_widget.update()
                self._get_view()._update_value()
            if self._long_click_state in [self.INSIDE, self.OUTSIDE]:
                event.accept()
                super(Slider, self).mouseReleaseEvent(event)
        else:
            event.ignore()

        super(Slider, self).mouseReleaseEvent(event)

        self._long_click_state = self.OUTSIDE

    def _cancel_long_click(self):
        if self._long_click_timer:
            self._long_click_timer.stop()
            self._long_click_timer = None
            self._long_click_state = self.SINGLE

    def mouseMoveEvent(self, event):

        local_pos = self._get_mouse_pos_item_coords()
        scene_pos = self.mapToScene(local_pos)

        if self._enabled:

            if self._long_click_state == self.WAIT:
                if (self._long_click_pos - scene_pos).manhattanLength() >= QApplication.startDragDistance():
                    self._cancel_long_click()
                    self._long_click_state = self.SINGLE
                    super(Slider, self).mouseMoveEvent(event)

            elif self._long_click_state == self.INSIDE:
                offset = local_pos - self._last_mouse

                event.accept()
                self.prepareGeometryChange()

                max_pos, min_pos = self._min_max_x_for_handle(self._last_click_widget)

                new_rect = self._long_click_rect.translated(0, 0)
                new_rect.translate(offset)

                if new_rect.left() < min_pos:
                    correction = min_pos - new_rect.left()
                elif new_rect.left() > max_pos:
                    correction = max_pos - new_rect.left()
                else:
                    correction = 0.0

                offset = offset.x() + correction

                self.offset_handle(offset)

            elif self._long_click_state != self.INSIDE:
                event.accept()

                offset = scene_pos - self._last_mouse_scene

                self._offset_slider(offset.x(), self._widget_pos, self._widget_rect)

            else:
                super(Slider, self).mouseMoveEvent(event)

        else:
            event.ignore()

    def _min_max_x_for_handle(self, target_widget):
        centre_min_width = self._centre.min_width()
        # min and max positions allowing for positions of other handle
        # measurements from left edge... [**not consistent**]
        # TODO: make consistent! we should always do all position in and measurements
        # from the virtual centre of the handle and then map to handles
        #   left: handle.right + min_width_centre/2
        #   right handle.left - min_width_centre/2
        if target_widget == self._handle_left:
            min_pos = self.scene().sceneRect().left()
            max_pos = self._handle_right.sceneRect().left() - centre_min_width - self._handle_left.width()
        elif target_widget == self._handle_right:
            min_pos = self._handle_left.sceneRect().right() + centre_min_width
            max_pos = self.scene().sceneRect().right() - self._handle_right.width()
        else:
            raise Exception(f"Error: widget must be either left or right handler got {widget}")
        return max_pos, min_pos

    def offset_handle(self, offset):
        our_view = self._get_view()
        new_pos = QPointF(self._long_click_widget_pos)
        new_pos.setX(new_pos.x() + offset)
        new_pos.setY(self._long_click_widget_pos.y())
        self._last_click_widget.setPos(new_pos)
        self._last_click_widget.setHighlighted(True)
        # this seems to be the only way to update the bounds ... weird!
        self.removeFromGroup(self._last_click_widget)
        self.addToGroup(self._last_click_widget)
        self._expand_centre()
        our_view._update_value()
        our_view._update_controls()

    def _offset_slider(self, offset, start_point, start_rect):
        our_view = self._get_view()
        raw_range_min, raw_range_max = self._get_view()._calculate_min_max_pixel_ranges()
        new_rect = start_rect.translated(0, 0)
        new_rect.translate(QPointF(offset, 0))
        range_pos_right = new_rect.right() - self._handle_right.width() - (self._centre.min_width() / 2)
        range_pos_left = new_rect.left() + self._handle_right.width() + (self._centre.min_width() / 2)
        if range_pos_left < raw_range_min:
            correction = raw_range_min - range_pos_left
        elif range_pos_right > raw_range_max:
            correction = raw_range_max - range_pos_right
        else:
            correction = 0
        offset = offset + correction
        #
        new_pos = QPointF(start_point)
        new_pos.setX(new_pos.x() + offset)
        new_pos.setY(self._get_slider_y())
        self.setPos(new_pos)
        our_view._update_value()

    def _get_mouse_pos_item_coords(self):

        cursor_pos = QCursor.pos()

        item_view = self._get_view()
        view_pos = item_view.mapFromGlobal(cursor_pos)

        scene_pos = item_view.mapToScene(view_pos)
        local_pos = self.mapFromScene(scene_pos)

        # there is always an offset of 1 here, not sure why...
        local_pos.setX(local_pos.x() - 1.0)
        local_pos.setY(local_pos.y() - 1.0)

        return local_pos

    def _get_view(self):
        return self.scene().views()[0]

    def _expand_centre(self):

        left = self._handle_left.pos().x() + self._handle_left.width() / 2.0
        right = self._handle_right.pos().x() - self._handle_right.width() / 2.0

        centre_x = left + ((right - left) / 2.0)
        centre_y = self._centre.pos().y()

        self._centre.setPos(centre_x, centre_y)
        self._centre.setWidth(right - left)

    def _long_clicked(self):
        self._long_click_timer = None
        self._long_click_state = self.INSIDE
        self._last_click_widget.setHighlighted(True)
        self._last_click_widget.update()


# noinspection PyMethodOverriding - draw method signature wrong
class GraphicsItemBase(QGraphicsObject):
    def __init__(self, parent=None):
        super(GraphicsItemBase, self).__init__(parent=parent)

        self._pen_width = 1

    def penWidth(self):
        return self._pen_width

    def setPenWidth(self, pen_width):
        self._pen_width = pen_width

    def rect(self):
        width_2 = self._width / 2.0
        height_2 = self._height / 2.0

        result = QRectF(-width_2, -height_2, self._width, self._height)

        return result

    def sceneRect(self):
        return self.mapRectToScene(self.rect())

    def boundingRect(self):
        pen_2 = self._pen_width / 2.0
        new_result = self.rect().adjusted(-pen_2, -pen_2, pen_2, pen_2)

        return new_result


class Centre(GraphicsItemBase, Named):
    def __init__(self, width=None, parent=None):
        super(Centre, self).__init__(parent=parent)

        self._height = float(28)
        self._text = '1'
        self._font = 'Helvetica'
        self._font_size = 13
        self._font_weight = QFont.Bold
        self._text_spacer = 3
        if width:
            self._width = float(width)
        else:
            self._width = self.min_width()

    def setText(self, text):
        self._text = text
        self.update()

    def width(self):
        return self._width

    @staticmethod
    def _max_width_digit():
        font = QFont("Helvetica", 13, QFont.Bold)
        metrics = QFontMetrics(font)
        width = 0
        for number in range(10):
            rect = metrics.tightBoundingRect(str(number))
            width = max(width, rect.width())
        return width

    def min_width(self):
        even_max_width_digit = self._max_width_digit()
        return even_max_width_digit + (2 * self._text_spacer)

    def height(self):
        return self._height

    def setWidth(self, width):
        self._width = width
        self.update(self.boundingRect())

    def paint(self, painter, option, target_widget):

        width_2 = self._width / 2.0
        height_2 = self._height / 2.0

        if self.isEnabled():
            brush = QBrush(QColor('#686dbe'))
        else:
            brush = QBrush(QColor('#e9e9e9'))

        painter.setBrush(brush)
        painter.setPen(Qt.transparent)

        painter.drawRect(self.rect())

        if self.isEnabled():
            pen = QPen(QColor('#9f9f9f'), self.penWidth())
        else:
            pen = QPen(QColor(OFF_LINE_COLOUR), self.penWidth())

        painter.setBrush(brush)
        painter.setPen(pen)

        left = -width_2 + (self.penWidth() / 2.0)
        right = width_2 - +(self.penWidth() / 2.0)
        painter.drawLine(QPointF(left, -height_2), QPointF(right, -height_2))
        painter.drawLine(QPointF(left, height_2), QPointF(right, height_2))

        font = QFont(self._font, self._font_size, self._font_weight)
        painter.setFont(font)

        if self.isEnabled():
            pen = QPen(QColor('white'))
        else:
            pen = QPen(QColor('#dbdbdb'))
        painter.setPen(pen)

        painter.drawText(self.rect(), Qt.AlignCenter, self._text)


# noinspection PyMethodOverriding - draw method signature wrong
class HandleItem(GraphicsItemBase, Named):

    def __init__(self, orientation=RIGHT, parent=None):
        super(HandleItem, self).__init__(parent=parent)

        self._width = float(10)
        self._height = float(28)
        self._radius = 4
        self._grip_length = 0.45
        self._grip_offset = 1.25
        self._orientation = orientation

        self._highlighted = False

        self._highlight_color = '#b9bbe0'  # '#686dbe'

    def reference_position_scene(self):
        """
            The position of the reference edge in scene space this is
                the right edge for the LEFT handle
                the left edge of the RIGHT handle

            :return: float reference position in scene space
        """

        if self._orientation == LEFT:
            position = self.mapToScene(self.rect().topRight()).x()
        elif self._orientation == RIGHT:
            position = self.mapToScene(self.rect().bottomLeft()).x()
        else:
            msg = f"""Unexpected error: bad orientation expected one of [LEFT,RIGHT] got {self._orientation}"""
            raise Exception(msg)

        return position

    def highlighted(self):
        return self._highlighted

    def setHighlighted(self, highlighted):
        self._highlighted = highlighted

    def width(self):
        return self._width

    def height(self):
        return self._height

    def paint(self, painter, option, target_widget):

        # could do with context manager
        painter.save()

        if self._highlighted:
            brush = QBrush(QColor(self._highlight_color))
        else:
            gradient = QLinearGradient(QPointF(0, -15), QPointF(0.0, 15))
            gradient.setColorAt(0, QColor('#fcfcfc'))
            gradient.setColorAt(1, QColor('#ededed'))
            brush = QBrush(gradient)
        if self.isEnabled():
            pen = QPen(QColor('#9f9f9f'), self.penWidth())
        else:
            pen = QPen(QColor(OFF_LINE_COLOUR), self.penWidth())

        painter.setBrush(brush)
        painter.setPen(pen)

        self._draw_handle(painter, self._orientation)

        # if self._orientation  ==  LEFT:
        #     pen = QPen(QColor('green'), self.penWidth())
        # else:
        #     pen = QPen(QColor('red'), self.penWidth())
        # painter.setPen(pen)
        # painter.drawLine(0,self.rect().topLeft().y(),0,self.rect().bottomRight().y())

        painter.restore()

    def _draw_handle(self, painter, orientation=RIGHT):

        width_2 = self._width / 2.0
        height_2 = self._height / 2.0

        x = -width_2
        y = -height_2
        w = self._width
        h = self._height
        r = self._radius

        handlePath = QPainterPath()

        if orientation == LEFT:
            handlePath.arcMoveTo(x, y, r, r, 180)
            handlePath.arcTo(x, y, r, r, 180, -90)
            handlePath.lineTo(x + w, y)
            handlePath.lineTo(x + w, y + h)
            handlePath.arcTo(x, y + h - r, r, r, 270, -90)
        elif orientation == RIGHT:
            handlePath.moveTo(x, 0)
            handlePath.lineTo(x, y)
            handlePath.arcTo(x + w - r, y, r, r, 90, -90)
            handlePath.arcTo(x + w - r, y + h - r, r, r, 0, -90)
            handlePath.lineTo(x, y + h)
        else:
            raise Exception('unexpected orientation %s' % orientation)

        handlePath.closeSubpath()
        painter.drawPath(handlePath)

        offset = self._grip_offset
        top = self._height / 2.0 * self._grip_length
        bottom = -top

        painter.drawLine(QPointF(-offset, top), QPointF(-offset, bottom))
        painter.drawLine(QPointF(offset, top), QPointF(offset, bottom))


class SelectArgument(QObject):
    output = pyqtSignal(object)

    def __init__(self, index):
        super(SelectArgument, self).__init__()
        self._index = index

    def input(self, *args):
        self.output.emit(args[self._index])


class MyApplication(QApplication):
    def __init__(self, arg):
        super(MyApplication, self).__init__(arg)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(0)

    def _update(self):
        pos = QCursor.pos()
        target_window = self.activeWindow()

        if window:
            target_window.move_pointer_to(pos)


class MyLabel(QLabel):

    def __init__(self, text, parent=None):
        super(MyLabel, self).__init__(text, parent)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super(MyLabel, self).paintEvent(a0)


class ConvertToStr(QObject):
    output = pyqtSignal(str)

    def __init__(self):
        super(ConvertToStr, self).__init__()
        self._converter = str

    def input(self, arg):
        self.output.emit(self._converter(arg))


class ConvertToInt(QObject):
    output = pyqtSignal(int)

    def __init__(self):
        super(ConvertToInt, self).__init__()
        self._converter = int

    def input(self, arg):
        value = None
        try:
            value = self._converter(arg)
        except ValueError:
            pass
        if value:
            self.output.emit(value)


class BufferTillEnter(QObject):
    output = pyqtSignal(str)

    def __init__(self):
        super(BufferTillEnter, self).__init__()
        self._buffer = ""

    def trigger(self):
        self.output.emit(self._buffer)

    def input(self, value):
        self._buffer = value


class SetOneOf(QObject):
    output = pyqtSignal(tuple)

    def __init__(self, index, target=None, instance=None):
        super(SetOneOf, self).__init__()
        self._index = index
        self._target = target
        self._instance = instance

    def input(self, value):

        if callable(self._target) and not isinstance(self._target, pyqtProperty):
            results = self._target()
        elif isinstance(self._target, (pyqtProperty, property)):
            results = self._target.__get__(self._instance, self._instance.__class__)
        else:
            raise Exception('unexpected')

        results = list(results)
        results[self._index] = value
        results = [int(result) for result in results]

        self.output.emit(tuple(results))


class PopoverButton(QToolButton):

    def __init__(self, balloon_side=Side.BOTTOM, *args, **kwargs):

        super(PopoverButton, self).__init__(*args, **kwargs)

        self.setFocusPolicy(Qt.NoFocus)

        self._balloon_side = balloon_side
        self._speech_balloon = SpeechBalloon(side=OPPOSITE_SIDES[balloon_side])
        self._speech_balloon.setWindowFlags(self._speech_balloon.windowFlags() | Qt.Popup)

        self.pressed.connect(self._press_handler)
        # self.setArrowType(Qt.DownArrow)
        self.setStyleSheet('''
                        border-style: solid;
                        border-width: 1px;
                        border-radius: 3px;
                        ''')

        # self.setAttribute(Qt.WA_MacShowFocusRect, 0)
        path = '/Users/garythompson/Dropbox/git/ccpnmr/ccpnmr_3.0.3.edge_gwv6/src/python/ccpn/ui/gui/widgets/icons/exclamation.png'
        self.setIcon(QIcon(path))

        self._event_filter = None

    @pyqtProperty(Side)
    def balloonSide(self):
        return self._balloon_side

    @balloonSide.setter
    def balloonSide(self, balloonSide):
        self.setBalloonSide(side)

    def setBalloonSide(self, side):
        self._balloon_side = side
        self._speech_balloon.pointerSide = OPPOSITE_SIDES[self._balloon_side]

    def _get_mouse_screen(self):

        position = QCursor.pos()

        result = None
        for screen in QGuiApplication.screens():
            if screen.geometry().contains(position):
                result = screen
                break

        return result

    def _press_handler(self):

        global_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.geometry().size())
        mouse_screen = self._get_mouse_screen()
        self._speech_balloon.showAt(global_rect, preferred_side=self._balloon_side, target_screen=mouse_screen)

    def popover(self):
        return self._speech_balloon


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = QMainWindow()

    widget = QWidget()

    test_button = PopoverButton(balloon_side=Side.RIGHT)
    label = QTextEdit('test2')

    test_button.popover().setCentralWidget(label)

    side_list = QComboBox()
    for side in Side:
        side_list.addItem(str(side.name), side)
    side_list.setCurrentIndex(OPPOSITE_SIDES[Side.LEFT])
    side_list.currentIndexChanged.connect(lambda: test_button.setBalloonSide(side_list.itemData(side_list.currentIndex(), Qt.UserRole)))

    left_value_display = QLabel()
    left_value_display.setText('unknown')
    right_value_display = QLabel()
    right_value_display.setText('unknown')
    check = QCheckBox()

    min_value_display = QLabel()
    min_value_display.setText('unknown')
    max_value_display = QLabel()
    max_value_display.setText('unknown')

    left_derived_value_display = QLabel()
    left_derived_value_display.setText('unknown')
    right_derived_value_display = QLabel()
    right_derived_value_display.setText('unknown')

    left_value_edit = QLineEdit()
    right_value_edit = QLineEdit()

    v_layout = QFormLayout()
    v_layout.addRow('Test button', test_button)
    v_layout.addRow('Side selector', side_list)
    v_layout.addRow('Left Value [signal]', left_value_display)
    v_layout.addRow('Right Value [signal]', right_value_display)
    v_layout.addRow('Min Value [signal]', min_value_display)
    v_layout.addRow('Max Value [signal]', max_value_display)
    v_layout.addRow('Derived value left [signal]', left_derived_value_display)
    v_layout.addRow('Derived value right[signal]', right_derived_value_display)
    v_layout.addRow('Left Value [set]', left_value_edit)
    v_layout.addRow('Right Value [set]', right_value_edit)

    v_layout.addRow('Enabled', check)

    container = QWidget()
    container.setLayout(v_layout)

    geometry = window.geometry()
    # this is really weird
    geometry.setHeight(200)
    window.setGeometry(geometry)
    # window.setStyleSheet('{ background-color: red }')

    window.setCentralWidget(container)
    bar = window.statusBar()
    bar.setStyleSheet("QStatusBar {min-height: 38}")
    # bar.showMessage(str(bar))

    view = DoubleRangeView()

    view.setValueConverter(lambda x: (x * -1.2))
    view.setValueFormatter(lambda x: "%4.3f" % x)

    argument_0 = SelectArgument(0)
    argument_1 = SelectArgument(1)
    view.valuesChanged.connect(argument_0.input)
    view.valuesChanged.connect(argument_1.input)

    argument_2 = SelectArgument(0)
    argument_3 = SelectArgument(1)
    view.rangeChanged.connect(argument_2.input)
    view.rangeChanged.connect(argument_3.input)

    argument_4 = SelectArgument(0)
    argument_5 = SelectArgument(1)
    view.displayValues.connect(argument_4.input)
    view.displayValues.connect(argument_5.input)

    check.setChecked(True)
    check.stateChanged.connect(view.setEnabled)

    argument_0.output.connect(left_value_display.setNum)
    argument_1.output.connect(right_value_display.setNum)
    argument_2.output.connect(min_value_display.setNum)
    argument_3.output.connect(max_value_display.setNum)
    argument_4.output.connect(left_derived_value_display.setNum)
    argument_5.output.connect(right_derived_value_display.setNum)

    str_1 = ConvertToStr()
    str_2 = ConvertToStr()
    argument_0.output.connect(str_1.input)
    argument_1.output.connect(str_2.input)
    str_1.output.connect(left_value_edit.setText)
    str_2.output.connect(right_value_edit.setText)

    int_1 = ConvertToInt()
    buffer_1 = BufferTillEnter()
    select_first = SetOneOf(0, target=DoubleRangeView.values, instance=view)
    left_value_edit.textEdited.connect(buffer_1.input)
    left_value_edit.returnPressed.connect(buffer_1.trigger)
    buffer_1.output.connect(int_1.input)
    int_1.output.connect(select_first.input)
    select_first.output.connect(view.setValues)

    int_2 = ConvertToInt()
    buffer_2 = BufferTillEnter()
    select_second = SetOneOf(1, target=DoubleRangeView.values, instance=view)
    right_value_edit.textEdited.connect(buffer_2.input)
    right_value_edit.returnPressed.connect(buffer_2.trigger)
    buffer_2.output.connect(int_2.input)
    int_2.output.connect(select_second.input)
    select_second.output.connect(view.setValues)

    view.values = 10, 20
    view.setEnabled(True)
    bar.addWidget(view)

    window.setGeometry(QStyle.alignedRect(Qt.LeftToRight, Qt.AlignCenter, window.size(), QGuiApplication.screens()[0].availableGeometry()))
    window.show()

    app.exec_()
