import re
import panel as pn
import holoviews as hv
import numpy as np
import param
from tornado.ioloop import IOLoop
from pyttoresque import simserver, netlist, analysis


pn.extension('plotly', sizing_mode='stretch_both', notifications=True)
param.parameterized.async_executor = IOLoop.current().add_callback

class Configuration(param.Parameterized):
    doc = """# Configuration
Configure how and what to simulate. Different simulators have different performance characteristics but also different compatibility with device models.
If the simulation host is set to "localhost", a local server will be started automatically if none is available.
"""

    schematic = param.String()
    database_url = param.String(label="Database URL")
    spice = param.String(precedence=-1)
    
    simulator = param.Selector(objects={"NgSpice": simserver.Ngspice, "Xyce": simserver.Xyce})
    host = param.String(default="localhost")
    port = param.Integer(default=5923)
    extra_spice = param.String()

    error = param.ClassSelector(Exception, precedence=-1)

    def __init__(self, **params):
        super().__init__(**params)
        self.param.watch(self._update_spice, ['database_url', 'schematic'])
        pn.state.location.sync(self, {'database_url': 'db', 'schematic': 'schem'})


    async def _update_spice(self, *events):
        try:
            url = self.database_url
            name = self.schematic
            print("update", name, url)
            async with netlist.SchematicService(url) as service:
                it = service.live_schem_docs(name)
                async for schem in it:
                    print("new schem")
                    print(url, self.database_url, name, self.schematic)
                    if url != self.database_url or name != self.schematic:
                        print("change detected, ending watcher")
                        break
                    self.spice = netlist.spice_netlist(name, schem, self.extra_spice)
                    print("no error")
                    self.error = None
        except Exception as e:
            self.error = e
            pn.state.notifications.error(str(e))

    @param.depends('schematic', 'host', 'port', 'simulator', 'spice')
    async def connect(self):
        filename = re.sub(r"[^a-zA-Z0-9]", "_", self.schematic)+".cir"
        sim = await simserver.connect(self.host, self.port, self.simulator)
        return sim.loadFiles([{'name': filename, 'contents': self.spice}])

    @param.depends('error')
    def errormsg(self):
        if self.error:
            return pn.pane.Alert(str(self.error), alert_type='danger')


    def panel(self):
        return pn.Column(
            pn.pane.Markdown(self.doc, sizing_mode='fixed', width=500),
            pn.Param(self, sizing_mode='fixed', show_name=False),
            pn.Row(self.errormsg, sizing_mode='fixed', width=500, margin=10),
            pn.Spacer(sizing_mode='stretch_both'))


class Simulation(param.Parameterized):
    vectors = param.List(precedence=0.5)
    rerun_on_change = param.Boolean(True, precedence=0.5)

    def cmd(self, fs):
        raise NotImplementedError()

    def plotcmd(self, buffer, cols):
        return analysis.table([buffer, cols]).opts(responsive=True)

class TranSimulation(Simulation):
    doc = """# Transient simulation
Perform a non-linear, time-domain simulation"""

    maximum_timestep = param.Number(1e-5)
    start_time = param.Number(0)
    stop_time = param.Number(1e-3)
    
    def cmd(self, fs):
        return fs.commands.tran(self.maximum_timestep, self.stop_time, self.start_time, self.vectors)
    
    def plotcmd(self, buffer, cols):
        return analysis.timeplot([buffer, cols]).opts(
            responsive=True,
            xlim=(self.start_time, self.stop_time)
        )


class AcSimulation(Simulation):
    doc = """# AC simulation
Compute the small-signal AC behavior of the circuit linearized about its DC operating point
"""

    point_spacing = param.Selector(objects={
        "Decade": simserver.AcType.dec,
        "Octave": simserver.AcType.oct,
        "Linear": simserver.AcType.lin,
    })
    number_of_points = param.Integer(10)
    start_frequency = param.Number(1)
    stop_frequency = param.Number(1e6)
    
    def cmd(self, fs):
        return fs.commands.ac(self.point_spacing, self.number_of_points, self.start_frequency, self.stop_frequency, self.vectors)
    
    def plotcmd(self, buffer, cols):
        return analysis.bodeplot([buffer, cols]).opts(
            hv.opts.Curve(
            responsive=True,
            xlim=(np.log10(self.start_frequency), np.log10(self.stop_frequency)))
        )

class OpSimulation(Simulation):
    doc = """# Operating point
Find the DC operating point, treating capacitances as open circuits and inductors as shorts
"""

    @param.depends('vectors')
    def cmd(self, fs):
        return fs.commands.op(self.vectors)

class DcSimulation(Simulation):
    doc = """# DC sweep
Compute the DC operating point of a circuit while sweeping independent sources
"""
    source_name = param.String()
    start_value = param.Number(0)
    stop_value = param.Number(1)
    increment = param.Number(0.1)
    
    def cmd(self, fs):
        return fs.commands.dc(self.source_name, self.start_value, self.stop_value, self.stop_value, self.vectors)
    
    def plotcmd(self, buffer, cols):
        return analysis.sweepplot([buffer, cols]).opts(
            responsive=True,
            xlim=(self.start_value, self.stop_value)
        )

