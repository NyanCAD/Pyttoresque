from subprocess import Popen
from time import sleep
import re
import os
from bokeh.io import curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import ColumnDataSource, Button, NumericInput, Panel, Tabs, Paragraph, Select, TextInput, RadioButtonGroup, CheckboxGroup, Div
from bokeh.plotting import figure
from bokeh.palettes import Colorblind
from pyttoresque import simserver, netlist
from bokeh.themes import Theme


doc = curdoc()

class Wizard:
    def __init__(self, children, next="Simulate", prev="Edit"):
        self.children = children
        self.active = 0
        self.nextbtn = Button(label=next, sizing_mode="fixed")
        self.nextbtn.on_click(self.next)
        self.prevbtn = Button(label=prev, disabled=True, sizing_mode="fixed")
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

# The main data source for all the simulation data
cds = ColumnDataSource()
# the Popen object representing a local simulator
simproc = None
# the name of the x axis of the current simulation
scale = "time"

##### simulator selection #####

simulator_h = header("Configuration")
params = doc.session_context.request.arguments
schemname = TextInput(title="Schematic", value=b''.join(params.get("schem", [])).decode())
simulator_type = Select(title="Simulator", options=["NgSpice", "Xyce"], value="NgSpice")
simulator_location = RadioButtonGroup(labels=["local", "remote"], active=0)
simulator_host = TextInput(title="Host", value="localhost", disabled=True)
simulator_port = NumericInput(title="Port", value=5923)

def hostdisabler(attr, old, new):
    if new==0:
        simulator_host.disabled = True
        simulator_host.value = "localhost"
    else:
        simulator_host.disabled = False
        # if a local simulator is running, terminate it
        if simproc and simproc.poll()==None:
            simproc.terminate()

simulator_location.on_change('active', hostdisabler)

sim_inputs = column(simulator_h, schemname, simulator_type, simulator_location, simulator_host, simulator_port, Spacer(sizing_mode="stretch_both"))
sim_tab = Panel(child=sim_inputs, title="Configuration")

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
        if simulator_location.active==0:
            print("starting new local server")
            simproc = Popen([simcmd, str(simulator_port.value)])
            sleep(1) # wait a bit for the server to start :(
            return simserver.connect(host, port, sim)
        else:
            raise

def sim_once(sim, cb):
    global scale
    name = schemname.value
    safename = re.sub(r"[^a-zA-Z0-9]", "_", name)
    # tricky, we want to reuse this but it currently doesn't update
    # so if it'd be global and a model was updated, it'd be wrong
    # so now it'll only request each model once per simulation at least
    m = netlist.Modeldict()
    seq, schem = netlist.get_all_schem_docs(name)
    spice = netlist.spice_netlist(name, schem, m)
    fileset = sim.loadFiles([{'name': safename+'.cir', 'contents': spice}])
    res = cb(fileset)
    scale, data = simserver.read(res)
    cds.data = data
    simserver.stream(res, cds)

##### transient simulation #####

tran_h = header("Transient")
tran_desc = Paragraph(text="Perform a non-linear, time-domain simulation")
t_step = NumericInput(title="Maximum timestep", value=1e-6, mode="float")
t_start = NumericInput(title="Data start time", value=0.0, mode="float")
t_stop = NumericInput(title="Stop time", value=1e-3, mode="float")
tran_inputs = column(tran_h, tran_desc, t_step, t_start, t_stop, Spacer(sizing_mode="stretch_both"))
tran_tab = Panel(child=tran_inputs, title="Transient")

##### AC simulation #####

ac_h = header("AC Analysis")
ac_desc = Paragraph(text="Compute the small-signal AC behavior of the circuit linearized about its DC operating point")
sweep_type = Select(title="Point spacing", options=[("dec", "Decade"), ("oct", "Octave"), ("lin", "Linear"), ("list", "List")], value="dec")
f_points = NumericInput(title="Number of points", value=10, mode="float")
f_start = NumericInput(title="Start frequency", value=1, mode="float")
f_stop = NumericInput(title="Stop frequency", value=1e6, mode="float")
ac_inputs = column(ac_h, ac_desc, sweep_type, f_points, f_start, f_stop, Spacer(sizing_mode="stretch_both"))
ac_tab = Panel(child=ac_inputs, title="AC Analysis")


##### DC sweep simulation #####

