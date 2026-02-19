import math
from scipy.optimize import fsolve

def power_required(v, cda, crr, mass=85, air_density=1.225, gravity=9.81):
    """Calculate power (W) for given speed (m/s), CdA, and Crr."""
    aerodynamic_power = 0.5 * air_density * cda * v**3
    rolling_power = mass * gravity * crr * v
    return (aerodynamic_power + rolling_power) * 1.03

def speed_from_power(power, cda, crr, mass=85, air_density=1.225, gravity=9.81):
    """Calculate speed (m/s) from power (W), CdA, and Crr by solving cubic."""
    a = 0.5 * air_density * cda
    b = mass * gravity * crr

    # Equation: a*v^3 + b*v - power = 0
    def func(v):
        return a * v**3 + b * v - (power * 0.97)

    # Initial guess
    v_initial = 10
    v_solution, = fsolve(func, v_initial)
    return v_solution if v_solution > 0 else None

def cda_from_power_speed(power, speed, crr, mass=85, air_density=1.225, gravity=9.81):
    """Calculate CdA from power (W), speed (m/s), and Crr."""
    rolling_power = mass * gravity * crr * speed
    aerodynamic_power = (power * 0.97) - rolling_power
    if aerodynamic_power <= 0:
        return None  # No valid CdA if power too low
    return (2 * aerodynamic_power) / (air_density * speed**3)

def main():
    print("Calculate: (1) CdA, (2) Power, (3) Speed")
    choice = input("Enter choice (1/2/3): ").strip()

    #mass = 85  # kg
    mass = 86  # kg
    gravity = 9.81  # m/s^2
    air_density = 1.225  # kg/m^3

    if choice == '1':
        power = float(input("Enter power (W): "))
        speed_kmh = float(input("Enter speed (km/h): "))
        crr = float(input("Enter rolling resistance coefficient (e.g., 0.0032): "))
        speed = speed_kmh / 3.6
        cda = cda_from_power_speed(power, speed, crr, mass, air_density, gravity)
        if cda is None:
            print("No valid CdA can be calculated with the given inputs.")
        else:
            print(f"Calculated CdA: {cda:.4f} m^2")

    elif choice == '2':
        speed_kmh = float(input("Enter speed (km/h): "))
        cda = float(input("Enter CdA (m^2): "))
        crr = float(input("Enter rolling resistance coefficient (e.g., 0.0032): "))
        speed = speed_kmh / 3.6
        power = power_required(speed, cda, crr, mass, air_density, gravity)
        print(f"Power required: {power:.1f} W")

    elif choice == '3':
        power = float(input("Enter power (W): "))
        cda = float(input("Enter CdA (m^2): "))
        crr = float(input("Enter rolling resistance coefficient (e.g., 0.0032): "))
        speed = speed_from_power(power, cda, crr, mass, air_density, gravity)
        if speed is None:
            print("No valid speed found for given inputs.")
        else:
            speed_kmh = speed * 3.6
            print(f"Calculated speed: {speed_kmh:.1f} km/h")

    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
