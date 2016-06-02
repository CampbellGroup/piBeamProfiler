"""
Test math.py module
"""
import unittest as ut
import pi_beam_profiler.lib.math as math
import numpy as np


class TestMath(ut.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test__gaussian(self):
        x = 2.
        a = 1.
        x0 = 0.
        w_I = 3.
        expect = math._gaussian(x, a, x0, w_I)
        value = 0.641180388
        self.assertAlmostEqual(expect, value, places=7)
    
    def test_fit_gaussian(self):
        a_guess = 1.
        x0_guess = 0.
        w_I_guess = 3.
        positions = np.linspace(-5, 5, 501)
        _amplitudes = math._gaussian(positions, a_guess, x0_guess, w_I_guess)
        noises = np.array([np.random.rand()*.001 for kk in _amplitudes])
        amplitudes = _amplitudes + noises
        a, x0, w_I = math.fit_gaussian(
            positions, amplitudes, a_guess, x0_guess, w_I_guess)
        self.assertAlmostEquals(a, a_guess, places=2)
        self.assertAlmostEquals(x0, x0_guess, places=2)
        self.assertAlmostEquals(w_I, w_I_guess, places=2)        
        