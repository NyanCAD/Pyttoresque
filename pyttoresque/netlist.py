from ibmcloudant.cloudant_v1 import CloudantV1
from collections import deque
import json

service = CloudantV1.new_instance()

dbdefault = "schematics"

mosfet_shape = [
    " D"
    "GB"
    " S"
]

twoport_shape = [
    "P"
    "N"
]


def shape_ports(shape):
    for x, s in enumerate(shape):
        for y, c in enumerate(s):
            if c != ' ':
                yield x, y, c


def get_schem_docs(name, db=dbdefault):
    res = service.post_all_docs(
        db=db,
        include_docs=True,
        startkey=f"{name}:",
        endkey=f"{name}:\ufff0",
        update_seq=True
    ).get_result()
    return res['update_seq'], {row['id']: row['doc'] for row in res['rows']}


def update_schem_docs(name, seq, docs, db=dbdefault):
    result = service.post_changes(
        db=db,
        filter="_selector",
        since=seq,
        include_docs=True,
        selector={"_id": {
            "$gt": name+":",
            "$lt": name+":\ufff0",
        }}).get_result()

    for change in result['results']:
        doc = change['doc']
        print(doc)
        if doc.get('_deleted', False):
            del docs[doc["_id"]]
        else:
            docs[doc["_id"]] = doc

    seq = result['last_seq']
    return seq, docs


def live_schem_docs(name, callback, db=dbdefault):
    seq, docs = get_schem_docs(name, db)
    callback(docs)

    result = service.post_changes_as_stream(
        db=db,
        feed='continuous',
        heartbeat=5000,
        filter="_selector",
        since=seq,
        include_docs=True,
        selector={"_id": {
            "$gt": name+":",
            "$lt": name+":\ufff0",
        }}).get_result()

    for chunk in result.iter_lines():
        if chunk:
            doc = json.loads(chunk)["doc"]
            print(doc)
            if doc.get('_deleted', False):
                del docs[doc["_id"]]
            else:
                docs[doc["_id"]] = doc
            callback(docs)


def ports(doc):
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
        return {(x+px, y+py): p for px, py, p in shape_ports(mosfet_shape)}
    elif cell in {'resistor', 'capacitor', 'inductor', 'vsource', 'isource', 'diode'}:
        return {(x+px, y+py): p for px, py, p in shape_ports(twoport_shape)}
    else:
        raise ValueError(cell)


def port_index(docs):
    wire_index = {}
    device_index = {}
    for doc in docs.values():
        cell = doc['cell']
        for (x, y), p in ports(doc).items():
            if cell in {'wire', 'label'}:
                wire_index.setdefault((x, y), []).append(doc)
            else:
                device_index[x, y] = (p, doc)
    return device_index, wire_index


def netlist(docs):
    device_index, wire_index = port_index(docs)
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
                for ploc in ports(doc).keys():
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


def circuit_spice(name, db=dbdefault):
    _, docs = get_schem_docs(name, db)
    nl = netlist(docs)
    cir = []
    for id, ports in nl.items():
        dev = docs[id]
        cell = dev['cell']
        model = dev.get('model', '')
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
            cir.append(f"X{name}")  # todo
    return '\n'.join(cir)


def spice_netlist(name, db=dbdefault):
    return f"* {name}\n" + circuit_spice(name, db) + "\n.end\n"


if __name__ == "__main__":
    print(live_schem_docs("newwire", print))
