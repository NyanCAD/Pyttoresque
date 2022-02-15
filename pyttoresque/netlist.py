from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.api_exception import ApiException
from ibm_cloud_sdk_core.authenticators import NoAuthAuthenticator, BasicAuthenticator
from collections import deque, namedtuple
import json
import urllib.parse as ulp


def shape_ports(shape):
    for y, s in enumerate(shape):
        for x, c in enumerate(s):
            if c != ' ':
                yield x, y, c


mosfet_shape = list(shape_ports([
    " D",
    "GB",
    " S",
]))

twoport_shape = list(shape_ports([
    "P",
    "N",
]))


class Modeldict(dict):
    def __init__(self, *args, service, db=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        if db == None:
            self.db = service.dbdefault
        else:
            self.db = db

    def __missing__(self, key):
        try:
            doc = self.service.get_document(self.db, key).get_result()
        except ApiException:
            raise KeyError(key)
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


def doc_selector(schem):
    ors = [{"_id": {
            "$gt": name+":",
            "$lt": name+":\ufff0",
        }} for name in schem.keys()]
    return {"$or": ors}


class SchematicService(CloudantV1):
    dbdefault = "schematics"

    @classmethod
    def from_url(cls, url):
        up = ulp.urlparse(url)
        dbname = cls.dbdefault
        pathseg = up.path.split('/')
        if pathseg:
            dbname = pathseg.pop() or dbname

        if up.username or up.password:
            auth = BasicAuthenticator(up.username, up.password)
        else:
            auth = NoAuthAuthenticator()

        if up.port:
            netloc = f"{up.hostname}:{up.port}"
        else:
            netloc = up.hostname

        url = ulp.urlunparse(up._replace(netloc=netloc, path='/'.join(pathseg)))
        print(up.username, up.password, dbname, url)

        serv = cls(auth)
        serv.dbdefault = dbname
        serv.set_service_url(url)
        return serv

    def get_schem_docs(self, name, db=None):
        res = self.post_all_docs(
            db=db or self.dbdefault,
            include_docs=True,
            startkey=f"{name}:",
            endkey=f"{name}:\ufff0",
            update_seq=True
        ).get_result()
        return res['update_seq'], {row['id']: row['doc'] for row in res['rows']}


    def get_all_schem_docs(self, name, db=None):
        schem = {}
        seq, docs = self.get_schem_docs(name, db)
        schem[name] = docs
        devs = deque(docs.values())
        while devs:
            dev = devs.popleft()
            _id = SchemId(dev["cell"], dev.get('props', {}).get('model'), None, None)
            if _id.model and _id.schem not in schem:
                seq, docs = self.get_schem_docs(_id.schem, db or self.dbdefault)
                if docs:
                    schem[_id.schem] = docs
                    devs.extend(docs.values())
        return seq, schem

    def update_schem(self, seq, schem, db=None):
        sel = doc_selector(schem)
        result = self.post_changes(
            db=db or self.dbdefault,
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


    def live_schem_docs(self, name, callback, db=None):
        seq, schem = self.get_all_schem_docs(name, db)
        if not callback(schem):
            return

        sel = doc_selector(schem)
        result = self.post_changes_as_stream(
            db=db or self.dbdefault,
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
                if not callback(schem):
                    break


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
    elif cell == 'label':
        return {(x, y): doc['name']}
    elif cell in {'nmos', 'pmos'}:
        return rotate(mosfet_shape, tr, x, y)
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
            if cell in {'wire', 'label'}:
                wire_index.setdefault((x, y), []).append(doc)
            else:
                device_index[x, y] = (p, doc)
    return device_index, wire_index


def netlist(docs, models):
    device_index, wire_index = port_index(docs, models)
    nl = {}
    netnum = 0
    while wire_index:  # while there are devices left
        loc, locdevs = wire_index.popitem()  # take one
        netname = f"net{netnum}"
        netnum+=1
        net = deque(locdevs)
        netdevs = {}
        while net:
            doc = net.popleft()
            cell = doc['cell']
            if cell == 'wire':
                for ploc in getports(doc, models).keys():
                    if ploc in wire_index:
                        net.extend(wire_index.pop(ploc))
                    if ploc in device_index:
                        p, dev = device_index[ploc]
                        netdevs.setdefault(dev['_id'], []).append(p)
            elif cell == 'label':
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


def spice_netlist(name, schem, models, extra=""):
    declarations = set()
    for subname, docs in schem.items():
        if name == subname: continue
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


if __name__ == "__main__":
    service = SchematicService.new_instance()
    # name = "comparator$sky130_1v8_120mhz"
    name = "top$top"
    models = Modeldict(service=service)
    seq, docs = service.get_all_schem_docs(name)
    # print(docs)
    # print(netlist(docs[name], models))
    print(spice_netlist(name, docs, models))
