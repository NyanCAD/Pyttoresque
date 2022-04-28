// SPDX-FileCopyrightText: 2022 Pepijn de Vos
//
// SPDX-License-Identifier: MPL-2.0

#include <iostream>
#include <fstream>

#include <cxxrtl_stream.hpp>

#include "blink.hpp"

using namespace std;

int main()
{
    cxxrtl_design::p_blink top;

    // debug_items maps the hierarchical names of signals and memories in the design
    // to a cxxrtl_object (a value, a wire, or a memory)
    cxxrtl::debug_items all_debug_items;

    // Load the debug items of the top down the whole design hierarchy
    top.debug_info(all_debug_items);

    // stream_writer is the CXXRTL object that's responsible for
    // streaming results to the simulation server
    cxxrtl::stream_writer stream;
    stream.timescale(1, "us");

    // Here we tell the vcd writer to dump all the signals of the design, except for the
    // memories, to the stream.
    //
    // It's not necessary to load all debug objects to the stream. There is, for example,
    // a  stream.add(<debug items>, <filter>)) method which allows creating your custom filter to decide
    // what to add and what not. 
    stream.add_without_memories(all_debug_items);

    bool prev_led = 0;

    top.step();

    // We need to manually tell the stream writer when sample and write out the traced items.
    // This is only a slight inconvenience and allows for complete flexibilty.
    // E.g. you could only start waveform tracing when an internal signal has reached some specific
    // value etc.
    stream.sample(0);

    for(int steps=0;steps<1000;++steps){

        top.p_clk.set<bool>(false);
        top.step();
        stream.sample(steps*2 + 0);

        top.p_clk.set<bool>(true);
        top.step();
        stream.sample(steps*2 + 1);

        bool cur_led = top.p_led.get<bool>();

        if (cur_led != prev_led)
            cout << "cycle " << steps << " - led: " << cur_led << endl;

        prev_led = cur_led;

    }
}

