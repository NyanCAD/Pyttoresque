<!--
SPDX-FileCopyrightText: 2022 Pepijn de Vos

SPDX-License-Identifier: MPL-2.0
-->

# SimServer

A Cap'n Proto interface for running simulations over the network.

## What

Most simulators have a command-line interface that takes source files and spits out data files.
Most also have a C API to do more tight integration.

SimServer is an abstraction over the C API of various simulators that allows you to offer tighter integration with multiple simulators. For example:

* Results as data structure instead of obscure file formats
* Progress updates
* Streaming results
* Simulator subclasses to access simulator-specific features

## Why

Some simulators can be hard to install, particularly on some operating systems. Running the simulator in Docker or on a server solves this problem.

You might want to develop locally on your laptop, but run simulations on a powerfull server. A simulation server allows this.

Shelling out to the CLI is simple but does not allow deep integration. Using the C API tightly couples your program to the simulator, and could segfault your whole program.

## Status

This collection of projects is extremely alpha. The API is subject to change, and the implemenations are far from complete.
Current implementations:

* [Xyce](https://github.com/NyanCAD/XyceSimServer)
* [Ngspice](https://github.com/NyanCAD/NgspiceSimServer)
* [cxxrtl](https://github.com/NyanCAD/CxxrtlSimServer)

Desired:

* [JuliaSpice](https://juliacomputing.com/media/2021/03/darpa-ditto/)
* WRSpice, Qucs, Gnucap?
* ghdl, verilator?
