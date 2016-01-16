import picamera as _picamera
import picamera.array as _array
import time as _time
import numpy as _n
import cv2 as _cv2


class PiBeamProfiler(object):
    """
    beam profiler object for raspberry-pi.

    To use the beam profiler:

    self.initialize_camera()
    self.run_beam_profiler()

    """

    def __init__(self):
        """
        Attributes
        ----------
        resolution_mode: str, resolution mode of the camera.
            Options: "high", "low". default('low')
        """
        self.resolution_mode = 'low'
        self.camera_format = 'bgr'
        self.color = 'green'
        self.coarsen = False
        self.counter = 0

    def run_beam_profiler(self):
        self._stream_video_and_fit()

    def restart_camera(self):
        self.close_camera()
        self.initialize_camera()
        self.run_beam_profiler()

    def initialize_camera(self):
        # initialize the camera
        self.camera = _picamera.PiCamera()
        # set camera resolution, gain , sutter speed and framerate
        self._set_camera_resolution()
        self.camera.framerate = 33  # in Hz
        self.set_camera_shutter_speed(100)  # in us
        self.camera.exposure_mode = 'off'
        self.camera.iso = 300
        # grab a reference to the raw camera capture
        rgbarray = _array.PiRGBArray
        self.current_frame = rgbarray(self.camera, size=self.camera_resolution)
        # allow the camera to warmup
        _time.sleep(0.1)

    def set_camera_resolution_mode(self, mode='low'):
        if mode in ('low', 'high'):
            self.resolution_mode = mode
        else:
            self.resolution_mode = 'low'

    def _set_camera_resolution(self):
        if self.resolution_mode == 'high':
            self.camera_resolution = (1296, 972)
        else:
            self.camera_resolution = (640, 480)
        self.camera.resolution = self.camera_resolution

    def set_camera_shutter_speed(self, shutter_speed):
        """ Set shutter speed in us. """
        self.camera.shutter_speed = shutter_speed

    def _stream_video_and_fit(self):
        capture = self.camera.capture_continuous
        for raw_image in capture(self.current_frame, format=self.camera_format,
                                 use_video_port=True):
            self.counter += 1
            print self.counter
            # cv2 thingy
            self._bypass_cv2_keyboard_event()
            # prepare and fit incoming image
            array = self._convert_raw_image_to_numpy_array(raw_image)
            image = self._set_image_color(array)
            self.camera_image = image
            self.print_image_info()
            # clear the stream in preparation for the next frame
            self._clear_current_image()

    def _convert_raw_image_to_numpy_array(self, raw_image):
        array = _n.nan_to_num(raw_image.array)
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

    def _bypass_cv2_keyboard_event(self):
        """
        See http://docs.opencv.org/3.0-beta/doc/py_tutorials/py_gui/
        py_image_display/py_image_display.html
        If waitKey(0) is passed then it waits indefinitely.
        """
        key = _cv2.waitKey(1) & 0xFF

    def _clear_current_image(self):
        self.current_frame.truncate(0)

    def print_image_info(self):
        print "image shape:", self.camera_image.shape

    def close_camera(self):
        self.camera.close()

