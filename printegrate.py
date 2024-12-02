import sys
import wx
import app as printegrate

def main(gcode_path):
    app = printegrate.PrintegrateApp(gcode_path=gcode_path)
    try:
        app.MainLoop()
    except KeyboardInterrupt:
        pass
    del app

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python printegrate.py <path_to_gcode_file>")
        sys.exit(1)
    main(sys.argv[1])

