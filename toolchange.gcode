;;;; INSERTED TOOLCHANGE
M204 P1250
;HEIGHT:[LAYER_HEIGHT]
;TYPE:Wipe tower
;WIDTH:0.5
;--------------------
; CP TOOLCHANGE START
; toolchange #?
; material : ???
;--------------------
M220 B
M220 S100
; CP TOOLCHANGE UNLOAD
;WIDTH:1
;WIDTH:0.5
G4 S0
M486 S-1
G1 E-[RETRACT] F3600
; Filament-specific end gcode
; removed M104

G1 F21000
P[FROM_TOOL] S1 L2 D0

M109 S[TO_TOOL_TEMP] T1
T[TO_TOOL] S1 L0 D0
M900 K0 ; Filament gcode

M142 S36 ; set heatbreak target temp
M109 S[TO_TOOL_TEMP] T[TO_TOOL] ; set temperature and wait for it to be reached

G1 X[WIPE_X1] Y[WIPE_Y1] F24000
G1 X[WIPE_X2] Y[WIPE_Y2]

G1 Z[LAYER_HEIGHT] F600
G1 E[DE_RETRACT] F1200
G4 S0

M220 R
G1 F24000
G4 S0
G92 E0
; CP TOOLCHANGE END
;------------------