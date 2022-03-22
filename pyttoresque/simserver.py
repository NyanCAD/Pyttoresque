from os import name
import capnp
from pyttoresque.api.Simulator_capnp import Ngspice, Xyce, Cxxrtl, AcType
from collections import namedtuple
from streamz import Stream, buffer
from streamz.dataframe import DataFrame
import numpy as np
import pandas as pd


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
        vecsdata =  {}
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

        index = vecsdata.pop(vecs.scale)
        data[vecs.name] = pd.DataFrame(vecsdata, index=index)

    return res.more, data


def stream(response, streamzdict):
    """
    Stream simulation data into a Streamz DataFrame
    Takes an optional document to stream in `add_next_tick_callback` or
    a cell handle to invoke `push_notebook` on.
    """
    more = True
    while more:
        more, res = read(response)
        for k, v in res.items():
            if k in streamzdict and (v.columns == streamzdict[k].columns).all():
                streamzdict[k].emit(v)
            else:
                s = buffer(Stream(), 100000)
                df = DataFrame(s, example=v)
                df.emit(v)
                streamzdict[k] = df
        yield


def readAll(response):
    """
    Read all the simulation data from a simulation command.
    """
    cdsdict = {}
    for _ in stream(response, cdsdict):
        pass
    return cdsdict

if __name__ == "__main__":
    con = connect("localhost")
    fs = loadFiles(con, "test.cir")
    res = fs.commands.tran(1e-6, 1e-3, 0)
    d = {}
    for _ in stream(res, d):
        print(d)
