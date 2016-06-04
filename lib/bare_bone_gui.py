import time
from PyQt4 import QtGui, QtCore
import matplotlib.pyplot as plt
import numpy as np
from PIL.ImageQt import ImageQt
from scipy.misc.pilutil import toimage
import sys
import bare_bone_image_taker as _pi_beam_profiler
import matplotlib.backends.backend_qt4agg as _qt4agg
FigureCanvas = _qt4agg.FigureCanvasQTAgg
import cv2 as _cv2


class PiBeamProfilerGUI(QtGui.QWidget):
    def __init__(self):
        super(PiBeamProfilerGUI, self).__init__()
        self.set_parameters()
        self.initialize_beam_profiler()
        self.initialize_gui()

    def set_parameters(self):
        self.zoom = 0
        self.zoom_gap_factor = .04
        self.update_image_time = .05
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
        # self.make_column_and_row_sum_plots()
        # self.make_exposure_slider()
        # self.make_exposure_bar()
        self.make_video_window()
        # self.make_texts()
        # self.make_buttons()

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

    def make_exposure_slider(self):
        self.exposure_slider = QtGui.QSlider(QtCore.Qt.Vertical)
        self.exposure_slider.setSingleStep(1)
        self.exposure_slider.valueChanged[int].connect(
            self.change_camera_exposure)

    def make_exposure_bar(self):
        self.exposure_bar = QtGui.QProgressBar()
        self.exposure_bar.setOrientation(QtCore.Qt.Vertical)
        self.exposure_bar.setValue(65)

    def make_video_window(self):
        self.video_window = QtGui.QLabel(self)

    def make_texts(self):
        self.column_sum_waist_label = QtGui.QLabel()
        self.row_sum_waist_label = QtGui.QLabel()
        font = 'color: #FF6600; font-weight: bold; font-family: Copperplate'
        font += ' / Copperplate Gothic Light, sans-serif'
        self.column_sum_waist_label.setStyleSheet(font)
        self.row_sum_waist_label.setStyleSheet(font)

    def make_buttons(self):
        self.zoomin_button = QtGui.QPushButton('Zoom In')
        self.zoomout_button = QtGui.QPushButton('Zoom Out')
        self.high_resolution_button = QtGui.QPushButton('1296x972')
        self.low_resolution_button = QtGui.QPushButton('640x480')

        button_width = self.monitor_screen_resolution[0]/12
        button_height = self.monitor_screen_resolution[1]/4
        button_size = (button_width, button_height)
        self.high_resolution_button.setFixedSize(*button_size)
        self.low_resolution_button.setFixedSize(*button_size)
        self.zoomin_button.setFixedSize(*button_size)
        self.zoomout_button.setFixedSize(*button_size)

        self.high_resolution_button.setCheckable(True)
        self.low_resolution_button.setCheckable(True)
        self.low_resolution_button.setChecked(True)

        self.zoomin_button.toggled.connect(self.zoom_in)
        self.zoomout_button.toggled.connect(self.zoom_out)
        self.low_resolution_button.clicked.connect(self.set_low_resolution)
        self.high_resolution_button.clicked.connect(self.set_high_resolution)

    def change_camera_exposure(self, value):
        # set shutter speed (exposure time) according to a scaling law that
        # Tony likes
        shutter_speed = int(.5 * value**2. + 1)
        self.profiler.set_camera_shutter_speed(shutter_speed)

    def zoom_in(self):
        if self.zoom >= 10:
            self.zoom = 10
        else:
            self.zoom += 1
            self.resize_plots()

    def zoom_out(self):
        if self.zoom <= 0:
            self.zoom = 0
        else:
            self.zoom -= 1
            self.resize_plots()

    def resize_plots(self):
        self.get_zoom_gaps()
        self.set_row_sum_plot_lims()
        self.set_column_sum_plot_lims()

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

    def set_low_resolution(self):
        self.high_resolution_button.setChecked(False)
        self.breakloop = True
        self.profiler.set_camera_resolution_mode('low')
        time.sleep(1)
        self.make_column_and_row_sum_plots()
        self.profiler.restart_camera()

    def set_high_resolution(self):
        self.low_resolution_button.setChecked(False)
        self.breakloop = True
        self.profiler.set_camera_resolution_mode('high')
        time.sleep(1)
        self.make_column_and_row_sum_plots()
        self.profiler.restart_camera()

    def setup_layout(self):
        layout = QtGui.QGridLayout()
        layout.addWidget(self.video_window, 0, 0, 2, 1)
