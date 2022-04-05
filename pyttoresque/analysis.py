import holoviews as hv
import datashader as ds
import numpy as np
from holoviews.streams import Buffer, Stream, param
from holoviews.operation.datashader import datashade, shade, dynspread, spread, rasterize

hv.extension('plotly')

active_traces = Stream.define('traces', cols=[])

def _timeplot(data, cols=[]):
    traces = {k: hv.Curve((data.index, data[k]), 'time', 'amplitude') for k in cols}
    if not cols:
        traces = {"dummy": hv.Curve([])}
    return hv.NdOverlay(traces, kdims='k')

def timeplot(streams):
    curve_dmap = hv.DynamicMap(_timeplot, streams=streams)
    # return dynspread(datashade(curve_dmap, aggregator=ds.by('k', ds.any())))
    # return spread(datashade(curve_dmap, aggregator=ds.by('k', ds.count()), width=1000, height=1000))
    return spread(datashade(curve_dmap, aggregator=ds.count_cat('k'), width=1000, height=1000))

def _bodeplot(data, cols=[]):
    print(cols)
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
    traces = {k: hv.Curve((data.index, data[k]), 'sweep', 'amplitude') for k in cols}
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