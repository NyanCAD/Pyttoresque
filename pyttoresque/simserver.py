from os import name
from time import sleep
from subprocess import Popen
import asyncio
import capnp
from pyttoresque.api.Simulator_capnp import Ngspice, Xyce, Cxxrtl, AcType
import numpy as np
import pandas as pd
from holoviews.streams import Buffer

async def capnpreader(client, reader):
    try:
        while True:
            data = await reader.read(4096)
            client.write(data)
    except Exception as e:
        print(e)


async def capnpwriter(client, writer):
    try:
        while True:
            data = await client.read(4096)
            writer.write(data.tobytes())
            await writer.drain()
    except Exception as e:
        print(e)


async def connect(host, port=5923, simulator=Ngspice, autostart=True):
    """
    Connect to a simulation server at the given `host:port`,
    which should be a `simulator` such as `Ngspice` or `Xyce`.

    If `host` is set to "localhost" and no server is running,
    we will attempt to start one automatically,
    unless `autostart=False`.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        client = capnp.TwoPartyClient()
        asyncio.gather(
            capnpreader(client, reader),
            capnpwriter(client, writer),
            return_exceptions=True)
        return client.bootstrap().cast_as(simulator)
    except:# ConnectionRefusedError: inside docker weird stuff happens
        # if we're doing a local simulation, start a new server
        if host=="localhost" and autostart:
            print("starting new local server")
            if simulator == Ngspice:
                simcmd = "NgspiceSimServer"
            elif simulator == Xyce:
                simcmd = "XyceSimServer"
            elif simulator == Cxxrtl:
                simcmd = "CxxrtlSimServer"
            else:
                raise ValueError(simulator)

            Popen([simcmd, str(port)])
            sleep(1) # wait a bit for the server to start :(
            return await connect(host, port, simulator, False)
        else:
            raise


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


async def read(response):
    """
    Read one chunk from a simulation command
    """
    data = {}
    res = await response.result.read().a_wait()
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
                vecsdata[vec.name] = map_complex(arr)
                # vecsdata[vec.name] = np.abs(comp)
                # vecsdata[vec.name+"_phase"] = np.angle(comp)
            else:
                vecsdata[vec.name] = np.array(arr)

        index = np.real(vecsdata.pop(vecs.scale))
        data[vecs.name] = pd.DataFrame(vecsdata, index=index)

    return res.more, data


async def stream(response, streamdict, newkey=lambda k:None):
    """
    Stream simulation data into a Buffer (DataFrame)
    """
    more = True
    while more:
        more, res = await read(response)
        for k, v in res.items():
            if k in streamdict and list(v.columns) == list(streamdict[k].data.columns):
                streamdict[k].send(v)
            else:
                buf = Buffer(v, length=int(1e9), index=False)
                streamdict[k] = buf
                newkey(k)


async def readAll(response):
    """
    Read all the simulation data from a simulation command.
    """
    streamdict = {}
    await stream(response, streamdict)
    return streamdict

async def main():
    con = await connect("localhost")
    fs = loadFiles(con, "test.cir")
    res = fs.commands.tran(1e-6, 1e-3, 0)
    d = {}
    print(await readAll(res))

if __name__ == "__main__":
    asyncio.run(main())