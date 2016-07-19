from PyQt4 import QtGui
import matplotlib.pyplot as plt
import numpy as np
import sys
import pi_beam_profiler as _pi_beam_profiler
import cv2 as _cv2
import matplotlib.backends.backend_qt4agg as _qt4agg
FigureCanvas = _qt4agg.FigureCanvasQTAgg


class PiBeamProfilerGUI(QtGui.QWidget):
    """
    NOTE: The beam size obtained from this GUI is scaled by a factor given as
    below. This seems to be necessary because there is some unresolvable
    discrepancy between Gaussian fit from the image, and knife edge
    measurements. In order to use this GUI properly, some initial calibration
    might be necessary.

    calibrated scaling factor (change the value in self.__init__):
    self.scale = .776
    """
    def __init__(self):
        super(PiBeamProfilerGUI, self).__init__()
        self.scale = .776
        self.zoom = 0.
        self.zoom_max = 4.
        self.left_column = None
        self.right_column = None
        self.top_row = None
        self.bottom_row = None
        self.initialize_beam_profiler()
        self.initialize_gui()

    def initialize_beam_profiler(self):
        self.profiler = _pi_beam_profiler.PiBeamProfiler()
        self.profiler.initialize_camera()
        self.column_count, self.row_count = self.profiler.camera_resolution
        self.column_positions = np.linspace(
            0, self.column_count-1, self.column_count)
        self.row_positions = np.linspace(0, self.row_count-1, self.row_count)

    def initialize_gui(self):
        self.get_screen_resolution()
        self.setWindowTitle('Beam Profiler')
        self.setGeometry(0, 0, *self.monitor_screen_resolution)
        self.make_widgets()
        self.setup_layout()

    def closeEvent(self, x):
        self.profiler.close_camera()

    def change_camera_exposure(self, value):
        # set shutter speed (exposure time) according to a scaling law that
        # Tony likes
        shutter_speed = int(.5 * value**2. + 1)
        self.profiler.set_camera_shutter_speed(shutter_speed)

    def check_zoom_status(self):
        if self.zoom == 0.:
            self.zoom_in_button.setEnabled(True)
            self.zoom_out_button.setDisabled(True)
        elif self.zoom == 4.:
            self.zoom_in_button.setDisabled(True)
            self.zoom_out_button.setEnabled(True)
        else:
            self.zoom_in_button.setEnabled(True)
            self.zoom_out_button.setEnabled(True)

    def convert_pixel_to_um(self, value):
        # pixel size on the camera sensor as given by specs
        camera_sensor_pixel_per_um = 1.4
        # resolution of 640 * 480 is scaled down from 2592 * 1944, which are
        # both 4:3 ratio. Need to have a conversion factor for this.
        resolution_factor = 2592./640.
        # actual conversion
        result = value * camera_sensor_pixel_per_um * resolution_factor
        scaled_result = result * self.scale
        return scaled_result

    def crop_image(self, image):
        cropped_image = image[self.top_row:self.bottom_row,
                              self.left_column:self.right_column]
        return cropped_image

    def get_screen_resolution(self):
        desktop = QtGui.QDesktopWidget()
        screensize = desktop.availableGeometry()
        width = screensize.width()
        height = screensize.height()
        self.monitor_screen_resolution = (width, height)

    def get_rows_and_columns_from_zoom(self, image):
        w, h = image.shape
        cropped_col_count_per_zoom_unit = int(w/4./self.zoom_max)
        cropped_row_count_per_zoom_unit = int(h/4./self.zoom_max)
        self.left_column = self.zoom * cropped_col_count_per_zoom_unit
        self.right_column = w - self.left_column + 1.
        self.top_row = self.zoom * cropped_row_count_per_zoom_unit
        self.bottom_row = h - self.top_row + 1.

    def make_widgets(self):
        self.make_column_and_row_sum_plots()
        self.make_video_window()
        self.make_button_panel()
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

    def make_button_panel(self):
        self.button_panel = QtGui.QFrame()
        self.make_buttons()
        panel_layout = QtGui.QVBoxLayout()
        panel_layout.addWidget(self.red_button)
        panel_layout.addWidget(self.green_button)
        panel_layout.addWidget(self.blue_button)
        panel_layout.addWidget(self.zoom_in_button)
        panel_layout.addWidget(self.zoom_out_button)
        self.button_panel.setLayout(panel_layout)

    def make_information_panel(self):
        self.information_panel = QtGui.QFrame()
        self.column_sum_waist_label = QtGui.QLabel()
        self.row_sum_waist_label = QtGui.QLabel()
        self.exposure_label = QtGui.QLabel()
        self.zoom_label = QtGui.QLabel()
        font = 'color: #FF6600; font-weight: bold; font-family: Copperplate'
        font += ' / Copperplate Gothic Light, sans-serif'
        self.column_sum_waist_label.setStyleSheet(font)
        self.row_sum_waist_label.setStyleSheet(font)
        self.exposure_label.setStyleSheet(font)
        self.zoom_label.setStyleSheet(font)
        panel_layout = QtGui.QVBoxLayout()
        panel_layout.addWidget(self.column_sum_waist_label)
        panel_layout.addWidget(self.row_sum_waist_label)
        panel_layout.addWidget(self.exposure_label)
        panel_layout.addWidget(self.zoom_label)
        self.information_panel.setLayout(panel_layout)

    def make_buttons(self):
        self.red_button = QtGui.QPushButton('red')
        self.green_button = QtGui.QPushButton('green')
        self.blue_button = QtGui.QPushButton('blue')

        self.zoom_in_button = QtGui.QPushButton('zoom in')
        self.zoom_out_button = QtGui.QPushButton('zoom out')

        self.red_button.setCheckable(True)
        self.green_button.setCheckable(True)
        self.blue_button.setCheckable(True)

        self.red_button.clicked.connect(self.set_image_color_red)
        self.green_button.clicked.connect(self.set_image_color_green)
        self.blue_button.clicked.connect(self.set_image_color_blue)

        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.update_zoom_label()
        self.check_zoom_status()

        self.red_button.setChecked(True)

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

    def set_image_color(self, color):
        self.profiler.set_image_color(color)

    def set_image_color_red(self):
        self.set_image_color('red')
        self.green_button.setChecked(False)
        self.blue_button.setChecked(False)

    def set_image_color_blue(self):
        self.set_image_color('blue')
        self.red_button.setChecked(False)
        self.green_button.setChecked(False)

    def set_image_color_green(self):
        self.set_image_color('green')
        self.red_button.setChecked(False)
        self.blue_button.setChecked(False)

    def set_row_sum_plot_lims(self):
        self.row_sum_ax.set_xlim(0, 300)
        ymin = 0
        ymax = self.row_count - 1
        self.row_sum_ax.set_ylim(ymin, ymax)

    def set_column_sum_plot_lims(self):
        xmin = 0
        xmax = self.column_count - 1
        self.column_sum_ax.set_xlim(xmin, xmax)
        self.column_sum_ax.set_ylim(0, 300)

    def setup_layout(self):
        layout = QtGui.QGridLayout()
        layout.addWidget(self.video_window, 0, 0)
        layout.addWidget(self.column_sum_canvas, 1, 0)
        layout.addWidget(self.row_sum_canvas, 0, 1)
        layout.addWidget(self.button_panel, 0, 2)
        layout.addWidget(self.information_panel, 1, 1, 1, 2)
        layout.setColumnStretch(0, 4)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 8)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        self.setLayout(layout)

    def update_GUI(self):
        self.update_video()
        self.update_column_and_row_sum_figures()
        self.update_image_information()

    def update_video(self):
        # convert RGB image np array to qPixmap and update canvas widget
        image = self.camera_image.image
        if self.left_column is None:
            self.get_rows_and_columns_from_zoom(image)
        image = self.crop_image(image)
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
        cropped_column_sum = self.camera_image.column_sum[
            self.left_column:self.right_column]

        cropped_column_positions = self.camera_image.column_positions[
            self.left_column:self.right_column]

        cropped_column_sum_fit = self.camera_image.column_sum_fit[
            self.left_column:self.right_column]

        self.column_sum_lines.set_xdata(cropped_column_positions)
        self.column_sum_lines.set_ydata(cropped_column_sum)
        self.column_sum_fit_lines.set_xdata(cropped_column_positions)
        self.column_sum_fit_lines.set_ydata(cropped_column_sum_fit)
        ymax = max(max(self.camera_image.column_sum), 300)
        self.column_sum_ax.set_ylim(0, ymax)
        self.column_sum_figure.canvas.draw()
        self.column_sum_figure.canvas.flush_events()

    def update_row_sum_figures(self):
        cropped_row_sum = self.camera_image.row_sum[
            self.top_row:self.bottom_row]

        cropped_row_positions = self.camera_image.row_positions[
            self.top_row:self.bottom_row]

        cropped_row_sum_fit = self.camera_image.row_sum_fit[
            self.top_row:self.bottom_row]

        self.row_sum_lines.set_xdata(cropped_row_sum)
        self.row_sum_lines.set_ydata(cropped_row_positions)
        self.row_sum_fit_lines.set_xdata(cropped_row_sum_fit)
        self.row_sum_fit_lines.set_ydata(cropped_row_positions)
        xmax = max(max(self.camera_image.row_sum), 300)
        self.row_sum_ax.set_xlim(0, xmax)
        self.row_sum_figure.canvas.draw()
        self.row_sum_figure.canvas.flush_events()

    def update_image_information(self):
        # update column and row beam diameter information
        text_ending = 'um, 1/e Int. diam.'
        column_diameter_in_pix = self.camera_image.column_width * 2.
        column_diameter = self.convert_pixel_to_um(column_diameter_in_pix)
        column_text = 'X = ' + str(column_diameter)[0:5] + text_ending
        self.column_sum_waist_label.setText(column_text)
        row_diameter_in_pix = self.camera_image.row_width * 2.
        row_diameter = self.convert_pixel_to_um(row_diameter_in_pix)
        row_text = 'Y = ' + str(row_diameter)[0:5] + text_ending
        self.row_sum_waist_label.setText(row_text)
        exposure_text = 'Exposure: %s' % round(self.camera_image.saturation, 0)
        exposure_text += "%"
        self.exposure_label.setText(exposure_text)

    def update_zoom_label(self):
        zoom_text = "Zoom: " % self.zoom
        self.zoom_label.setText(zoom_text)

    def zoom_in(self):
        if self.zoom < 4.:
            self.zoom += 1.
        self.get_rows_and_columns_from_zoom()
        self.update_zoom_label()
        self.check_zoom_status()

    def zoom_out(self):
        if self.zoom > 0.:
            self.zoom -= 1.
        self.get_rows_and_columns_from_zoom()
        self.update_zoom_label()
        self.check_zoom_status()


