#!/usr/bin/env python
# Copyright (C) 2015 Anthony Ransford
#
# VERSION 2.0
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import picamera as _picamera
import time as _time
import numpy as _n
import camera_image as _ci


class PiBeamProfiler(object):
    """ beam profiler object for raspberry-pi. """

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
        self.start_camera()

    def start_camera(self):
        self._initialize_camera()
        self._stream_video_and_fit()

    def _initialize_camera(self):
        # initialize the camera
        self.camera = _picamera.PiCamera()
        # set camera resolution, gain , sutter speed and framerate
        self.set_camera_resolution()
        self.camera.framerate = 33  # in Hz
        self.set_camera_shutter_speed(100)  # in us
        self.camera.exposure_mode = 'off'
        self.camera.iso = 300
        # grab a reference to the raw camera capture
        rgbarray = _picamera.array.PiRGBArray
        self.current_frame = rgbarray(self.camera, size=self.camera_resolution)
        # allow the camera to warmup
        _time.sleep(0.1)

    def set_camera_resolution(self):
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
            # cv2 thingy
            self._bypass_cv2_keyboard_event()
            # prepare and fit incoming image
            array = self._convert_raw_image_to_numpy_array(raw_image)
            image = self._set_image_color(array)
            self.camera_image = _ci.CameraImage(image=image,
                                                coarsen=self.coarsen)
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

    def close_camera(self):
        self.camera.close()
