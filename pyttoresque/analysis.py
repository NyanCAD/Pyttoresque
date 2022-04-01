import holoviews as hv
import datashader as ds
from holoviews.streams import Buffer, Stream, param
from holoviews.operation.datashader import datashade, shade, dynspread, spread, rasterize

hv.extension('plotly')

active_traces = Stream.define('traces', cols=[])

def _timeplot(data, cols=[]):
    traces = {k: hv.Curve((data.index, data[k]), 'time', 'amplitude') for k in cols}
    if not traces:
        traces = {"dummy": hv.Curve([])}
    return hv.NdOverlay(traces, kdims='k')

def timeplot(streams):
    curve_dmap = hv.DynamicMap(_timeplot, streams=streams)
    # return dynspread(datashade(curve_dmap, aggregator=ds.by('k', ds.any())))
    return spread(datashade(curve_dmap, aggregator=ds.count_cat('k'), width=1000, height=1000))