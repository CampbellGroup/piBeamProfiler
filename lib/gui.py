import time
from PyQt4 import QtGui, QtCore
import matplotlib.pyplot as plt
import numpy as np
from PIL.ImageQt import ImageQt
from scipy.misc.pilutil import toimage
import sys
import pi_beam_profiler as _pi_beam_profiler
import cv2 as _cv2
import matplotlib.backends.backend_qt4agg as _qt4agg
FigureCanvas = _qt4agg.FigureCanvasQTAgg


class PiBeamProfilerGUI(QtGui.QWidget):
    def __init__(self):
        super(PiBeamProfilerGUI, self).__init__()
        self.set_parameters()
        self.initialize_beam_profiler()
        self.initialize_gui()

    def set_parameters(self):
        self.zoom = 0
        self.zoom_gap_factor = .04
        self.image_scale_factor = 2.1
        self.image_h_to_v_conversion_factor = 4./3.
        self.profiler_running = True
        self.breakloop = False

    def initialize_beam_profiler(self):
        self.profiler = _pi_beam_profiler.PiBeamProfiler()
        self.profiler.initialize_camera()
        self.column_count, self.row_count = self.profiler.camera_resolution
        self.column_positions = np.linspace(
            0, self.column_count-1, self.column_count)
        self.row_positions = np.linspace(0, self.row_count-1, self.row_count)

    def initialize_gui(self):
        self.get_image_boundaries()
        self.get_screen_resolution()
        self.setWindowTitle('Beam Profiler')
        self.setGeometry(0, 0, *self.monitor_screen_resolution)
        self.make_widgets()
        self.setup_layout()

    def get_image_boundaries(self):
        column_gap = self.column_count*(self.zoom * self.zoom_gap_factor)
        row_gap = self.row_count*(self.zoom * self.zoom_gap_factor)
        self.min_row_index = row_gap
        self.max_row_index = self.row_count - row_gap
        self.min_column_index = column_gap
        self.max_column_index = self.column_count - column_gap

    def get_screen_resolution(self):
        desktop = QtGui.QDesktopWidget()
        screensize = desktop.availableGeometry()
        width = screensize.width()
        height = screensize.height()
        self.monitor_screen_resolution = (width, height)

    def make_widgets(self):
        self.make_column_and_row_sum_plots()
        self.make_video_window()
        self.make_information_panel()

    def make_column_and_row_sum_plots(self):
        self.make_column_sum_plot()
        self.make_row_sum_plot()

    def make_column_sum_plot(self):
        # Set up plot axes and figure positions
        self.column_sum_figure, self.column_sum_ax = plt.subplots()
        # add figure to canvas
        self.column_sum_canvas = FigureCanvas(self.column_sum_figure)
        # Create line objects for fast plot redrawing
        self.column_sum_lines, = self.column_sum_ax.plot(
            [], [], linewidth=2, color='purple')

        self.column_sum_fit_lines, = self.column_sum_ax.plot(
            [], [], linestyle='--', linewidth=2, color='yellow')

        # set column sum plot details
        self.set_column_sum_plot_lims()
        self.column_sum_ax.xaxis.set_ticks_position('none')
        self.column_sum_ax.yaxis.set_ticks_position('none')
        self.column_sum_ax.get_xaxis().set_visible(False)
        self.column_sum_ax.get_yaxis().set_visible(False)
        self.column_sum_ax.patch.set_visible(False)

    def make_row_sum_plot(self):
        # Set up plot axes and figure positions
        self.row_sum_figure, self.row_sum_ax = plt.subplots()
        # add figure to canvas
        self.row_sum_canvas = FigureCanvas(self.row_sum_figure)
        # Create line objects for fast plot redrawing
        self.row_sum_lines, = self.row_sum_ax.plot(
            [], [], linewidth=2, color='purple')

        self.row_sum_fit_lines, = self.row_sum_ax.plot(
            [], [], linestyle='--', linewidth=2, color='yellow')

        # set row sum plot details
        self.set_row_sum_plot_lims()
        self.row_sum_ax.xaxis.set_ticks_position('none')
        self.row_sum_ax.yaxis.set_ticks_position('none')
        self.row_sum_ax.get_xaxis().set_visible(False)
        self.row_sum_ax.get_yaxis().set_visible(False)
        self.row_sum_ax.patch.set_visible(False)

    def make_video_window(self):
        self.video_window = CameraDisplay(
            monitor_screen_resolution=self.monitor_screen_resolution)

    def make_information_panel(self):
        self.information_panel = QtGui.QFrame()
        self.column_sum_waist_label = QtGui.QLabel()
        self.row_sum_waist_label = QtGui.QLabel()
        self.exposure_label = QtGui.QLabel()
        font = 'color: #FF6600; font-weight: bold; font-family: Copperplate'
        font += ' / Copperplate Gothic Light, sans-serif'
        self.column_sum_waist_label.setStyleSheet(font)
        self.row_sum_waist_label.setStyleSheet(font)
        self.exposure_label.setStyleSheet(font)
        panel_layout = QtGui.QGridLayout()
        panel_layout.addWidget(self.column_sum_waist_label)
        panel_layout.addWidget(self.row_sum_waist_label)
        panel_layout.addWidget(self.exposure_label)
        self.information_panel.setLayout(panel_layout)

    def change_camera_exposure(self, value):
        # set shutter speed (exposure time) according to a scaling law that
        # Tony likes
        shutter_speed = int(.5 * value**2. + 1)
        self.profiler.set_camera_shutter_speed(shutter_speed)

    def set_row_sum_plot_lims(self):
        self.row_sum_ax.set_xlim(0, 300)
        ymin = self.min_row_index
        ymax = self.max_row_index
        self.row_sum_ax.set_ylim(ymin, ymax)

    def set_column_sum_plot_lims(self):
        xmin = self.min_column_index
        xmax = self.max_column_index
        self.column_sum_ax.set_xlim(xmin, xmax)
        self.column_sum_ax.set_ylim(0, 300)

    def setup_layout(self):
        layout = QtGui.QGridLayout()
        layout.addWidget(self.video_window, 0, 0, 2, 1)
        layout.addWidget(self.column_sum_canvas, 2, 0, 2, 1)
        layout.addWidget(self.row_sum_canvas, 0, 1, 2, 1)
        layout.addWidget(self.information_panel, 2, 1, 1, 2)
        self.setLayout(layout)

    def run_beam_profiler(self):
        capture = self.profiler.camera.capture_continuous
        current_frame = self.profiler.current_frame
        camera_format = self.profiler.camera_format
        self.counter = 0
        for raw_image in capture(current_frame, format=camera_format,
                                 use_video_port=True):
            # cv2 thingy
            self._bypass_cv2_keyboard_event()
            self.camera_image = self.profiler.prepare_for_raw_image(raw_image)
            # clear the stream in preparation for the next frame
            current_frame.truncate(0)
            self.update_GUI()

    def update_GUI(self):
        self.update_video()
        self.update_column_and_row_sum_figures()
        self.update_image_information()

    def update_video(self):
        # convert RGB image np array to qPixmap and update canvas widget
        image = self.camera_image.image
