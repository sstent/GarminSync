import os
import gzip
import fitdecode
import xml.etree.ElementTree as ET
from datetime import datetime

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

def parse_fit_file(file_path):
    """Parse FIT file to extract activity metrics"""
    metrics = {}
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
                        if frame.frame_type == fitdecode.FrameType.DATA and frame.name == 'session':
                            metrics = {
                                "sport": frame.get_value("sport"),
                                "total_timer_time": frame.get_value("total_timer_time"),
                                "total_distance": frame.get_value("total_distance"),
                                "max_heart_rate": frame.get_value("max_heart_rate"),
                                "avg_power": frame.get_value("avg_power"),
                                "total_calories": frame.get_value("total_calories")
                            }
                            break
        else:
            with fitdecode.FitReader(file_path) as fit:
                for frame in fit:
                    if frame.frame_type == fitdecode.FrameType.DATA and frame.name == 'session':
                        metrics = {
                            "sport": frame.get_value("sport"),
                            "total_timer_time": frame.get_value("total_timer_time"),
                            "total_distance": frame.get_value("total_distance"),
                            "max_heart_rate": frame.get_value("max_heart_rate"),
                            "avg_power": frame.get_value("avg_power"),
                            "total_calories": frame.get_value("total_calories")
                        }
                        break
    
        return {
            "activityType": {"typeKey": metrics.get("sport", "other")},
            "summaryDTO": {
                "duration": metrics.get("total_timer_time"),
                "distance": metrics.get("total_distance"),
                "maxHR": metrics.get("max_heart_rate"),
                "avgPower": metrics.get("avg_power"),
                "calories": metrics.get("total_calories")
            }
        }
    except Exception:
        return None

def get_activity_metrics(activity, client=None):
    """
    Get activity metrics from local file or Garmin API
    Returns parsed metrics or None
    """
    metrics = None
    if activity.filename and os.path.exists(activity.filename):
        file_type = detect_file_type(activity.filename)
        if file_type == 'fit':
            metrics = parse_fit_file(activity.filename)
        elif file_type == 'xml':
            metrics = parse_xml_file(activity.filename)
    if not metrics and client:
        try:
            metrics = client.get_activity_details(activity.activity_id)
        except Exception:
            pass
    return metrics
