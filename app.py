import wx
from printrun.gcview import GcodeViewMainWrapper
from printrun.gcoder import GCode
import printrun.gcview
import printrun.gviz as gviz
import printrun
from marker import MarkerActor
import re
import os

DEFAULT_DIMENSIONS = [250, 210, 210, 0, 0, 0]  # Default to MK3 size

def parse_bed_shape(line):
    # Parse line like "; bed_shape = 0x0,360x0,360x360,0x360"
    try:
        # Extract the coordinates part
        coords_str = line.split('=')[1].strip()
        # Split into individual coordinate pairs
        coords = coords_str.split(',')
        
        # Get max values for x and y
        max_x = max_y = 0
        for coord in coords:
            x, y = map(float, coord.split('x'))
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            
        return [max_x, max_y, max_x, 0, 0, 0]  # Using max_x as Z height too
    except Exception as e:
        print(f"Error parsing bed shape: {str(e)}")
        return None

def get_build_dimensions(gcode_path):
    try:
        with open(gcode_path) as f:
            for line in f:
                if '; bed_shape =' in line:
                    dims = parse_bed_shape(line)
                    if dims:
                        print(f"Found bed dimensions in GCode: {dims}")
                        return dims
                    
        print("No bed dimensions found in GCode, using defaults")
        return DEFAULT_DIMENSIONS
    except Exception as e:
        print(f"Error reading GCode file: {str(e)}")
        return DEFAULT_DIMENSIONS



class PrintegrateApp(wx.App):

    def __init__(self, gcode_path=None):
        self.gcode_path = gcode_path
        super(PrintegrateApp, self).__init__()

    def OnInit(self):
        frame = PrintegrateFrame(None, gcode_path=self.gcode_path)
        self.SetTopWindow(frame)
        frame.Show()
        return True

