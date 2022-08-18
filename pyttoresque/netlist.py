# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0
"""
This module communicates with CouchDB to fetch schematics, and generate SPICE netlists out of them.

Basic usage:
```
async with SchematicService("http://localhost:5984/offline") as service:
    name = "top$top"
    seq, docs = await service.get_all_schem_docs(name)
    print(spice_netlist(name, docs))
```

The sequence number can later be used to efficiently update the netlist with `update_schem`.
For live updates, use `live_schem_docs`.
"""

import aiohttp
from collections import deque, namedtuple
from json import loads
import urllib.parse as ulp
from contextlib import AbstractAsyncContextManager
from aiohttp.client_exceptions import ClientError
from datetime import datetime
import numpy as np
from holoviews.streams import Buffer


def shape_ports(shape):
    for y, s in enumerate(shape):
        for x, c in enumerate(s):
            if c != ' ':
                yield x, y, c


mosfet_shape = list(shape_ports([
    " D ",
    "GB ",
    " S ",
]))

bjt_shape = list(shape_ports([
    " C ",
    "B  ",
    " E ",
]))


twoport_shape = list(shape_ports([
    " P ",
    "   ",
    " N ",
]))


class SchemId(namedtuple("SchemId", ["cell", "model", "device"])):
    @classmethod
    def from_string(cls, id):
        schem, dev, *_= id.split(':') + [None]
        cell, model = schem.split('$')
        return cls(cell, model, dev)

    @property
    def schem(self):
        return f"{self.cell}${self.model}"


def doc_selector(schem):
    ors = [{"_id": {
            "$gt": name+":",
            "$lt": name+":\ufff0",
        }} for name in schem.keys()]
    return {"$or": ors}


class StatusError(ClientError):
    """Non-200 response"""

class SchematicService(AbstractAsyncContextManager):
    "A context manager for getting schematics from a CouchDB database"

    def __init__(self, url):
        "Create a HTTP session with the given database URL"
        self.url = url+"/"
        self.session = aiohttp.ClientSession()

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def dbget(self, path, **kwargs):
        "Do a GET request to the given database endpoint and query parameters"
        url = ulp.urljoin(self.url, path)
        async with self.session.get(url, params=kwargs) as res:
            if res.status >= 400:
                raise StatusError(await res.json())
            return await res.json()

    async def dbpost(self, path, json, **kwargs):
        "Do a POST request to the given database endpoint, JSON data, and query parameters"
        url = ulp.urljoin(self.url, path)
        async with self.session.post(url, json=json, params=kwargs) as res:
            if res.status >= 400:
                raise StatusError(await res.json())
            return await res.json()

    async def dbput(self, path, json, **kwargs):
        "Do a PUT request to the given database endpoint, data, and query parameters"
        url = ulp.urljoin(self.url, path)
        async with self.session.put(url, json=json, params=kwargs) as res:
            if res.status >= 400:
                raise StatusError(await res.json())
            return await res.json()

    async def dbstream(self, path, json, **kwargs):
        "Stream data from the given database endpoint, JSON data, and query parameters"
        url = ulp.urljoin(self.url, path)
        async with self.session.post(url, json=json, params=kwargs) as res:
            if res.status >= 400:
                raise StatusError(await res.json())
            while True:
                line = await res.content.readline()
                if not line: break
                if not line.strip(): continue
                yield loads(line)

    async def get_docs(self, name):
        "Get all the documents with the specified schematic ID"
        res = await self.dbget("_all_docs",
            include_docs="true",
            startkey=f'"{name}:"',
            endkey=f'"{name}:\ufff0"',
            update_seq="true"
        )
        return res['update_seq'], {row['id']: row['doc'] for row in res['rows']}


    async def get_all_schem_docs(self, name):
        """
        Recursively get all the documents of the specified schematic and all the subcircuits inside it.
        And all the model definitions.
        Returns a sequence number and a dictionary of schematic ID: documents.
        """
        schem = {}
        seq, models = await self.get_docs("models")
        schem["models"] = models
        seq, docs = await self.get_docs(name)
        schem[name] = docs
        devs = deque(docs.values())
        while devs:
            dev = devs.popleft()
            _id = SchemId(dev["cell"], dev.get('props', {}).get('model'), None)
            typ = models.get('models:'+_id.cell, {}).get('models', {}).get(_id.model, {}).get('type')
            if _id.model and _id.schem not in schem and typ == "schematic":
                seq, docs = await self.get_docs(_id.schem)
                if docs:
                    schem[_id.schem] = docs
                    devs.extend(docs.values())
        return seq, schem

    async def update_schem(self, seq, schem):
        "Take a sequence number and dictionary as returned by `get_all_schem_docs` and update it."
        sel = doc_selector(schem)
        result = await self.dbget("_changes",
            filter="_selector",
            since=seq,
            include_docs="true",
            json={"selector": sel})

        for change in result['results']:
            print(change)
            doc = change['doc']
            _id = SchemId.from_string(doc["_id"])
            if doc.get('_deleted', False):
                del schem[_id.schem][doc["_id"]]
            else:
                schem[_id.schem][doc["_id"]] = doc

        seq = result['last_seq']
        return seq, schem


    async def live_schem_docs(self, name):
        "A live stream of updated dictionaries, as returned by `get_all_schem_docs`"
        seq, schem = await self.get_all_schem_docs(name)
        yield schem

        sel = doc_selector(schem)
        result = self.dbstream('_changes',
            feed='continuous',
            heartbeat=10000,
            filter="_selector",
            since=seq,
            include_docs="true",
            json={"selector": sel})

        async for chunk in result:
            doc = chunk["doc"]
            _id = SchemId.from_string(doc["_id"])
            if doc.get('_deleted', False):
                del schem[_id.schem][doc["_id"]]
            else:
                schem[_id.schem][doc["_id"]] = doc
            yield schem

    async def save_simulation(self, name, data):
        """takes a schematic name and data as populated by
        `pyttoresque.simserver.stream` and saves it to the database.
        Additional keys can be added as the designer sees fit."""
        time = datetime.utcnow().isoformat()
        _id = name + "$result:" + time
        jsondata = {}
        for k, v in data.items():
            if isinstance(v, Buffer):
                df = v.data.reset_index()
                jsondata[k] = {}
                for col in df:
                    if df[col].dtype == complex:
                        jsondata[k][col] = {
                            "mag": df[col].abs().to_list(),
                            "arg": list(np.angle(df[col].to_list()))
                        }
                    else:
                        jsondata[k][col] = df[col].to_list()
            else:
                jsondata[k] = v
        return await self.dbput(_id, jsondata)


