from subprocess import Popen
from time import sleep
import re
import os
from threading import Thread
from more_itertools import roundrobin
from bokeh.io import curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import *
from bokeh.plotting import figure
from bokeh.palettes import Colorblind
from pyttoresque import simserver, netlist

doc = curdoc()

class Wizard:
    def __init__(self, children, next="Simulate", prev="Edit"):
        self.children = children
        self.active = 0
        self.nextbtn = Button(label=next)
        self.nextbtn.on_click(self.next)
        self.prevbtn = Button(label=prev, disabled=True)
        self.prevbtn.on_click(self.prev)
        controls = row(self.prevbtn, Spacer(sizing_mode="stretch_width"), self.nextbtn, sizing_mode="stretch_width", css_classes=["wizard-controls"])
        self.widget = column(children[0], controls, sizing_mode="stretch_both", spacing=1, css_classes=["wizard"])
    
    def next(self):
        if self.active < len(self.children)-1:
            self.active += 1
            self.widget.children[0] = self.children[self.active]
        # self.nextbtn.disabled = self.active == len(self.children)-1
        self.prevbtn.disabled = self.active == 0

    def prev(self):
        if self.active > 0:
            self.active -= 1
            self.widget.children[0] = self.children[self.active]
        # self.nextbtn.disabled = self.active == len(self.children)-1
        self.prevbtn.disabled = self.active == 0

def header(txt):
    return Div(text=f"<h1>{txt}</h1>", css_classes=["heading"])

# The main data sources for all the simulation data
simdata = {}
# the Popen object representing a local simulator
simproc = None

##### simulator selection #####

params = doc.session_context.request.arguments
getparam = lambda p: b''.join(params.get(p, [])).decode()

simulator_h = header("Configuration")
sim_doc = Paragraph(text="""
Configure how and what to simulate. Different simulators have different performance characteristics but also different compatibility with device models.
If the simulation host is set to "localhost", a local server will be started automatically if none is available.
""")
schemparam = getparam("schem")
dbparam = getparam("db")
dbdefault = "http://localhost:5984"
schemname = TextInput(title="Schematic", value=schemparam, disabled=schemparam!="")
dbhost = TextInput(title="Database URL", value=dbparam or dbdefault, disabled=dbparam!="")
simulator_type = Select(title="Simulator", options=["NgSpice", "Xyce"], value="NgSpice")
simulator_host = TextInput(title="Host", value="localhost")
simulator_port = NumericInput(title="Port", value=5923)
simulator_vectors = TextInput(title="Vectors to save")
simulator_spice = TextAreaInput(title="Spice commands")

sim_inputs = column(simulator_h, sim_doc, schemname, dbhost, simulator_type, simulator_host, simulator_port, simulator_vectors, simulator_spice, Spacer(sizing_mode="stretch_both"))
sim_tab = Panel(child=sim_inputs, title="Configuration")

# database connection
service = netlist.SchematicService.from_url(dbhost.value)
def set_service(prop, old, new):
    global service
    service = netlist.SchematicService.from_url(new)
dbhost.on_change("value", set_service)

##### transient simulation #####

tran_h = header("Transient")
tran_desc = Paragraph(text="Perform a non-linear, time-domain simulation")
t_step = NumericInput(title="Maximum timestep", value=1e-6, mode="float")
t_start = NumericInput(title="Data start time", value=0.0, mode="float")
t_stop = NumericInput(title="Stop time", value=1e-3, mode="float")
tran_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
tran_inputs = column(tran_h, tran_desc, t_step, t_start, t_stop, tran_opts, Spacer(sizing_mode="stretch_both"))
tran_tab = Panel(child=tran_inputs, title="Transient")

##### AC simulation #####

ac_h = header("AC Analysis")
ac_desc = Paragraph(text="Compute the small-signal AC behavior of the circuit linearized about its DC operating point")
sweep_type = Select(title="Point spacing", options=[("dec", "Decade"), ("oct", "Octave"), ("lin", "Linear"), ("list", "List")], value="dec")
f_points = NumericInput(title="Number of points", value=10, mode="float")
f_start = NumericInput(title="Start frequency", value=1, mode="float")
f_stop = NumericInput(title="Stop frequency", value=1e6, mode="float")
ac_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
ac_inputs = column(ac_h, ac_desc, sweep_type, f_points, f_start, f_stop, ac_opts, Spacer(sizing_mode="stretch_both"))
ac_tab = Panel(child=ac_inputs, title="AC Analysis")


##### DC sweep simulation #####

dc_h = header("DC Analysis")
dc_desc = Paragraph(text="Compute the DC operating point of a circuit while sweeping independent sources")
dc_source = TextInput(title="Sweeped source name")
dc_start = NumericInput(title="Start value", value=0, mode="float")
dc_stop = NumericInput(title="Stop value", value=5, mode="float")
dc_step = NumericInput(title="Increment", value=0.1, mode="float")
dc_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
dc_inputs = column(dc_h, dc_desc, dc_source, dc_start, dc_stop, dc_step, dc_opts, Spacer(sizing_mode="stretch_both"))
dc_tab = Panel(child=dc_inputs, title="DC Sweep")

