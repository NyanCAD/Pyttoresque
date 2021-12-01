import capnp
import Simulator_capnp as api
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def loadFiles(sim, *names):
    data = []
    for name in names:
        with open(name, 'rb') as f:
            data.append({
                "name": name,
                "contents": f.read()
            })
    return sim.loadFiles(data)

def map_complex(vec):
    return [complex(v.real, v.imag) for v in vec.complex]

def readAll(result):
    data = {}
    scale = None
    while True:
        res = result.read().wait()
        for vec in res.data:
            if vec.data.which() == 'real':
                data.setdefault(vec.name, []).extend(vec.data.real)
            elif vec.data.which() == 'complex':
                cdata = map_complex(vec.data)
                data.setdefault(vec.name, []).extend(cdata)
            elif vec.data.which() == 'digital':
                data.setdefault(vec.name, []).extend(vec.data.digital)
            else:
                raise TypeError(vec.data.which())

        if res.scale:
            scale = res.scale
        if not res.more: break
    df = pd.DataFrame(data)
    if scale:
        df[scale] = df[scale].abs()
        return df.set_index(scale)
    else:
        return df

def take_args(q):
    res = []
    while q and q[0] not in {'ngspice', 'xyce', 'cxxrtl', 'op', 'ac', 'tran', 'run'}:
        res.append(q.popleft())
    return res

if __name__ == "__main__":
    import sys
    from collections import deque

    usage = f"usage: {sys.argv[0]} sim host:port file cmd args..."

    args = deque(sys.argv[1:])
    res = None
    while args:
        arg = args.popleft()

        if arg == "ngspice":
            host = args.popleft()
            files = take_args(args)
            sim = capnp.TwoPartyClient(host).bootstrap().cast_as(api.Ngspice)
            res = loadFiles(sim, *files)
        elif arg == "xyce":
            host = args.popleft()
            files = take_args(args)
            sim = capnp.TwoPartyClient(host).bootstrap().cast_as(api.Xyce)
            res = loadFiles(sim, *files)
        elif arg == "cxxrtl":
            host = args.popleft()
            files = take_args(args)
            sim = capnp.TwoPartyClient(host).bootstrap().cast_as(api.Cxxrtl)
            res = loadFiles(sim, *files)
        elif arg == "op":
            df = readAll(res.commands.op().result)
            print(df)
        elif arg == "ac":
            fnum = float(args.popleft())
            fstart = float(args.popleft())
            fstop = float(args.popleft())
            vecs = take_args(args)
            df = readAll(res.commands.ac(api.AcType.dec, fnum, fstart, fstop, vectors=vecs).result)
            fig, (ax1, ax2) = plt.subplots(nrows=2)
            df.abs().plot(ax=ax1, loglog=True)
            df.apply(np.angle).apply(np.rad2deg).plot(ax=ax2, logx=True)
        elif arg == "tran":
            tstep = float(args.popleft())
            tstop = float(args.popleft())
            tstart = float(args.popleft())
            vecs = take_args(args)
            df = readAll(res.commands.tran(tstep, tstop, tstart, vectors=vecs).result)
            df.plot()
        elif arg == "run":
            vecs = take_args(args)
            df = readAll(res.commands.run(vectors=vecs).result)
            (df*1).plot(subplots=True)
        else:
            print(usage)
            raise RuntimeError(arg)

    plt.show()