def rotate(shape, transform, devx, devy):
    a, b, c, d, e, f = transform
    width = max(max(x, y) for x, y, _ in shape)+1
    mid = width/2-0.5
    res = {}
    for px, py, p in shape:
        x = px-mid
        y = py-mid
        nx = a*x+c*y+e
        ny = b*x+d*y+f
        res[round(devx+nx+mid), round(devy+ny+mid)] = p
    return res


def getports(doc, models):
    cell = doc['cell']
    x = doc['x']
    y = doc['y']
    tr = doc.get('transform', [1, 0, 0, 1, 0, 0])
    if cell == 'wire':
        rx = doc['rx']
        ry = doc['ry']
        return {(x, y): None,
                (x+rx, y+ry): None}
    elif cell == 'text':
        return {}
    elif cell == 'port':
        return {(x, y): doc['name']}
    elif cell in {'nmos', 'pmos'}:
        return rotate(mosfet_shape, tr, x, y)
    elif cell in {'npn', 'pnp'}:
        return rotate(bjt_shape, tr, x, y)
    elif cell in {'resistor', 'capacitor', 'inductor', 'vsource', 'isource', 'diode'}:
        return rotate(twoport_shape, tr, x, y)
    else:
        return rotate(models[f"models:{cell}"]['conn'], tr, x, y)


def port_index(docs, models):
    wire_index = {}
    device_index = {}
    for doc in docs.values():
        cell = doc['cell']
        for (x, y), p in getports(doc, models).items():
            if cell in {'wire', 'port'}:
                wire_index.setdefault((x, y), []).append(doc)
            else:
                device_index.setdefault((x, y), []).append((p, doc))
                # add a dummy net so two devices can connect directly
                wire_index.setdefault((x, y), []).append({"cell": "wire", "x": x, "y": y, "rx": 0, "ry": 0})
    return device_index, wire_index