#        image = image[self.min_row_index: self.max_row_index,
#                      self.min_column_index: self.max_column_index]
        self.video_window.update_video(image)

    def _bypass_cv2_keyboard_event(self):
        """
        See http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_gui/
        py_image_display/py_image_display.html
        If waitKey(0) is passed then it waits indefinitely.
        """
        key = _cv2.waitKey(1) & 0xFF

    def update_column_and_row_sum_figures(self):
        self.update_column_sum_figures()
        self.update_row_sum_figures()

    def update_column_sum_figures(self):
        self.column_sum_lines.set_xdata(self.camera_image.column_positions)
        self.column_sum_lines.set_ydata(self.camera_image.column_sum)
        self.column_sum_fit_lines.set_xdata(self.camera_image.column_positions)
        self.column_sum_fit_lines.set_ydata(self.camera_image.column_sum_fit)
        self.column_sum_figure.canvas.draw()
        self.column_sum_figure.canvas.flush_events()

    def update_row_sum_figures(self):
        self.row_sum_lines.set_xdata(self.camera_image.row_sum)
        self.row_sum_lines.set_ydata(self.camera_image.row_positions)
        self.row_sum_fit_lines.set_xdata(self.camera_image.row_sum_fit)
        self.row_sum_fit_lines.set_ydata(self.camera_image.row_positions)
        self.row_sum_figure.canvas.draw()
        self.row_sum_figure.canvas.flush_events()

    def update_image_information(self):
        # update column and row beam diameter information
        text_ending = 'um, 1/e**2 Int. diam.'
        column_diameter = self.camera_image.column_width * 2.
        column_text = 'X = ' + str(column_diameter)[0:5] + text_ending
        self.column_sum_waist_label.setText(column_text)
        row_diameter = self.camera_image.row_width * 2.
        row_text = 'Y = ' + str(row_diameter)[0:5] + text_ending
        self.row_sum_waist_label.setText(row_text)
        exposure_text = 'Exposure: %s' % round(self.camera_image.saturation, 0)
        exposure_text += "%"
        self.exposure_label.setText(exposure_text)

    def closeEvent(self, x):
        self.profiler.close_camera()


class CameraDisplay(QtGui.QLabel):
    def __init__(self, monitor_screen_resolution=(640, 480)):
        super(CameraDisplay, self).__init__()
        self.monitor_screen_resolution = monitor_screen_resolution
        self.initialize_image()

    def initialize_image(self):
        self.image = np.zeros((480, 640))
        self.image_scale_factor = 2.1
        self.image_h_to_v_conversion_factor = 4./3.
        self.videoy = int(self.monitor_screen_resolution[0] /
                          self.image_scale_factor)
        self.videox = int(self.image_h_to_v_conversion_factor * self.videoy)
        self.update_frame()

    def update_video(self, image):
        self.image = image
        self.update_frame()

    def update_frame(self):
        qPixmap = self.nparrayToQPixmap(self.image)
        self.setPixmap(qPixmap.scaled(self.videox, self.videoy))
        self.setPixmap(qPixmap)
        self.repaint()
#        self.show()

    def nparrayToQPixmap(self, array):
        h, w = array.shape
        gray_image = np.require(array, np.uint8, 'C')
        q_image = QtGui.QImage(gray_image.data, w, h,
                               QtGui.QImage.Format_Indexed8)

        qPixmap = QtGui.QPixmap(q_image)
        return qPixmap


if __name__ == "__main__":
    a = QtGui.QApplication([])
    profilerwidget = PiBeamProfilerGUI()
    profilerwidget.show()
    a.processEvents()
    profilerwidget.run_beam_profiler()
    sys.exit(a.exec_())
