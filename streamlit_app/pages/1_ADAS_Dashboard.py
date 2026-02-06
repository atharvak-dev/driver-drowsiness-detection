import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Add root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.vehicle_dynamics import VehicleDynamicsAnalyzer
from src.data.mock_loader import ADSDataLoader

st.set_page_config(page_title="ADAS Research Dashboard", page_icon="🚘", layout="wide")

st.title("🚘 ADAS Research Prototype: Impairment Detection")
st.markdown("""
> **⚠️ RESEARCH PREVIEW**: This tool visualizes **Vehicle Dynamics** metrics for detecting impairment. 
> It is a prototype for algorithmic validation and is **not** a safety-critical system.
""")

# Sidebar controls
st.sidebar.header("Data Source")
data_source = st.sidebar.radio("Select Input:", ["Generate Mock Data", "Upload CSV"])

df = pd.DataFrame()

if data_source == "Generate Mock Data":
    scenario = st.sidebar.selectbox("Scenario:", ["Sober (Baseline)", "Drunk (High Variance)"])
    if st.sidebar.button("Generate Simulation"):
        with st.spinner(f"Simulating {scenario} driver behavior..."):
            df = ADSDataLoader.generate_mock_data(duration_sec=60, scenario=scenario.lower().split()[0])
            st.toast(f"Generated 60s of {scenario} data!")
            
elif data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CAN Bus Data (CSV)", type=["csv"])
    if uploaded_file:
        df = ADSDataLoader.load_csv(uploaded_file)
        if not df.empty:
            st.success(f"Loaded {len(df)} samples")
        else:
            st.error("Could not parse CSV. Ensure formatting.")

# Main Dashboard
if not df.empty:
    # Initialize Analyzer
    analyzer = VehicleDynamicsAnalyzer(sample_rate_hz=10)
    
    # Calculate Metrics
    entropy = analyzer.calculate_steering_entropy(df['steering_angle'].values)
    speed_var = analyzer.calculate_speed_variability(df['speed_kmh'].values)
    risk_label = analyzer.detect_high_risk_event(entropy, speed_var)
    
    # 1. Top Level Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Steering Entropy (Impairment)", f"{entropy:.3f}", 
                  help="Measure of steering unpredictability. >0.45 suggests impairment.")
        
    with col2:
        st.metric("Speed Variability", f"{speed_var:.1f}%",
                  help="Coefficient of variation in speed. >15% suggests lack of control.")
        
    with col3:
        color = "green" if risk_label == "NORMAL" else "red"
        st.markdown(f"### Risk Level: :{color}[{risk_label}]")

    # 2. Visualizations
    st.subheader("Signal Analysis")
    
    # Steering Plot
    fig_steering = go.Figure()
    fig_steering.add_trace(go.Scatter(x=df['timestamp'], y=df['steering_angle'], 
                                      mode='lines', name='Steering Angle',
                                      line=dict(color='#3498db')))
    
    fig_steering.update_layout(title="Steering Angle (Degrees)", 
                               xaxis_title="Time (s)", yaxis_title="Angle",
                               height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_steering, use_container_width=True)

    # Speed Plot
    fig_speed = go.Figure()
    fig_speed.add_trace(go.Scatter(x=df['timestamp'], y=df['speed_kmh'], 
                                   mode='lines', name='Speed',
                                   line=dict(color='#e74c3c')))
                                   
    fig_speed.update_layout(title="Vehicle Speed (km/h)", 
                            xaxis_title="Time (s)", yaxis_title="Speed",
                            height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_speed, use_container_width=True)

    # 3. Explanation
    with st.expander("ℹ️ How to interpret these graphs"):
        st.markdown("""
        *   **Sober Driver**: Steering looks like smooth curves (sine waves) with minimal noise. Speed is consistent.
        *   **Impaired Driver**: 
            *   **Steering**: Contains "micro-corrections" (fuzzy lines) and sudden jerks (spikes). This increases **Entropy**.
            *   **Speed**: Fluctuates significantly as the driver loses focus on the pedal.
        """)

else:
    st.info("👈 Select a Data Source in the sidebar to begin.")
