class WobbleGenerator:

    def __init__(self, gcode_container):

        self.gcode_container = gcode_container
        self.gcode_df = gcode_container.gcode_df

        self.layer_parameter = []

        self.analyze_layer()

    def analyze_layer(self):

        for layer_nr in range(self.gcode_container.model_layer_count):

            lines = self.gcode_container.gcode_df[self.gcode_df["layer_nr"] == layer_nr]
            layer_length = lines["distance_xy"].sum()
            self.layer_parameter.append({"length": layer_length})

    def generate_wobble(self, wobble_count, wobble_amplitude, wobble_segments, toggle_multiplier=0):

        for layer_nr in range(self.gcode_container.model_layer_count):

            wobble_length = self.layer_parameter[layer_nr]["length"] / wobble_count
            wobble_segment_length = wobble_length/wobble_segments

            lines = self.gcode_container.gcode_df[self.gcode_df["layer_nr"] == 0]

            # split layer lines into wobble segments

            # add sinus signal

            for line in lines:
                line[""]

            break