class CameraDisplay(QtGui.QLabel):
    def __init__(self, monitor_screen_resolution=(640, 480), image_scale=1.3):
        super(CameraDisplay, self).__init__()
        self.monitor_screen_resolution = monitor_screen_resolution
        self.image_scale = image_scale
        self.set_image_resolution_from_scale()
        self.initialize_image()

    def set_image_resolution_from_scale(self):
        height = self.monitor_screen_resolution[1]/self.image_scale
        width = height * 4./3.  # adopt a 4:3 ratio for width and height
        self.width = int(width)
        self.height = int(height)

    def initialize_image(self):
        self.image = np.zeros((480, 640))
        self.update_frame()

    def update_video(self, image):
        self.image = image
        self.update_frame()

    def update_frame(self):
        qPixmap = self.nparrayToQPixmap(self.image)
        self.setPixmap(qPixmap)
        self.show()

    def nparrayToQPixmap(self, array):
        h, w = array.shape
        gray_image = np.require(array, np.uint8, 'C')
        q_image = QtGui.QImage(gray_image.data, w, h,
                               QtGui.QImage.Format_Indexed8)
        qPixmap = QtGui.QPixmap(q_image)
        qPixmap = qPixmap.scaled(self.width, self.height)
        return qPixmap


if __name__ == "__main__":
    a = QtGui.QApplication([])
    profilerwidget = PiBeamProfilerGUI()
    profilerwidget.show()
    a.processEvents()
    profilerwidget.run_beam_profiler()
    sys.exit(a.exec_())