##### Noise simulation #####

noise_h = header("Noise")
noise_desc = Paragraph(text="Perform a stochastic noise analysis of the circuit linearised about the DC operating point, measuring input referred noise at the selected output node and input source")
noise_output = TextInput(title="Name of output node")
noise_input = TextInput(title="Name input source")
n_sweep_type = Select(title="Point spacing", options=[("dec", "Decade"), ("oct", "Octave"), ("lin", "Linear"), ("list", "List")], value="dec")
n_f_points = NumericInput(title="Number of points", value=10, mode="float")
n_f_start = NumericInput(title="Start frequency", value=1, mode="float")
n_f_stop = NumericInput(title="Stop frequency", value=1e6, mode="float")
noise_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
noise_inputs = column(noise_h, noise_desc, noise_output, noise_input, n_sweep_type, n_f_points, n_f_start, n_f_stop, noise_opts, Spacer(sizing_mode="stretch_both"))
noise_tab = Panel(child=noise_inputs, title="Noise")

##### DC transfer simulation #####
# not implemented yet

dct_h = header("DC Transfer")
dct_desc = Paragraph(text="Find the DC small-signal transfer function")
dct_output = TextInput(title="Name of output node")
dct_input = TextInput(title="Name input source")
dct_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
dct_inputs = column(dct_h, dct_desc, dct_output, dct_input, dct_opts, Spacer(sizing_mode="stretch_both"))
dct_tab = Panel(child=dct_inputs, title="DC Transfer")

##### operating point simulation #####

op_h = header("DC Operating Point")
op_desc = Paragraph(text="Find the DC operating point, treating capacitances as open circuits and inductors as shorts")
op_opts = CheckboxGroup(labels=["Enable this simulation", "Rerun on changes"])
op_inputs = column(op_h, op_desc, op_opts, sizing_mode="stretch_both")
op_tab = Panel(child=op_inputs, title="DC Operating Point")

tabs = Tabs(tabs=[tran_tab, ac_tab, dc_tab, noise_tab, op_tab, sim_tab], tabs_location='left', sizing_mode="stretch_both")

##### result browser #####

tracecolumn = column(Spacer(sizing_mode="stretch_height"))
# def set_traces(prop, old, new):
#     traces.labels = list(new)
# cds.on_change('column_names', set_traces)
# cds.on_change('data', set_traces)

fig = figure(title="Simulation Results", output_backend="webgl", sizing_mode="stretch_both")
browser = row([column(tracecolumn, Spacer(sizing_mode="stretch_height")), fig], sizing_mode="stretch_height")

def sim_connect():
    global simproc
    if simulator_type.value == "NgSpice":
        sim = simserver.Ngspice
        simcmd = "NgspiceSimServer"
    elif simulator_type.value == "Xyce":
        sim = simserver.Xyce
        simcmd = "XyceSimServer"
    else:
        raise ValueError(simulator_type.value)
    host = simulator_host.value
    port = simulator_port.value
    try:
        return simserver.connect(host, port, sim)
    except ConnectionRefusedError:
        # if we're doing a local simulation, start a new server
        if simulator_host.value=="localhost":
            print("starting new local server")
            simproc = Popen([simcmd, str(simulator_port.value)])
            sleep(1) # wait a bit for the server to start :(
            return simserver.connect(host, port, sim)
        else:
            raise


tracemap = {}
def update_traces():
    # to capture the loop variable
    def closurehack(title, scale, data):
        return lambda attr, old, new: plot_active(title, scale, data, new)

    if tracemap.keys() != simdata.keys():
        # The set of simulations changed, clear everything
        tracecolumn.children.clear()
        tracemap.clear()

    for k, (scale, data) in simdata.items():
        # check if any CheckboxGroups need to be added/updated
        if k in tracemap:
            if data.column_names != tracemap[k].labels:
                # the key is already there, but the columns are different
                # clear active columns and set new labels
                tracemap[k].labels = data.column_names
                tracemap[k].active.clear()
        else:
            # the key is not there yet, add a new CheckboxGroup
            div = header(k)
            grp = CheckboxGroup(labels=data.column_names)
            grp.on_change('active', closurehack(k, scale, data))
            tracemap[k] = grp
            tracecolumn.children.append(div)
            tracecolumn.children.append(grp)



