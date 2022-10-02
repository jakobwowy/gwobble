from datetime import datetime

from gcodeparser import GcodeLine


class ColorChange:

    def __init__(self, index, gcode_line_from_df, order=0):
        self.index = int(index)
        self.order = int(order)
        self.gcode_line_from_df = gcode_line_from_df


class ColorChangeHandler:

    def __init__(self, gcode_container, color_change_order, reduce_pressure_filament_distance, negative_pressure_reduction_factor=1,
                 retraction_length=None, retraction_speed=None, refill_retraction_length=None):

        self.gcode_container = gcode_container
        self.gcode_df = gcode_container.gcode_df
        self.gcode_df_color = None

        self.color_change_order = color_change_order

        self.color_changes = []

        # retraction
        self.retraction_length = retraction_length
        if refill_retraction_length is None:
            self.refill_retraction_length = retraction_length
        else:
            self.refill_retraction_length = refill_retraction_length
        self.retraction_speed = retraction_speed

        # pressure control color change
        self.reduce_pressure_filament_distance = reduce_pressure_filament_distance
        self.negative_pressure_reduction_factor = negative_pressure_reduction_factor

        self.gcode_result = None
        self.type_of_change_label_list = []

    @staticmethod
    def get_color_change_commands(color_param):

        color_change_commands = [
            GcodeLine(("M", 163), {"S": 0, "P": color_param[0]}, comment=""),
            GcodeLine(("M", 163), {"S": 1, "P": color_param[1]}, comment=""),
            GcodeLine(("M", 163), {"S": 2, "P": color_param[2]}, comment=""),
            GcodeLine(("M", 164), {"S": 0}, comment="")]

        return color_change_commands

    def adjust_pressure_around_color_change(self, color_change, gcode_raw):

        # scan for gcode lines for pressure reduction
        # 1. first reverse
        reduction_distance = 0
        for i in range(200):
            gcode_index = color_change.index - i - 1
            line = gcode_raw[gcode_index]
            if "E" not in line.params:
                print("NO E", line.gcode_str)
                e_len = 0
            else:
                e_len = line.params["E"]

            if line.command != ("G", 1):
                print("Warning adjust pressure no G1: {}".format(line.gcode_str))
            else:

                start_e = reduction_distance
                center_e = start_e + 0.5 * e_len

                center_percent = center_e / self.reduce_pressure_filament_distance

                e_len_new = e_len * center_percent

                # set new e_len
                gcode_raw[gcode_index].params["E"] = e_len_new
                gcode_raw[gcode_index].comment = "PressureControlFactor: {}".format(center_percent)

                reduction_distance += e_len

            if reduction_distance >= self.reduce_pressure_filament_distance:
                break

        # 2. forward
        accel_distance = 0
        for i in range(200):
            gcode_index = color_change.index + i

            if gcode_index >= len(gcode_raw):
                break

            line = gcode_raw[gcode_index]

            if "E" not in line.params:
                print("NO E", line.gcode_str)
                e_len = 0
            else:
                e_len = line.params["E"]

            if line.command != ("G", 1):
                print("Warning adjust pressure no G1: {}".format(line.gcode_str))
            else:

                start_e = accel_distance
                center_e = start_e + 0.5 * e_len

                center_percent = 2 - (center_e / self.reduce_pressure_filament_distance)

                e_len_new = e_len * center_percent

                # set new e_len
                gcode_raw[gcode_index].params["E"] = e_len_new
                gcode_raw[gcode_index].comment = "PressureControlFactor: {}".format(center_percent)
                accel_distance += e_len

            if accel_distance >= self.reduce_pressure_filament_distance:
                break

        return gcode_raw

    def add_retraction_commands(self, color_change_commands, layer_nr):

        # retraction_length
        if isinstance(self.retraction_length, list):
            number_of_sections = len(self.retraction_length)
            layers_per_section = int(self.gcode_container.model_layer_count / number_of_sections)
            section_index = layer_nr // layers_per_section
            retraction_length_loc = self.retraction_length[section_index]

        else:
            retraction_length_loc = self.retraction_length

        # retraction_length
        if isinstance(self.refill_retraction_length, list):
            number_of_sections = len(self.refill_retraction_length)
            layers_per_section = int(self.gcode_container.model_layer_count / number_of_sections)
            section_index = layer_nr // layers_per_section
            refill_retraction_length_loc = self.refill_retraction_length[section_index]
        else:
            refill_retraction_length_loc = self.refill_retraction_length

        # retraction_length
        if isinstance(self.retraction_speed, list):
            number_of_sections = len(self.retraction_speed)
            layers_per_section = int(self.gcode_container.model_layer_count / number_of_sections)
            section_index = layer_nr // layers_per_section
            retraction_speed_loc = self.retraction_speed[section_index]
        else:
            retraction_speed_loc = self.retraction_speed

        if retraction_length_loc != 0:
            color_change_commands = \
                [GcodeLine(("G", 1), {"E": -retraction_length_loc, "F": retraction_speed_loc}, comment="")] + color_change_commands

            color_change_commands += [GcodeLine(("G", 1), {"E": refill_retraction_length_loc, "F": retraction_speed_loc}, comment="")]

        return color_change_commands

    def calc_color_changes(self, gcode_df_color, color_val_label):
        gcode_df_color["color_change_index"] = gcode_df_color["delta_val"].diff().abs()

        self.gcode_df_color = gcode_df_color

        # find colorChangeIndex
        color_change_lines = gcode_df_color[gcode_df_color["color_change_index"] == 1]
        color_changes = [ColorChange(index=line.line_nr, gcode_line_from_df=line) for _, line in color_change_lines.iterrows()]

        self.color_changes += color_changes

    def calc_color_change_index_by_layer_count(self, delta_layer_count):
        color_val_label = "layer"
        self.type_of_change_label_list.append("layer")
        gcode_df_color = self.gcode_df.copy()
        color_change_val = gcode_df_color["layer"]
        gcode_df_color["delta"] = color_change_val % delta_layer_count
        gcode_df_color["delta_val"] = color_change_val // delta_layer_count

        self.calc_color_changes(gcode_df_color, color_val_label)

    def calc_color_change_index_by_distance_xy(self, delta_distance_mm):
        color_val_label = "distance_xy_cumsum"
        self.type_of_change_label_list.append("distance")
        gcode_df_color = self.gcode_df.copy()
        color_change_val = gcode_df_color["distance_xy_cumsum"]
        gcode_df_color["delta"] = color_change_val % delta_distance_mm
        gcode_df_color["delta_val"] = color_change_val // delta_distance_mm

        self.calc_color_changes(gcode_df_color, color_val_label)

    def calc_color_change_index_by_polar_splits(self, phi_split_number):
        split_degree = 360 / phi_split_number
        color_val_label = "phi"
        self.type_of_change_label_list.append("phi")
        gcode_df_color = self.gcode_df.copy()
        color_change_val = gcode_df_color["phi"]
        gcode_df_color["delta"] = color_change_val % split_degree
        gcode_df_color["delta_val"] = color_change_val // split_degree

        self.calc_color_changes(gcode_df_color, color_val_label)

    def add_color_change_commands_to_gcode(self, g_lines_raw):

        color_index = 0

        for color_change in reversed(self.color_changes):

            color = self.color_change_order[color_index % len(self.color_change_order)]

            layer_nr = int(color_change.gcode_line_from_df.layer)

            color_command = self.get_color_change_commands(color)

            if self.reduce_pressure_filament_distance is not None:
                self.adjust_pressure_around_color_change(color_change, g_lines_raw)
            else:
                # retraction only if no pressure control
                color_command = self.add_retraction_commands(color_command, layer_nr)

            # add color commands and
            g_lines_raw[color_change.index:color_change.index] = color_command

            color_index += 1

        self.gcode_result = g_lines_raw

    def write_results_to_file(self):
        all_lines = ["{}\n".format(line.gcode_str) for line in self.gcode_result]

        date_str = datetime.now().strftime("%m%d-%H:%M")

        new_file_name = "{}_colored{}_{}_{}".format(date_str, len(self.color_change_order), "-".join(self.type_of_change_label_list) , file_name)

        out = open(new_file_name, "w")
        out.writelines(all_lines)
        out.close()

        print(new_file_name)