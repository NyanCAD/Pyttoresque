from subprocess import Popen
from time import sleep
import re
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.events import ButtonClick
from bokeh.models import ColumnDataSource, Button, NumericInput, Panel, Tabs, Paragraph, Select, TextInput, RadioButtonGroup, CheckboxGroup
from bokeh.plotting import figure
from bokeh.palettes import Colorblind
from pyparsing import col
from pyttoresque import simserver, netlist

doc = curdoc()

# The main data source for all the simulation data
cds = ColumnDataSource()
# the Popen object representing a local simulator
simproc = None
# the name of the x axis of the current simulation
scale = "time"

##### simulator selection #####

params = doc.session_context.request.arguments
schemname = TextInput(title="Schematic", value=b''.join(params.get("schem", [])).decode())

simulator_type = Select(title="Simulator", options=["NgSpice", "Xyce"], value="NgSpice")
simulator_location = RadioButtonGroup(labels=["local", "remote"], active=0)
simulator_host = TextInput(title="Host", value="localhost", disabled=True)
simulator_port = NumericInput(title="Port", value=5923)
simulator_url = row(simulator_host, simulator_port)

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

sim_inputs = column(schemname, simulator_type, simulator_location, simulator_url)
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
    # horrible hack because Bokeh doesn't like complex numbers
    if scale == "frequency": scale = "frequency_mag"
    cds.data = data
    simserver.stream(res, cds)

##### transient simulation #####

tran_desc = Paragraph(text="Perform a non-linear, time-domain simulation")
t_step = NumericInput(title="Maximum timestep", value=1e-6, mode="float")
t_start = NumericInput(title="Time to start saving data", value=0.0, mode="float")
t_stop = NumericInput(title="Stop time", value=1e-3, mode="float")
tran_btn = Button(label="Simulate")
tran_inputs = column(tran_desc, t_step, t_start, t_stop, tran_btn)
tran_tab = Panel(child=tran_inputs, title="Transient")

def run_tran(e):
    sim = sim_connect()
    sim_once(sim, lambda fs: fs.commands.tran(t_step.value, t_stop.value, t_start.value, ["all"]))

tran_btn.on_click(run_tran)

##### AC simulation #####

ac_desc = Paragraph(text="Compute the small-signal AC behavior of the circuit linearized about its DC operating point")
sweep_type = Select(title="Point spacing", options=[("dec", "Decade"), ("oct", "Octave"), ("lin", "Linear"), ("list", "List")], value="dec")
f_points = NumericInput(title="Number of points", value=10, mode="float")
f_start = NumericInput(title="Start frequency", value=1, mode="float")
f_stop = NumericInput(title="Stop frequency", value=1e6, mode="float")
ac_btn = Button(label="Simulate")
ac_inputs = column(ac_desc, sweep_type, f_points, f_start, f_stop, ac_btn)
ac_tab = Panel(child=ac_inputs, title="AC Analysis")

sweep_types = {
    "dec": simserver.AcType.dec,
    "oct": simserver.AcType.oct,
    "lin": simserver.AcType.lin,
}
def run_ac(e):
    sim = sim_connect()
    st = sweep_types[sweep_type.value]
    sim_once(sim, lambda fs: fs.commands.ac(st, f_points.value, f_start.value, f_stop.value, ["all"]))

ac_btn.on_click(run_ac)

##### DC sweep simulation #####

dc_desc = Paragraph(text="Compute the DC operating point of a circuit while sweeping independent sources")
dc_source = TextInput(title="Name of source to sweep")
dc_start = NumericInput(title="Start value", value=0, mode="float")
dc_stop = NumericInput(title="Stop value", value=5, mode="float")
dc_step = NumericInput(title="Increment", value=0.1, mode="float")
dc_inputs = column(dc_desc, dc_source, dc_start, dc_stop, dc_step)
dc_tab = Panel(child=dc_inputs, title="DC Sweep")

##### Noise simulation #####

noise_desc = Paragraph(text="Perform a stochastic noise analysis of the circuit linearised about the DC operating point, measuring input referred noise at the selected output node and input source")
noise_output = TextInput(title="Name of output node")
noise_input = TextInput(title="Name input source")
noise_inputs = column(noise_desc, noise_output, noise_input, sweep_type, f_points, f_start, f_stop)
noise_tab = Panel(child=noise_inputs, title="Noise")

##### DC transfer simulation #####

dct_desc = Paragraph(text="Find the DC small-signal transfer function")
dct_output = TextInput(title="Name of output node")
dct_input = TextInput(title="Name input source")
dct_inputs = column(dct_desc, dct_output, dct_input)
dct_tab = Panel(child=dct_inputs, title="DC Transfer")

##### operating point simulation #####

op_desc = Paragraph(text="Find the DC operating point, treating capacitances as open circuits and inductors as shorts")
op_inputs = column(op_desc)
op_tab = Panel(child=op_inputs, title="DC operating point")

tabs = Tabs(tabs=[tran_tab, ac_tab, dc_tab, noise_tab, dct_tab, op_tab, sim_tab], tabs_location='left')

##### result browser #####

traces = CheckboxGroup()
def set_traces(prop, old, new):
    traces.labels = list(new)
# cds.on_change('column_names', set_traces)
cds.on_change('data', set_traces)

fig = figure(title="Simulation Results", output_backend="webgl")
renderers={}
def plot_active(prop, old, new):
    if not scale: return
    old = set(old)
    new = set(new)
    added = new-old
    removed = old-new
    for column in removed:
        key = cds.column_names[column]
        ren = renderers[key]
        fig.renderers.remove(ren)
    for column in added:
        color = Colorblind[8][column%8]
        key = cds.column_names[column]
        renderers[key] = fig.line(scale, key, source=cds, color=color)
traces.on_change('active', plot_active)

browser = row([traces, fig])
root = column([tabs, browser])

doc.add_root(root)
doc.title = "Simulate"