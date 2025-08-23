import os
import gzip
import fitdecode
import xml.etree.ElementTree as ET
import numpy as np
from .fit_processor.power_estimator import PowerEstimator
from .fit_processor.gear_analyzer import SinglespeedAnalyzer
from math import radians, sin, cos, sqrt, atan2

def detect_file_type(file_path):
    """Detect file format (FIT, XML, or unknown)"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(128)
            if b'<?xml' in header[:20]:
                return 'xml'
            if len(header) >= 8 and header[4:8] == b'.FIT':
                return 'fit'
            if (len(header) >= 8 and 
                (header[0:4] == b'.FIT' or 
                 header[4:8] == b'FIT.' or 
                 header[8:12] == b'.FIT')):
                return 'fit'
            return 'unknown'
    except Exception as e:
        return 'error'

def parse_xml_file(file_path):
    """Parse XML (TCX) file to extract activity metrics"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        namespaces = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
        
        sport = root.find('.//ns:Activity', namespaces).get('Sport', 'other')
        distance = root.find('.//ns:DistanceMeters', namespaces)
        distance = float(distance.text) if distance is not None else None
        duration = root.find('.//ns:TotalTimeSeconds', namespaces)
        duration = float(duration.text) if duration is not None else None
        calories = root.find('.//ns:Calories', namespaces)
        calories = int(calories.text) if calories is not None else None
        
        hr_values = []
        for hr in root.findall('.//ns:HeartRateBpm/ns:Value', namespaces):
            try:
                hr_values.append(int(hr.text))
            except:
                continue
        max_hr = max(hr_values) if hr_values else None
        
        return {
            "activityType": {"typeKey": sport},
            "summaryDTO": {
                "duration": duration,
                "distance": distance,
                "maxHR": max_hr,
                "avgPower": None,
                "calories": calories
            }
        }
    except Exception:
        return None

def compute_gradient(altitudes, positions, distance_m=10):
    """Compute gradient percentage for each point using elevation changes"""
    if len(altitudes) < 2:
        return [0] * len(altitudes)
    
    gradients = []
    for i in range(1, len(altitudes)):
        elev_change = altitudes[i] - altitudes[i-1]
        if positions and i < len(positions):
            distance = distance_between_points(positions[i-1], positions[i])
        else:
            distance = distance_m
        gradients.append((elev_change / distance) * 100)
    
    return [gradients[0]] + gradients

