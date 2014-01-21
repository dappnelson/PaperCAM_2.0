from __future__ import print_function # require print to be called as a function for easier forward-compatibility
from __future__ import division # python 2 does "integer division" by default, we want regular division
import numpy as np

# INITIALIZATION

PROFILE_FILE = 'Profile_Curve.eps'
STOS_FILE = 'STOS_Curves.sbp'
PROFILE_INTERPOLATED_FILE = 'Profile_Curve_Interpolation.csv'
STOS_3D_FILE = 'STOS_Curves_3D.sbp'

FIXTURE_SAFE_HEIGHT = 0.5
MATERIAL_SAFE_HEIGHT = 0.25

class Profile2D(object):
    def __init__(self, input_file_name):
        # read profile data from file
        print("processing profile data...")
        data_list = []
        with open(input_file_name, 'r') as f:
            for line in f:
                line = line.strip()
                if line: # filter empty lines
                    if not line.startswith('%') and not line.startswith('stroke'): # filter comments, 'stroke' lines
                        data_list.append([float(x.strip()) for x in line.split()[:2]])

        # ensure values are in ascending order (required by np.interp) and convert to numpy array
        if data_list[0][0] > data_list[-1][0]:
            data_list.reverse()
        data = np.array(data_list) / 25.4 # convert from mm to in
        self.X_data = data[:, 0]
        self.Z_data = data[:, 1]


class CAMSketch2D(object):
    def __init__(self, input_file_name):
        self.header = []
        self.curve = []
        self.footer = []
        # read sketch data from file
        print('processing STOS curves')
        with open(input_file_name, 'r') as f:
            while True:
                line = f.readline()
                if not line.startswith('JZ'):
                    self.header.append(line.strip()) # first lines are header
                else:
                    self.curve.append(line.strip()) # first JZ line marks beginning of curve
                    break
            self.curve.append(f.readline().strip()) # first J2 line immediately follows
            while True:
                line = f.readline()
                self.curve.append(line.strip())
                if line.startswith('J2'):
                    break # second (assumed last) J2 line marks end of curve
            while True:
                line = f.readline()
                if not line:
                    break
                self.footer.append(line.strip()) # rest are footer

class CAMCurve3D(object):
    def __init__(self, profile2D, sketch2D):
        self.header = sketch2D.header
        self.curves = []
        self.footer = sketch2D.footer
        self.Z_max = -np.inf

        curve = sketch2D.curve[:] # copy sketch curve

        # modify M3 commands
        for i, command in enumerate(curve):
            if command.startswith('M3'):
                x, _, _ = get_command_values(command) # '_' is the conventional name for a throwaway variable
                z = np.interp(x, profile2D.X_data, profile2D.Z_data)
                if z > self.Z_max:
                    self.Z_max = z
                curve[i] = change_command_values(command, False, False, z)

        # modify JZ commands
        for i, command in enumerate(curve):
            if command.startswith('JZ'):
                curve[i] = change_command_values(curve[i], self.Z_max + FIXTURE_SAFE_HEIGHT)

        # modify J3 commands
        i = 0
        while True:
            if curve[i].startswith('J3'):
                if curve[i+1].startswith('M3'): # first J3
                    _, _, z = get_command_values(curve[i+1])
                    curve[i] = change_command_values(curve[i], False, False, z + MATERIAL_SAFE_HEIGHT)
                elif curve[i+1].startswith('J3'): # beginning of J3/J3/M3 triplet
                    curve[i] = change_command_values(curve[i], False, False, self.Z_max + FIXTURE_SAFE_HEIGHT)
                    curve[i+1] = change_command_values(curve[i+1], False, False, self.Z_max + FIXTURE_SAFE_HEIGHT)
                    curve.insert(i+2, curve[i+1]) # duplicate second J3 command
                    _, _, z = get_command_values(curve[i+3]) # get Z from next M3 command
                    curve[i+2] = change_command_values(curve[i+2], False, False, z + MATERIAL_SAFE_HEIGHT)
                    i+=3
                else: # final J3
                    curve.pop(i)
                    break
            i+=1

        # store curve
        self.curves.append(curve)

def get_command_values(command):
    return tuple([float(val.strip()) for val in command.strip().split(',')[1:]])

def change_command_values(command, *args):
    tokens = command.strip().split(',')
    name = tokens.pop(0)
    values = [float(x) for x in tokens]
    for i, val in enumerate(args):
        if args[i] is not False:
            values[i] = args[i]
    return name + ',' + ','.join(['%.6f' % x for x in values]) # 6 decimal places

if __name__ == '__main__':
    profile = Profile2D(PROFILE_FILE)
    sketch = CAMSketch2D(STOS_FILE)
    curve3D = CAMCurve3D(profile, sketch)

    # write output
    with open(STOS_3D_FILE, 'w') as f:
        for line in curve3D.header:
            f.write(line + '\n')
        for line in curve3D.curves[0]:
            f.write(line + '\n')
        for line in curve3D.footer:
            f.write(line + '\n')