dc_h = header("DC Analysis")
dc_desc = Paragraph(text="Compute the DC operating point of a circuit while sweeping independent sources")
dc_source = TextInput(title="Sweeped source name")
dc_start = NumericInput(title="Start value", value=0, mode="float")
dc_stop = NumericInput(title="Stop value", value=5, mode="float")
dc_step = NumericInput(title="Increment", value=0.1, mode="float")
dc_inputs = column(dc_h, dc_desc, dc_source, dc_start, dc_stop, dc_step, Spacer(sizing_mode="stretch_both"))
dc_tab = Panel(child=dc_inputs, title="DC Sweep")

##### Noise simulation #####

noise_h = header("Noise")
noise_desc = Paragraph(text="Perform a stochastic noise analysis of the circuit linearised about the DC operating point, measuring input referred noise at the selected output node and input source")
noise_output = TextInput(title="Name of output node")
noise_input = TextInput(title="Name input source")
noise_inputs = column(noise_h, noise_desc, noise_output, noise_input, sweep_type, f_points, f_start, f_stop, Spacer(sizing_mode="stretch_both"))
noise_tab = Panel(child=noise_inputs, title="Noise")

##### DC transfer simulation #####

dct_h = header("DC Transfer")
dct_desc = Paragraph(text="Find the DC small-signal transfer function")
dct_output = TextInput(title="Name of output node")
dct_input = TextInput(title="Name input source")
dct_inputs = column(dct_h, dct_desc, dct_output, dct_input, Spacer(sizing_mode="stretch_both"))
dct_tab = Panel(child=dct_inputs, title="DC Transfer")

##### operating point simulation #####

op_h = header("DC Operating Point")
op_desc = Paragraph(text="Find the DC operating point, treating capacitances as open circuits and inductors as shorts")
op_inputs = column(op_h, op_desc, sizing_mode="stretch_both")
op_tab = Panel(child=op_inputs, title="DC Operating Point")

tabs = Tabs(tabs=[tran_tab, ac_tab, dc_tab, noise_tab, dct_tab, op_tab, sim_tab], tabs_location='left', sizing_mode="stretch_both")

##### result browser #####

traces = CheckboxGroup()
tracecolumn = column(traces, Spacer(sizing_mode="stretch_height"))
def set_traces(prop, old, new):
    traces.labels = list(new)
# cds.on_change('column_names', set_traces)
cds.on_change('data', set_traces)

fig = figure(title="Simulation Results", output_backend="webgl", sizing_mode="stretch_both")
browser = row([tracecolumn, fig], sizing_mode="stretch_height")

def plot_active(prop, old, new):
    if scale.lower() == "time":
        fig = figure(title="Simulation Results", output_backend="webgl", sizing_mode="stretch_both")
        browser.children[1] = fig
        for col in new:
            color = Colorblind[8][col%8]
            print(cds.column_names)
            key = cds.column_names[col]
            fig.line(scale, key, source=cds, color=color)
    elif scale.lower() == "frequency":
        figamp = figure(title="Amplitude", output_backend="webgl", y_axis_type="log", x_axis_type="log", height=100)
        figphase = figure(title="Phase", output_backend="webgl", x_range=figamp.x_range, x_axis_type="log", height=100)
        browser.children[1] = column(figamp, figphase, sizing_mode="stretch_both")
        for col in new:
            color = Colorblind[8][col%8]
            key = cds.column_names[col]
            if key.endswith("_phase"):
                figphase.line(scale, key, source=cds, color=color)
            else:
                figamp.line(scale, key, source=cds, color=color)
    else:
        raise ValueError(scale)

traces.on_change('active', plot_active)



root = Wizard(children=[tabs, browser])

sweep_types = {
    "dec": simserver.AcType.dec,
    "oct": simserver.AcType.oct,
    "lin": simserver.AcType.lin,
}

vectors = []
simcmds = [
    lambda fs: fs.commands.tran(t_step.value, t_stop.value, t_start.value, vectors),
    lambda fs: fs.commands.ac(sweep_types[sweep_type.value], f_points.value, f_start.value, f_stop.value, vectors)
]

def run_simulation(e):
    sim = sim_connect()
    cb = simcmds[tabs.active]
    sim_once(sim, cb)

root.nextbtn.on_click(run_simulation)

# test = figure(title="foo", sizing_mode="stretch_both")
# test = Tabs(tabs=[Panel(title="foo", child=Paragraph(text="foo", sizing_mode="stretch_both"))], tabs_location='left', sizing_mode="stretch_both")
doc.add_root(root.widget)
# doc.add_root(test)
doc.title = "Simulate"
doc.height=1000