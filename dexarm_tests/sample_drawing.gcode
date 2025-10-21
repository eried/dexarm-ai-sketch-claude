; Sample DexArm Drawing - Simple Smiley Face
; Generated for testing gcode execution
; Adjust Z values based on your calibration

; Initialize
G28 ; Home all axes
G90 ; Absolute positioning
G21 ; Set units to millimeters

; Drawing parameters
; Z10 = pen up, Z-3 = pen down (ADJUST THESE!)

; Draw face circle (outer)
G0 X200 Y20 Z10 ; Move to start (pen up)
G1 Z-3 F1000 ; Pen down
G2 X200 Y20 I0 J-20 F2000 ; Draw circle (center at Y=0, radius=20)
G1 Z10 ; Pen up

; Draw left eye
G0 X190 Y5 Z10 ; Move to left eye position
G1 Z-3 F1000 ; Pen down
G2 X190 Y5 I0 J-3 F2000 ; Small circle
G1 Z10 ; Pen up

; Draw right eye
G0 X210 Y5 Z10 ; Move to right eye position
G1 Z-3 F1000 ; Pen down
G2 X210 Y5 I0 J-3 F2000 ; Small circle
G1 Z10 ; Pen up

; Draw smile (arc)
G0 X190 Y-5 Z10 ; Move to smile start
G1 Z-3 F1000 ; Pen down
G3 X210 Y-5 I10 J-5 F2000 ; Draw smile arc
G1 Z10 ; Pen up

; Return home
G0 X200 Y0 Z10 ; Move to safe position
G28 ; Home

; End of program
M2
