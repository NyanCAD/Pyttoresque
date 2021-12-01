*SPICE netlist created from BLIF module blink by blif2BSpice

* cells and mosfets from osu035
* https://vlsiarch.ecen.okstate.edu/flow/
* http://opencircuitdesign.com/qflow/

Xb1 vdd 0 clk led blink
Vdd vdd 0 1.8
Vin clk 0 PULSE(0 1.8 0 1n 1n 1u 2u)
.tran 1u 2m

.subckt blink vdd gnd clk led 
.ic v(counter[0])=0
.ic v(counter[1])=0
.ic v(counter[2])=0
.ic v(counter[3])=0
.ic v(counter[4])=0
.ic v(counter[5])=0
.ic v(counter[6])=0
.ic v(counter[7])=0
.ic v(counter[8])=0
.ic v(counter[9])=0
.ic v(counter[10])=0
.ic v(counter[11])=0
XINVX1_1 counter[0] _0_[0] vdd gnd INVX1
XAND2X2_1 vdd gnd counter[0] counter[1] _1_ AND2X2
XNOR2X1_1 vdd counter[1] gnd _2_ counter[0] NOR2X1
XNOR2X1_2 vdd _1_ gnd _0_[1] _2_ NOR2X1
XXOR2X1_1 _0_[2] vdd counter[2] _1_ gnd XOR2X1
XNAND3X1_1 counter[1] vdd gnd counter[0] counter[2] _3_ NAND3X1
XXNOR2X1_1 _3_ counter[3] gnd vdd _0_[3] XNOR2X1
XAND2X2_2 vdd gnd counter[2] counter[3] _4_ AND2X2
XNAND2X1_1 vdd _5_ gnd _1_ _4_ NAND2X1
XXNOR2X1_2 _5_ counter[4] gnd vdd _0_[4] XNOR2X1
XNAND2X1_2 vdd _6_ gnd counter[3] counter[4] NAND2X1
XNOR2X1_3 vdd _3_ gnd _7_ _6_ NOR2X1
XXOR2X1_2 _0_[5] vdd counter[5] _7_ gnd XOR2X1
XINVX1_2 counter[6] _8_ vdd gnd INVX1
XNAND3X1_2 counter[4] vdd gnd counter[3] counter[5] _9_ NAND3X1
XNOR2X1_4 vdd _9_ gnd _10_ _3_ NOR2X1
XXNOR2X1_3 _10_ _8_ gnd vdd _0_[6] XNOR2X1
XAND2X2_3 vdd gnd counter[4] counter[5] _11_ AND2X2
XNAND3X1_3 _4_ vdd gnd _1_ _11_ _12_ NAND3X1
XOAI21X1_1 gnd vdd _8_ _12_ _13_ counter[7] OAI21X1
XINVX1_3 counter[7] _14_ vdd gnd INVX1
XNAND3X1_4 _14_ vdd gnd counter[6] _10_ _15_ NAND3X1
XNAND2X1_3 vdd _0_[7] gnd _15_ _13_ NAND2X1
XBUFX2_1 vdd gnd counter[7] led BUFX2
XDFFPOSX1_1 vdd _0_[0] gnd counter[0] clk DFFPOSX1
XDFFPOSX1_2 vdd _0_[1] gnd counter[1] clk DFFPOSX1
XDFFPOSX1_3 vdd _0_[2] gnd counter[2] clk DFFPOSX1
XDFFPOSX1_4 vdd _0_[3] gnd counter[3] clk DFFPOSX1
XDFFPOSX1_5 vdd _0_[4] gnd counter[4] clk DFFPOSX1
XDFFPOSX1_6 vdd _0_[5] gnd counter[5] clk DFFPOSX1
XDFFPOSX1_7 vdd _0_[6] gnd counter[6] clk DFFPOSX1
XDFFPOSX1_8 vdd _0_[7] gnd counter[7] clk DFFPOSX1
XBUFX2_2 vdd gnd gnd counter[8] BUFX2
XBUFX2_3 vdd gnd gnd counter[9] BUFX2
XBUFX2_4 vdd gnd gnd counter[10] BUFX2
XBUFX2_5 vdd gnd gnd counter[11] BUFX2
.ends blink* run N88Y

