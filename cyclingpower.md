# Cycling FIT Analysis Implementation Plan

## Overview
Extend the existing GarminSync FIT parser to calculate cycling-specific metrics including power estimation and singlespeed gear ratio analysis for activities without native power data.


**Key Components:**
- **Environmental factors**: Air density, wind resistance, temperature
- **Bike specifications**: Weight (22 lbs = 10 kg), aerodynamic drag coefficient
- **Rider assumptions**: Weight (75 kg default), position (road bike)
- **Terrain analysis**: Gradient calculation from GPS elevation data

**Core Algorithm:**
```python
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
        # Power = (Rolling + Gravity + Aerodynamic + Kinetic) / Efficiency
```

**Power Components:**
1. **Rolling resistance**: `P_roll = Crr × (m_bike + m_rider) × g × cos(θ) × v`
2. **Gravitational**: `P_grav = (m_bike + m_rider) × g × sin(θ) × v`
3. **Aerodynamic**: `P_aero = 0.5 × ρ × Cd × A × v³`
4. **Acceleration**: `P_accel = (m_bike + m_rider) × a × v`

### 2.2 Peak Power Analysis
**Methods:**
- 1-second, 5-second, 20-second, 5-minute peak power windows
- Normalized Power (NP) calculation using 30-second rolling average
- Training Stress Score (TSS) estimation based on NP and ride duration

## Singlespeed Gear Ratio Analysis

### Gear Ratio Calculator

**Strategy:**
- Analyze flat terrain segments (gradient < 3%)
- Use speed/cadence relationship to determine gear ratio
- Test against common singlespeed ratios for 38t and 46t chainrings
- Calculate confidence scores based on data consistency

**Core Algorithm:**
```python
class SinglespeedAnalyzer:
    def __init__(self):
        self.chainring_options = [38, 46]  # teeth
        self.common_cogs = list(range(11, 28))  # 11t to 27t rear cogs
        self.wheel_circumference_m = 2.096  # 700x25c tire
    
    def analyze_gear_ratio(self, speed_data, cadence_data, gradient_data):
        """Determine most likely singlespeed gear ratio"""
        # Filter for flat terrain segments
        # Calculate gear ratio from speed/cadence
        # Match against common ratios
        # Return best fit with confidence score
```

**Gear Metrics:**
- **Gear ratio**: Chainring teeth ÷ Cog teeth
- **Gear inches**: Gear ratio × wheel diameter (inches)
- **Development**: Distance traveled per pedal revolution (meters)

### 3.2 Analysis Methodology
1. **Segment filtering**: Identify flat terrain (gradient < 3%, speed > 15 km/h)
2. **Ratio calculation**: `gear_ratio = (speed_ms × 60) ÷ (cadence_rpm × wheel_circumference_m)`
3. **Ratio matching**: Compare calculated ratios against theoretical singlespeed options
4. **Confidence scoring**: Based on data consistency and segment duration
