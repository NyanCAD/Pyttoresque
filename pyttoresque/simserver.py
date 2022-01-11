from os import name
import capnp
from pyttoresque.api.Simulator_capnp import Ngspice, Xyce, Cxxrtl
from bokeh.models import ColumnDataSource
from bokeh.io import push_notebook
from collections import namedtuple
import numpy as np


def connect(host, port=5923, simulator=Ngspice):
    """
    Connect to a simulation server at the given `host:port`,
    which is should be a `simulator` such as `Ngspice` or `Xyce`.
    """
    return capnp.TwoPartyClient(f"{host}:{port}").bootstrap().cast_as(simulator)


def loadFiles(sim, *names):
    """
    Load the specified filenames into the simulation server.
    The first file is the entrypoint for the simulator.
    Returns a handle to run simulation commands on.

    For in-memory data, directly call `sim.loadFiles`.
    The data should be of the form `[{"name": name, "content": content"}]`
    """
    data = []
    for name in names:
        with open(name, 'rb') as f:
            data.append({
                "name": name,
                "contents": f.read()
            })
    return sim.loadFiles(data)


def map_complex(vec):
    return np.array(complex(v.real, v.imag) for v in vec.complex)


Result = namedtuple("Result", ("scale", "data"))


def read(response):
    """
    Read one chunk from a simulation command
    """
    while True:
        res = response.result.read().wait()
        if not res.scale:
            continue
        data = {}
        for vec in res.data:
                arr = getattr(vec.data, vec.data.which())
                if arr:
                    if vec.data.which() == 'complex':
                        data[vec.name] = map_complex(arr)
                    else:
                        data[vec.name] = np.array(arr)

        if data:
            return Result(res.scale, ColumnDataSource(data))
        if not res.more:
            return


def stream(response, cds, *, doc=None, cell=None):
    """
    Stream simulation data into a ColumnDataSource
    Takes an optional document to stream in `add_next_tick_callback` or
    a cell handle to invoke `push_notebook` on.
    """
    while True:
        res = read(response)
        if res:
            if doc: # if we're running in a thread, update on next tick
                doc.add_next_tick_callback(lambda: cds.stream(res.data.data))
            else:
                cds.stream(res.data.data)
            if cell: # if we're running in a notebook, push update
                push_notebook(handle=cell)
        else:
            break


def readAll(response):
    """
    Read all the simulation data from a simulation command.
    """
    res = read(response)
    while True:
        newres = read(response)
        if newres:
            res.data.stream(newres.data.data)
        else:
            break
    return res
