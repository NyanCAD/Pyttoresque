import aiohttp
from collections import deque, namedtuple
from json import loads
import urllib.parse as ulp
from contextlib import AbstractAsyncContextManager
from aiohttp.client_exceptions import ClientError


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


class SchemId(namedtuple("SchemId", ["cell", "model", "device", "key"])):
    @classmethod
    def from_string(cls, id):
        schem, dev, *_= id.split(':') + [None]
        if dev:
            device, key = dev.split('-')
        else:
            device = None
            key = None
        cell, model = schem.split('$')
        return cls(cell, model, device, key)

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
    @classmethod
    def __init__(self, url):
        self.url = url+"/"
        self.session = aiohttp.ClientSession()

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def dbget(self, path, **kwargs):
        url = ulp.urljoin(self.url, path)
        async with self.session.get(url, params=kwargs) as res:
            if res.status != 200:
                raise StatusError(await res.json())
            return await res.json()

    async def dbpost(self, path, json, **kwargs):
        url = ulp.urljoin(self.url, path)
        async with self.session.post(url, json=json, params=kwargs) as res:
            if res.status != 200:
                raise StatusError(await res.json())
            return await res.json()

    async def dbstream(self, path, json, **kwargs):
        url = ulp.urljoin(self.url, path)
        async with self.session.post(url, json=json, params=kwargs) as res:
            if res.status != 200:
                raise StatusError(await res.json())
            while True:
                line = await res.content.readline()
                if not line: break
                if not line.strip(): continue
                yield loads(line)

    async def get_docs(self, name):
        res = await self.dbget("_all_docs",
            include_docs="true",
            startkey=f'"{name}:"',
            endkey=f'"{name}:\ufff0"',
            update_seq="true"
        )
        return res['update_seq'], {row['id']: row['doc'] for row in res['rows']}


    async def get_all_schem_docs(self, name):
        schem = {}
        seq, models = await self.get_docs("models")
        schem["models"] = models
        seq, docs = await self.get_docs(name)
        schem[name] = docs
        devs = deque(docs.values())
        while devs:
            dev = devs.popleft()
            _id = SchemId(dev["cell"], dev.get('props', {}).get('model'), None, None)
            if _id.model and _id.schem not in schem:
                seq, docs = await self.get_docs(_id.schem)
                if docs:
                    schem[_id.schem] = docs
                    devs.extend(docs.values())
        return seq, schem

    async def update_schem(self, seq, schem):
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
                wire_index.setdefault((x, y), [{"cell": "wire", "x": x, "y": y, "rx": 0, "ry": 0}])
    return device_index, wire_index


def netlist(docs, models):
    device_index, wire_index = port_index(docs, models)
    nl = {}
    netnum = 0
    while wire_index:  # while there are wires left
        loc, locwires = wire_index.popitem()  # take one
        netname = f"net{netnum}"
        netnum+=1
        net = deque(locwires) # all the wires on this net
        netdevs = {} # all the devices on this net
        while net:
            doc = net.popleft() # take a wire from the net
            cell = doc['cell']
            if cell == 'wire':
                wirename = doc.get('name')
                if wirename:
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


def spicename(n):
    return n.split('-',)[-1]


def circuit_spice(docs, models, declarations):
    nl = netlist(docs, models)
    cir = []
    for id, ports in nl.items():
        dev = docs[id]
        cell = dev['cell']
        mname = dev.get('props', {}).get('model', '')
        name = dev.get('name') or spicename(id)
        def p(p): return spicename(ports[p])
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
            m = models[f"models:{cell}"]["models"][mname]
            templ = m['reftempl']
            declarations.add(m['decltempl'])
        except KeyError:
            pass

        cir.append(templ.format(name=name, ports=ports, properties=propstr))
    return '\n'.join(cir)


def spice_netlist(name, schem, extra=""):
    models = schem["models"]
    declarations = set()
    for subname, docs in schem.items():
        if subname in {name, "models"}: continue
        _id = SchemId.from_string(subname)
        mod = models[f"models:{_id.cell}"]
        ports = ' '.join(c[2] for c in mod['conn'])
        body = circuit_spice(docs, models, declarations)
        declarations.add(f".subckt {_id.model} {ports}\n{body}\n.ends {_id.model}") # parameters??

    body = circuit_spice(schem[name], models, declarations)
    ckt = []
    ckt.append(f"* {name}")
    ckt.extend(declarations)
    ckt.append(body)
    ckt.append(extra)
    ckt.append(".end\n")

    return "\n".join(ckt)


async def main():
    async with SchematicService("http://localhost:5984/offline") as service:
        name = "top$top"
        seq, docs = await service.get_all_schem_docs(name)
        # print(port_index(docs[name], models))
        # print(netlist(docs[name], models))
        print(spice_netlist(name, docs))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
