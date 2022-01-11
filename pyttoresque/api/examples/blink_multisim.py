import sys
sys.path.append("..")
import capnp
import Simulator_capnp as api
import pandas as pd
import matplotlib.pyplot as plt

def loadFiles(sim, *names):
    data = []
    for name in names:
        with open(name, 'rb') as f:
            data.append({
                "name": name,
                "contents": f.read()
            })
    return sim.loadFiles(data)

plt.figure()
plt.ion()
plt.pause(10)

ngspice = capnp.TwoPartyClient("localhost:5924").bootstrap().cast_as(api.Ngspice)
xyce = capnp.TwoPartyClient("localhost:5923").bootstrap().cast_as(api.Xyce)
cxxrtl = capnp.TwoPartyClient("localhost:5925").bootstrap().cast_as(api.Cxxrtl)
cmd = {
    "ngspice": loadFiles(ngspice, "blink.sp").commands.run(vectors=["V(led)"]).result,
    "xyce": loadFiles(xyce, "blink.sp").commands.run(vectors=["TIME", "V(led)"]).result,
    "cxxrtl": loadFiles(cxxrtl, "blink.v", "CMakeLists.txt", "main.cpp").commands.run(vectors=["led"]).result,
}

done = {k: False for k in cmd.keys()}
dataframes = {}
ax = plt.gca()
while not all(done.values()):
    for sim, result in cmd.items():
        print(sim, "reading")
        res = result.read().wait()
        print(sim, res.more)
        if not res.more:
            done[sim] = True
        if not res.scale:
            continue

        data = {}
        scale = res.scale
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

        df = pd.DataFrame(data)
        df = df.set_index(scale)
        if sim == 'cxxrtl':
            df = df*1.8
        if sim in dataframes:
            dataframes[sim] = dataframes[sim].append(df)
        else:
            dataframes[sim] = df

    plt.gca().cla()
    for k in ['cxxrtl', 'ngspice', 'xyce']:
        if k in dataframes and not dataframes[k].empty:
            df = dataframes[k]
            (df).plot(ax=ax)
    plt.draw()
    plt.pause(0.1)

plt.show(block=True)