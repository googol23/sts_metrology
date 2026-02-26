import numpy as np
import matplotlib.pyplot as plt

n_markers = [4,4,4,4] # Number of markers on edge of the sensor [top,right,bottom,left]
sensor_w = 6e+6  # Sensor width [um]
sensor_h = 6e+6  # Sensor height [um]
sensor_t = 0.300   # Sensor thinckness [um]
sensor_dimensions = [sensor_w, sensor_h, sensor_t]

dx_max = 0.100 # Maximum simulated offset along x-axis [um]
dy_max = 0.100 # Maximum simulated offset along y-axis [um]
dz_max = 0.100 # Maximum simulated offset along z-axis [um]

def random_offset():
    return np.random.uniform(-dx_max, dx_max), np.random.uniform(-dy_max, dy_max), np.random.uniform(-dz_max, dz_max)

marker_positions = []
for edge,n in enumerate(n_markers):
    # Markers are equally spaces along the edges of the sensor
    # Calculate the marker positions
    for i in range(n):
        if edge == 0: # Top edge
            x = i * sensor_w / (n - 1)
            y = 0
        elif edge == 1: # Right edge
            x = sensor_w
            y = i * sensor_h / (n - 1)
        elif edge == 2: # Bottom edge
            x = sensor_w - i * sensor_w / (n - 1)
            y = sensor_h
        elif edge == 3: # Left edge
            x = 0
            y = sensor_h - i * sensor_h / (n - 1)
        z = 0  # Markers are on the surface of the sensor

        # Apply random offset to each marker position
        dx, dy, dz = random_offset()
        marker_positions.append((x + dx, y + dy, z + dz))

# Draw the markers and connect them with lines in a 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_xlim(0, sensor_w)
ax.set_ylim(0, sensor_h)
ax.set_zlim(0, sensor_t)
for i, (x, y, z) in enumerate(marker_positions):
    ax.scatter(x, y, z, color='b')
    if i > 0:
        x_prev, y_prev, z_prev = marker_positions[i - 1]
        ax.plot([x_prev, x], [y_prev, y], [z_prev, z], color='r')
# Connect the last marker to the first to close the loop
x_first, y_first, z_first = marker_positions[0]
x_last, y_last, z_last = marker_positions[-1]
ax.plot([x_last, x_first], [y_last, y_first], [z_last, z_first], color='r')
# plt.show()


# Calculate the best-fit plane
def fit_plane(points):
    """
    Find the best-fit plane through a set of 3D points using least squares regression.
    Returns the plane equation coefficients [a, b, c, d] where ax + by + cz + d = 0
    """
    points = np.array(points)

    # Calculate centroid
    centroid = np.mean(points, axis=0)

    # Create the design matrix A
    A = np.column_stack([points[:, 0] - centroid[0],
                        points[:, 1] - centroid[1],
                        points[:, 2] - centroid[2]])

    # Singular Value Decomposition
    U, S, Vh = np.linalg.svd(A)

    # The normal vector to the plane is the last row of Vh
    normal = Vh[-1]

    # Calculate d
    d = -np.dot(normal, centroid)

    # Return plane equation coefficients [a, b, c, d]
    return [*normal, d]

# Calculate and display the best-fit plane
plane_coeffs = fit_plane(marker_positions)
print("\nBest-fit plane equation:")
print(f"{plane_coeffs[0]:.6f}x + {plane_coeffs[1]:.6f}y + {plane_coeffs[2]:.6f}z + {plane_coeffs[3]:.6f} = 0")

# Calculate residuals
def calculate_residuals(points, plane_coeffs):
    """
    Calculate the perpendicular distance from each point to the plane
    """
    points = np.array(points)
    a, b, c, d = plane_coeffs
    normal_magnitude = np.sqrt(a**2 + b**2 + c**2)
    distances = np.abs(np.dot(points, [a, b, c]) + d) / normal_magnitude
    return distances

residuals = calculate_residuals(marker_positions, plane_coeffs)
print("\nResiduals statistics:")
print(f"Mean residual: {np.mean(residuals):.6f} μm")
print(f"Max residual: {np.max(residuals):.6f} μm")
print(f"Min residual: {np.min(residuals):.6f} μm")
print(f"RMS residual: {np.sqrt(np.mean(residuals**2)):.6f} μm")

# Plot the best-fit plane along with the markers
x_range = np.linspace(0, sensor_w, 10)
y_range = np.linspace(0, sensor_h, 10)
X, Y = np.meshgrid(x_range, y_range)
Z = (-plane_coeffs[0] * X - plane_coeffs[1] * Y - plane_coeffs[3]) / plane_coeffs[2]

ax.plot_surface(X, Y, Z, alpha=0.2, color='g')
plt.show()


def calculate_transformation(points, plane_coeffs):
    """
    Calculate the rotation and translation that transforms the nominal plane (z=0)
    to the fitted plane.
    
    Returns:
    - R: 3x3 rotation matrix
    - t: 3x1 translation vector
    """
    points = np.array(points)
    
    # Get the normal vector of the fitted plane
    a, b, c, d = plane_coeffs
    plane_normal = np.array([a, b, c])
    plane_normal = plane_normal / np.linalg.norm(plane_normal)  # normalize
    
    # The nominal plane's normal vector (pointing in z direction)
    nominal_normal = np.array([0, 0, 1])
    
    # Calculate the rotation axis and angle
    rotation_axis = np.cross(nominal_normal, plane_normal)
    if np.allclose(rotation_axis, 0):
        R = np.eye(3)  # No rotation needed
    else:
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        cos_angle = np.dot(nominal_normal, plane_normal)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        # Rodriguez rotation formula
        K = np.array([[0, -rotation_axis[2], rotation_axis[1]],
                     [rotation_axis[2], 0, -rotation_axis[0]],
                     [-rotation_axis[1], rotation_axis[0], 0]])
        R = np.eye(3) + np.sin(angle) * K + (1 - cos_angle) * K @ K
    
    # Calculate centroid (translation)
    centroid = np.mean(points, axis=0)
    t = centroid
    
    return R, t

# Calculate the transformation
R, t = calculate_transformation(marker_positions, plane_coeffs)

print("\nTransformation from nominal to fitted plane:")
print("\nRotation matrix:")
print(R)
print("\nTranslation vector (μm):")
print(t)

# Calculate rotation angles in degrees
rx = np.arctan2(R[2,1], R[2,2])
ry = np.arctan2(-R[2,0], np.sqrt(R[2,1]**2 + R[2,2]**2))
rz = np.arctan2(R[1,0], R[0,0])

print("\nRotation angles (degrees):")
print(f"rx (around x-axis): {np.degrees(rx):.6f}°")
print(f"ry (around y-axis): {np.degrees(ry):.6f}°")
print(f"rz (around z-axis): {np.degrees(rz):.6f}°")

plt.savefig("mock_sensor.png", dpi=300)