# SPDX-FileCopyrightText: 2022 Pepijn de Vos
#
# SPDX-License-Identifier: MPL-2.0

@0x8c03f73b3ceae3de;

using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("Sim");

interface Simulator(Cmd) {
    loadFiles @0 (files :List(File)) -> (commands :Cmd);
    loadPath @1 (file :Text) -> (commands :Cmd);
}

interface Run {
    run @0 (vectors :List(Text)) -> (result :Result);
}

interface Tran {
    tran @0 (step :Float64, stop :Float64, start :Float64, vectors :List(Text)) -> (result :Result);
}

interface Op {
    op @0 (vectors :List(Text)) -> (result :Result);
}

interface Ac {
    ac @0 (mode :AcType, num :UInt64, fstart :Float64, fstop :Float64, vectors :List(Text)) -> (result :Result);
}

interface Noise {
    noise @0 (output :Text, src :Text, mode :AcType, num :UInt64, fstart :Float64, fstop :Float64, vectors :List(Text)) -> (result :Result);
}

interface Dc {
    dc @0 (src :Text, vstart :Float64, vstop :Float64, vincr :Float64, vectors :List(Text)) -> (result :Result);
}

enum AcType {
    lin @0;
    dec @1;
    oct @2;
}

interface Result {
    read @0 () -> (more :Bool, data :List(Vectors), stdout :Text);
}

struct Vectors {
    name @0 :Text;
    scale @1 :Text;
    data @2 :List(Vector);
}

struct Vector {
    name @0 :Text;
    data :union {
        real @1 :List(Float64);
        complex @2 :List(Complex);
        digital @3 :List(Bool); # actually packed as 1 bit, cool
    }
}

struct Complex {
    real @0 :Float64;
    imag @1 :Float64;
}

struct File {
    name @0 :Text;
    contents @1 :Data;
}

# Implementations

interface Xyce extends(Simulator(Run)) { }

interface NgspiceCommands extends(Run, Tran, Op, Dc, Ac, Noise) {}
interface Ngspice extends(Simulator(NgspiceCommands)) { }

interface Cxxrtl extends(Simulator(Run)) { }