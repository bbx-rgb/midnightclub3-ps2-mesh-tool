Usage
The main Python file is named midnightclub3-mesh-tool.py. You can run it from your command line:

bash
python midnightclub3-mesh-tool.py
How It Works
File Selection:
The tool lists files in the current directory. Select the file you want to process by entering its number.

Group Selection:
After processing the file, the tool displays a list of groups (from the PCK_INDEX with associated NAMELIST).
Enter the number corresponding to the group you wish to use.

Export/Visualization Options:
You will be presented with six options:

Generate Global OBJ (Unscaled):
Combines all meshes into a single OBJ file without scaling.

Generate Individual OBJ Files (Unscaled):
Exports each mesh group as a separate OBJ file in a folder.

Do Not Generate OBJ:
The tool will not export any OBJ file.

3D Visualization Only:
Only displays the 3D mesh without exporting OBJ.

Generate Global OBJ (Scaled):
Scales all vertices and UVs (dividing by 256) and exports them as a single OBJ file.

Generate Individual OBJ Files (Scaled):
Scales vertices and UVs and exports each mesh group individually to a folder.

Smooth Shading and Colors:
The tool computes smooth shading (calculates vertex normals) for better visualization.
It also applies a colormap (using "tab20") to color-code each mesh group for easier differentiation.

OBJ Export:
The exported OBJ file(s) include the texture coordinates (UVs) and are saved with a name derived from the selected group's name.

