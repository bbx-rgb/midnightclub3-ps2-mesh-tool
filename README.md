This project is a Python-based tool for reading, processing, visualizing, and exporting mesh data from binary files—commonly used in modding projects (such as for PlayStation 2 games). The tool extracts mesh information (vertices, UV mapping, and flags) from the binary file, generates smooth-shaded 3D meshes, and provides several export options in OBJ format.

Features
Binary File Processing:
Reads a binary file and extracts a set of pointers, groups, and mesh entries based on a custom file format.

Mesh Data Extraction:
Parses the binary data to extract:

Vertices: Two patterns are searched for:
Pattern 1: EE 00 XX 69
Pattern 2: 1B 02 XX 69
Each occurrence provides the number of vertices followed by 3 signed 16-bit integers (x, y, z).
UV Mapping:
Two patterns are used:
Pattern 1: C4 00 XX 65 or C4 00 XX 66
Pattern 2: F1 01 XX 65 or F1 01 XX 66
Each occurrence specifies the number of UVs followed by 2 signed 16-bit integers per UV coordinate.
Face Flags (FFlags_idx):
Two patterns are searched for:
Pattern 1: 9A 00 XX 6A
Pattern 2: C7 01 XX 6A
These indicate how many face flags exist and whether each face should be active.
Face Generation:
Faces are generated from consecutive vertices (triangle strip style).
For example:

Face 1: vertices 0, 1, 2
Face 2: vertices 1, 2, 3
... and so on.
Smooth Shading:
Normals are computed for smooth shading to improve the 3D visualization.

Color Differentiation:
Each mesh (or group) is assigned a different color when visualized, using a colormap (default: "tab20").

Export Options:
The tool provides multiple export options:

Global OBJ (No Scale):
Combine all meshes into a single OBJ file.
Individual OBJ Files (No Scale):
Export each mesh group as an individual OBJ file in a dedicated folder.
No OBJ Export:
Do not generate any OBJ file.
Visualization Only:
Visualize the meshes in 3D without exporting.
Global OBJ with Scaled Vertices and UVs:
All vertex coordinates and UV mappings are divided by 256 before export.
Individual OBJ Files with Scaled Data:
Export each group individually with vertices and UVs divided by 256.

Code Structure
File Selection:
escolher_arquivo() lists files and allows selection.

Binary Processing:
processar_arquivo() reads the file header, extracts the offset, pointers, and lists (PCK_INDEX, NAMELIST).

Group and Mesh Extraction:
processar_grupo(), processar_meshgroup(), and processar_mesh_entries() extract the data necessary to locate and define each mesh.

Mesh Data Parsing:
processar_mesh_data() scans each mesh for vertices, UVs, and flags using regular expressions.

Face Generation:
gerar_faces() creates triangular faces from a list of vertices while checking face flags.

Scaling Functions:
scale_vertices() and scale_uvs() divide vertex and UV values by 256 when required.

Visualization and Export Functions:
visualizar_global() displays the combined mesh with smooth shading and group colors, and exports it if a filename is provided.
exportar_individualmente() exports each mesh group separately to a folder.

Main Function:
main() orchestrates the file selection, processing, and user menu for export/visualization options.