#        layout.addWidget(self.column_sum_canvas, 2, 0, 2, 1)
#        layout.addWidget(self.row_sum_canvas, 0, 1, 2, 1)
#        layout.addWidget(self.exposure_bar, 0, 4, 2, 1)
#        layout.addWidget(self.column_sum_waist_label, 2, 1, 1, 3)
#        layout.addWidget(self.row_sum_waist_label, 3, 1, 1, 3)
#
#        # withholds these widgets for tiny screens
#        if not any(side <= 400 for side in self.monitor_screen_resolution):
#            layout.addWidget(self.low_resolution_button, 1, 2)
#            layout.addWidget(self.high_resolution_button, 1, 3)
#            layout.addWidget(self.zoomin_button, 0, 3)
#            layout.addWidget(self.zoomout_button, 0, 2)
#            layout.addWidget(self.exposure_slider, 0, 5, 2, 1)

        self.setLayout(layout)

    def run_beam_profiler(self):
        capture = self.profiler.camera.capture_continuous
        current_frame = self.profiler.current_frame
        for raw_image in capture(current_frame, format=self.camera_format,
                                 use_video_port=True):
            # cv2 thingy
            self._bypass_cv2_keyboard_event()
            self.profiler.fit_an_image(raw_image)
            # clear the stream in preparation for the next frame
            self._clear_current_image()
            self.update_GUI()

    def _bypass_cv2_keyboard_event(self):
        """
        See http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_gui/
        py_image_display/py_image_display.html
        If waitKey(0) is passed then it waits indefinitely.
        """
        key = _cv2.waitKey(1) & 0xFF

    def update_GUI(self):
        self.fetch_data()
        self.update_video()
        self.update_column_and_row_sum_figures()
        self.update_beam_diameter_information()

    def fetch_data(self):
        self.camera_image = self.profiler.camera_image

    def update_video(self):
        # convert RGB image np array to qPixmap and update canvas widget
        image = self.camera_image.image
        array = image[self.min_row_index: self.max_row_index,
                      self.min_column_index: self.max_column_index]
        qPixmap = self.nparrayToQPixmap(array)
        videoy = int(self.monitor_screen_resolution[0]/self.image_scale_factor)
        videox = int(self.image_h_to_v_conversion_factor * videoy)
        self.video_window.setPixmap(qPixmap.scaled(videox, videoy))

    def nparrayToQPixmap(self, array):
        pil_image = toimage(array)
        qt_image = ImageQt(pil_image)
        q_image = QtGui.QImage(qt_image)
        qPixmap = QtGui.QPixmap(q_image)
        return qPixmap

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

    def update_beam_diameter_information(self):
        # update column and row beam diameter information
        text_ending = 'um, 1/e**2 Int. diam.'
        column_diameter = self.camera_image.column_width * 2.
        column_text = 'X = ' + str(column_diameter)[0:5] + text_ending
        self.column_sum_waist_label.setText(column_text)
        row_diameter = self.camera_image.row_width * 2.
        row_text = 'Y = ' + str(row_diameter)[0:5] + text_ending
        self.row_sum_waist_label.setText(row_text)

    def closeEvent(self, x):
        self.profiler.close_camera()


if __name__ == "__main__":
    a = QtGui.QApplication([])
    profilerwidget = PiBeamProfilerGUI()
    profilerwidget.show()
    profilerwidget.run_beam_profiler()
    sys.exit(a.exec_())
