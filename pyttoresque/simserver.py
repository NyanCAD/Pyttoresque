from os import name
import capnp
from pyttoresque.api.Simulator_capnp import Ngspice, Xyce, Cxxrtl, AcType
from bokeh.models import ColumnDataSource
from bokeh.io import push_notebook
from collections import namedtuple
import numpy as np


def connect(host, port=5923, simulator=Ngspice):
    """
    Connect to a simulation server at the given `host:port`,
    which should be a `simulator` such as `Ngspice` or `Xyce`.
    """
    return capnp.TwoPartyClient(f"{host}:{port}").bootstrap().cast_as(simulator)


def loadFiles(sim, *names):
    """
    Load the specified filenames into the simulation server.
    The first file is the entrypoint for the simulator.
    Returns a handle to run simulation commands on.

    For in-memory data, directly call `sim.loadFiles`.
    The data should be of the form `[{"name": name, "contents": contents}]`

    For files already present on the simulator use `sim.loadPath`.
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
    return np.fromiter((complex(v.real, v.imag) for v in vec), complex)


Result = namedtuple("Result", ("scale", "data"))

def read(response):
    """
    Read one chunk from a simulation command
    """
    data = {}
    res = response.result.read().wait()
    # print(res)
    for vecs in res.data:
        # this set of vectors is not initialised, skip it
        if not vecs.scale:
            continue
        scale, vecsdata = data.setdefault(vecs.name, Result(vecs.scale, {}))
        for vec in vecs.data:
            # array *could* be empty
            arr = getattr(vec.data, vec.data.which())
            if vec.data.which() == 'complex':
                # horrible hack because Bokeh doesn't like complex numbers
                comp = map_complex(arr)
                vecsdata[vec.name] = np.abs(comp)
                vecsdata[vec.name+"_phase"] = np.angle(comp)
            else:
                vecsdata[vec.name] = np.array(arr)

    return res.more, data


def stream(response, cdsdict, *, doc=None, cell=None):
    """
    Stream simulation data into a ColumnDataSource
    Takes an optional document to stream in `add_next_tick_callback` or
    a cell handle to invoke `push_notebook` on.
    """
    # this closure will capture the data so it doesn't change
    def push(k, v):
        if k in cdsdict and list(v.data.keys()) == cdsdict[k].data.column_names:
            cdsdict[k].data.stream(v.data)
            if cell: # if we're running in a notebook, push update
                push_notebook(handle=cell)
        else:
            cdsdict[k] = Result(v.scale, ColumnDataSource(v.data))
    more = True
    while more:
        more, res = read(response)
        for k, v in res.items():
            if doc: # if we're running in a thread, update on next tick
                doc.add_next_tick_callback(lambda: push(k, v))
            else:
                push(k, v)
        yield


def readAll(response):
    """
    Read all the simulation data from a simulation command.
    """
    cdsdict = {}
    for _ in stream(response, cdsdict):
        pass
    return cdsdict