* this is really a TSMC model from Mosis website
.MODEL nfet NMOS (     LEVEL   = 49
+VERSION = 3.1            TNOM    = 27             TOX     = 7.6E-9
+XJ      = 1.5E-7         NCH     = 1.7E17         VTH0    = 0.4964448
+K1      = 0.5307769      K2      = 0.0199705      K3      = 0.2963637
+K3B     = 0.2012165      W0      = 2.836319E-6    NLX     = 2.894802E-7
+DVT0W   = 0              DVT1W   = 5.3E6          DVT2W   = -0.032
+DVT0    = 0.112017       DVT1    = 0.2453972      DVT2    = -0.171915
+U0      = 444.9381976    UA      = 2.921284E-10   UB      = 1.773281E-18
+UC      = 7.067896E-11   VSAT    = 1.130785E5     A0      = 1.1356246
+AGS     = 0.2810374      B0      = 2.844393E-7    B1      = 5E-6
+KETA    = -7.8181E-3     A1      = 0              A2      = 1
+RDSW    = 925.2701982    PRWG    = -1E-3          PRWB    = -1E-3
+WR      = 1              WINT    = 7.186965E-8    LINT    = 1.735515E-9
+XL      = -2E-8          XW      = 0              DWG     = -1.712973E-8
+DWB     = 5.851691E-9    VOFF    = -0.132935      NFACTOR = 0.5710974
+CIT     = 0              CDSC    = 8.607229E-4    CDSCD   = 0
+CDSCB   = 0              ETA0    = 2.128321E-3    ETAB    = 0
+DSUB    = 0.0257957      PCLM    = 0.6766314      PDIBLC1 = 1
+PDIBLC2 = 1.787424E-3    PDIBLCB = 0              DROUT   = 0.7873539
+PSCBE1  = 6.973485E9     PSCBE2  = 1.46235E-7     PVAG    = 0.05
+DELTA   = 0.01           MOBMOD  = 1              PRT     = 0
+UTE     = -1.5           KT1     = -0.11          KT1L    = 0
+KT2     = 0.022          UA1     = 4.31E-9        UB1     = -7.61E-18
+UC1     = -5.6E-11       AT      = 3.3E4          WL      = 0
+WLN     = 1              WW      = 0              WWN     = 1
+WWL     = 0              LL      = 0              LLN     = 1
+LW      = 0              LWN     = 1              LWL     = 0
+CAPMOD  = 2              CGDO    = 1.96E-10       CGSO    = 1.96E-10
+CGBO    = 0              CJ      = 9.276962E-4    PB      = 0.8157962
+MJ      = 0.3557696      CJSW    = 3.181055E-10   PBSW    = 0.6869149
+MJSW    = 0.1            PVTH0   = -0.0252481     PRDSW   = -96.4502805
+PK2     = -4.805372E-3   WKETA   = -7.643187E-4   LKETA   = -0.0129496      )
* run n88y
.MODEL pfet PMOS (     LEVEL   = 49
+VERSION = 3.1            TNOM    = 27             TOX     = 7.6E-9
+XJ      = 1.5E-7         NCH     = 1.7E17         VTH0    = -0.6636594
+K1      = 0.4564781      K2      = -0.019447      K3      = 39.382919
+K3B     = -2.8930965     W0      = 2.655585E-6    NLX     = 1.51028E-7
+DVT0W   = 0              DVT1W   = 5.3E6          DVT2W   = -0.032
+DVT0    = 1.1744581      DVT1    = 0.7631128      DVT2    = -0.1035171
+U0      = 151.3305606    UA      = 2.061211E-10   UB      = 1.823477E-18
+UC      = -8.97321E-12   VSAT    = 9.915604E4     A0      = 1.1210053
+AGS     = 0.3961954      B0      = 6.493139E-7    B1      = 4.273215E-6
+KETA    = -9.27E-3       A1      = 0              A2      = 1
+RDSW    = 2.30725E3      PRWG    = -1E-3          PRWB    = 0
+WR      = 1              WINT    = 5.962233E-8    LINT    = 4.30928E-9
+XL      = -2E-8          XW      = 0              DWG     = -1.596201E-8
+DWB     = 1.378919E-8    VOFF    = -0.15          NFACTOR = 2
+CIT     = 0              CDSC    = 6.593084E-4    CDSCD   = 0
+CDSCB   = 0              ETA0    = 0.0286461      ETAB    = 0
+DSUB    = 0.2436027      PCLM    = 4.3597508      PDIBLC1 = 7.447024E-4
+PDIBLC2 = 4.256073E-3    PDIBLCB = 0              DROUT   = 0.0120292
+PSCBE1  = 1.347622E10    PSCBE2  = 5E-9           PVAG    = 3.669793
+DELTA   = 0.01           MOBMOD  = 1              PRT     = 0
+UTE     = -1.5           KT1     = -0.11          KT1L    = 0
+KT2     = 0.022          UA1     = 4.31E-9        UB1     = -7.61E-18
+UC1     = -5.6E-11       AT      = 3.3E4          WL      = 0
+WLN     = 1              WW      = 0              WWN     = 1
+WWL     = 0              LL      = 0              LLN     = 1
+LW      = 0              LWN     = 1              LWL     = 0
+CAPMOD  = 2              CGDO    = 2.307E-10      CGSO    = 2.307E-10
+CGBO    = 0              CJ      = 1.420282E-3    PB      = 0.99
+MJ      = 0.5490877      CJSW    = 4.773605E-10   PBSW    = 0.99
+MJSW    = 0.1997417      PVTH0   = 6.58707E-3     PRDSW   = -93.5582228
+PK2     = 1.011593E-3    WKETA   = -0.0101398     LKETA   = 6.027967E-3     )
* duplicated nfet
.MODEL hnfet NMOS (     LEVEL   = 49
+VERSION = 3.1            TNOM    = 27             TOX     = 7.6E-9
+XJ      = 1.5E-7         NCH     = 1.7E17         VTH0    = 0.4964448
+K1      = 0.5307769      K2      = 0.0199705      K3      = 0.2963637
+K3B     = 0.2012165      W0      = 2.836319E-6    NLX     = 2.894802E-7
+DVT0W   = 0              DVT1W   = 5.3E6          DVT2W   = -0.032
+DVT0    = 0.112017       DVT1    = 0.2453972      DVT2    = -0.171915
+U0      = 444.9381976    UA      = 2.921284E-10   UB      = 1.773281E-18
+UC      = 7.067896E-11   VSAT    = 1.130785E5     A0      = 1.1356246
+AGS     = 0.2810374      B0      = 2.844393E-7    B1      = 5E-6
+KETA    = -7.8181E-3     A1      = 0              A2      = 1
+RDSW    = 925.2701982    PRWG    = -1E-3          PRWB    = -1E-3
+WR      = 1              WINT    = 7.186965E-8    LINT    = 1.735515E-9
+XL      = -2E-8          XW      = 0              DWG     = -1.712973E-8
+DWB     = 5.851691E-9    VOFF    = -0.132935      NFACTOR = 0.5710974
+CIT     = 0              CDSC    = 8.607229E-4    CDSCD   = 0
+CDSCB   = 0              ETA0    = 2.128321E-3    ETAB    = 0
+DSUB    = 0.0257957      PCLM    = 0.6766314      PDIBLC1 = 1
+PDIBLC2 = 1.787424E-3    PDIBLCB = 0              DROUT   = 0.7873539
+PSCBE1  = 6.973485E9     PSCBE2  = 1.46235E-7     PVAG    = 0.05
+DELTA   = 0.01           MOBMOD  = 1              PRT     = 0
+UTE     = -1.5           KT1     = -0.11          KT1L    = 0
+KT2     = 0.022          UA1     = 4.31E-9        UB1     = -7.61E-18
+UC1     = -5.6E-11       AT      = 3.3E4          WL      = 0
+WLN     = 1              WW      = 0              WWN     = 1
+WWL     = 0              LL      = 0              LLN     = 1
+LW      = 0              LWN     = 1              LWL     = 0
+CAPMOD  = 2              CGDO    = 1.96E-10       CGSO    = 1.96E-10
+CGBO    = 0              CJ      = 9.276962E-4    PB      = 0.8157962
+MJ      = 0.3557696      CJSW    = 3.181055E-10   PBSW    = 0.6869149
+MJSW    = 0.1            PVTH0   = -0.0252481     PRDSW   = -96.4502805
+PK2     = -4.805372E-3   WKETA   = -7.643187E-4   LKETA   = -0.0129496      )
* duplicated
.MODEL hpfet PMOS (     LEVEL   = 49
+VERSION = 3.1            TNOM    = 27             TOX     = 7.6E-9
+XJ      = 1.5E-7         NCH     = 1.7E17         VTH0    = -0.6636594
+K1      = 0.4564781      K2      = -0.019447      K3      = 39.382919
+K3B     = -2.8930965     W0      = 2.655585E-6    NLX     = 1.51028E-7
+DVT0W   = 0              DVT1W   = 5.3E6          DVT2W   = -0.032
+DVT0    = 1.1744581      DVT1    = 0.7631128      DVT2    = -0.1035171
+U0      = 151.3305606    UA      = 2.061211E-10   UB      = 1.823477E-18
+UC      = -8.97321E-12   VSAT    = 9.915604E4     A0      = 1.1210053
+AGS     = 0.3961954      B0      = 6.493139E-7    B1      = 4.273215E-6
+KETA    = -9.27E-3       A1      = 0              A2      = 1
+RDSW    = 2.30725E3      PRWG    = -1E-3          PRWB    = 0
+WR      = 1              WINT    = 5.962233E-8    LINT    = 4.30928E-9
+XL      = -2E-8          XW      = 0              DWG     = -1.596201E-8
+DWB     = 1.378919E-8    VOFF    = -0.15          NFACTOR = 2
+CIT     = 0              CDSC    = 6.593084E-4    CDSCD   = 0
+CDSCB   = 0              ETA0    = 0.0286461      ETAB    = 0
+DSUB    = 0.2436027      PCLM    = 4.3597508      PDIBLC1 = 7.447024E-4
+PDIBLC2 = 4.256073E-3    PDIBLCB = 0              DROUT   = 0.0120292
+PSCBE1  = 1.347622E10    PSCBE2  = 5E-9           PVAG    = 3.669793
+DELTA   = 0.01           MOBMOD  = 1              PRT     = 0
+UTE     = -1.5           KT1     = -0.11          KT1L    = 0
+KT2     = 0.022          UA1     = 4.31E-9        UB1     = -7.61E-18
+UC1     = -5.6E-11       AT      = 3.3E4          WL      = 0
+WLN     = 1              WW      = 0              WWN     = 1
+WWL     = 0              LL      = 0              LLN     = 1
+LW      = 0              LWN     = 1              LWL     = 0
+CAPMOD  = 2              CGDO    = 2.307E-10      CGSO    = 2.307E-10
+CGBO    = 0              CJ      = 1.420282E-3    PB      = 0.99
+MJ      = 0.5490877      CJSW    = 4.773605E-10   PBSW    = 0.99
+MJSW    = 0.1997417      PVTH0   = 6.58707E-3     PRDSW   = -93.5582228
+PK2     = 1.011593E-3    WKETA   = -0.0101398     LKETA   = 6.027967E-3     )

