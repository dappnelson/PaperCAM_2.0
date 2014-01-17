from __future__ import print_function
import numpy as np

PROFILE_FILE = 'Profile_Curve.eps'
STOS_FILE = 'STOS_Curves.sbp'
PROFILE_INTERPOLATED_FILE = 'Profile_Curve_Interpolation.csv'
STOS_3D_FILE = 'STOS_Curves_3D.sbp'

FIXTURE_SAFE_HEIGHT = 0.5
MATERIAL_SAFE_HEIGHT = 0.25

profile_list = []

# read profile data from file
print("processing profile data...")
with open(PROFILE_FILE, 'r') as f:
    for line in f:
        line = line.strip()
        if line: # filter empty lines
            if not line.startswith('%') and not line.startswith('stroke'): # filter comments, 'stroke' lines
                profile_list.append([float(x.strip()) for x in line.split()[:2]])

# ensure values are in ascending order (required by np.interp)
if profile_list[0][0] > profile_list[-1][0]:
    profile_list.reverse()

# convert to numpy array
profile_array = np.array(profile_list)
profile_array /= 25.4

# load STOS file and update M3 Z values based on profile
max_M3 = -np.inf
STOS_3D_file_lines = []

with open(STOS_FILE, 'r') as f:
    for line in f:
        if line.startswith('M3'):
            x, y = [float(val.strip()) for val in line.strip().split(',')[1:3]]
            z = np.interp(x, profile_array[:, 0], profile_array[:, 1])
            if z > max_M3:
                max_M3 = z
            STOS_3D_file_lines.append('M3,%.6f,%.6f,%.6f' % (x, y, z))
        else:
            STOS_3D_file_lines.append(line.strip())

# adjust JZ commands
for i in range(len(STOS_3D_file_lines)):
    if STOS_3D_file_lines[i].startswith('JZ'):
        STOS_3D_file_lines[i] = 'JZ,' + str(max_M3 + FIXTURE_SAFE_HEIGHT)

with open(STOS_3D_FILE, 'w') as f:
    for line in STOS_3D_file_lines:
        f.write(line + '\n')

