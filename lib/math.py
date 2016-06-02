import numpy as _n
from scipy.optimize import curve_fit as _curve_fit


def _gaussian(x, a, x0, w_I):
    """ A Gaussian profile function used in fitting routine.

    Parameters
    ----------
    x: float, abscissa
    a: float, amplitude coefficient
    x0: float, center
    w_I: float, 1/e intensity radius in pixels

    Returns
    -------
    float
    """
    return a*_n.exp(-(x-x0)**2/(w_I**2))
    
    
def fit_gaussian(positions, amplitudes, a_guess, x0_guess, w_I_guess=200):
    """ Return result from a gaussian fit.
    
    Parameters
    ----------
    positions: list of float, positions on a gaussian curve
    amplitudes: list of float, amplitudes on a gaussian curve
    a_guess: float, guessed peak amplitude of the gaussian
    x0_guess: float, guessed center position of the gaussian
    w_I_guess: float, guessed 1/e intensity radius in pixels
    
    Returns
    -------
    a: float, peak amplitude of the gaussian from fit result
    x0: float, center position of the gaussian from fit result
    w_I: float, 1/e intensity radius in pixels from fit result
    """
    # guessed parameters that gets sent into the curve_fit function
    p0 = [a_guess, x0_guess, w_I_guess]
    try:
        popt, pcov = _curve_fit(_gaussian, positions, amplitudes, p0=p0)
    # TODO: replace the following with a real excetion, rather than a general
    # except
    except:
        # if a fit cannot be obtained, return [0, 0, 1] for a, x0 and w_I
        popt = [0, 0, 1]
    a, x0, w_I = popt
    return a, x0, w_I
