"""
Risk Mapping Visualization Module
Premium interactive maps for driver safety analytics
"""
import folium
from folium import plugins
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import json


@dataclass
class RoutePoint:
    """A single point on the driving route"""
    lat: float
    lng: float
    timestamp: datetime
    state: str  # normal, low_risk, moderate_risk, high_risk, drowsy, distracted
    speed: float = 0.0
    ear_value: float = 0.0
    risk_score: float = 0.0


@dataclass  
class Incident:
    """A safety incident marker"""
    lat: float
    lng: float
    timestamp: datetime
    incident_type: str  # drowsy, distracted, high_risk, microsleep
    severity: str  # low, medium, high, critical
    duration: float  # seconds
    description: str = ""
    metrics: Dict = field(default_factory=dict)


@dataclass
class RiskZone:
    """A geographic risk zone"""
    center_lat: float
    center_lng: float
    radius_m: float
    risk_level: str  # low, moderate, high, critical
    incident_count: int = 0
    name: str = ""


class MapVisualization:
    """Premium map visualization for driver safety monitoring"""
    
    # State color mapping
    STATE_COLORS = {
        'normal': '#00ff88',
        'low_risk': '#00ffff',
        'moderate_risk': '#ffa500',
        'high_risk': '#ff4444',
        'drowsy': '#ff6b6b',
        'asleep': '#ff0000',
        'distracted': '#ff8800'
    }
    
    # Incident icon mapping
    INCIDENT_ICONS = {
        'drowsy': 'eye-slash',
        'distracted': 'mobile',
        'high_risk': 'exclamation-triangle',
        'microsleep': 'bed',
        'speeding': 'tachometer-alt',
        'harsh_braking': 'hand-paper'
    }
    
    SEVERITY_COLORS = {
        'low': '#ffc107',
        'medium': '#ff9800',
        'high': '#ff5722',
        'critical': '#f44336'
    }
    
    def __init__(self, center_lat: float = 28.6139, center_lng: float = 77.2090, zoom: int = 13):
        """Initialize map with center coordinates (default: New Delhi, India)"""
        self.center_lat = center_lat
        self.center_lng = center_lng
        self.zoom = zoom
        self.route_points: List[RoutePoint] = []
        self.incidents: List[Incident] = []
        self.risk_zones: List[RiskZone] = []
    
    def add_route_point(self, point: RoutePoint):
        """Add a point to the route"""
        self.route_points.append(point)
    
    def add_incident(self, incident: Incident):
        """Add an incident marker"""
        self.incidents.append(incident)
    
    def add_risk_zone(self, zone: RiskZone):
        """Add a risk zone"""
        self.risk_zones.append(zone)
    
    def generate_demo_data(self, num_points: int = 100, num_incidents: int = 5):
        """Generate realistic demo route and incident data"""
        np.random.seed(42)
        
        # Generate a realistic driving route (curved path)
        base_lat = self.center_lat
        base_lng = self.center_lng
        
        for i in range(num_points):
            # Create a winding path
            lat = base_lat + (i * 0.001) + np.sin(i * 0.1) * 0.002
            lng = base_lng + (i * 0.0015) + np.cos(i * 0.15) * 0.003
            
            # Vary states along the route
            if i < 20:
                state = 'normal'
            elif 20 <= i < 30:
                state = 'low_risk' if np.random.random() > 0.3 else 'normal'
            elif 30 <= i < 40:
                state = np.random.choice(['moderate_risk', 'drowsy'], p=[0.6, 0.4])
            elif 40 <= i < 50:
                state = 'high_risk' if np.random.random() > 0.5 else 'moderate_risk'
            elif 50 <= i < 60:
                state = 'distracted' if np.random.random() > 0.7 else 'normal'
            else:
                state = 'normal'
            
            point = RoutePoint(
                lat=lat,
                lng=lng,
                timestamp=datetime.now() - timedelta(seconds=(num_points - i) * 5),
                state=state,
                speed=40 + np.random.normal(0, 10),
                ear_value=0.25 + np.random.normal(0, 0.05),
                risk_score=0.3 if state == 'normal' else 0.7
            )
            self.add_route_point(point)
        
        # Generate incidents at specific route points
        incident_indices = [25, 35, 45, 55, 75][:num_incidents]
        incident_types = ['drowsy', 'distracted', 'high_risk', 'microsleep', 'harsh_braking']
        severities = ['low', 'medium', 'high', 'critical', 'medium']
        
        for i, idx in enumerate(incident_indices):
            if idx < len(self.route_points):
                point = self.route_points[idx]
                incident = Incident(
                    lat=point.lat,
                    lng=point.lng,
                    timestamp=point.timestamp,
                    incident_type=incident_types[i % len(incident_types)],
                    severity=severities[i % len(severities)],
                    duration=np.random.uniform(2, 15),
                    description=f"Safety incident detected at point {idx}",
                    metrics={'ear': point.ear_value, 'risk': point.risk_score}
                )
                self.add_incident(incident)
        
        # Generate risk zones
        risk_zone_centers = [
            (base_lat + 0.025, base_lng + 0.03, 'high', "Highway Junction"),
            (base_lat + 0.045, base_lng + 0.06, 'moderate', "School Zone"),
            (base_lat + 0.08, base_lng + 0.1, 'low', "Residential Area")
        ]
        
        for lat, lng, risk, name in risk_zone_centers:
            zone = RiskZone(
                center_lat=lat,
                center_lng=lng,
                radius_m=200 + np.random.randint(0, 300),
                risk_level=risk,
                incident_count=np.random.randint(1, 10),
                name=name
            )
            self.add_risk_zone(zone)
    
    def create_base_map(self) -> folium.Map:
        """Create the base map with dark theme"""
        m = folium.Map(
            location=[self.center_lat, self.center_lng],
            zoom_start=self.zoom,
            tiles=None,
            control_scale=True
        )
        
        # Add dark mode tile layer
        folium.TileLayer(
            tiles='cartodbdark_matter',
            name='Dark Mode',
            control=True
        ).add_to(m)
        
        # Add satellite option
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            control=True
        ).add_to(m)
        
        # Add normal map option
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='Street Map',
            control=True
        ).add_to(m)
        
        return m
    
    def add_route_layer(self, m: folium.Map) -> folium.Map:
        """Add the driving route with state-based coloring"""
        if not self.route_points:
            return m
        
        # Create feature group for route
        route_group = folium.FeatureGroup(name='🛣️ Driving Route')
        
        # Group consecutive points by state for colored segments
        segments = []
        current_segment = [self.route_points[0]]
        
        for i in range(1, len(self.route_points)):
            if self.route_points[i].state == current_segment[-1].state:
                current_segment.append(self.route_points[i])
            else:
                segments.append(current_segment)
                current_segment = [self.route_points[i]]
        segments.append(current_segment)
        
        # Draw each segment with appropriate color
        for segment in segments:
            if len(segment) >= 2:
                coords = [[p.lat, p.lng] for p in segment]
                state = segment[0].state
                color = self.STATE_COLORS.get(state, '#ffffff')
                
                folium.PolyLine(
                    coords,
                    weight=6,
                    color=color,
                    opacity=0.8,
                    popup=f"State: {state.replace('_', ' ').title()}",
                    tooltip=f"{state.replace('_', ' ').title()}"
                ).add_to(route_group)
        
        # Add start marker
        start = self.route_points[0]
        folium.Marker(
            [start.lat, start.lng],
            popup=f"<b>🚗 Trip Start</b><br>Time: {start.timestamp.strftime('%H:%M:%S')}",
            icon=folium.Icon(color='green', icon='play', prefix='fa'),
            tooltip="Trip Start"
        ).add_to(route_group)
        
        # Add end marker
        end = self.route_points[-1]
        folium.Marker(
            [end.lat, end.lng],
            popup=f"<b>🏁 Trip End</b><br>Time: {end.timestamp.strftime('%H:%M:%S')}",
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa'),
            tooltip="Trip End"
        ).add_to(route_group)
        
        route_group.add_to(m)
        return m
    
    def add_incident_markers(self, m: folium.Map) -> folium.Map:
        """Add incident markers with popups"""
        if not self.incidents:
            return m
        
        incident_group = folium.FeatureGroup(name='🚨 Incidents')
        
        for incident in self.incidents:
            color = self.SEVERITY_COLORS.get(incident.severity, '#ff9800')
            icon = self.INCIDENT_ICONS.get(incident.incident_type, 'exclamation')
            
            popup_html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; min-width: 200px;">
                <h4 style="color: {color}; margin: 0 0 10px 0;">
                    ⚠️ {incident.incident_type.replace('_', ' ').title()}
                </h4>
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><b>Severity:</b></td><td>{incident.severity.upper()}</td></tr>
                    <tr><td><b>Time:</b></td><td>{incident.timestamp.strftime('%H:%M:%S')}</td></tr>
                    <tr><td><b>Duration:</b></td><td>{incident.duration:.1f}s</td></tr>
                    <tr><td><b>EAR:</b></td><td>{incident.metrics.get('ear', 'N/A'):.3f}</td></tr>
                    <tr><td><b>Risk:</b></td><td>{incident.metrics.get('risk', 'N/A'):.2f}</td></tr>
                </table>
            </div>
            """
            
            folium.Marker(
                [incident.lat, incident.lng],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(
                    color='red' if incident.severity in ['high', 'critical'] else 'orange',
                    icon=icon,
                    prefix='fa'
                ),
                tooltip=f"{incident.incident_type.replace('_', ' ').title()} ({incident.severity})"
            ).add_to(incident_group)
        
        incident_group.add_to(m)
        return m
    
    def add_risk_zones(self, m: folium.Map) -> folium.Map:
        """Add risk zone circles with heatmap effect"""
        if not self.risk_zones:
            return m
        
        zone_group = folium.FeatureGroup(name='🔥 Risk Zones')
        
        zone_colors = {
            'low': '#4CAF50',
            'moderate': '#FF9800',
            'high': '#f44336',
            'critical': '#9C27B0'
        }
        
        for zone in self.risk_zones:
            color = zone_colors.get(zone.risk_level, '#FF9800')
            
            folium.Circle(
                [zone.center_lat, zone.center_lng],
                radius=zone.radius_m,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.3,
                popup=f"""
                <b>{zone.name}</b><br>
                Risk Level: {zone.risk_level.upper()}<br>
                Past Incidents: {zone.incident_count}
                """,
                tooltip=f"{zone.name} - {zone.risk_level.title()} Risk"
            ).add_to(zone_group)
        
        zone_group.add_to(m)
        return m
    
    def add_heatmap_layer(self, m: folium.Map) -> folium.Map:
        """Add a heatmap layer based on incident density"""
        if not self.incidents and not self.route_points:
            return m
        
        # Collect heat data from high-risk points
        heat_data = []
        
        for point in self.route_points:
            if point.state in ['high_risk', 'drowsy', 'asleep', 'distracted']:
                heat_data.append([point.lat, point.lng, point.risk_score])
        
        for incident in self.incidents:
            weight = {'low': 0.3, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
            heat_data.append([
                incident.lat, 
                incident.lng, 
                weight.get(incident.severity, 0.5)
            ])
        
        if heat_data:
            plugins.HeatMap(
                heat_data,
                name='🌡️ Risk Heatmap',
                min_opacity=0.3,
                max_val=1.0,
                radius=25,
                blur=15,
                gradient={
                    0.2: '#00ff88',
                    0.4: '#ffff00',
                    0.6: '#ff9800',
                    0.8: '#ff5722',
                    1.0: '#f44336'
                }
            ).add_to(m)
        
        return m
    
    def add_minimap(self, m: folium.Map) -> folium.Map:
        """Add a minimap for context"""
        minimap = plugins.MiniMap(
            tile_layer='cartodbdark_matter',
            toggle_display=True,
            minimized=False,
            position='bottomright'
        )
        minimap.add_to(m)
        return m
    
    def add_fullscreen(self, m: folium.Map) -> folium.Map:
        """Add fullscreen button"""
        plugins.Fullscreen(
            position='topleft',
            title='Fullscreen',
            title_cancel='Exit Fullscreen'
        ).add_to(m)
        return m
    
    def add_draw_tools(self, m: folium.Map) -> folium.Map:
        """Add drawing tools for user annotations"""
        draw = plugins.Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': True,
                'polygon': True,
                'circle': True,
                'marker': True,
                'circlemarker': False,
                'rectangle': True
            }
        )
        draw.add_to(m)
        return m
    
    def add_measure_control(self, m: folium.Map) -> folium.Map:
        """Add distance measurement tool"""
        plugins.MeasureControl(
            position='topleft',
            primary_length_unit='kilometers',
            secondary_length_unit='miles'
        ).add_to(m)
        return m
    
    def generate_map(self, include_heatmap: bool = True) -> folium.Map:
        """Generate the complete map with all layers"""
        m = self.create_base_map()
        
        # Add all layers
        m = self.add_route_layer(m)
        m = self.add_incident_markers(m)
        m = self.add_risk_zones(m)
        
        if include_heatmap:
            m = self.add_heatmap_layer(m)
        
        # Add controls
        m = self.add_minimap(m)
        m = self.add_fullscreen(m)
        m = self.add_draw_tools(m)
        m = self.add_measure_control(m)
        
        # Add layer control
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # Fit bounds to route if available
        if self.route_points:
            coords = [[p.lat, p.lng] for p in self.route_points]
            m.fit_bounds(coords)
        
        return m
    
    def get_map_html(self, height: int = 600) -> str:
        """Get the map as HTML string for embedding"""
        m = self.generate_map()
        return m._repr_html_()
    
    def get_route_stats(self) -> Dict:
        """Calculate route statistics"""
        if not self.route_points:
            return {}
        
        total_points = len(self.route_points)
        state_counts = {}
        
        for point in self.route_points:
            state_counts[point.state] = state_counts.get(point.state, 0) + 1
        
        # Calculate percentages
        state_percentages = {
            state: (count / total_points) * 100 
            for state, count in state_counts.items()
        }
        
        # Calculate duration (assuming 5 seconds between points)
        duration_seconds = total_points * 5
        
        # Calculate distance (approximate using Haversine)
        total_distance = 0
        for i in range(1, len(self.route_points)):
            p1, p2 = self.route_points[i-1], self.route_points[i]
            # Simplified distance calculation
            lat_diff = (p2.lat - p1.lat) * 111000  # meters
            lng_diff = (p2.lng - p1.lng) * 111000 * np.cos(np.radians(p1.lat))
            total_distance += np.sqrt(lat_diff**2 + lng_diff**2)
        
        return {
            'total_points': total_points,
            'total_incidents': len(self.incidents),
            'duration_minutes': duration_seconds / 60,
            'distance_km': total_distance / 1000,
            'state_distribution': state_percentages,
            'avg_speed': np.mean([p.speed for p in self.route_points]),
            'max_speed': np.max([p.speed for p in self.route_points]),
            'risk_zones_crossed': len(self.risk_zones)
        }


def create_demo_map() -> Tuple[folium.Map, Dict]:
    """Create a demo map with sample data"""
    viz = MapVisualization(center_lat=28.6139, center_lng=77.2090)
    viz.generate_demo_data(num_points=100, num_incidents=5)
    m = viz.generate_map()
    stats = viz.get_route_stats()
    return m, stats
