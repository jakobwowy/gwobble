# gwobble

## restrictions for gcode
- absolute positioning G90 (x,y coordinates are always absolute)

##gcode dataframe

**Columns:**

| column             | description                          | unit   | example                                                                |
|--------------------|--------------------------------------|--------|------------------------------------------------------------------------|
| layer_nr           | layer number                         |        |                                                                        |
| line_nr            | line number                          |        |                                                                        |
| X                  | x coordinate of the endpoint         | mm     |                                                                        |
| Y                  | y coordinate of the endpoint         | mm     |                                                                        |
| Z                  | z coordinate (layer height)          | mm     |                                                                        |
| E                  | relative coordinate of extruder      | mm     | E1.2  ->  extruding 22.4mm of filament between the start and end point |
| F                  | feed rate of the movement            | mm/min |                                                                        |
| distance_xy        | distance between start and end point | mm     |                                                                        |
| distance_xy_cumsum |                                      | mm     |                                                                        |
| rho                |                                      | rad    |                                                                        |
| phi                |                                      | °      |                                                                        |