def distance_between_points(point1, point2):
    """Calculate distance between two (lat, lon) points in meters using Haversine"""
    R = 6371000  # Earth radius in meters
    
    lat1, lon1 = radians(point1[0]), radians(point1[1])
    lat2, lon2 = radians(point2[0]), radians(point2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def parse_fit_file(file_path):
    """Parse FIT file to extract activity metrics and detailed cycling data"""
    metrics = {}
    detailed_metrics = {
        'speeds': [], 'cadences': [], 'altitudes': [],
        'positions': [], 'gradients': [], 'powers': [], 'timestamps': []
    }
    
    power_estimator = PowerEstimator()
    gear_analyzer = SinglespeedAnalyzer()
    
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(2)
            f.seek(0)
            is_gzipped = magic == b'\x1f\x8b'
        
        if is_gzipped:
            with gzip.open(file_path, 'rb') as gz_file:
                from io import BytesIO
                with BytesIO(gz_file.read()) as fit_data:
                    fit = fitdecode.FitReader(fit_data)
                    for frame in fit:
                        if frame.frame_type == fitdecode.FrameType.DATA:
                            if frame.name == 'record':
                                if timestamp := frame.get_value('timestamp'):
                                    detailed_metrics['timestamps'].append(timestamp)
                                if (lat := frame.get_value('position_lat')) and (lon := frame.get_value('position_long')):
                                    detailed_metrics['positions'].append((lat, lon))
                                if altitude := frame.get_value('altitude'):
                                    detailed_metrics['altitudes'].append(altitude)
                                if speed := frame.get_value('speed'):
                                    detailed_metrics['speeds'].append(speed)
                                if cadence := frame.get_value('cadence'):
                                    detailed_metrics['cadences'].append(cadence)
                                if power := frame.get_value('power'):
                                    detailed_metrics['powers'].append(power)
                            
                            elif frame.name == 'session':
                                metrics = {
                                    "sport": frame.get_value("sport"),
                                    "total_timer_time": frame.get_value("total_timer_time"),
                                    "total_distance": frame.get_value("total_distance"),
                                    "max_heart_rate": frame.get_value("max_heart_rate"),
                                    "avg_power": frame.get_value("avg_power"),
                                    "total_calories": frame.get_value("total_calories")
                                }
        else:
            with fitdecode.FitReader(file_path) as fit:
                for frame in fit:
                    if frame.frame_type == fitdecode.FrameType.DATA:
                        if frame.name == 'record':
                            if timestamp := frame.get_value('timestamp'):
                                detailed_metrics['timestamps'].append(timestamp)
                            if (lat := frame.get_value('position_lat')) and (lon := frame.get_value('position_long')):
                                detailed_metrics['positions'].append((lat, lon))
                            if altitude := frame.get_value('altitude'):
                                detailed_metrics['altitudes'].append(altitude)
                            if speed := frame.get_value('speed'):
                                detailed_metrics['speeds'].append(speed)
                            if cadence := frame.get_value('cadence'):
                                detailed_metrics['cadences'].append(cadence)
                            if power := frame.get_value('power'):
                                detailed_metrics['powers'].append(power)
                        
                        elif frame.name == 'session':
                            metrics = {
                                "sport": frame.get_value("sport"),
                                "total_timer_time": frame.get_value("total_timer_time"),
                                "total_distance": frame.get_value("total_distance"),
                                "max_heart_rate": frame.get_value("max_heart_rate"),
                                "avg_power": frame.get_value("avg_power"),
                                "total_calories": frame.get_value("total_calories")
                            }
    
        # Compute gradients if data available
        if detailed_metrics['altitudes']:
            detailed_metrics['gradients'] = compute_gradient(
                detailed_metrics['altitudes'],
                detailed_metrics['positions']
            )
        
        # Process cycling-specific metrics
        if metrics.get('sport') in ['cycling', 'road_biking', 'mountain_biking']:
            # Estimate power if not present
            if not detailed_metrics['powers']:
                for speed, gradient in zip(detailed_metrics['speeds'], detailed_metrics['gradients']):
                    estimated_power = power_estimator.calculate_power(speed, gradient)
                    detailed_metrics['powers'].append(estimated_power)
                metrics['avg_power'] = np.mean(detailed_metrics['powers']) if detailed_metrics['powers'] else None
            
            # Run gear analysis
            if detailed_metrics['speeds'] and detailed_metrics['cadences']:
                gear_analysis = gear_analyzer.analyze_gear_ratio(
                    detailed_metrics['speeds'],
                    detailed_metrics['cadences'],
                    detailed_metrics['gradients']
                )
                metrics['gear_analysis'] = gear_analysis or {}
        
        return {
            "activityType": {"typeKey": metrics.get("sport", "other")},
            "summaryDTO": {
                "duration": metrics.get("total_timer_time"),
                "distance": metrics.get("total_distance"),
                "maxHR": metrics.get("max_heart_rate"),
                "avgPower": metrics.get("avg_power"),
                "calories": metrics.get("total_calories"),
                "gearAnalysis": metrics.get("gear_analysis", {})
            },
            "detailedMetrics": detailed_metrics
        }
    except Exception as e:
        print(f"Error parsing FIT file: {str(e)}")
        return None

def get_activity_metrics(activity, client=None, force_reprocess=False):
    """
    Get activity metrics from local file or Garmin API
    
    :param activity: Activity object
    :param client: Optional GarminClient instance
    :param force_reprocess: If True, re-process file even if already parsed
    :return: Activity metrics dictionary
    """
    metrics = None
    # Always re-process if force_reprocess is True
    if force_reprocess and activity.filename and os.path.exists(activity.filename):
        file_type = detect_file_type(activity.filename)
        try:
            if file_type == 'fit':
                metrics = parse_fit_file(activity.filename)
            elif file_type == 'xml':
                metrics = parse_xml_file(activity.filename)
        except Exception as e:
            print(f"Error parsing activity file: {str(e)}")
    
    # Only parse if metrics not already obtained through force_reprocess
    if not metrics:
        if activity.filename and os.path.exists(activity.filename):
            file_type = detect_file_type(activity.filename)
            try:
                if file_type == 'fit':
                    metrics = parse_fit_file(activity.filename)
                elif file_type == 'xml':
                    metrics = parse_xml_file(activity.filename)
            except Exception as e:
                print(f"Error parsing activity file: {str(e)}")
        
        if not metrics and client:
            try:
                metrics = client.get_activity_details(activity.activity_id)
            except Exception as e:
                print(f"Error fetching activity from API: {str(e)}")
    
    # Return summary DTO for compatibility
    return metrics.get("summaryDTO") if metrics and "summaryDTO" in metrics else metrics
