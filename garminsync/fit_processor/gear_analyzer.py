import numpy as np

class SinglespeedAnalyzer:
    def __init__(self):
        self.chainring_options = [38, 46]  # teeth
        self.common_cogs = list(range(11, 28))  # 11t to 27t rear cogs
        self.wheel_circumference_m = 2.096  # 700x25c tire
    
    def analyze_gear_ratio(self, speed_data, cadence_data, gradient_data):
        """Determine most likely singlespeed gear ratio"""
        # Validate input parameters
        if not speed_data or not cadence_data or not gradient_data:
            raise ValueError("Input data cannot be empty")
        if len(speed_data) != len(cadence_data) or len(speed_data) != len(gradient_data):
            raise ValueError("Input data arrays must be of equal length")
            
        # Filter for flat terrain segments (gradient < 3%)
        flat_indices = [i for i, grad in enumerate(gradient_data) if abs(grad) < 3.0]
        flat_speeds = [speed_data[i] for i in flat_indices]
        flat_cadences = [cadence_data[i] for i in flat_indices]
        
        # Only consider data points with sufficient speed (15 km/h) and cadence
        valid_indices = [i for i in range(len(flat_speeds)) 
                         if flat_speeds[i] > 4.17 and flat_cadences[i] > 0]  # 15 km/h threshold
        
        if not valid_indices:
            return None  # Not enough data
        
        valid_speeds = [flat_speeds[i] for i in valid_indices]
        valid_cadences = [flat_cadences[i] for i in valid_indices]
        
        # Calculate gear ratios from speed and cadence
        gear_ratios = []
        for speed, cadence in zip(valid_speeds, valid_cadences):
            # Gear ratio = (speed in m/s * 60 seconds/minute) / (cadence in rpm * wheel circumference in meters)
            gr = (speed * 60) / (cadence * self.wheel_circumference_m)
            gear_ratios.append(gr)
        
        # Calculate average gear ratio
        avg_gear_ratio = sum(gear_ratios) / len(gear_ratios)
        
        # Find best matching chainring and cog combination
        best_fit = None
        min_diff = float('inf')
        for chainring in self.chainring_options:
            for cog in self.common_cogs:
                theoretical_ratio = chainring / cog
                diff = abs(theoretical_ratio - avg_gear_ratio)
                if diff < min_diff:
                    min_diff = diff
                    best_fit = (chainring, cog, theoretical_ratio)
        
        if not best_fit:
            return None
        
        chainring, cog, ratio = best_fit
        
        # Calculate gear metrics
        wheel_diameter_inches = 27.0  # 700c wheel diameter
        gear_inches = ratio * wheel_diameter_inches
        development_meters = ratio * self.wheel_circumference_m
        
        # Calculate confidence score (1 - relative error)
        confidence = max(0, 1 - (min_diff / ratio)) if ratio > 0 else 0
        
        return {
            'estimated_chainring_teeth': chainring,
            'estimated_cassette_teeth': cog,
            'gear_ratio': ratio,
            'gear_inches': gear_inches,
            'development_meters': development_meters,
            'confidence_score': confidence
        }
