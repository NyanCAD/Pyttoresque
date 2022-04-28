# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0

import holoviews as hv
import datashader as ds
import numpy as np
import pandas as pd
import scipy.fft
import scipy.interpolate
import functools
from holoviews.streams import Buffer, Stream, param
from holoviews.operation.datashader import datashade, shade, dynspread, spread, rasterize

hv.extension('plotly')

active_traces = Stream.define('traces', cols=[])

def _timeplot(data, cols=[]):
    traces = {k: hv.Curve(data, 'index', k).redim(**{k:'amplitude', 'index':'time'}) for k in cols}
    if not cols: # hack
        traces = {"dummy": hv.Scatter([])}
    return hv.NdOverlay(traces, kdims='k')

def timeplot(streams):
    curve_dmap = hv.DynamicMap(_timeplot, streams=streams)
    # return dynspread(datashade(curve_dmap, aggregator=ds.by('k', ds.any())))
    return spread(datashade(curve_dmap, aggregator=ds.by('k', ds.count()), width=1000, height=1000))
    # return spread(datashade(curve_dmap, aggregator=ds.count_cat('k'), width=1000, height=1000))

def _bodeplot(data, cols=[]):
    mag_traces = []
    pha_traces = []
    for k in cols:
        mt = hv.Curve((data.index, np.abs(data[k])), 'freqency', 'amplitude')
        pt = hv.Curve((data.index, np.angle(data[k], deg=True)), 'freqency', 'angle')
        mag_traces.append(mt)
        pha_traces.append(pt)
    
    if not cols:
        mag_traces = [hv.Curve([])]
        pha_traces = [hv.Curve([])]

    mag = hv.Overlay(mag_traces).opts(logx=True, logy=True)
    phase = hv.Overlay(pha_traces).opts(logx=True)
    return hv.Layout([mag, phase]).cols(1)

def bodeplot(streams):
    return hv.DynamicMap(_bodeplot, streams=streams)

def _sweepplot(data, cols=[]):
    traces = {k: hv.Curve(data, 'index', k).redim(**{k:'amplitude', 'index':'sweep'}) for k in cols}
    if not cols:
        traces = {"dummy": hv.Curve([])}
    return hv.NdOverlay(traces, kdims='k')

def sweepplot(streams):
    return hv.DynamicMap(_sweepplot, streams=streams)

def table(streams):
    return hv.DynamicMap(
        lambda data, cols: hv.Table(data[cols]),
        streams=streams
    )

def _fftplot(data, cols=[], n=1024):
    traces = []
    for k in cols:
        fftdat = fft(data[k], n).iloc[:n//2]
        mt = hv.Curve((fftdat.index, fftdat.abs()), 'freqency', 'amplitude')
        traces.append(mt)

    if not cols:
        traces = [hv.Curve([])]

    return hv.Overlay(traces).opts(logx=True, logy=True)

def fftplot(streams, n=1024):
    return hv.DynamicMap(functools.partial(_fftplot, n=n), streams=streams)

## processing

def span(ts):
    return ts.index[-1] - ts.index[0]

def interpolate(ts):
    x = ts.index.to_numpy()
    y = ts.to_numpy()
    return scipy.interpolate.interp1d(x, y)

def sample(ts, n):
    Y = interpolate(ts)
    return Y(np.linspace(ts.index[0], ts.index[-1], n))

def fft(ts, n):
    ft = sample(ts, n)
    dt = span(ts)/n
    fftdat = scipy.fft.fft(ft)
    fftfreq = scipy.fft.fftfreq(ft.size, dt);
    print(ft.size, dt, fftfreq, fftdat)
    return pd.Series(fftdat, fftfreq, name=ts.name)