def wire_net(wireid, docs, models):
    device_index, wire_index = port_index(docs, models)
    netname = None
    net = deque([docs[wireid]]) # all the wires on this net
    while net:
        doc = net.popleft() # take a wire from the net
        cell = doc['cell']
        if cell == 'wire':
            wirename = doc.get('name')
            if netname == None and wirename != None:
                netname = wirename
            for ploc in getports(doc, models).keys(): # get the wire ends
                # if the wire connects to another wire,
                # that we have not seen, add it to the net
                if ploc in wire_index:
                    net.extend(wire_index.pop(ploc))
        elif cell == 'port':
            netname = doc.get('name')
        else:
            raise ValueError(cell)
    return netname

def netlist(docs, models):
    """
    Turn a collection of documents as returned by `get_docs` into a netlist structure.
    Returns a dictionary of device ID: {port: net}
    Usage:
    ```
    async with SchematicService("http://localhost:5984/offline") as service:
        name = "top$top"
        seq, docs = await service.get_all_schem_docs(name)
        print(netlist(docs[name], models))
    ```
    """
    device_index, wire_index = port_index(docs, models)
    nl = {}
    netnum = 0
    while wire_index:  # while there are wires left
        loc, locwires = wire_index.popitem()  # take one
        netname = None
        net = deque(locwires) # all the wires on this net
        netdevs = {} # all the devices on this net
        while net:
            doc = net.popleft() # take a wire from the net
            cell = doc['cell']
            if cell == 'wire':
                wirename = doc.get('name')
                if netname == None and wirename != None:
                    netname = wirename
                for ploc in getports(doc, models).keys(): # get the wire ends
                    # if the wire connects to another wire,
                    # that we have not seen, add it to the net
                    if ploc in wire_index:
                        net.extend(wire_index.pop(ploc))
                    # if the wire connect to a device, add its port to netdevs
                    if ploc in device_index:
                        for p, dev in device_index[ploc]:
                            netdevs.setdefault(dev['_id'], []).append(p)
            elif cell == 'port':
                netname = doc.get('name')
            else:
                raise ValueError(cell)
        if netname == None:
            netname = f"net{netnum}"
            netnum += 1
        for k, v in netdevs.items():
            nl.setdefault(netname, {}).setdefault(k, []).extend(v)
    inl = {}
    for net, devs in nl.items():
        for dev, pts in devs.items():
            for port in pts:
                inl.setdefault(dev, {})[port] = net
    return inl


def print_props(props):
    prs = []
    for k, v in props.items():
        if k == "model":
            prs.insert(0, v)
        elif k == "spice":
            prs.append(v)
        else:
            prs.append(f"{k}={v}")
    return " ".join(prs)


def circuit_spice(docs, models, declarations, corner, sim):
    nl = netlist(docs, models)
    cir = []
    for id, ports in nl.items():
        dev = docs[id]
        cell = dev['cell']
        mname = dev.get('props', {}).get('model', '')
        name = dev.get('name') or id
        # print(ports)
        def p(p): return ports[p]
        propstr = print_props(dev.get('props', {}))
        if cell == "resistor":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "R{name} {ports} {properties}"
        elif cell == "capacitor":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "C{name} {ports} {properties}"
        elif cell == "inductor":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "L{name} {ports} {properties}"
        elif cell == "diode":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "D{name} {ports} {properties}"
        elif cell == "vsource":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "V{name} {ports} {properties}"
        elif cell == "isource":
            ports = ' '.join(p(c) for c in ['P', 'N'])
            templ = "I{name} {ports} {properties}"
        elif cell in {"pmos", "nmos"}:
            ports = ' '.join(p(c) for c in ['D', 'G', 'S', 'B'])
            templ = "M{name} {ports} {properties}"
        elif cell in {"npn", "pnp"}:
            ports = ' '.join(p(c) for c in ['C', 'B', 'E'])
            templ = "Q{name} {ports} {properties}"
        else:  # subcircuit
            m = models[f"models:{cell}"]
            ports = ' '.join(p(c[2]) for c in m['conn'])
            templ = "X{name} {ports} {properties}"

        # a spice type model can overwrite its reference
        # for example if the mosfet is really a subcircuit
        try:
            m = models[f"models:{cell}"]["models"][mname][sim]
            templ = m['reftempl']
            declarations.add(m['decltempl'].format(corner=corner))
        except KeyError:
            pass

        cir.append(templ.format(name=name, ports=ports, properties=propstr))
    return '\n'.join(cir)