.subckt AND2X2 vdd gnd A B Y
M0 a_2_6# A vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 vdd B a_2_6# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 Y a_2_6# vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 a_9_6# A a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 gnd B a_9_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 Y a_2_6# gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends AND2X2

.subckt BUFX2 vdd gnd A Y
M0 vdd A a_2_6# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 Y a_2_6# vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 gnd A a_2_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 Y a_2_6# gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends BUFX2

.subckt DFFPOSX1 vdd D gnd Q CLK
M0 vdd CLK a_2_6# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 a_17_74# D vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 a_22_6# CLK a_17_74# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 a_31_74# a_2_6# a_22_6# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 vdd a_34_4# a_31_74# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 a_34_4# a_22_6# vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M6 a_61_74# a_34_4# vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M7 a_66_6# a_2_6# a_61_74# vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M8 a_76_84# CLK a_66_6# vdd pfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M9 vdd Q a_76_84# vdd pfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M10 gnd CLK a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M11 Q a_66_6# vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M12 a_17_6# D gnd gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M13 a_22_6# a_2_6# a_17_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M14 a_31_6# CLK a_22_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M15 gnd a_34_4# a_31_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M16 a_34_4# a_22_6# gnd gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M17 a_61_6# a_34_4# gnd gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M18 a_66_6# CLK a_61_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M19 a_76_6# a_2_6# a_66_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M20 gnd Q a_76_6# gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M21 Q a_66_6# gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends DFFPOSX1