class PrintegrateFrame(wx.Frame):
        
        def __init__(self, *args, **kwargs):
            self.gcode_path = kwargs.pop("gcode_path", None)
            super().__init__(*args, **kwargs, title="Printegration", size=(1200, 900)) 
            
            self.SetBackgroundColour(wx.Colour(255, 255, 255))
            self.drl_path = None
            
            # Create main vertical sizer
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            
            # Create horizontal sizer for viewer and layer slider
            viewer_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            # Create a vertical sizer for the main content
            content_sizer = wx.BoxSizer(wx.VERTICAL)
            
            # Add file browser panel
            browser_panel = wx.Panel(self)
            browser_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            # Add static text for showing selected file
            self.file_text = wx.StaticText(browser_panel, label="No .drl file selected")
            browser_sizer.Add(self.file_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            
            # Add browse button
            browse_btn = wx.Button(browser_panel, label="Browse .drl")
            browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
            browser_sizer.Add(browse_btn, 0, wx.ALL, 5)
            
            # Add Drill tool selector
            tool_label = wx.StaticText(browser_panel, label="Drill Tool:")
            browser_sizer.Add(tool_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            self.tool_choice = wx.Choice(browser_panel, choices=["None"])
            self.tool_choice.SetSelection(0)  # Select None by default
            self.tool_choice.Bind(wx.EVT_CHOICE, self.on_tool_select)
            browser_sizer.Add(self.tool_choice, 0, wx.ALL, 5)
            
            # Add conductive tool selector
            conductive_sizer = wx.BoxSizer(wx.HORIZONTAL)
            conductive_label = wx.StaticText(browser_panel, label="Conductive Tool:")
            conductive_sizer.Add(conductive_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            
            self.conductive_choice = wx.Choice(browser_panel, choices=["None"])
            self.conductive_choice.SetSelection(0)  # Start with None selected
            self.conductive_choice.Bind(wx.EVT_CHOICE, self.on_conductive_tool_select)
            conductive_sizer.Add(self.conductive_choice, 0, wx.ALL, 0)
            browser_sizer.Add(conductive_sizer, 0, wx.ALL, 5)

            # Add Printegrate button
            printegrate_btn = wx.Button(browser_panel, label="Printegrate")
            printegrate_btn.Bind(wx.EVT_BUTTON, self.on_printegrate)
            browser_sizer.Add(printegrate_btn, 0, wx.ALL, 5)

            # Add Reset button
            reset_btn = wx.Button(browser_panel, label="Reset")
            reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
            browser_sizer.Add(reset_btn, 0, wx.ALL, 5)

            # Add Save button
            save_btn = wx.Button(browser_panel, label="Save")
            save_btn.Bind(wx.EVT_BUTTON, self.on_save)
            browser_sizer.Add(save_btn, 0, wx.ALL, 5)
            
            browser_panel.SetSizer(browser_sizer)
            content_sizer.Add(browser_panel, 0, wx.EXPAND | wx.ALL, 5)
            
            # Get build dimensions from GCode file or use defaults
            build_dimensions = get_build_dimensions(self.gcode_path) if self.gcode_path else DEFAULT_DIMENSIONS
            print(f"Using build dimensions: {build_dimensions}")
            
            # Add gcview component
            self.gcview = GcodeViewMainWrapper(self, build_dimensions, None, False, 0, (1, 10))
            self.gcview.clickcb = self.on_click  # Set click callback
            
            # Add custom movable marker actor
            self.marker = MarkerActor(parent_viewer=self.gcview)
            # Add marker after platform but before model
            self.gcview.objects.insert(1, printrun.gcview.GCObject(self.marker))
            
            content_sizer.Add(self.gcview.widget, 1, wx.EXPAND | wx.ALL, 5)
            
            # Add content sizer to viewer sizer
            viewer_sizer.Add(content_sizer, 1, wx.EXPAND)
            
            # Add vertical layer slider in a separate sizer
            slider_sizer = wx.BoxSizer(wx.VERTICAL)
            self.layer_slider = wx.Slider(
                self,
                minValue=0, 
                maxValue=100,
                style=wx.SL_VERTICAL | wx.SL_LABELS | wx.SL_INVERSE
            )
            self.layer_slider.Bind(wx.EVT_SLIDER, self.on_layer_change)
            slider_sizer.Add(self.layer_slider, 1, wx.EXPAND | wx.ALL, 5)
            
            # Add layer slider to viewer sizer
            viewer_sizer.Add(slider_sizer, 0, wx.EXPAND)
            
            # Add viewer sizer to main sizer
            main_sizer.Add(viewer_sizer, 1, wx.EXPAND)
            
            # Create bottom sizer for movement slider
            bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
            movement_label = wx.StaticText(self, label="Movement:")
            bottom_sizer.Add(movement_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            
            self.movement_slider = wx.Slider(
                self,
                minValue=0,
                maxValue=100,
                size=(200, -1),
                style=wx.SL_HORIZONTAL | wx.SL_LABELS
            )
            self.movement_slider.Bind(wx.EVT_SLIDER, self.on_movement_change)
            bottom_sizer.Add(self.movement_slider, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
            
            # Add bottom sizer to main sizer
            main_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.ALL, 5)
            
            self.SetSizer(main_sizer)
            
            # Disable sliders initially
            self.layer_slider.Disable()
            self.movement_slider.Disable()
            
            # Load G-code if path was provided
            if self.gcode_path:
                self.load_gcode(self.gcode_path)
                # After loading G-code, if we have tools, select the last one
                tools = self.get_gcode_tools()
                if tools:
                    self.conductive_choice.SetSelection(len(tools))
            
            browser_panel.Layout()

        def parse_drill_file(self, filepath):
            """Parse a drill file and extract tool definitions and coordinates"""
            tools = {}
            current_tool = None
            
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Parse tool definitions (e.g., T1C0.300)
                    if line.startswith('T') and 'C' in line:
                        match = re.match(r'T(\d+)C([\d.]+)', line)
                        if match:
                            tool_num = match.group(1)
                            tool_size = float(match.group(2))
                            tools[f'T{tool_num}'] = {
                                'size': tool_size,
                                'points': []
                            }
                    
                    # Parse coordinates
                    elif line.startswith('X') and 'Y' in line:
                        if current_tool and current_tool in tools:
                            match = re.match(r'X([\d.-]+)Y([\d.-]+)', line)
                            if match:
                                x = float(match.group(1))
                                y = float(match.group(2))
                                # Convert to positive Y coordinates and add current Z height
                                z = self.marker.get_current_layer_height()
                                tools[current_tool]['points'].append([x, -y, z])
                    
                    # Track current tool
                    elif line.startswith('T'):
                        current_tool = f'T{line[1:]}'
            
            return tools

        def on_tool_select(self, event):
            """Handle tool selection"""
            if event is None:
                # Called programmatically, use current selection
                selection = self.tool_choice.GetSelection()
            else:
                selection = event.GetSelection()
                
            tool = self.tool_choice.GetString(selection).split(" (")[0]  # Get just the tool name
            self.marker.set_current_tool(tool)

        def load_drill_file(self, filepath):
            """Load and parse a drill file"""
            print("\n=== Starting Drill File Load ===")
            try:
                self.drl_path = filepath
                # Clear existing drill points
                print("Clearing existing drill points...")
                self.marker.clear_drill_points()
                print("Drill points cleared")
                
                # Clear and reset tool choice, keeping None as first option
                print("Resetting tool choice...")
                self.tool_choice.Clear()
                self.tool_choice.Append("None")
                self.tool_choice.Enable(False)
                print("Tool choice reset")
                
                print("Parsing drill file...")
                tools_data = self.parse_drill_file(filepath)
                if not tools_data:
                    print("No tools data found")
                    return
                print(f"Found {len(tools_data)} tools")
                
                # Add points for each tool
                for tool_name, data in tools_data.items():
                    if data['points']:  # Only add tools that have points
                        print(f"Adding points for {tool_name}")
                        self.marker.add_drill_points(tool_name, data['points'], data['size'])
                        self.tool_choice.Append(f"{tool_name} ({data['size']}mm)")
                        
                self.tool_choice.Enable(True)
                if self.tool_choice.GetCount() > 1:  # If we have tools besides None
                    print("Setting initial tool selection")
                    self.tool_choice.SetSelection(1)  # Select first actual tool
                    self.on_tool_select(None)  # Update current tool
                else:
                    self.tool_choice.SetSelection(0)  # Select None if no tools
                
                print("Drill file loaded successfully")
                
            except Exception as e:
                print(f"Error loading drill file: {e}")
                wx.MessageBox(f"Error loading drill file: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        
            print("=== Drill File Load Complete ===\n")

        def create_file_dialog(self):
            """Create a file dialog without showing it"""
            return wx.FileDialog(
                parent=self,
                message="Choose a drill file",
                defaultDir=os.getcwd(),
                defaultFile="",
                wildcard="Drill files (*.drl)|*.drl",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            )

        def on_browse(self, event):
            """Handle browse button click"""
            print("\n=== Starting Browse Operation ===")
            print(f"Active windows: {len(wx.GetTopLevelWindows())}")
            print(f"Is main window shown: {self.IsShown()}")
            
            # Try to ensure clean state before showing dialog
            try:
                print("Preparing for dialog...")
                # Force a refresh of the main window
                self.Refresh()
                self.Update()
                # Process any pending events
                wx.Yield()
                
                print("Creating dialog...")
                dlg = wx.FileDialog(
                    parent=None,  # Try with no parent
                    message="Choose a drill file",
                    defaultDir=os.getcwd(),
                    defaultFile="",
                    wildcard="Drill files (*.drl)|*.drl",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
                )
                print("Dialog created successfully")
                
                try:
                    # Process any pending events again
                    wx.Yield()
                    print("Showing modal dialog...")
                    result = dlg.ShowModal()
                    print(f"Dialog result: {result}")
                    
                    if result == wx.ID_OK:
                        filepath = dlg.GetPath()
                        print(f"Selected file: {filepath}")
                        # Use CallAfter to process the file after dialog is fully closed
                        wx.CallAfter(self._process_drill_file, filepath)
                    
                except Exception as e:
                    print(f"Error during dialog operation: {e}")
                    wx.MessageBox(f"Error in dialog: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
                finally:
                    print("Destroying dialog...")
                    dlg.Destroy()
                    print("Dialog destroyed")
                    
            except Exception as e:
                print(f"Error creating dialog: {e}")
                wx.MessageBox(f"Error creating dialog: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
            
            print(f"Final active windows: {len(wx.GetTopLevelWindows())}")
            print("=== Browse Operation Complete ===\n")

        def _process_drill_file(self, filepath):
            """Process drill file after dialog is closed"""
            self.file_text.SetLabel(filepath)
            self.load_drill_file(filepath)

        def load_gcode(self, path):
            """Load a G-code file and update the visualization"""
            if not path:
                print("No G-code file path provided")
                return
                
            try:
                # Check printer compatibility
                is_compatible, printer_name = self.check_printer_compatibility(path)
                if not is_compatible:
                    dlg = wx.MessageDialog(self,
                        "This G-code file appears to be for an unsupported printer.\n"
                        "Currently supported printers:\n- Prusa XL\n\n"
                        "The file must be generated by PrusaSlicer and contain a printer model comment\n"
                        "(e.g. ; printer_model = XL5).\n"
                        "The file may not work correctly with this application.",
                        "Unsupported Printer",
                        wx.OK | wx.ICON_WARNING)
                    dlg.ShowModal()
                    dlg.Destroy()
                    exit()
            
                # Initialize variables dictionary
                self.gcode_variables = {}
                
                # Parse G-code variables
                with open(path, 'r') as f:
                    for line in f:
                        if line.startswith(';'):  # Comment line
                            # Remove semicolon and whitespace
                            comment = line[1:].strip()
                            if '=' in comment:
                                # Split on first equals sign
                                key, value = comment.split('=', 1)
                                # Clean up key and value
                                key = key.strip()
                                value = value.strip()
                                self.gcode_variables[key] = value
        
                # Load the G-code file into the viewer
                gcode = GCode([line for line in open(path)])
                self.gcview.addfile(gcode)
                
                # Update UI elements
                self.update_layer_slider()
                self.update_move_slider()
                
                # Enable UI elements
                self.layer_slider.Enable()
                self.movement_slider.Enable()
                
                # Update conductive tool choices
                print("Updating tool choices...")
                tools = self.get_gcode_tools()
                print(f"Found tools: {tools}")
                
                # Check if there's only one tool
                if len(tools) == 1:
                    dlg = wx.MessageDialog(self,
                        "Only one tool detected in the G-code file.\n"
                        "This application requires multiple tools to function properly.",
                        "Single Tool Error",
                        wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    dlg.Destroy()
                    # Close the application
                    self.Close()
                    return
                
                self.conductive_choice.Clear()
                self.conductive_choice.Append("None")  # Add None option
                for tool in tools:
                    self.conductive_choice.Append(f"T{tool}")
                # Select last tool if available, otherwise select None
                if len(tools) > 0:
                    self.conductive_choice.SetSelection(len(tools))  # Select last tool
                else:
                    self.conductive_choice.SetSelection(0)  # Select None if no tools
                print("Tool choices updated")
                
                print(f"Loaded G-code file: {path}")
                if is_compatible:
                    print(f"Detected compatible printer: {printer_name}")
        
            except Exception as e:
                print(f"Error loading G-code: {str(e)}")
                import traceback
                traceback.print_exc()
        
            # Wait for model to be initialized before updating colors
            self.update_colors_after_load()

        def get_gcode_tools(self):
            """Extract all unique tool numbers from the loaded G-code"""
            if not hasattr(self.gcview, 'model') or not self.gcview.model:
                return []
                
            tools = set()
            gcode = self.gcview.model.gcode
            
            # Look through all lines for tool changes
            for layer in gcode.all_layers:
                for line in layer:
                    if hasattr(line, 'command') and line.command.startswith('T'):
                        # Extract tool number from T command
                        try:
                            tool_num = int(line.command[1:])
                            tools.add(tool_num)
                        except ValueError:
                            continue
            
            return sorted(list(tools))

        def get_active_tool_at_layer_start(self, layer_num):
            if layer_num < 0 or layer_num >= len(self.gcview.model.gcode.all_layers):
                return None
            
            first_line = self.gcview.model.gcode.all_layers[layer_num][0]
            
            return getattr(first_line, 'current_tool', None)


        def on_movement_change(self, event):
            """Handle movement slider changes"""

            try:
                movement = self.movement_slider.GetValue()
                current_layer = self.layer_slider.GetValue()
                
                if hasattr(self.gcview.model, 'gcode'):
                    # Get all move commands in current layer
                    gcode = self.gcview.model.gcode
                    if current_layer >= len(gcode.all_layers):
                        print(f"Invalid layer index: {current_layer}")
                        return
                        
                    layer = gcode.all_layers[current_layer]
                    if not layer:
                        print("Empty layer")
                        return
                        
                    # Create list of indices where the line is a move command
                    move_indices = []
                    for i, line in enumerate(layer):
                        # Make sure we have a valid GLine object
                        if isinstance(line, (int, str)):
                            continue
                        if not hasattr(line, 'command'):
                            continue
                        # Check if it's a move command (G0, G1, G2, G3)
                        if hasattr(line, 'is_move') and line.is_move:
                            move_indices.append(i)
                    
                    if not move_indices:
                        print("No move commands found in layer")
                        return
                        
                    if movement < len(move_indices):
                        # Get the index of the selected move
                        move = layer[move_indices[movement]]
                        
                        # Update visualization
                        if hasattr(self.gcview, 'set_current_gline'):
                            self.gcview.set_current_gline(move)
                            self.gcview.Refresh()
                    else:
                        print(f"Invalid movement index: {movement} (max: {len(move_indices)-1})")
                    
            except Exception as e:
                print(f"Error changing movement: {str(e)}")
                import traceback
                traceback.print_exc()

        def get_layer_height(self, layer):
            """Get the Z height for a given layer"""
            try:
                if hasattr(self.gcview, 'model') and self.gcview.model:
                    return self.gcview.model.gcode.layer_stops[layer]
                return 0
            except Exception as e:
                print(f"Error getting layer height: {str(e)}")
                return 0

        def on_move_marker(self, event):
            """Move marker to a new position"""
            self.marker.position[0] += 10  # Move 10mm in X

        def on_conductive_tool_select(self, event):
            """Handle conductive tool selection"""
            selection = self.conductive_choice.GetSelection()
            tool = self.conductive_choice.GetString(selection)
            print(f"Selected conductive tool: {tool}")
            
            # Get the model instance
            if hasattr(self.gcview, 'model') and self.gcview.model:
                # Reset all tool colors to default
                self.gcview.model.color_tool0 = (1.0, 0.0, 0.0, 0.6)  # Red
                self.gcview.model.color_tool1 = (0.67, 0.05, 0.9, 0.6)  # Purple
                self.gcview.model.color_tool2 = (1.0, 0.8, 0., 0.6)  # Yellow
                self.gcview.model.color_tool3 = (1.0, 0., 0.62, 0.6)  # Pink
                self.gcview.model.color_tool4 = (0., 1.0, 0.58, 0.6)  # Green
                
                # If a tool is selected (not None), set it to very dark grey
                if tool != "None":
                    tool_num = int(tool[1:])  # Extract number from "T1" etc
                    setattr(self.gcview.model, f'color_tool{tool_num}', (0.15, 0.15, 0.15, 1.0))  # Very dark grey
        
                # Force redraw
                self.gcview.model.update_colors()
                self.gcview.widget.Refresh()

        def on_printegrate(self, event):
            """Handle Printegrate button click - print drill hole coordinates"""
            print("\n=== Drill Hole Coordinates ===")

            # Check if a marker file is loaded
            if not self.drl_path:
                dlg = wx.MessageDialog(self,
                    "No marker file loaded.\n"
                    "Please load a .drl file before attempting to printegrate.",
                    "No Marker File",
                    wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
                return

            # Make sure a G-code file is loaded
            if not hasattr(self.gcview, 'model') or not self.gcview.model:
                print("No G-code loaded - load a G-code file first")
                return
            
            # Make sure a drill file is loaded
            if not hasattr(self, 'marker') or not self.marker:
                print("No marker available - load a drill file first")
                return
            
                
            # Print selected conductive tool
            conductive_tool = self.conductive_choice.GetString(self.conductive_choice.GetSelection())
            conductive_tool = int(conductive_tool[1:])  # Make it an int
           
            # Get the Layer index of the markers
            layer_idx = self.marker.last_layer_number

            # Get the coordinates of the drill points to do printegration with
            holes = []
            current_tool = self.marker.current_tool
            if current_tool and current_tool in self.marker.drill_points:
                data = self.marker.drill_points[current_tool]
                for point in data['points']:
                    # Apply any transformations from the marker's position
                    x = point[0] + self.marker.position[0]
                    y = point[1] + self.marker.position[1]
                    holes.append([x, y])
                    

            
            active_tool = self.get_active_tool_at_layer_start(layer_idx)
            if active_tool is not None:
                print(f"  Active Tool: T{active_tool}")
            else:
                print("  No active tool found")
            
            print("\n=== End Drill Hole Coordinates ===")

            ## If the active tool is not the same as the conductive tool, then we are going to need to change to
            ## the tool and perform a wipe

            gcode_to = ""
            gcode_from = ""

            if active_tool is not None and active_tool != conductive_tool:
                
                # Find if the gcode contains a wipe tower
                ## Search g-code for comment line '; wipe_tower = 1'
                gcode = self.gcview.model.gcode
                # Loop though all lines of gcode
                for idx, line in enumerate(gcode.lines):
                    if hasattr(line, 'raw') and '; wipe_tower = 1' in line.raw:	
                        print("Found wipe tower")
                        break
                    if idx == len(gcode.lines) - 1:
                        print("No wipe tower found")
                        exit()
            
                ## Now we know the g-code contains a wipe tower, so we need to work ou tthe parameters needed to populate
                ## the wipe tower g-code snipet

                ### Things we need to work out
                ### 1. The current layer height
                ### 2. The current tool number
                ### 3. The current tool temperature
                ### 4. The conductive tool temperature
                ### 5. The location of the wipe tower (x, y)
                ### 7. The retract length before a toolchange

                ## Current layer height is easy we can just take the marker's current layer height
                current_layer_height = self.marker.get_current_layer_height()

                ## Current tool number is easy we can use the model's active_tool
                current_tool_number = active_tool

                ## Tool temps can be parsed from g-code with the form "; temperature = 205,205,205,230,245" 

                # Loop though all lines of gcode
                for line in gcode.lines:
                    if hasattr(line, 'raw') and '; temperature = ' in line.raw:
                        tool_temps = [int(temp.strip()) for temp in line.raw.split('=')[1].split(',')]
                        break

                # Convert tool numbers to integers for indexing
                conductive_tool_idx = int(conductive_tool)
                current_tool_idx = int(current_tool_number)

                to_temp = tool_temps[conductive_tool_idx]
                from_temp = tool_temps[current_tool_idx]

                # Lets find the coordinates of the wipe tower
                # We're looking for a comment line like this:
                #; wipe_tower_x = 190.747
                #; wipe_tower_y = 296.1

                wipe_tower_x = None
                wipe_tower_y = None

                # Loop though all lines of gcode
                for line in gcode.lines:
                    if hasattr(line, 'raw') and '; wipe_tower_x = ' in line.raw:
                        wipe_tower_x = float(line.raw.split('=')[1].strip())
                    if hasattr(line, 'raw') and '; wipe_tower_y = ' in line.raw:
                        wipe_tower_y = float(line.raw.split('=')[1].strip())

                # Print everything nicely
                print(f"Current Layer Height: {current_layer_height}")
                print(f"Current Tool Number: {current_tool_number}")
                # print(f"Conductive Tool Temperature: {self.gcview.model.conductive_tool_temp}")
                print(f"Wipe Tower X: {wipe_tower_x}")
                print(f"Wipe Tower Y: {wipe_tower_y}")

                ## Fill g-code snippets
                # Read the template file
                with open('toolchange.gcode', 'r') as f:
                    template = f.read()

                # Calculate wipe coordinates (offset from wipe tower center)
                wipe_x1 = wipe_tower_x - 0.25  # 0.25mm left of wipe tower
                wipe_x2 = wipe_tower_x - 1.75  # 1.75mm left of wipe tower
                wipe_y1 = wipe_tower_y + 0.25  # 0.25mm above wipe tower
                wipe_y2 = wipe_tower_y - 0.75  # 0.75mm below wipe tower

                # Set retract amount
                retract_amount = 20  # mm

                # Populate the template for changing TO the conductive tool
                gcode_to = template.replace('[LAYER_HEIGHT]', str(current_layer_height))
                gcode_to = gcode_to.replace('[RETRACT]', str(retract_amount))
                gcode_to = gcode_to.replace('[FROM_TOOL]', str(current_tool_number))
                gcode_to = gcode_to.replace('[TO_TOOL]', str(conductive_tool))
                gcode_to = gcode_to.replace('[TO_TOOL_TEMP]', str(to_temp))
                gcode_to = gcode_to.replace('[WIPE_X1]', str(wipe_x1))
                gcode_to = gcode_to.replace('[WIPE_X2]', str(wipe_x2))
                gcode_to = gcode_to.replace('[WIPE_Y1]', str(wipe_y1))
                gcode_to = gcode_to.replace('[WIPE_Y2]', str(wipe_y2))
                gcode_to = gcode_to.replace('[DE_RETRACT]', str(retract_amount))

                # Populate the template for changing FROM the conductive tool back to the original tool
                gcode_from = template.replace('[LAYER_HEIGHT]', str(current_layer_height))
                gcode_from = gcode_from.replace('[RETRACT]', str(retract_amount))
                gcode_from = gcode_from.replace('[FROM_TOOL]', str(conductive_tool))
                gcode_from = gcode_from.replace('[TO_TOOL]', str(current_tool_number))
                gcode_from = gcode_from.replace('[TO_TOOL_TEMP]', str(from_temp))
                gcode_from = gcode_from.replace('[WIPE_X1]', str(wipe_x1))
                gcode_from = gcode_from.replace('[WIPE_X2]', str(wipe_x2))
                gcode_from = gcode_from.replace('[WIPE_Y1]', str(wipe_y1))
                gcode_from = gcode_from.replace('[WIPE_Y2]', str(wipe_y2))
                gcode_from = gcode_from.replace('[DE_RETRACT]', str(retract_amount))

                # Print the generated G-code for verification
                print("\nGenerated G-code for changing TO conductive tool:")
                print(gcode_to)
                print("\nGenerated G-code for changing FROM conductive tool:")
                print(gcode_from)

            # Generate G-code for drilling holes
            print("\nGenerating G-code for holes...")
            # Get the first line of the current layer to get the starting position
            layer = self.gcview.model.gcode.all_layers[layer_idx]
            
            # Find the first move command in the layer to get the starting position
            first_move = None
            for line in layer:
                if hasattr(line, 'is_move') and line.is_move:
                    first_move = line
                    break
            
            if first_move is None:
                print("Error: No move commands found in layer")
                return
            
            layer_start_pos = [first_move.current_x, first_move.current_y, first_move.current_z]
            print(f"Layer start position: {layer_start_pos}")

            hole_gcode = self.generate_gcode_for_holes(holes, layer_start_pos)
            print("\nGenerated G-code for holes:")
            
            combined_gcode = [line for line in gcode_to.split('\n')]
            combined_gcode.extend(["M601 \n"])
            combined_gcode.extend(hole_gcode)
            combined_gcode.extend([line for line in gcode_from.split('\n')])


            ## Prepend the gcode to the model
            self.gcview.model.gcode.prepend_to_layer(combined_gcode, layer_idx)
            
            # Get all gcode lines
            gcode_lines = [line.raw + "\n" for line in self.gcview.model.gcode.all_layers[0]]
            for layer in self.gcview.model.gcode.all_layers[1:]:
                gcode_lines.extend(line.raw + "\n" for line in layer)
            
            # Clear and reload visualization
            self.gcview.clear()
            self.gcview.addfile(GCode(gcode_lines))
            self.on_layer_change(None)
            
            # Reapply colors after reloading
            self.update_colors_after_load()

        def generate_gcode_for_holes(self, holes, last_pos, extrusion_amount=0.48, retraction_amount=7.5, print_retraction=2.5):
            """Generate G-code commands for drilling holes
            
            Args:
                holes: List of [x, y] coordinates for holes
                last_pos: List of [x, y, z] coordinates for starting position
                extrusion_amount: Amount to extrude for each hole
                retraction_amount: Amount to retract between holes
                print_retraction: Amount to retract before returning to print
            """
            x_start, y_start, z_start = last_pos
            gcode = []
            move_above_height = 5 + z_start  # Move 5mm above the last Z-height

            z_down = round(z_start-0.05, 4)

            # Set the temp a bit higher
            gcode.append(f"M104 S240")
            # Retract a bit
            gcode.append(f"G1 E-{retraction_amount} F4200")
            # Move up a bit
            gcode.append(f"G0 Z{move_above_height} F4200")
            
            for x, y in holes:
                x = round(x, 4)
                y = round(y, 4)
                # Move above the hole
                gcode.append(f"G0 X{x} Y{y} Z{move_above_height} F4200")
                # Lower down to the point
                gcode.append(f"G0 Z{z_down} F4200")
                # Un-retract
                gcode.append(f"G1 E{retraction_amount} F4200")
                # Extrude some plastic
                gcode.append(f"G1 E{extrusion_amount} F4200")
                # Wait for 1 second
                gcode.append(f"G4 P1000")
                # Retract a bit
                gcode.append(f"G1 E-{retraction_amount} F4200")
                # Wait for 1 second
                gcode.append(f"G4 P1000")
                # Move 1mm to the right
                gcode.append(f"G0 X{x+1} Y{y} F4200")
                # Move up back to 5mm above before going to the next hole
                gcode.append(f"G0 Z{move_above_height} F4200")
            
            # Move back to the last x, y position
            gcode.append(f"G0 X{x_start} Y{y_start} F4200")
            # Move back to the last z position
            gcode.append(f"G0 Z{z_start} F4200")

            # Set the temp back to 220
            gcode.append(f"M104 S220")
            gcode.append(f"G1 E{retraction_amount-print_retraction} F4200")

            return gcode

        def on_layer_change(self, event):
            """Handle layer slider changes"""
            try:
                layer = self.layer_slider.GetValue()
                if hasattr(self.gcview, 'setlayer'):
                    self.gcview.setlayer(layer)
                    
                    # Update movement slider for new layer
                    if hasattr(self.gcview.model, 'gcode'):
                        current_layer = self.gcview.model.gcode.all_layers[layer]
                        moves_count = len([line for line in current_layer if hasattr(line, 'is_move') and line.is_move])
                        self.movement_slider.SetMax(moves_count - 1)
                        self.movement_slider.SetValue(0)
                    
                    # Force refresh after layer change
                    self.gcview.Refresh()
                else:
                    print("No model loaded")
            except Exception as e:
                print(f"Error changing layer: {str(e)}")

        def check_printer_compatibility(self, gcode_path):
            """Check if the loaded G-code is compatible with supported printers"""
            # List of supported printers and their identifying markers
            SUPPORTED_PRINTERS = {
                'Prusa XL': {
                    'model_markers': ['printer_model = XL', 'printer_model = XL2', 'printer_model = XL5'],
                    'content_markers': ['generated by PrusaSlicer']
                }
            }
            
            try:
                with open(gcode_path, 'r') as file:
                    content = file.read()
                    
                    # Check each supported printer
                    for printer, markers in SUPPORTED_PRINTERS.items():
                        # Check printer model markers
                        model_match = any(marker in content for marker in markers['model_markers'])
                        # Check content markers
                        content_match = any(marker in content for marker in markers['content_markers'])
                        
                        if model_match and content_match:
                            return True, printer
                        
                return False, None
            except Exception as e:
                print(f"Error checking printer compatibility: {str(e)}")
                return False, None

        def update_layer_slider(self):
            """Update the layer slider based on loaded G-code"""
            if hasattr(self.gcview, 'model') and self.gcview.model and hasattr(self.gcview.model, 'max_layers'):
                max_layers = self.gcview.model.max_layers
                if max_layers > 0:
                    self.layer_slider.SetMax(max_layers)
                    self.layer_slider.SetValue(0)
                    print(f"Setting layer slider range: 0-{max_layers}")

        def update_move_slider(self):
            """Update the movement slider based on current layer"""
            if hasattr(self.gcview.model, 'gcode'):
                current_layer = self.gcview.model.gcode.all_layers[0]
                moves_count = len([line for line in current_layer if hasattr(line, 'is_move') and line.is_move])
                self.movement_slider.SetMax(moves_count - 1)
                self.movement_slider.SetValue(0)

        def on_click(self, event):
            """Handle click events from gcview"""
            # For now, just pass the event
            pass

        def get_gcode_variable(self, key, default=None):
            """Get a G-code variable from the parsed dictionary"""
            return self.gcode_variables.get(key, default)

        def on_save(self, event):
            """Save the current G-code back to the original file"""
            if not self.gcode_path:
                wx.MessageBox("No G-code file loaded to save", "Error", wx.OK | wx.ICON_ERROR)
                return
            
            try:
                # Get the current gcode from the model
                if not self.gcview.model or not self.gcview.model.gcode:
                    wx.MessageBox("No G-code model to save", "Error", wx.OK | wx.ICON_ERROR)
                    return
                
                # Get raw gcode lines from all layers
                gcode_lines = [line.raw + "\n" for line in self.gcview.model.gcode.all_layers[0]]
                for layer in self.gcview.model.gcode.all_layers[1:]:
                    gcode_lines.extend(line.raw + "\n" for line in layer)
                
                # Save the gcode to the original file
                with open(self.gcode_path, 'w') as f:
                    f.writelines(gcode_lines)
            
                # wx.MessageBox("G-code saved successfully", "Success", wx.OK | wx.ICON_INFORMATION)
                # Close the application after successful save
                self.Close(True)
            
            except Exception as e:
                wx.MessageBox(f"Error saving G-code: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

        def update_colors_after_load(self):
            """Update colors after model is loaded"""
            def update_colors():
                if hasattr(self.gcview.model, 'vertex_color_buffer'):
                    self.gcview.widget.Refresh()
                    self.on_conductive_tool_select(None)
                else:
                    wx.CallLater(100, update_colors)
            wx.CallLater(100, update_colors)

        def on_reset(self, event):
            """Handle Reset button click - reload original G-code"""
            if self.gcode_path and os.path.exists(self.gcode_path):
                self.load_gcode(self.gcode_path)
            else:
                wx.MessageBox("No G-code file loaded to reset to.", "Error", wx.OK | wx.ICON_ERROR)
