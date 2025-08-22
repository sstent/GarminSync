# Cycling FIT Analysis Implementation Plan

## Overview
Extend the existing GarminSync FIT parser to calculate cycling-specific metrics including power estimation and singlespeed gear ratio analysis for activities without native power data.

## Phase 1: Core Infrastructure Setup

### 1.1 Database Schema Extensions
**File: `garminsync/database.py`**
- Extend existing `PowerAnalysis` table with cycling-specific fields:
  ```python
  # Add to PowerAnalysis class:
  peak_power_1s = Column(Float, nullable=True)
  peak_power_5s = Column(Float, nullable=True) 
  peak_power_20s = Column(Float, nullable=True)
  peak_power_300s = Column(Float, nullable=True)
  normalized_power = Column(Float, nullable=True)
  intensity_factor = Column(Float, nullable=True)
  training_stress_score = Column(Float, nullable=True)
  ```

- Extend existing `GearingAnalysis` table:
  ```python
  # Add to GearingAnalysis class:
  estimated_chainring_teeth = Column(Integer, nullable=True)
  estimated_cassette_teeth = Column(Integer, nullable=True)
  gear_ratio = Column(Float, nullable=True)
  gear_inches = Column(Float, nullable=True)
  development_meters = Column(Float, nullable=True)
  confidence_score = Column(Float, nullable=True)
  analysis_method = Column(String, default="singlespeed_estimation")
  ```

### 1.2 Enhanced FIT Parser
**File: `garminsync/fit_processor/parser.py`**
- Extend `FITParser` to extract cycling-specific data points:
  ```python
  def _extract_cycling_data(self, message):
      """Extract cycling-specific metrics from FIT records"""
      # GPS coordinates for elevation/gradient
      # Speed and cadence for gear analysis
      # Power data (if available) for validation
      # Temperature for air density calculations
  ```

## Phase 2: Power Estimation Engine

### 2.1 Physics-Based Power Calculator
**New file: `garminsync/fit_processor/power_estimator.py`**

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

## Phase 3: Singlespeed Gear Ratio Analysis

### 3.1 Gear Ratio Calculator
**New file: `garminsync/fit_processor/gear_analyzer.py`**

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

## Phase 4: Integration with Existing System

### 4.1 FIT Processing Workflow Enhancement
**File: `garminsync/fit_processor/analyzer.py`**
- Integrate power estimation and gear analysis into existing analysis workflow
- Add cycling-specific analysis triggers (detect cycling activities)
- Store results in database using existing schema

### 4.2 Database Population
**Migration strategy:**
- Extend existing migration system to handle new fields
- Process existing FIT files retroactively
- Add processing status tracking for cycling analysis

### 4.3 CLI Integration
**File: `garminsync/cli.py`**
- Add new command: `garminsync analyze --cycling --activity-id <id>`
- Add batch processing: `garminsync analyze --cycling --missing`
- Add reporting: `garminsync report --power-analysis --gear-analysis`

## Phase 5: Validation and Testing

### 5.1 Test Data Requirements
- FIT files with known power data for validation
- Various singlespeed configurations for gear ratio testing
- Different terrain types (flat, climbing, mixed)

### 5.2 Validation Methodology
- Compare estimated vs. actual power (where available)
- Validate gear ratio estimates against known bike configurations
- Test edge cases (very low/high cadence, extreme gradients)

### 5.3 Performance Optimization
- Efficient gradient calculation from GPS data
- Optimize power calculation loops for large datasets
- Cache intermediate calculations

## Phase 6: Advanced Features (Future)

### 6.1 Environmental Corrections
- Wind speed/direction integration
- Barometric pressure for accurate altitude
- Temperature-based air density adjustments

### 6.2 Machine Learning Enhancement
- Train models on validated power data
- Improve gear ratio detection accuracy
- Personalized power estimation based on rider history

### 6.3 Comparative Analysis
- Compare estimated metrics across rides
- Trend analysis for fitness progression
- Gear ratio optimization recommendations

## Implementation Priority

**High Priority:**
1. Database schema extensions
2. Basic power estimation using physics model
3. Singlespeed gear ratio analysis for flat terrain
4. Integration with existing FIT processing pipeline

**Medium Priority:**
1. Peak power analysis (1s, 5s, 20s, 5min)
2. Normalized Power and TSS calculations
3. Advanced gear analysis with confidence scoring
4. CLI commands for analysis and reporting

**Low Priority:**
1. Environmental corrections (wind, pressure)
2. Machine learning enhancements
3. Advanced comparative analysis features
4. Web UI integration for visualizing results

## Success Criteria

1. **Power Estimation**: Within ±10% of actual power data (where available for validation)
2. **Gear Ratio Detection**: Correctly identify gear ratios within ±1 tooth accuracy
3. **Processing Speed**: Analyze typical FIT file (1-hour ride) in <5 seconds
4. **Data Coverage**: Successfully analyze 90%+ of cycling FIT files
5. **Integration**: Seamlessly integrate with existing GarminSync workflow

## File Structure Summary

```
garminsync/
├── fit_processor/
│   ├── parser.py (enhanced)
│   ├── analyzer.py (enhanced) 
│   ├── power_estimator.py (new)
│   └── gear_analyzer.py (new)
├── database.py (enhanced)
├── cli.py (enhanced)
└── migrate_cycling_analysis.py (new)
```

This plan provides a comprehensive roadmap for implementing cycling-specific FIT analysis while building on the existing GarminSync infrastructure and maintaining compatibility with current functionality.