.subckt INVX1 A Y vdd gnd
M0 Y A vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 Y A gnd gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends INVX1

.subckt NAND2X1 vdd Y gnd A B
M0 Y A vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 vdd B Y vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 a_9_6# A gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 Y B a_9_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends NAND2X1

.subckt NAND3X1 B vdd gnd A C Y
M0 Y A vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 vdd B Y vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 Y C vdd vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 a_9_6# A gnd gnd nfet w=6u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 a_14_6# B a_9_6# gnd nfet w=6u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 Y C a_14_6# gnd nfet w=6u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends NAND3X1

.subckt NOR2X1 vdd B gnd Y A
M0 a_9_54# A vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 Y B a_9_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 Y A gnd gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 gnd B Y gnd nfet w=2u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends NOR2X1

.subckt OAI21X1 gnd vdd A B Y C
M0 a_9_54# A vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 Y B a_9_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 vdd C Y vdd pfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 gnd A a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 a_2_6# B gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 Y C a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends OAI21X1

.subckt XOR2X1 Y vdd B A gnd
M0 vdd A a_2_6# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 a_18_54# a_13_43# vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 Y A a_18_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 a_35_54# a_2_6# Y vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 vdd B a_35_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 a_13_43# B vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M6 gnd A a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M7 a_18_6# a_13_43# gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M8 Y a_2_6# a_18_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M9 a_35_6# A Y gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M10 gnd B a_35_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M11 a_13_43# B gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends XOR2X1

.subckt XNOR2X1 A B gnd vdd Y
M0 vdd A a_2_6# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M1 a_18_54# a_12_41# vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M2 Y a_2_6# a_18_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M3 a_35_54# A Y vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M4 vdd B a_35_54# vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M5 a_12_41# B vdd vdd pfet w=8u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M6 gnd A a_2_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M7 a_18_6# a_12_41# gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M8 Y A a_18_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M9 a_35_6# a_2_6# Y gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M10 gnd B a_35_6# gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
M11 a_12_41# B gnd gnd nfet w=4u l=0.4u
+ ad=0p pd=0u as=0p ps=0u 
.ends XNOR2X1
