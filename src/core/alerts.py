"""
Production Alert System
Multi-channel alerting with escalation and throttling.
"""
import logging
import threading
import time
from typing import Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import queue

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("pygame not available, audio alerts disabled")

logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    """Alert delivery channels."""
    AUDIO = "audio"
    VISUAL = "visual"
    HAPTIC = "haptic"
    LOG = "log"
    CALLBACK = "callback"


@dataclass
class AlertConfig:
    """Configuration for alert system."""
    audio_enabled: bool = True
    visual_enabled: bool = True
    haptic_enabled: bool = False
    
    # Throttling
    min_interval_sec: float = 5.0
    escalation_threshold: int = 3  # Escalate after N alerts
    
    # Audio
    audio_file: str = "assets/alarm.wav"
    audio_volume: float = 0.8
    audio_duration_sec: float = 2.0
    
    # Escalation
    enable_escalation: bool = True
    escalation_interval_sec: float = 30.0


class AlertSystem:
    """
    Production alert system with multiple delivery channels.
    
    Features:
    - Multi-channel alerting (audio, visual, haptic)
    - Throttling to prevent alert fatigue
    - Escalation for persistent impairment
    - Custom callbacks
    - Thread-safe operation
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Initialize alert system.
        
        Args:
            config: Alert configuration
        """
        self.config = config or AlertConfig()
        
        # State
        self._last_alert_time: Optional[datetime] = None
        self._alert_count = 0
        self._escalation_level = 0
        self._is_active = False
        
        # Threading
        self._lock = threading.Lock()
        self._alert_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._callbacks: List[Callable] = []
        
        # Initialize audio
        if self.config.audio_enabled and PYGAME_AVAILABLE:
            self._init_audio()
        
        # Start worker
        self._start_worker()
        
        logger.info("Alert system initialized")
    
    def _init_audio(self) -> None:
        """Initialize audio system."""
        try:
            pygame.mixer.init()
            logger.info("Audio alert system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self.config.audio_enabled = False
    
    def _start_worker(self) -> None:
        """Start alert worker thread."""
        self._is_active = True
        self._worker_thread = threading.Thread(
            target=self._alert_worker,
            daemon=True
        )
        self._worker_thread.start()
    
    def _alert_worker(self) -> None:
        """Worker thread to process alerts."""
        while self._is_active:
            try:
                alert_data = self._alert_queue.get(timeout=1.0)
                self._deliver_alert(alert_data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in alert worker: {e}")
    
    def trigger_alert(
        self,
        level: str = "WARNING",
        message: str = "Impairment detected",
        channels: Optional[List[AlertChannel]] = None
    ) -> bool:
        """
        Trigger an alert.
        
        Args:
            level: Alert level (WARNING, DANGER, CRITICAL)
            message: Alert message
            channels: Specific channels to use (None for all enabled)
            
        Returns:
            True if alert was triggered, False if throttled
        """
        with self._lock:
            # Check throttling
            if not self._should_trigger_alert():
                logger.debug("Alert throttled")
                return False
            
            # Update state
            self._last_alert_time = datetime.now()
            self._alert_count += 1
            
            # Check escalation
            if (self.config.enable_escalation and 
                self._alert_count % self.config.escalation_threshold == 0):
                self._escalation_level += 1
                logger.warning(f"Alert escalation level: {self._escalation_level}")
            
            # Queue alert
            alert_data = {
                "level": level,
                "message": message,
                "channels": channels or self._get_default_channels(),
                "escalation_level": self._escalation_level,
                "timestamp": datetime.now()
            }
            
            self._alert_queue.put(alert_data)
            
            return True
    
    def _should_trigger_alert(self) -> bool:
        """Check if alert should be triggered based on throttling."""
        if self._last_alert_time is None:
            return True
        
        time_since_last = (datetime.now() - self._last_alert_time).total_seconds()
        return time_since_last >= self.config.min_interval_sec
    
    def _get_default_channels(self) -> List[AlertChannel]:
        """Get list of enabled channels."""
        channels = []
        
        if self.config.audio_enabled:
            channels.append(AlertChannel.AUDIO)
        if self.config.visual_enabled:
            channels.append(AlertChannel.VISUAL)
        if self.config.haptic_enabled:
            channels.append(AlertChannel.HAPTIC)
        
        channels.append(AlertChannel.LOG)
        
        if self._callbacks:
            channels.append(AlertChannel.CALLBACK)
        
        return channels
    
    def _deliver_alert(self, alert_data: dict) -> None:
        """
        Deliver alert through specified channels.
        
        Args:
            alert_data: Alert data dictionary
        """
        channels = alert_data["channels"]
        
        # Audio alert
        if AlertChannel.AUDIO in channels:
            self._play_audio_alert(alert_data)
        
        # Visual alert (logged for now, can be extended)
        if AlertChannel.VISUAL in channels:
            logger.warning(f"VISUAL ALERT: {alert_data['message']}")
        
        # Haptic alert (placeholder)
        if AlertChannel.HAPTIC in channels:
            self._trigger_haptic(alert_data)
        
        # Log alert
        if AlertChannel.LOG in channels:
            logger.warning(
                f"Alert triggered - Level: {alert_data['level']}, "
                f"Message: {alert_data['message']}, "
                f"Escalation: {alert_data['escalation_level']}"
            )
        
        # Custom callbacks
        if AlertChannel.CALLBACK in channels:
            self._execute_callbacks(alert_data)
    
    def _play_audio_alert(self, alert_data: dict) -> None:
        """Play audio alert."""
        if not PYGAME_AVAILABLE or not self.config.audio_enabled:
            return
        
        try:
            # Load and play sound
            sound = pygame.mixer.Sound(self.config.audio_file)
            sound.set_volume(self.config.audio_volume)
            
            # Escalate volume/repetition for higher levels
            if alert_data["escalation_level"] > 0:
                sound.set_volume(min(1.0, self.config.audio_volume * 1.2))
            
            sound.play()
            
            # Play multiple times for critical alerts
            if alert_data["level"] == "CRITICAL":
                time.sleep(0.5)
                sound.play()
            
        except Exception as e:
            logger.error(f"Failed to play audio alert: {e}")
    
    def _trigger_haptic(self, alert_data: dict) -> None:
        """Trigger haptic feedback (placeholder for hardware integration)."""
        logger.debug(f"Haptic alert: {alert_data['message']}")
        # TODO: Integrate with haptic hardware (vibration motor, etc.)
    
    def _execute_callbacks(self, alert_data: dict) -> None:
        """Execute registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Callback execution failed: {e}")
    
    def register_callback(self, callback: Callable) -> None:
        """
        Register a custom alert callback.
        
        Args:
            callback: Function to call on alert (receives alert_data dict)
        """
        self._callbacks.append(callback)
        logger.info(f"Registered alert callback: {callback.__name__}")
    
    def reset(self) -> None:
        """Reset alert state."""
        with self._lock:
            self._last_alert_time = None
            self._alert_count = 0
            self._escalation_level = 0
        logger.info("Alert system reset")
    
    def get_statistics(self) -> dict:
        """Get alert system statistics."""
        with self._lock:
            return {
                "total_alerts": self._alert_count,
                "escalation_level": self._escalation_level,
                "last_alert_time": (
                    self._last_alert_time.isoformat() 
                    if self._last_alert_time else None
                ),
                "config": {
                    "audio_enabled": self.config.audio_enabled,
                    "visual_enabled": self.config.visual_enabled,
                    "haptic_enabled": self.config.haptic_enabled,
                    "min_interval_sec": self.config.min_interval_sec
                }
            }
    
    def shutdown(self) -> None:
        """Shutdown alert system."""
        self._is_active = False
        
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass
        
        logger.info("Alert system shutdown")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.shutdown()


def play_alarm_sound(audio_file: str, duration: float = 2.0) -> None:
    """
    Simple audio alert function (for backward compatibility).
    
    Args:
        audio_file: Path to audio file
        duration: Play duration in seconds
    """
    if not PYGAME_AVAILABLE:
        logger.warning("pygame not available, cannot play audio")
        return
    
    try:
        pygame.mixer.init()
        sound = pygame.mixer.Sound(audio_file)
        sound.play()
        time.sleep(duration)
    except Exception as e:
        logger.error(f"Failed to play alarm: {e}")
