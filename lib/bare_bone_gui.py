import time
import picamera as _picamera
import picamera.array as _array
from PyQt4 import QtGui
import numpy as np
from PIL.ImageQt import ImageQt
from scipy.misc.pilutil import toimage
import sys
import cv2 as _cv2
import matplotlib.backends.backend_qt4agg as _qt4agg
FigureCanvas = _qt4agg.FigureCanvasQTAgg


class PiBeamProfilerGUI(QtGui.QWidget):
    def __init__(self):
        super(PiBeamProfilerGUI, self).__init__()
        self.initialize_camera()
        self.initialize_gui()

    def initialize_camera(self):
        # initialize the camera
        self.camera = _picamera.PiCamera()
        # set camera resolution, gain , sutter speed and framerate
        self.camera_resolution = (640, 480)
        self.camera.resolution = self.camera_resolution
        self.camera.framerate = 33  # in Hz
        self.set_camera_shutter_speed(100)  # in us
        self.camera.exposure_mode = 'off'
        self.camera.iso = 300
        self.color = 'green'
        # grab a reference to the raw camera capture
        rgbarray = _array.PiRGBArray
        self.current_frame = rgbarray(self.camera, size=self.camera_resolution)
        # allow the camera to warmup
        time.sleep(0.1)

    def initialize_gui(self):
        self.get_screen_resolution()
        self.setWindowTitle('Beam Profiler')
        self.setGeometry(0, 0, *self.monitor_screen_resolution)
        self.make_widgets()
        self.setup_layout()

    def get_screen_resolution(self):
        desktop = QtGui.QDesktopWidget()
        screensize = desktop.availableGeometry()
        width = screensize.width()
        height = screensize.height()
        self.monitor_screen_resolution = (width, height)

    def make_widgets(self):
        self.make_video_window()

    def make_video_window(self):
        self.video_window = CameraDisplay()

    def set_camera_shutter_speed(self, shutter_speed):
        """ Set shutter speed in us. """
        self.camera.shutter_speed = shutter_speed

    def setup_layout(self):
        layout = QtGui.QGridLayout()
        layout.addWidget(self.video_window, 0, 0)
        self.setLayout(layout)

    def _convert_raw_image_to_numpy_array(self, raw_image):
        array = np.nan_to_num(raw_image.array)
        return array

    def _set_image_color(self, array):
        """ Pick color pixel to use for image. Default(green). """
        red_image = array[:, :, 0]
        green_image = array[:, :, 1]
        blue_image = array[:, :, 2]
        if self.color == 'red':
            image = red_image
        elif self.color == 'blue':
            image = blue_image
        else:
            image = green_image
        return image

    def run_beam_profiler(self):
        capture = self.camera.capture_continuous
        self.counter = 0
        for raw_image in capture(self.current_frame, format='bgr',
                                 use_video_port=True):
            # clear the stream in preparation for the next frame
            self.current_frame.truncate(0)
            # cv2 thingy
            self._bypass_cv2_keyboard_event()
            array = self._convert_raw_image_to_numpy_array(raw_image)
            self.camera_image = array
            self.counter += 1
            if self.counter == 10:
                np.save('3color.npy', array)
            self.update_video()

    def update_video(self):
        # convert RGB image np array to qPixmap and update canvas widget
        image = self.camera_image
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

    def closeEvent(self, x):
        self.camera.close()


class CameraDisplay(QtGui.QLabel):
    def __init__(self):
        super(CameraDisplay, self).__init__()
        self.initialize_image()

    def initialize_image(self):
        self.image = np.zeros((480, 640))
        self.update_frame()

    def update_video(self, image):
        self.image = image
        self.update_frame()

    def update_frame(self):
        qPixmap = self.nparrayToQPixmap(self.image)
#        self.setPixmap(qPixmap.scaled(self.videox, self.videoy))
        self.setPixmap(qPixmap)
        self.repaint()
#        self.show()

    def nparrayToQPixmap(self, array):
        pil_image = toimage(array)
        qt_image = ImageQt(pil_image)
        q_image = QtGui.QImage(qt_image)
        qPixmap = QtGui.QPixmap(q_image)
        return qPixmap


if __name__ == "__main__":
    a = QtGui.QApplication([])
    profilerwidget = PiBeamProfilerGUI()
    profilerwidget.show()
    a.processEvents()
    profilerwidget.run_beam_profiler()
    sys.exit(a.exec_())
