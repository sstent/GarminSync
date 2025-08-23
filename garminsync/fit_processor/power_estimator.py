import numpy as np

class PowerEstimator:
    def __init__(self):
        self.bike_weight_kg = 10.0  # 22 lbs
        self.rider_weight_kg = 75.0  # Default assumption
        self.drag_coefficient = 0.88  # Road bike
        self.frontal_area_m2 = 0.4  # Typical road cycling position
        self.rolling_resistance = 0.004  # Road tires
        self.drivetrain_efficiency = 0.97
        self.air_density = 1.225  # kg/m³ at sea level, 20°C
    
    def calculate_power(self, speed_ms, gradient_percent, 
                       air_temp_c=20, altitude_m=0):
        """Calculate estimated power using physics model"""
        # Validate input parameters
        if not isinstance(speed_ms, (int, float)) or speed_ms < 0:
            raise ValueError("Speed must be a non-negative number")
        if not isinstance(gradient_percent, (int, float)):
            raise ValueError("Gradient must be a number")
        
        # Calculate air density based on temperature and altitude
        temp_k = air_temp_c + 273.15
        pressure = 101325 * (1 - 0.0000225577 * altitude_m) ** 5.25588
        air_density = pressure / (287.05 * temp_k)
        
        # Convert gradient to angle
        gradient_rad = np.arctan(gradient_percent / 100.0)
        
        # Total mass
        total_mass = self.bike_weight_kg + self.rider_weight_kg
        
        # Power components
        P_roll = self.rolling_resistance * total_mass * 9.81 * np.cos(gradient_rad) * speed_ms
        P_grav = total_mass * 9.81 * np.sin(gradient_rad) * speed_ms
        P_aero = 0.5 * air_density * self.drag_coefficient * self.frontal_area_m2 * speed_ms ** 3
        
        # Power = (Rolling + Gravity + Aerodynamic) / Drivetrain efficiency
        return (P_roll + P_grav + P_aero) / self.drivetrain_efficiency

    def estimate_peak_power(self, power_values, durations):
        """Calculate peak power for various durations"""
        # This will be implemented in Phase 3
        return {}
