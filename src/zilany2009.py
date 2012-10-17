#!/usr/bin/env python

"""Zilany, M. S. A., Bruce, I. C., Nelson, P. C., and Carney,
L. H. (2009). A phenomenological model of the synapse between the
inner hair cell and auditory nerve: long-term adaptation with
power-law dynamics. The Journal of the Acoustical Society of America,
126(5):2390-2412.

"""

from __future__ import division
from __future__ import print_function

__author__ = "Marek Rudnicki"

import warnings

import numpy as np
import pandas as pd

from . import _pycat



def run_zilany2009(
        sound,
        fs,
        anf_num,
        seed,
        cf,
        cohc=1,
        cihc=1,
        powerlaw_implnt='approx',
        with_ffGn=False):



    np.random.seed(seed)

    assert np.max(sound) < 1000, "Signal should be given in Pa"
    assert sound.ndim == 1


    anf_count = {
        'hsr': anf_num[0],
        'msr': anf_num[1],
        'lsr': anf_num[2]
    }



    ### Calculate CFs
    if np.isscalar(cf):
        cfs = [float(cf)]

    elif isinstance(cf, tuple):
        # Based on GenerateGreenwood_CFList() from DSAM
        # Liberman (1982)
        aA = 456
        k = 0.8
        a = 2.1

        freq_min, freq_max, freq_num = cf

        xmin = np.log10( freq_min / aA + k) / a
        xmax = np.log10( freq_max / aA + k) / a

        x_map = np.linspace(xmin, xmax, freq_num)
        cfs = aA * ( 10**( a*x_map ) - k)

    elif isinstance(cf, list) or isinstance(cf, np.ndarray):
        cfs = cf

    else:
        raise RuntimeError("CF must be a scalar, a tuple or a list.")




    ### Run Middle Ear filter
    meout = _pycat.run_me(signal=sound, fs=fs)



    trains = []
    for freq in cfs:

        ### Run IHC model
        vihc = _pycat.run_ihc(
            signal=meout,
            cf=freq,
            fs=fs,
            cohc=float(cohc),
            cihc=float(cihc)
        )

        for typ,cnt in anf_count.items():

            tr = _run_anf(
                vihc=vihc,
                fs=fs,
                cf=freq,
                anf_type=typ,
                anf_cnt=cnt,
                with_ffGn=with_ffGn,
                powerlaw_implnt=powerlaw_implnt
            )
            trains.extend(tr)


    spike_trains = pd.DataFrame(
        trains
    )

    np.fft.fftpack._fft_cache = {}

    return spike_trains



def _run_anf(vihc, fs, cf, anf_type, anf_cnt, with_ffGn, powerlaw_implnt):

    synout = None
    duration = len(vihc) / fs
    anf_trains = []
    for anf_idx in range(anf_cnt):
        if (synout is None) or with_ffGn:
            synout = _pycat.run_synapse(
                fs=fs,
                vihc=vihc,
                cf=cf,
                anf_type=anf_type,
                powerlaw_implnt=powerlaw_implnt,
                with_ffGn=with_ffGn
            )

        spikes = _pycat.run_spike_generator(
            fs=fs,
            synout=synout
        )

        spikes = np.array(spikes[spikes != 0])

        anf_trains.append({
            'spikes': spikes,
            'duration': duration,
            'cf': cf,
            'type': anf_type,
            'index': anf_idx
        })

    return anf_trains




class Zilany2009(object):
    name = 'Zilany2009'

    def __init__(self,
                 anf_num=(1,1,1),
                 cf=1000,
                 cohc=1.,
                 cihc=1.,
                 powerlaw_implnt='approx',
                 with_ffGn=False):
        """ Auditory periphery model of a cat (Zilany et al. 2009)

        anf_num: (hsr_num, msr_num, lsr_num)
        cf: CF
        powerlaw_implnt: 'approx' or 'actual' implementation of the power-law
        with_ffGn: enable/disable Gausian noise

        """
        warnings.warn("Obsolited: use run_zilany2009() instead")


        self._hsr_num = anf_num[0]
        self._msr_num = anf_num[1]
        self._lsr_num = anf_num[2]

        self._powerlaw_implnt = powerlaw_implnt
        self._with_ffGn = with_ffGn

        self._cohc = float(cohc)
        self._cihc = float(cihc)

        self.set_freq(cf)


    def run(self, sound, fs, seed):
        """ Run the model.

        fs: sampling frequency of the signal; model is run at the same frequency
        sound: input signal

        """
        np.random.seed(seed)

        assert np.max(sound) < 1000, "Signal should be given in Pa"


        # Run Middle Ear filter
        meout = _pycat.run_me(signal=sound, fs=fs)


        trains = []
        for cf in self._freq_map:
            # Run IHC model
            vihc = _pycat.run_ihc(signal=meout, cf=cf, fs=fs,
                                  cohc=self._cohc, cihc=self._cihc)

            # Run HSR synapse
            if self._hsr_num > 0:
                tr = self._run_anf(fs, cf, vihc,
                                   anf_type='hsr',
                                   anf_num=self._hsr_num)
                trains.extend(tr)

            # Run MSR synapse
            if self._msr_num > 0:
                tr = self._run_anf(fs, cf, vihc,
                                   anf_type='msr',
                                   anf_num=self._msr_num)
                trains.extend(tr)

            # Run LSR synapse
            if self._lsr_num > 0:
                tr = self._run_anf(fs, cf, vihc,
                                   anf_type='lsr',
                                   anf_num=self._lsr_num)
                trains.extend(tr)

        spike_trains = np.array(
            trains,
            dtype=[('spikes', np.ndarray),
                   ('duration', float),
                   ('cf', float),
                   ('type', '|S3'),
                   ('index', int)]
            )

        np.fft.fftpack._fft_cache = {}

        return spike_trains



    def _run_anf(self, fs, cf, vihc, anf_type, anf_num):

        synout = None
        duration = len(vihc) / fs # [s]
        anf_trains = []
        for anf_idx in range(anf_num):
            if (synout is None) or self._with_ffGn:
                synout = _pycat.run_synapse(fs=fs, vihc=vihc, cf=cf,
                                            anf_type=anf_type,
                                            powerlaw_implnt=self._powerlaw_implnt,
                                            with_ffGn=self._with_ffGn)

            spikes = _pycat.run_spike_generator(fs=fs,
                                                synout=synout)

            spikes = spikes[spikes != 0] # [s]
            anf_trains.append( (spikes,
                                duration,
                                cf,
                                anf_type,
                                anf_idx) )

        return anf_trains


    def set_freq(self, cf):
        """ Set signle or range of CF for the model."""

        if isinstance(cf, float):
            self._freq_map = [cf]
        elif isinstance(cf, int):
            self._freq_map = [float(cf)]
        elif isinstance(cf, tuple):
            # Based on GenerateGreenwood_CFList() from DSAM
            # Liberman (1982)
            aA = 456
            k = 0.8
            a = 2.1

            freq_min, freq_max, freq_num = cf

            xmin = np.log10( freq_min / aA + k) / a
            xmax = np.log10( freq_max / aA + k) / a

            x_map = np.linspace(xmin, xmax, freq_num)
            self._freq_map = aA * ( 10**( a*x_map ) - k)
        elif isinstance(cf, list) or isinstance(cf, np.ndarray):
            self._freq_map = cf
        else:
            assert False, "CF must be int, float, tuple or list"


    def get_freq_map(self):
        return self._freq_map