class NoiseSimulation(Simulation):
    doc = """# Noise simulation
Perform a stochastic noise analysis of the circuit linearised about the DC operating point, measuring input referred noise at the selected output node and input source
"""
    noise_output_node = param.String("v(out)")
    noise_input_source = param.String("vin")
    point_spacing = param.Selector(objects={
        "Decade": simserver.AcType.dec,
        "Octave": simserver.AcType.oct,
        "Linear": simserver.AcType.lin,
    })
    number_of_points = param.Integer(10)
    start_frequency = param.Number(1)
    stop_frequency = param.Number(1e6)
    
    def cmd(self, fs):
        return fs.commands.noise(self.noise_output_node, self.noise_input_source, self.point_spacing, self.number_of_points, self.start_frequency, self.stop_frequency, self.vectors)
    
    def plotcmd(self, buffer, cols):
        if len(buffer.data.index) == 1:
            return analysis.table([buffer, cols]).opts(responsive=True)
        else:
            return analysis.bodeplot([buffer, cols]).opts(
                hv.opts.Curve(
                responsive=True,
                xlim=(np.log10(self.start_frequency), np.log10(self.stop_frequency)))
            )


class SimTabs(param.Parameterized):
    sim = param.Selector([
            OpSimulation(name="Operating point"),
            TranSimulation(name="Transient simulation"),
            AcSimulation(name="AC simulation"),
            DcSimulation(name="DC sweep"),
            NoiseSimulation(name="Noise simulation"),
        ])

    def cb(self, _, e):
        print('tabs changed', e.obj.active)
        vals = list(self.param.sim.get_range().values())
        self.sim = vals[e.obj.active]

    def panel(self):
        print('tabs panel')
        active = list(self.param.sim.get_range().keys()).index(self.sim.name)
        tabs = pn.Tabs(
            *(pn.Column(
                pn.pane.Markdown(t.doc, sizing_mode='fixed', width=500),
                pn.Param(t, sizing_mode='fixed', show_name=False),
                pn.Spacer(),
                name=t.name)
                for t in self.param.sim.get_range().values()),
            tabs_location='left',
            active=active)
        tabs.link(self, callbacks={'active': self.cb})
        return tabs

class Results(param.Parameterized):
    cmd = param.Action(label="Simulate")
    plotcmd = param.Callable()
    data = param.Dict({})

    error = param.ClassSelector(Exception)

    async def simulate(self, _=None):
        try:
            for v in self.data.values():
                v.clear()
            res = await self.cmd()
            newkey = lambda k: self.param.trigger('data')
            await simserver.stream(res, self.data, newkey)
        except Exception as e:
            self.error = e
        else:
            self.error = None

    @param.depends('data', 'error')
    def view(self):
        col = pn.Column(sizing_mode='stretch_both')
        if self.error:
            col.append(pn.pane.Alert(str(self.error),
            alert_type='danger',
            sizing_mode='fixed', width=500, margin=10))
            col.append(pn.Spacer(sizing_mode='stretch_both'))
            return col

        for k, v in self.data.items():
            colnames = list(v.data.columns)
            cols = analysis.active_traces(cols=colnames)
            sel = pn.widgets.CheckBoxGroup(options=colnames, value=colnames, sizing_mode='fixed')
            sel.link(cols, {"value": lambda t, e: t.event(cols=e.obj.value)})
            plt = self.plotcmd(v, cols)
            col.append(pn.Row(pn.Card(sel, title=k, sizing_mode='fixed'), pn.Column(plt)))
        return col

    def panel(self):
        col = pn.Pane(self.view)
        return col

class Simulator(param.Parameterized):
    conf = param.ClassSelector(Configuration)
    tabs = param.ClassSelector(SimTabs)
    res = param.ClassSelector(Results)

    stage = param.Selector(["conf", "tabs", "res"], "tabs")

    def __init__(self):
        super().__init__(
            conf=Configuration(),
            tabs=SimTabs(),
            res=Results(),
        )
        self.conf.param.watch(self._run, ['spice'])
        self.param.watch(self._run, ['stage'], onlychanged=False)
        self.tabs.param.watch(self._cmd, ['sim'])
        self._cmd(None)

    def _cmd(self, e):
        print("new cmd")
        async def simcmd():
            con = await self.conf.connect()
            return self.tabs.sim.cmd(con)
        self.res.data = {}
        self.res.cmd = simcmd
        self.res.plotcmd = self.tabs.sim.plotcmd
    
    async def _run(self, e):
        if (self.res.cmd
        and self.stage == "res"
        and self.tabs.sim.rerun_on_change):
            print("running on change")
            await self.res.simulate()

    @param.depends('stage')
    def view(self):
        if self.stage == "conf":
            return self.conf.panel()
        elif self.stage == "tabs":
            return self.tabs.panel()
        else:
            return self.res.panel()

    @param.depends('stage')
    def nextbtn(self):
        if self.stage == "conf":
            btn = pn.widgets.Button(name="Edit", margin=20)
            btn.on_click(lambda _: setattr(self, 'stage', 'tabs'))
        else:
            btn = pn.widgets.Button(name="Simulate!", button_type='primary', margin=20)
            btn.on_click(lambda _: setattr(self, 'stage', 'res'))
        return btn

    @param.depends('stage')
    def prevbtn(self):
        if self.stage == "res":
            btn = pn.widgets.Button(name="Edit", margin=20)
            btn.on_click(lambda _: setattr(self, 'stage', 'tabs'))
        else:
            btn = pn.widgets.Button(name="Setup", margin=20)
            btn.on_click(lambda _: setattr(self, 'stage', 'conf'))
        return btn

    def panel(self):
        print(type(self.view()))
        print(type(self.tabs.panel()))
        return pn.Column(
            self.view,
            pn.Row(
                self.prevbtn,
                pn.Spacer(),
                self.nextbtn,
                sizing_mode='stretch_width',
                css_classes=['wizard-controls']
            ),
            sizing_mode='stretch_both',
            spacing=1
        )

Simulator().panel().servable()