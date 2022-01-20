from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.events import ButtonClick
from bokeh.models import ColumnDataSource, Button, NumericInput, Panel, Tabs, Paragraph, Select, TextInput
from bokeh.plotting import figure

doc = curdoc()

tran_desc = Paragraph(text="Perform a non-linear, time-domain simulation")
t_step = NumericInput(title="Maximum timestep", value=1e-6, mode="float")
t_start = NumericInput(title="Time to start saving data", value=0.0, mode="float")
t_stop = NumericInput(title="Stop time", value=1e-3, mode="float")
tran_inputs = column(tran_desc, t_step, t_start, t_stop)
tran_tab = Panel(child=tran_inputs, title="Transient")

ac_desc = Paragraph(text="Compute the small-signal AC behavior of the circuit linearized about its DC operating point")
sweep_type = Select(options=[("dec", "Decade"), ("oct", "Octave"), ("lin", "Linear"), ("list", "List")])
f_points = NumericInput(title="Number of points", value=10, mode="float")
f_start = NumericInput(title="Start frequency", value=1, mode="float")
f_stop = NumericInput(title="Stop frequency", value=1e6, mode="float")
ac_inputs = column(ac_desc, sweep_type, f_points, f_start, f_stop)
ac_tab = Panel(child=ac_inputs, title="AC Analysis")

dc_desc = Paragraph(text="Compute the DC operating point of a circuit while sweeping independent sources")
dc_source = TextInput(title="Name of source to sweep")
dc_start = NumericInput(title="Start value", value=0, mode="float")
dc_stop = NumericInput(title="Stop value", value=5, mode="float")
dc_step = NumericInput(title="Increment", value=0.1, mode="float")
dc_inputs = column(dc_desc, dc_source, dc_start, dc_stop, dc_step)
dc_tab = Panel(child=dc_inputs, title="DC Sweep")

noise_desc = Paragraph(text="Perform a stochastic noise analysis of the circuit linearised about the DC operating point, measuring input referred noise at the selected output node and input source")
noise_output = TextInput(title="Name of output node")
noise_input = TextInput(title="Name input source")
noise_inputs = column(noise_desc, noise_output, noise_input, sweep_type, f_points, f_start, f_stop)
noise_tab = Panel(child=noise_inputs, title="Noise")

dct_desc = Paragraph(text="Find the DC small-signal transfer function")
dct_output = TextInput(title="Name of output node")
dct_input = TextInput(title="Name input source")
dct_inputs = column(dct_desc, dct_output, dct_input)
dct_tab = Panel(child=dct_inputs, title="DC Transfer")

op_desc = Paragraph(text="Find the DC operating point, treating capacitances as open circuits and inductors as shorts")
op_inputs = column(op_desc)
op_tab = Panel(child=op_inputs, title="DC operating point")

tabs = Tabs(tabs=[tran_tab, ac_tab, dc_tab, noise_tab, dct_tab, op_tab], tabs_location='left')

btn = Button(label="Simulate")

doc.add_root(tabs)
doc.title = "Simulate"