def spice_netlist(name, schem, extra="", corner='tt', temp=None, sim="NgSpice", **params):
    """
    Generate a spice netlist, taking a dictionary of schematic documents, and the name of the top level schematic.
    It is possible to pass extra SPICE code and specify the simulation corner.
    """
    models = schem["models"]
    declarations = set()
    for subname, docs in schem.items():
        if subname in {name, "models"}: continue
        _id = SchemId.from_string(subname)
        mod = models[f"models:{_id.cell}"]
        ports = ' '.join(c[2] for c in mod['conn'])
        body = circuit_spice(docs, models, declarations, corner, sim)
        declarations.add(f".subckt {_id.model} {ports}\n{body}\n.ends {_id.model}") # parameters??

    body = circuit_spice(schem[name], models, declarations, corner, sim)
    ckt = []
    ckt.append(f"* {name}")
    ckt.extend(declarations)
    ckt.append(body)
    ckt.append(extra)
    ckt.append(".end\n")

    return "\n".join(ckt)

default_device_vectors = {
    'resistor': ['i'],
    'capacitor': ['i'],
    'inductor': ['i'],
    'vsource': ['i'],
    'isource': [],
    'diode': [],
    'nmos': ['gm', 'id', 'vdsat'],
    'pmos': ['gm', 'id', 'vdsat'],
    'npn': ['gm', 'ic', 'ib'],
    'pnp': ['gm', 'ic', 'ib'],

}
device_prefix = {
    'resistor': 'r',
    'capacitor': 'c',
    'inductor': 'l',
    'vsource': 'v',
    'isource': 'i',
    'diode': 'd',
    'nmos': 'm',
    'pmos': 'm',
    'npn': 'q',
    'pnp': 'q',

}
# @m.xx1.xmc1.msky130_fd_pr__nfet_01v8[gm]
def ngspice_vectors(name, schem, path=()):
    """
    Extract all the relevant vectors from the schematic,
    and format them in NgSpice syntax.
    Saves label/port net names, and vectors indicated on spice models.
    """
    models = schem["models"]
    vectors = []
    for id, elem in schem[name].items():
        if elem['cell'] == 'port' and elem['name'].lower() != 'gnd':
            vectors.append(('.'.join(path + (elem['name'],))).lower())
            continue
        m = models.get("models:"+elem['cell'], {})
        n = m.get('models', {}).get(elem.get('props', {}).get('model'), {})
        if n.get('type') == 'spice':
            vex = n.get('NgSpice', {}).get('vectors', [])
            comp = n.get('NgSpice', {}).get('component')
            reftempl = n.get('NgSpice', {}).get('reftempl')
            typ = (comp or reftempl or 'X')[0]
            dtyp = (reftempl or 'X')[0]
            if comp:
                full = typ + '.' + '.'.join(path + (dtyp+elem['name'], comp))
            elif path:
                full = typ + '.' + '.'.join(path + (dtyp+elem['name'],))
            else:
                full = typ+elem['name']
            vectors.extend(f"@{full}[{v}]".lower() for v in vex)
        elif n.get('type') == 'schematic':
            name = elem['cell']+"$"+elem['props']['model']
            vectors.extend(ngspice_vectors(name, schem, path+("X"+elem['name'],)))
        elif elem['cell'] in default_device_vectors: # no model specified
            vex = default_device_vectors[elem['cell']]
            typ = device_prefix.get(elem['cell'], 'x')
            if path:
                full = typ + '.' + '.'.join(path + (typ+elem['name'],))
            else:
                full = typ+elem['name']
            vectors.extend(f"@{full}[{v}]".lower() for v in vex)
    return vectors

async def main():
    async with SchematicService("http://localhost:5984/offline") as service:
        name = "top$top"
        seq, docs = await service.get_all_schem_docs(name)
        # print(port_index(docs[name], models))
        # print(netlist(docs[name], models))
        # print(spice_netlist(name, docs))
        print(ngspice_vectors(name, docs))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