def plot_active(title, scale, cds, new):
    print(title, scale, cds, new)
    if scale.lower() in {"time", "v-sweep"}:
        fig = figure(title=title, output_backend="webgl", sizing_mode="stretch_both")
        browser.children[1] = fig
        for col in new:
            color = Colorblind[8][col%8]
            key = cds.column_names[col]
            fig.line(scale, key, source=cds, color=color, legend_label=key)
    elif scale.lower() == "frequency":
        if f"{scale}_phase" in cds.column_names:
            # we have complex data
            figamp = figure(title="Amplitude", output_backend="webgl", y_axis_type="log", x_axis_type="log", height=100)
            figphase = figure(title="Phase", output_backend="webgl", x_range=figamp.x_range, x_axis_type="log", height=100)
            browser.children[1] = column(figamp, figphase, sizing_mode="stretch_both")
            for col in new:
                color = Colorblind[8][col%8]
                key = cds.column_names[col]
                if key.endswith("_phase"):
                    figphase.line(scale, key, source=cds, color=color, legend_label=key)
                else:
                    figamp.line(scale, key, source=cds, color=color, legend_label=key)
        else:
            # we have real data
            fig = figure(title=title, output_backend="webgl", sizing_mode="stretch_both", y_axis_type="log", x_axis_type="log")
            browser.children[1] = fig
            for col in new:
                color = Colorblind[8][col%8]
                key = cds.column_names[col]
                fig.line(scale, key, source=cds, color=color, legend_label=key)
    else:
        # just show a table with the data
        cols = [TableColumn(field=cds.column_names[i], title=cds.column_names[i]) for i in new]
        browser.children[1] = DataTable(source=cds, columns=cols)
        # raise ValueError(scale)


root = Wizard(children=[tabs, browser])

sweep_types = {
    "dec": simserver.AcType.dec,
    "oct": simserver.AcType.oct,
    "lin": simserver.AcType.lin,
}

def vectors():
    return simulator_vectors.value.split()
simcmds = [
    lambda fs: fs.commands.tran(t_step.value, t_stop.value, t_start.value, vectors()),
    lambda fs: fs.commands.ac(sweep_types[sweep_type.value], f_points.value, f_start.value, f_stop.value, vectors()),
    lambda fs: fs.commands.dc(dc_source.value, dc_start.value, dc_stop.value, dc_step.value, vectors()),
    lambda fs: fs.commands.noise(noise_output.value, noise_input.value, sweep_types[sweep_type.value], f_points.value, f_start.value, f_stop.value, vectors()),
    lambda fs: fs.commands.op(vectors()),
]
opts = [tran_opts, ac_opts, dc_opts, noise_opts, op_opts]

def disable_next(prop, old, new):
    root.nextbtn.disabled = new >= len(simcmds)
tabs.on_change('active', disable_next)

class SimRunner(Thread):
    def __init__(self):
        super().__init__()
        self.first_run = True
        self.running = False

    def run(self):
        self.running = True
        service.live_schem_docs(schemname.value, self.do_simulations)
        print("thread done")

    def run_main(self, filename, enabled, spice):
        # simdata.clear()
        for scale, data in simdata.values():
            data.data = {k: [] for k in data.column_names}

        caps = []
        first = True
        for cmd in enabled:
            sim = sim_connect()
            if first:
                # upload files once, if multiple connections, wait
                cap = sim.loadFiles([{'name': filename, 'contents': spice}])
                capw = cap if len(enabled) == 1 else cap.wait()
                caps.append(simserver.stream(cmd(capw), simdata))
            else:
                cap = sim.loadPath(filename)
                caps.append(simserver.stream(cmd(cap), simdata))
        
        for _ in roundrobin(*caps):
            update_traces()

    def do_simulations(self, schem):
        enabled = []
        has_live = False
        for opt, cmd in zip(opts, simcmds):
            if 0 in opt.active:
                if 1 in opt.active:
                    enabled.append(cmd)
                    has_live = True
                elif self.first_run:
                    # on startup run all active simulations
                    enabled.append(cmd)

        if not enabled: return False
        self.first_run = False # thread is running live simulations 

        name = schemname.value
        filename = re.sub(r"[^a-zA-Z0-9]", "_", name)+".cir"
        # TODO make global once it updates itself
        m = netlist.Modeldict(service=service)
        spice = netlist.spice_netlist(name, schem, m, simulator_spice.value)
        print(spice)

        doc.add_next_tick_callback(lambda: self.run_main(filename, enabled, spice))

        # set running to False to end live updates
        return self.running and has_live

thread = None
# TODO reuse thread, avoid capnp freaking out
def run_simulation(e):
    global thread
    # tell old thread to stop
    if thread:
        thread.running = False
    # start new thread
    thread = SimRunner()
    thread.daemon = True
    thread.start()
root.nextbtn.on_click(run_simulation)

# test = figure(title="foo", sizing_mode="stretch_both")
# test = Tabs(tabs=[Panel(title="foo", child=Paragraph(text="foo", sizing_mode="stretch_both"))], tabs_location='left', sizing_mode="stretch_both")
doc.add_root(root.widget)
# doc.add_root(test)
doc.title = "Simulate"
doc.height=1000