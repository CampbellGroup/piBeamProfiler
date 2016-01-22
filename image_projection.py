# -*- coding: utf-8 -*-
"""
Class to hold row and column sum data, projections of the image.
"""
import numpy as np


class ImageProjection(object):

    def __init__(self, image, axis, pixels):
        self._image = image
        self._axis = axis
        self._pixels = pixels

        self._set_projection_sum()
        self._background_subtraction()
        self._coarsen()
        self._convert_nans_to_numbers()
        self._set_amplitude_guess_for_fitting()
        self._set_center_guess_for_fitting()
        self._set_fitting_parameters_guess()

    def _set_projection_sum(self):
        unknown_param = 40.0
        self._raw_array = self._image.sum(axis=self._axis)/unknown_param

    def _background_subtraction(self):
        self._sum_array = self._raw_array - np.min(self._raw_array)

    def _coarsen(self, xdata, ydata, points):
        xdata = self._pixels
        ydata = self._sum_array
        points = 3

        newlength = int(len(xdata)/points)
        newxdata = []
        newydata = []
        j = 0
        for i in range(newlength):
            i = points*(i)
            newydata.append(np.mean(ydata[int(j):int(i)]))
            newxdata.append(xdata[int((i + j)/2)])
            j = i

        coarsened_xdata = np.array(newxdata)
        coarsened_ydata = np.array(newydata)

        self.positions = coarsened_xdata
        self.values = coarsened_ydata

    def _convert_nans_to_numbers(self):
        self.positions = np.nan_to_num(self.positions)
        self.values = np.nan_to_num(self.values)

    def _set_amplitude_guess_for_fitting(self):
        self.amplitude_guess = self.values.max()

    def _set_center_guess_for_fitting(self):
        self.center_guess = np.argmax(self.values)

    def _set_fitting_parameters_guess(self):
        unkown_param = 200
        self.p0 = [self.amplitude_guess, self.center_guess, unkown_param]
