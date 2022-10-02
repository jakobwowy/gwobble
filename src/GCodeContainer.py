import copy

from gcodeparser import GcodeLine, GcodeParser
import pandas as pd
import numpy as np


class GcodeContainer:

    def __init__(self, gcode_raw, printer_setting_line_height, start_layer_height=0.0):
        self.gcode_raw = gcode_raw
        self.lines_raw = GcodeParser(gcode_raw, include_comments=True).lines
        self.start_layer_height = start_layer_height

        self.lines_start = None
        self.lines_end = None
        self.lines = None
        self.gcode_df = None

        self.model_center_point_xy = None
        self.model_height_mm = None
        self.model_layer_count = None

        self.printer_setting_line_height = printer_setting_line_height

        self.isCura = ';Generated with Cura_SteamEngine' in self.gcode_raw

        self.add_parameters_to_lines(self.lines_raw)

    @staticmethod
    def load_gcode_file(file_path: str) -> str or None:
        # load gcode file
        with open(file_path) as f:
            gcode = f.read()
        return gcode

    def add_parameters_to_lines(self, lines_raw):
        self.lines = copy.deepcopy(lines_raw)

        section_type = None
        layer_nr = 0

        # add line number to params
        for ind, line in enumerate(self.lines):
            if "TYPE:" in line.gcode_str and self.isCura:
                section_type = line.gcode_str.split("TYPE:")[1]
            if "LAYER:" in line.gcode_str and self.isCura:
                layer_nr = line.gcode_str.split("LAYER:")[1]
            line.params["line_nr"] = ind
            line.params["layer_nr"] = int(layer_nr)
            line.params["section_type"] = section_type

    def separate_start_end(self, remove_first_line_count, limit_lines=None):

        gcode_lines = self.lines

        start_g_code = GcodeLine(command=(';', None), params={}, comment='END OF THE START GCODE')
        end_g_code = GcodeLine(command=(';', None), params={}, comment='START OF THE END GCODE')

        start_index = self.lines_raw.index(start_g_code) + remove_first_line_count
        end_index = self.lines_raw.index(end_g_code)

        # exclude bottom layer by adjusting the start_index
        start_index = self.exclude_bottom_layer(gcode_lines, start_index)

        self.lines_start = gcode_lines[:start_index]
        self.lines_end = gcode_lines[end_index:]
        self.lines = gcode_lines[start_index + 1: end_index]

        if limit_lines is not None:
            self.lines = self.lines[: limit_lines]
            self.lines_raw = self.lines_start + self.lines + self.lines_end
            for line in self.lines_raw:
                if 'line_nr' in line.params: del line.params['line_nr']

        for i, line in enumerate(self.lines_start[:20]):
            print(i, line.gcode_str)

        print("-------------")

        for i, line in enumerate(self.lines[:20]):
            print(i, line.gcode_str)

    def exclude_bottom_layer(self, gcode_lines, start_index):
        if self.start_layer_height > 0:
            # scan for layer
            start_layer_index = None
            line = None
            for ind, line in enumerate(gcode_lines):
                if line.command == ("G", 1) and ind > start_index:
                    if "Z" in line.params:
                        if line.params["Z"] >= self.start_layer_height:
                            start_layer_index = ind
                            break
            if start_layer_index is not None and line is not None:
                print("start found after bottom layers")
                print(line.gcode_str)
                print("------------------------")
                print([line.gcode_str for line in gcode_lines[start_layer_index - 10: start_layer_index + 10]])
                start_index = start_layer_index
        return start_index

    def calc_g1_dataframe(self):
        # filter line extrusion command G1
        df_dict_list = [line.params for line in self.lines if line.command == ('G', 1)]
        gcode_df = pd.DataFrame(df_dict_list)

        # fill null with absolute (coordinates)
        gcode_df.E = gcode_df.E.fillna(0)
        gcode_df.fillna(method="ffill", inplace=True)
        gcode_df = gcode_df.fillna(method="bfill")

        # calculate additional columns

        # line_number
        if not self.isCura:
            gcode_df["layer_nr"] = (gcode_df["Z"] // self.printer_setting_line_height)

        # distance
        gcode_df["distance_xy"] = np.sqrt((gcode_df.X.shift(1) - gcode_df.X) ** 2 + (gcode_df.Y.shift(1) - gcode_df.Y) ** 2)
        # gcode_df["e_ratio_distance"] = (gcode_df.E / gcode_df.distance_xy )
        gcode_df["distance_xy_cumsum"] = gcode_df["distance_xy"].cumsum()

        center_point = (gcode_df.X.mean(), gcode_df.Y.mean())
        self.model_center_point_xy = center_point
        self.model_height_mm = gcode_df.Z.max()
        self.model_layer_count = int(round(self.model_height_mm / self.printer_setting_line_height))
        print("CenterPointXY", center_point)

        # calculate polar coordinates
        gcode_df["rho"] = np.sqrt((gcode_df["X"] - center_point[0]) ** 2 + (gcode_df["Y"] - center_point[1]) ** 2)
        gcode_df["phi"] = np.degrees(np.arctan2(gcode_df["X"] - center_point[0], gcode_df["Y"] - center_point[1]))

        self.gcode_df = gcode_df
