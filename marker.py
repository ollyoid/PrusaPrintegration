from pyglet.gl import glPushMatrix, glPopMatrix, glTranslatef, \
    glBegin, glEnd, GL_LINES, glColor4f, glVertex3f, \
    glEnable, glDisable, GL_LINE_SMOOTH, glLineWidth, \
    glGetDoublev, GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX, \
    GLdouble, glGetIntegerv, GL_VIEWPORT, GLint
import wx
import numpy as np
import math

class MarkerActor:
    def __init__(self, parent_viewer=None):
        self.color = (0.0, 0.0, 0.0, 1.0)  # Black (R,G,B,A)
        self.position = [0, 0, 0]
        self.size = 5
        self.loaded = True
        self.initialized = False
        self.parent_viewer = parent_viewer
        self.is_dragging = False
        self.drag_start = None
        self.drill_points = {}  # Dictionary to store drill points by tool
        self.current_tool = None
        self.center_offset = [0, 0, 0]  # Offset from center to drill points
        self.last_layer_number = 0
        
        # Get build platform dimensions and offsets
        if self.parent_viewer:
            dims = self.parent_viewer.build_dimensions
            self.width = dims[0]
            self.depth = dims[1]
            self.height = dims[2]
            self.xoffset = dims[3]
            self.yoffset = dims[4]
            self.zoffset = dims[5]
            
            # Initialize marker at center of platform
            self.position = [self.width/2 + self.xoffset, 
                           self.depth/2 + self.yoffset, 
                           self.get_current_layer_height()]
            
            # Bind mouse events
            canvas = self.parent_viewer.glpanel.canvas
            canvas.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
            canvas.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
            canvas.Bind(wx.EVT_MOTION, self.on_mouse_move)

    def calculate_center(self):
        """Calculate the center point of current tool's drill points"""
        if not self.drill_points or not self.current_tool:
            return self.position

        # Get only the current tool's points
        points = self.drill_points[self.current_tool]['points']
        if not points:
            return self.position

        # Find bounding box
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Calculate center of bounding box
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        z = self.get_current_layer_height()

        return [center_x, center_y, z]

    def add_drill_points(self, tool_name, points, tool_size):
        """Add drill points for a specific tool"""
        # Calculate bounding box center of new points
        if points:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            
            # Store points as offsets from their center
            relative_points = []
            for point in points:
                relative_points.append([
                    point[0] - center_x,  # Store as offset from center
                    point[1] - center_y,
                    0  # Z offset is always relative to current layer
                ])
            points = relative_points

        self.drill_points[tool_name] = {
            'points': points,
            'size': tool_size
        }
        if not self.current_tool:
            self.current_tool = tool_name

        if self.parent_viewer:
            self.parent_viewer.Refresh()

    def clear_drill_points(self):
        """Clear all drill points and reset current tool"""
        self.drill_points = {}
        self.current_tool = None
        if self.parent_viewer:
            self.parent_viewer.Refresh()

    def display(self, mode_2d=False):
        """Draw the marker(s)"""
        if not self.initialized:
            self.init()

        # Enable line smoothing for better appearance
        glEnable(GL_LINE_SMOOTH)
        glLineWidth(2.0)  # Thicker lines

        # Draw center marker in green
        glPushMatrix()
        glTranslatef(*self.position)
        glColor4f(0.0, 1.0, 0.0, 1.0)  # Green
        
        # Draw cross
        glBegin(GL_LINES)
        # Horizontal line
        glVertex3f(-self.size, 0, 0)
        glVertex3f(self.size, 0, 0)
        # Vertical line
        glVertex3f(0, -self.size, 0)
        glVertex3f(0, self.size, 0)
        # Vertical line in Z
        glVertex3f(0, 0, -self.size)
        glVertex3f(0, 0, self.size)
        glEnd()
        glPopMatrix()

        # Only draw points for current tool
        if self.current_tool and self.current_tool in self.drill_points:
            data = self.drill_points[self.current_tool]
            points = data['points']
            size = data['size'] * 2.5  # Make crosses 2.5x the tool size
            
            glColor4f(0.0, 0.0, 0.0, 1.0)  # Black for drill points
            
            for point in points:
                glPushMatrix()
                # Calculate absolute position based on marker position
                abs_pos = [
                    self.position[0] + point[0],  # Add offset to marker position
                    self.position[1] + point[1],
                    self.position[2]
                ]
                glTranslatef(*abs_pos)
                
                # Draw cross
                glBegin(GL_LINES)
                # Horizontal line
                glVertex3f(-size/4, 0, 0)
                glVertex3f(size/4, 0, 0)
                # Vertical line
                glVertex3f(0, -size/4, 0)
                glVertex3f(0, size/4, 0)
                glEnd()
                
                glPopMatrix()

        glDisable(GL_LINE_SMOOTH)
        glLineWidth(1.0)

        glPushMatrix()
        glTranslatef(*self.position)
        glColor4f(*self.color)

        
        glPopMatrix()

    def get_3d_pos(self, x, y):
        """Convert screen coordinates to 3D world coordinates"""
        if not self.parent_viewer:
            return None
            
        glpanel = self.parent_viewer.glpanel
        pos = glpanel.mouse_to_plane(x, y, plane_normal=(0, 0, 1), plane_offset=-self.position[2], local_transform=True)
        
        if pos is None:
            return None
            
        # Update z position to current layer height
        pos = list(pos)
        pos[2] = self.get_current_layer_height()
        return pos

    def on_mouse_down(self, event):
        """Handle mouse button press"""
        if not self.parent_viewer:
            event.Skip()
            return

        # Get mouse position in world coordinates
        x, y = event.GetPosition()
        pos = self.get_3d_pos(x, y)
        if not pos:
            event.Skip()
            return

        # Check if click is near marker center
        dx = pos[0] - self.position[0]
        dy = pos[1] - self.position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < self.size * 2:  # Click within marker size
            self.is_dragging = True
            self.drag_start = pos
            event.Skip(False)  # Don't propagate event if we're handling it
        else:
            event.Skip()

    def on_mouse_up(self, event):
        """Handle mouse button release"""
        self.is_dragging = False
        event.Skip()

    def on_mouse_move(self, event):
        """Handle mouse movement"""
        if self.is_dragging and self.parent_viewer:
            x, y = event.GetPosition()
            pos = self.get_3d_pos(x, y)
            if not pos:
                event.Skip()
                return

            # Calculate movement delta
            dx = pos[0] - self.drag_start[0]
            dy = pos[1] - self.drag_start[1]
            
            # Update marker position
            self.position[0] += dx
            self.position[1] += dy
            self.position[2] = self.get_current_layer_height()
            
            self.drag_start = pos
            
            if self.parent_viewer:
                self.parent_viewer.Refresh()
            event.Skip(False)  # Don't propagate event if we're handling it
        else:
            event.Skip()

    def get_current_layer_height(self):
        """Get the z-height of the current layer"""
        if not self.parent_viewer or not self.parent_viewer.model:
            return self.zoffset
            
        current_layer = self.parent_viewer.model.num_layers_to_draw
        if not hasattr(self.parent_viewer.model, 'gcode'):
            return self.zoffset
            
        # Find the z-height of the current layer
        gcode = self.parent_viewer.model.gcode
        self.last_layer_number = current_layer - 1  # Convert to 0-based index
        
        # Find first Z movement in layer
        for line in gcode.all_layers[self.last_layer_number]:
            if hasattr(line, 'current_z') and line.current_z is not None:
                return line.current_z + self.zoffset
                
        return self.zoffset

    def set_current_tool(self, tool_name):
        """Set the current tool for visualization"""
        if tool_name in self.drill_points:
            self.current_tool = tool_name
            if self.parent_viewer:
                self.parent_viewer.Refresh()

    def init(self):
        """Initialize OpenGL state"""
        self.initialized = True