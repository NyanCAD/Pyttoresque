from typing import NamedTuple
from ibmcloudant.cloudant_v1 import CloudantV1
from collections import deque, namedtuple
import json

service = CloudantV1.new_instance()

dbdefault = "schematics"


def shape_ports(shape):
    for x, s in enumerate(shape):
        for y, c in enumerate(s):
            if c != ' ':
                yield x, y, c


mosfet_shape = list(shape_ports([
    " D"
    "GB"
    " S"
]))

twoport_shape = list(shape_ports([
    "P"
    "N"
]))


class Modeldict(dict):
    def __init__(self, *args, db=dbdefault, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    def __missing__(self, key):
        doc = service.get_document(self.db, key).get_result()
        self[key] = doc
        return doc

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


def get_schem_docs(name, db=dbdefault):
    res = service.post_all_docs(
        db=db,
        include_docs=True,
        startkey=f"{name}:",
        endkey=f"{name}:\ufff0",
        update_seq=True
    ).get_result()
    return res['update_seq'], {row['id']: row['doc'] for row in res['rows']}


def get_all_schem_docs(name, db=dbdefault):
    schem = {}
    seq, docs = get_schem_docs(name, db)
    schem[name] = docs
    devs = deque(docs.values())
    while devs:
        dev = devs.popleft()
        _id = SchemId(dev["cell"], dev.get('props', {}).get('model'), None, None)
        if _id.model and _id.schem not in schem:
            seq, docs = get_schem_docs(_id.schem, db)
            schem[_id.schem] = docs
            devs.extend(docs.values())
    return seq, schem

def doc_selector(schem):
    ors = [{"_id": {
            "$gt": name+":",
            "$lt": name+":\ufff0",
        }} for name in schem.keys()]
    return {"$or": ors}

def update_schem(seq, schem, db=dbdefault):
    sel = doc_selector(schem)
    result = service.post_changes(
        db=db,
        filter="_selector",
        since=seq,
        include_docs=True,
        selector=sel).get_result()

    for change in result['results']:
        doc = change['doc']
        _id = SchemId.from_string(doc["_id"])
        if doc.get('_deleted', False):
            del schem[_id.schem][doc["_id"]]
        else:
            schem[_id.schem][doc["_id"]] = doc

    seq = result['last_seq']
    return seq, schem


def live_schem_docs(name, callback, db=dbdefault):
    seq, schem = get_all_schem_docs(name, db)
    callback(schem)

    sel = doc_selector(schem)
    result = service.post_changes_as_stream(
        db=db,
        feed='continuous',
        heartbeat=5000,
        filter="_selector",
        since=seq,
        include_docs=True,
        selector=sel).get_result()

    for chunk in result.iter_lines():
        if chunk:
            doc = json.loads(chunk)["doc"]
            _id = SchemId.from_string(doc["_id"])
            if doc.get('_deleted', False):
                del schem[_id.schem][doc["_id"]]
            else:
                schem[_id.schem][doc["_id"]] = doc
            callback(schem)



def ports(doc, models):
    cell = doc['cell']
    x = doc['x']
    y = doc['y']
    if cell == 'wire':
        rx = doc['rx']
        ry = doc['ry']
        return {(x, y): None,
                (x+rx, y+ry): None}
    elif cell == 'label':
        return {(x, y): doc['name']}
    elif cell in {'nmos', 'pmos'}:
        return {(x+px, y+py): p for px, py, p in mosfet_shape}
    elif cell in {'resistor', 'capacitor', 'inductor', 'vsource', 'isource', 'diode'}:
        return {(x+px, y+py): p for px, py, p in twoport_shape}
    else:
        return {(x+px, y+py): p for px, py, p in models[f"models:{cell}"]['conn']}


def port_index(docs, models):
    wire_index = {}
    device_index = {}
    for doc in docs.values():
        cell = doc['cell']
        for (x, y), p in ports(doc, models).items():
            if cell in {'wire', 'label'}:
                wire_index.setdefault((x, y), []).append(doc)
            else:
                device_index[x, y] = (p, doc)
    return device_index, wire_index


def netlist(docs, models):
    device_index, wire_index = port_index(docs, models)
    nl = {}
    while wire_index:  # while there are devices left
        loc, locdevs = wire_index.popitem()  # take one
        netname = None
        net = deque(locdevs)
        netdevs = {}
        while net:
            doc = net.popleft()
            cell = doc['cell']
            if cell == 'wire':
                for ploc in ports(doc, models).keys():
                    if ploc in wire_index:
                        net.extend(wire_index.pop(ploc))
                    if ploc in device_index:
                        p, dev = device_index[ploc]
                        netdevs[dev['_id']] = p
            elif cell == 'label':
                netname = doc.get('name')
            else:
                raise ValueError(cell)
        nl[netname] = netdevs
    inl = {}
    for net, devs in nl.items():
        for dev, port in devs.items():
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


def circuit_spice(docs, models):
    nl = netlist(docs, models)
    cir = []
    for id, ports in nl.items():
        dev = docs[id]
        cell = dev['cell']
        model = dev.get('props', {}).get('model', '')
        name = dev.get('name') or spicename(id)
        def p(p): return spicename(ports[p])
        propstr = print_props(dev.get('props', {}))
        if cell == "resistor":
            cir.append(f"R{name} {p('P')} {p('N')} {propstr}")
        elif cell == "capacitor":
            cir.append(f"C{name} {p('P')} {p('N')} {propstr}")
        elif cell == "inductor":
            cir.append(f"L{name} {p('P')} {p('N')} {propstr}")
        elif cell == "diode":
            cir.append(f"D{name} {p('P')} {p('N')} {propstr}")
        elif cell == "vsource":
            cir.append(f"V{name} {p('P')} {p('N')} {propstr}")
        elif cell == "isource":
            cir.append(f"I{name} {p('P')} {p('N')} {propstr}")
        elif cell in {"pmos", "nmos"}:
            cir.append(
                f"M{name} {p('D')} {p('G')} {p('S')} {p('B')} {model} {propstr}")
        else:  # subcircuit
            m = models[f"models:{cell}"]
            ports = ' '.join(p(c[2]) for c in m['conn'])
            cir.append(f"X{name} {ports} {model}")  # todo
    return '\n'.join(cir)


def spice_netlist(name, schem, models):
    ckt = []
    ckt.append(f"* {name}")
    for subname, docs in schem.items():
        if name == subname: continue
        _id = SchemId.from_string(subname)
        mod = models[f"models:{_id.cell}"]
        ports = ' '.join(c[2] for c in mod['conn'])
        body = circuit_spice(docs, models)
        ckt.append(f".subckt {_id.model} {ports}")
        ckt.append(body)
        ckt.append(f".ends {_id.model}")

    body = circuit_spice(schem[name], models)
    ckt.append(body)
    ckt.append(".end\n")

    return "\n".join(ckt)


if __name__ == "__main__":
    models = Modeldict()
    seq, docs = get_all_schem_docs("top$top")
    # print(docs.keys())
    # print(netlist(docs, models))
    print(spice_netlist("top$top", docs, models))
