# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0

import re
import os
import traceback
import urllib.parse as ulp
import panel as pn
import holoviews as hv
import numpy as np
import param
from tornado.ioloop import IOLoop
from pyttoresque import simserver, netlist, analysis


pn.extension('plotly', 'terminal', sizing_mode='stretch_both')
param.parameterized.async_executor = IOLoop.current().add_callback

class Configuration(param.Parameterized):
    doc = """# Configuration
Configure how and what to simulate. Different simulators have different performance characteristics but also different compatibility with device models.
If the simulation host is set to "localhost", a local server will be started automatically if none is available.
"""

    schematic = param.String()
    database_url = param.String(label="Database URL")
    spice = param.String(precedence=-1)
    vectors = param.List(precedence=-1)
    
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
            # if we have a localhost couchdb proxied through Jupyter
            # actually use localhost because Jupyter is token authenticated
            purl = ulp.urlparse(url)
            if purl.hostname == "localhost" and purl.path.startswith("/couchdb"):
                pw = os.environ.get("COUCHDB_ADMIN_PASSWORD", "admin")
                port = os.environ.get("COUCHDB_LISTEN_PORT", 5984)
                netloc = f"admin:{pw}@localhost:{port}"
                path = purl.path[8:]
                url = purl._replace(path=path, netloc=netloc).geturl()
                self.database_url = url

            name = self.schematic
            async with netlist.SchematicService(url) as service:
                it = service.live_schem_docs(name)
                async for schem in it:
                    if url != self.database_url or name != self.schematic:
                        break
                    self.spice = netlist.spice_netlist(name, schem, self.extra_spice)
                    if self.simulator == simserver.Ngspice:
                        self.vectors = netlist.ngspice_vectors(name, schem)
                        print(self.vectors)
                    self.error = None
        except Exception as e:
            self.error = e
            traceback.print_exc()

    async def connect(self):
        sim = await simserver.connect(self.host, self.port, self.simulator)
        filename = re.sub(r"[^a-zA-Z0-9]", "_", self.schematic)+".cir"
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
    vectors = param.ListSelector(default=[], precedence=0.5)
    rerun_on_change = param.Boolean(True, precedence=0.5)
    back_annotate = param.Boolean(False, precedence=0.5)

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

    rerun_on_change = param.Boolean(False, precedence=0.5)
    
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

    back_annotate = param.Boolean(True, precedence=0.5)

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


class FftSimulation(TranSimulation):
    doc = """# FFT simulation
Perform a non-linear, time-domain simulation and plot the FFT"""

    fft_samples = param.Integer(1024)
    # TODO window function

    def plotcmd(self, buffer, cols):
        return analysis.fftplot([buffer, cols], self.fft_samples).opts(
            responsive=True,
        )

class SimTabs(param.Parameterized):
    # TODO user loadable simulations, move FFT to contrib module
    # sim = param.ClassSelector(Simulation, OpSimulation())
    sim = param.Selector([
            OpSimulation(name="Operating point"),
            TranSimulation(name="Transient simulation"),
            AcSimulation(name="AC simulation"),
            DcSimulation(name="DC sweep"),
            NoiseSimulation(name="Noise simulation"),
            #FftSimulation(name="FFT simulation"),
        ])

    def cb(self, _, e):
        vals = list(self.param.sim.get_range().values())
        self.sim = vals[e.obj.active]

    def panel(self):
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
    probe = param.String()

    error = param.ClassSelector(Exception)

    def __init__(self):
        super().__init__()
        self.terminal = pn.widgets.Terminal(height=300, sizing_mode='stretch_width')

    async def simulate(self, *, save=False, database_url=None, name=None):
        try:
            for v in self.data.values():
                v.clear()
            res = await self.cmd()
            newkey = lambda k: self.param.trigger('data')
            await simserver.stream(res, self.data, newkey, self.terminal)
            if save and database_url and name:
                async with netlist.SchematicService(database_url) as service:
                    await service.save_simulation(name, self.data)
        except Exception as e:
            self.error = e
            traceback.print_exc()
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
            cols = analysis.active_traces(cols=[])
            sel = pn.widgets.CheckBoxGroup(options=colnames, value=[], sizing_mode='fixed')
            sel.link(cols, {"value": lambda t, e: t.event(cols=e.obj.value)})
            def update(e):
                sel.value.append(self.probe)
                sel.param.trigger('value')
            self.param.watch(update, ['probe'])
            plt = self.plotcmd(v, cols)
            row = pn.Row(
                pn.Card(sel, title=k, sizing_mode='fixed'),
                pn.Column(plt, sizing_mode='stretch_both'),
                sizing_mode='stretch_both'
            )
            col.append(row)
        # col.append(pn.Spacer(sizing_mode='stretch_both'))
        col.append(pn.Card(self.terminal, title="Simulator output", collapsed=True, sizing_mode='stretch_width'))
        return col

    def panel(self):
        col = pn.Pane(self.view)
        return col

class BroadcastChannel(pn.reactive.ReactiveHTML):
    value = param.String(default=None, allow_None=True)

    _template = """<div>
    <input id="hiddenmsg" type="hidden" value="${value}"></input>
    <script>
    var inp = document.currentScript.previousSibling;
    var name = "${name}".trim()
    var ch = new BroadcastChannel(name)
    ch.addEventListener("message", function(msg) {
        inp.value = msg.data;
        inp.dispatchEvent(new Event('change'));
    })
    </script>
    </div>"""

    _dom_events = {'hiddenmsg': ['change']}

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
        self.brch = BroadcastChannel(name="probe", sizing_mode='fixed')
        self.brch.param.watch(self._probe, ['value'], onlychanged=False)
        self.conf.param.watch(self._run_change, ['spice'])
        self.param.watch(self._run_btn, ['stage'], onlychanged=False)
        self.tabs.param.watch(self._cmd, ['sim'])
        self._cmd(None)

    def _cmd(self, e):
        async def simcmd():
            con = await self.conf.connect()
            return self.tabs.sim.cmd(con)
        self.res.data = {}
        self.res.cmd = simcmd
        self.res.plotcmd = self.tabs.sim.plotcmd
        self.tabs.sim.param.vectors.objects = self.conf.vectors
    
    async def _run_change(self, e):
        self.tabs.sim.param.vectors.objects = self.conf.vectors
        if (self.res.cmd
        and self.stage == "res"
        and self.tabs.sim.rerun_on_change):
            await self.res.simulate(
                save=self.tabs.sim.back_annotate,
                database_url=self.conf.database_url,
                name=self.conf.schematic,
            )

    async def _run_btn(self, e):
        if (self.res.cmd
        and self.stage == "res"):
            await self.res.simulate(
                save=self.tabs.sim.back_annotate,
                database_url=self.conf.database_url,
                name=self.conf.schematic,
            )


    def _probe(self, e):
        key = e.obj.value
        id = netlist.SchemId.from_string(key)
        models = self.conf.netlist.get("models", {})
        schem = self.conf.netlist.get(id.schem, {})
        net = netlist.wire_net(key, schem, models)
        self.res.probe = net

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
            btn = pn.widgets.Button(name="Setup", margin=20, disabled=self.stage=="conf")
            btn.on_click(lambda _: setattr(self, 'stage', 'conf'))
        return btn

    def panel(self):
        return pn.Column(
            self.view,
            pn.Row(
                self.prevbtn,
                pn.Spacer(),
                self.brch,
                self.nextbtn,
                sizing_mode='stretch_width',
                css_classes=['wizard-controls']
            ),
            sizing_mode='stretch_both',
            spacing=1
        )

Simulator().panel().servable()