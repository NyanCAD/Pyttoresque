from threading import Thread, current_thread
import re
from tkinter import W
import panel as pn
import param
from pyttoresque import simserver, netlist, analysis

pn.extension('plotly')

class Configuration(param.Parameterized):
    schematic = param.String("top$top2")
    database_url = param.String("https://c6be5bcc-59a8-492d-91fd-59acc17fef02-bluemix.cloudantnosqldb.appdomain.cloud/schematics", label="Database URL")
    spice = param.String(precedence=-1)
    
    simulator = param.Selector(objects={"NgSpice": simserver.Ngspice, "Xyce": simserver.Xyce})
    host = param.String(default="localhost")
    port = param.Integer(default=5923)
    extra_spice = param.String()

    def __del__(self):
        print("stopping thread")
        if hasattr(self, 'thread'):
            self.thread.running = False

    @param.depends('schematic', 'database_url', watch=True, on_init=True)
    def _update_spice(self):
        print("update", self.schematic, self.database_url)
        if hasattr(self, 'thread'):
            self.thread.running = False
        self.service = netlist.SchematicService.from_url(self.database_url)
        self.models = netlist.Modeldict(service=self.service)
        self.thread = Thread(target=self.service.live_schem_docs, args=(self.schematic, self._callback))
        self.thread.daemon = True
        self.thread.running = True
        self.thread.start()

    def _callback(self, schem):
        print("new schem")
        self.spice = netlist.spice_netlist(self.schematic, schem, self.models, self.extra_spice)
        return current_thread().running

    @param.depends('schematic', 'host', 'port', 'simulator', 'spice')
    def connect(self):
        filename = re.sub(r"[^a-zA-Z0-9]", "_", self.schematic)+".cir"
        sim = simserver.connect(self.host, self.port, self.simulator)
        return sim.loadFiles([{'name': filename, 'contents': self.spice}])

    def panel(self):
        return self.param


class Simulation(param.Parameterized):
    vectors = param.List(precedence=0.5)
    rerun_on_change = param.Boolean(True, precedence=0.5)

    def cmd(self, fs):
        raise NotImplementedError()

    def xlim(self):
        raise NotImplementedError()

class TranSimulation(Simulation):
    maximum_timestep = param.Number(1e-5)
    start_time = param.Number(0)
    stop_time = param.Number(1e-3)
    
    @param.depends('maximum_timestep', 'start_time', 'stop_time', 'vectors')
    def cmd(self, fs):
        return fs.commands.tran(self.maximum_timestep, self.stop_time, self.start_time, self.vectors)
    
    @param.depends('start_time', 'stop_time')
    def xlim(self):
        return (self.start_time, self.stop_time)


class AcSimulation(Simulation):
    point_spacing = param.Selector(objects={
        "Decade": simserver.AcType.dec,
        "Octave": simserver.AcType.oct,
        "Linear": simserver.AcType.lin,
    })
    number_of_points = param.Integer(10)
    start_frequency = param.Number(1)
    stop_frequency = param.Number(1e6)
    
    @param.depends('point_spacing', 'number_of_points', 'start_frequency', 'stop_frequency', 'vectors')
    def cmd(self, fs):
        return fs.commands.ac(self.point_spacing, self.number_of_points, self.start_frequency, self.stop_frequency, self.vectors)
    
    @param.depends('start_frequency', 'stop_frequency')
    def xlim(self):
        return (self.start_frequency, self.stop_frequency)

class OpSimulation(Simulation):
    @param.depends('vectors')
    def cmd(self, fs):
        return fs.commands.op(self.vectors)


class SimTabs(param.Parameterized):
    sim = param.Selector([
            OpSimulation(name="Operating point"),
            AcSimulation(name="AC simulation"),
            TranSimulation(name="Transient simulation"),
        ])

    def cb(self, _, e):
        print('tabs changed', e.obj.active)
        vals = list(self.param.sim.get_range().values())
        self.sim = vals[e.obj.active]

    def panel(self):
        print('tabs panel')
        active = list(self.param.sim.get_range().keys()).index(self.sim.name)
        tabs = pn.Tabs(
            *self.param.sim.get_range().values(),
            tabs_location='left',
            active=active)
        tabs.link(self, callbacks={'active': self.cb})
        return tabs

class Results(param.Parameterized):
    cmd = param.Action(label="Simulate")
    xlim = param.Action()
    data = param.Dict({})

    def simulate(self, _=None):
        for v in self.data.values():
            v.clear()
        res = self.cmd()
        it = simserver.stream(res, self.data)
        for _ in it:
            self.param.trigger('data')
            # print(self.data)

    @param.depends('data')
    def view(self):
        col = pn.Column()
        for k, v in self.data.items():
            cols = analysis.active_traces(cols=list(v.data.columns))
            if not v.data.empty:
                plt = analysis.timeplot([v, cols]).opts(width=1000, height=500, xlim=self.xlim())
                col.append(plt)
        return col

    def panel(self):
        btn = pn.widgets.Button(name="Simulate")
        btn.on_click(self.simulate)
        col = pn.Column(btn, self.view)
        return col

class Simulator(param.Parameterized):
    conf = param.ClassSelector(Configuration)
    tabs = param.ClassSelector(SimTabs)
    res = param.ClassSelector(Results)

    def __init__(self):
        super().__init__(
            conf=Configuration(),
            tabs=SimTabs(),
            res=Results(),
        )
        self.conf.param.watch(self._run, ['spice'], queued=True)

    @param.depends('tabs.sim', watch=True, on_init=True)
    def _cmd(self):
        print("new cmd")
        self.res.cmd = lambda: self.tabs.sim.cmd(self.conf.connect())
        self.res.xlim = self.tabs.sim.xlim
    
    def _run(self, e):
        print(current_thread())
        if self.res.cmd:
            print("running on change")
            self.res.simulate()

    def panel(self):
        return pn.pipeline.Pipeline([
            ("Setup", self.conf),
            ("Simulation", self.tabs),
            ("Results", self.res)],
            inherit_params=False,
            debug=True)
        # return pn.Row(self.conf, self.tabs.panel(), self.res.panel)

Simulator().panel().servable()