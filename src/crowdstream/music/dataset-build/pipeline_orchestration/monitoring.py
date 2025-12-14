"""
Monitoring and Error Handling for CrowdStream Music Dataset Pipeline

This module provides comprehensive monitoring, error handling, and alerting
capabilities for the Dagster pipeline execution.
"""

from dagster import (
    DefaultSensorStatus,
    RunFailureSensorContext,
    RunRequest,
    SensorResult,
    SkipReason,
    asset_sensor,
    failure_hook,
    get_dagster_logger,
    run_failure_sensor,
    sensor,
    success_hook
)
from typing import Dict, List, Optional, Any
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass, asdict
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
import os

logger = get_dagster_logger()

@dataclass
class PipelineMetrics:
    """Data class for pipeline execution metrics."""
    run_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    assets_succeeded: int = 0
    assets_failed: int = 0
    total_tracks_processed: int = 0
    total_stems_created: int = 0
    total_segments_created: int = 0
    error_messages: List[str] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate asset success rate."""
        total_assets = self.assets_succeeded + self.assets_failed
        if total_assets == 0:
            return 0.0
        return (self.assets_succeeded / total_assets) * 100

class MetricsCollector:
    """Collects and stores pipeline execution metrics."""
    
    def __init__(self, metrics_file: str = "data/music/metrics/pipeline_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_run_metrics: Optional[PipelineMetrics] = None
    
    def start_run(self, run_id: str) -> PipelineMetrics:
        """Initialize metrics for a new pipeline run."""
        self.current_run_metrics = PipelineMetrics(
            run_id=run_id,
            start_time=time.time()
        )
        return self.current_run_metrics
    
    def end_run(self, status: str):
        """Finalize metrics for the current run."""
        if self.current_run_metrics:
            self.current_run_metrics.end_time = time.time()
            self.current_run_metrics.status = status
            self._save_metrics()
    
    def update_asset_result(self, asset_name: str, success: bool, metadata: Dict[str, Any] = None):
        """Update metrics based on asset execution result."""
        if not self.current_run_metrics:
            return
        
        if success:
            self.current_run_metrics.assets_succeeded += 1
        else:
            self.current_run_metrics.assets_failed += 1
        
        # Extract specific metrics from asset metadata
        if metadata:
            self.current_run_metrics.total_tracks_processed += metadata.get('total_tracks', 0)
            self.current_run_metrics.total_stems_created += metadata.get('stems_created', 0)
            self.current_run_metrics.total_segments_created += metadata.get('segments_created', 0)
    
    def add_error(self, error_message: str):
        """Add an error message to current run metrics."""
        if self.current_run_metrics:
            self.current_run_metrics.error_messages.append(error_message)
    
    def _save_metrics(self):
        """Save current run metrics to file."""
        if not self.current_run_metrics:
            return
        
        # Load existing metrics
        existing_metrics = []
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    existing_metrics = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_metrics = []
        
        # Add current run metrics
        existing_metrics.append(asdict(self.current_run_metrics))
        
        # Keep only last 100 runs
        if len(existing_metrics) > 100:
            existing_metrics = existing_metrics[-100:]
        
        # Save updated metrics
        with open(self.metrics_file, 'w') as f:
            json.dump(existing_metrics, f, indent=2)
        
        logger.info(f"Saved pipeline metrics to {self.metrics_file}")
    
    def get_recent_metrics(self, days: int = 7) -> List[PipelineMetrics]:
        """Get metrics from recent pipeline runs."""
        if not self.metrics_file.exists():
            return []
        
        try:
            with open(self.metrics_file, 'r') as f:
                metrics_data = json.load(f)
            
            cutoff_time = time.time() - (days * 24 * 3600)
            recent_metrics = []
            
            for data in metrics_data:
                if data['start_time'] >= cutoff_time:
                    metrics = PipelineMetrics(**data)
                    recent_metrics.append(metrics)
            
            return recent_metrics
            
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load metrics: {e}")
            return []
    
    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate a comprehensive metrics report."""
        recent_metrics = self.get_recent_metrics(days)
        
        if not recent_metrics:
            return {"error": "No metrics available"}
        
        # Calculate aggregated statistics
        successful_runs = [m for m in recent_metrics if m.status == "success"]
        failed_runs = [m for m in recent_metrics if m.status == "failed"]
        
        total_runs = len(recent_metrics)
        success_rate = (len(successful_runs) / total_runs) * 100 if total_runs > 0 else 0
        
        # Calculate average processing metrics
        total_tracks = sum(m.total_tracks_processed for m in recent_metrics)
        total_stems = sum(m.total_stems_created for m in recent_metrics)
        total_segments = sum(m.total_segments_created for m in recent_metrics)
        
        # Calculate average duration for successful runs
        successful_durations = [m.duration_seconds for m in successful_runs if m.duration_seconds]
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Most common errors
        all_errors = []
        for m in recent_metrics:
            all_errors.extend(m.error_messages)
        
        error_frequency = {}
        for error in all_errors:
            error_frequency[error] = error_frequency.get(error, 0) + 1
        
        common_errors = sorted(error_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        
        report = {
            "period_days": days,
            "total_runs": total_runs,
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "success_rate_percent": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "total_tracks_processed": total_tracks,
            "total_stems_created": total_stems,
            "total_segments_created": total_segments,
            "most_common_errors": common_errors,
            "last_run_time": max(m.start_time for m in recent_metrics) if recent_metrics else None
        }
        
        return report

# Global metrics collector instance
metrics_collector = MetricsCollector()

class AlertManager:
    """Manages alerts and notifications for pipeline failures."""
    
    def __init__(self):
        self.email_enabled = self._check_email_config()
        self.webhook_url = os.getenv('CROWDSTREAM_WEBHOOK_URL')
        self.alert_threshold_failures = int(os.getenv('CROWDSTREAM_ALERT_THRESHOLD', '3'))
    
    def _check_email_config(self) -> bool:
        """Check if email configuration is available."""
        required_vars = [
            'CROWDSTREAM_SMTP_SERVER',
            'CROWDSTREAM_SMTP_PORT', 
            'CROWDSTREAM_EMAIL_USER',
            'CROWDSTREAM_EMAIL_PASSWORD',
            'CROWDSTREAM_ALERT_RECIPIENTS'
        ]
        return all(os.getenv(var) for var in required_vars)
    
    def send_failure_alert(self, run_id: str, error_message: str, asset_name: str = None):
        """Send failure alert via configured channels."""
        try:
            # Check if we should send alert based on recent failure frequency
            if not self._should_send_alert():
                logger.info("Skipping alert due to threshold limits")
                return
            
            alert_message = self._format_alert_message(run_id, error_message, asset_name)
            
            # Send email alert
            if self.email_enabled:
                self._send_email_alert(alert_message, run_id)
            
            # Send webhook alert
            if self.webhook_url:
                self._send_webhook_alert(alert_message, run_id)
            
            logger.info(f"Sent failure alert for run {run_id}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _should_send_alert(self) -> bool:
        """Determine if alert should be sent based on recent failures."""
        recent_metrics = metrics_collector.get_recent_metrics(days=1)
        recent_failures = [m for m in recent_metrics if m.status == "failed"]
        
        return len(recent_failures) >= self.alert_threshold_failures
    
    def _format_alert_message(self, run_id: str, error_message: str, asset_name: str = None) -> str:
        """Format alert message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
CrowdStream Pipeline Failure Alert
=====================================

Time: {timestamp}
Run ID: {run_id}
Asset: {asset_name or 'Unknown'}

Error Message:
{error_message}

Recent Pipeline Status:
{self._get_recent_status_summary()}

Please check the Dagster UI for more details.
        """.strip()
        
        return message
    
    def _get_recent_status_summary(self) -> str:
        """Get summary of recent pipeline runs."""
        recent_metrics = metrics_collector.get_recent_metrics(days=7)
        
        if not recent_metrics:
            return "No recent runs found"
        
        successful = len([m for m in recent_metrics if m.status == "success"])
        failed = len([m for m in recent_metrics if m.status == "failed"])
        total = len(recent_metrics)
        
        return f"Last 7 days: {successful} successful, {failed} failed out of {total} total runs"
    
    def _send_email_alert(self, message: str, run_id: str):
        """Send email alert."""
        try:
            smtp_server = os.getenv('CROWDSTREAM_SMTP_SERVER')
            smtp_port = int(os.getenv('CROWDSTREAM_SMTP_PORT', '587'))
            email_user = os.getenv('CROWDSTREAM_EMAIL_USER')
            email_password = os.getenv('CROWDSTREAM_EMAIL_PASSWORD')
            recipients = os.getenv('CROWDSTREAM_ALERT_RECIPIENTS').split(',')
            
            msg = MimeMultipart()
            msg['From'] = email_user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"CrowdStream Pipeline Failure - {run_id}"
            
            msg.attach(MimeText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, message: str, run_id: str):
        """Send webhook alert (e.g., to Slack, Discord, etc.)."""
        try:
            import requests
            
            payload = {
                "text": f"CrowdStream Pipeline Failure - {run_id}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```\n{message}\n```"
                        }
                    }
                ]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("Webhook alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

# Global alert manager instance
alert_manager = AlertManager()

# Dagster hooks for monitoring
@success_hook
def success_monitoring_hook(context):
    """Hook executed on successful asset materialization."""
    try:
        asset_name = context.solid_def.name if hasattr(context, 'solid_def') else 'unknown'
        run_id = context.run_id
        
        # Update metrics
        metadata = context.asset_materialization.metadata if hasattr(context, 'asset_materialization') else {}
        metrics_collector.update_asset_result(asset_name, success=True, metadata=metadata)
        
        logger.info(f"Asset {asset_name} completed successfully in run {run_id}")
        
    except Exception as e:
        logger.error(f"Error in success monitoring hook: {e}")

@failure_hook
def failure_monitoring_hook(context):
    """Hook executed on asset materialization failure."""
    try:
        asset_name = context.solid_def.name if hasattr(context, 'solid_def') else 'unknown'
        run_id = context.run_id
        
        # Extract error message
        error_message = str(context.failure_data.error) if hasattr(context, 'failure_data') else "Unknown error"
        
        # Update metrics
        metrics_collector.update_asset_result(asset_name, success=False)
        metrics_collector.add_error(f"{asset_name}: {error_message}")
        
        # Send alert
        alert_manager.send_failure_alert(run_id, error_message, asset_name)
        
        logger.error(f"Asset {asset_name} failed in run {run_id}: {error_message}")
        
    except Exception as e:
        logger.error(f"Error in failure monitoring hook: {e}")

@run_failure_sensor(default_status=DefaultSensorStatus.RUNNING)
def pipeline_failure_sensor(context: RunFailureSensorContext):
    """Sensor to detect and respond to pipeline run failures."""
    try:
        run_id = context.dagster_run.run_id
        
        # End the run in metrics
        metrics_collector.end_run("failed")
        
        # Generate comprehensive failure report
        failure_logs = context.failure_data.error if hasattr(context, 'failure_data') else "No error details available"
        
        # Send comprehensive failure alert
        alert_manager.send_failure_alert(
            run_id=run_id,
            error_message=f"Pipeline run failed: {failure_logs}",
            asset_name="pipeline"
        )
        
        logger.error(f"Pipeline run {run_id} failed")
        
        # Could trigger automatic retry logic here if desired
        # return RunRequest(run_key=f"retry_{run_id}")
        
    except Exception as e:
        logger.error(f"Error in pipeline failure sensor: {e}")

@sensor(
    name="data_quality_sensor",
    default_status=DefaultSensorStatus.STOPPED
)
def data_quality_sensor(context):
    """Sensor to monitor data quality metrics."""
    try:
        # Check for data quality issues
        metadata_dir = Path("data/music/metadata")
        
        if not metadata_dir.exists():
            return SkipReason("Metadata directory not found")
        
        # Check final dataset quality
        final_dataset_path = metadata_dir / "final_dataset.csv"
        
        if final_dataset_path.exists():
            df = pd.read_csv(final_dataset_path)
            
            # Define quality thresholds
            min_tracks = 100
            min_sample_rate = 80.0  # percentage
            min_stems_rate = 60.0   # percentage
            
            # Check quality metrics
            total_tracks = len(df)
            sample_rate = (df['has_sample'].sum() / total_tracks) * 100
            stems_rate = (df['has_stems'].sum() / total_tracks) * 100
            
            quality_issues = []
            
            if total_tracks < min_tracks:
                quality_issues.append(f"Low track count: {total_tracks} < {min_tracks}")
            
            if sample_rate < min_sample_rate:
                quality_issues.append(f"Low sample rate: {sample_rate:.1f}% < {min_sample_rate}%")
            
            if stems_rate < min_stems_rate:
                quality_issues.append(f"Low stems rate: {stems_rate:.1f}% < {min_stems_rate}%")
            
            if quality_issues:
                # Send quality alert
                alert_message = f"Data quality issues detected:\n" + "\n".join(quality_issues)
                alert_manager.send_failure_alert(
                    run_id="quality_check",
                    error_message=alert_message,
                    asset_name="data_quality"
                )
                
                logger.warning(f"Data quality issues: {quality_issues}")
            else:
                logger.info("Data quality check passed")
        
        return SkipReason("Data quality check completed")
        
    except Exception as e:
        logger.error(f"Error in data quality sensor: {e}")
        return SkipReason(f"Data quality sensor error: {e}")

# Export monitoring components
__all__ = [
    'MetricsCollector',
    'AlertManager', 
    'PipelineMetrics',
    'metrics_collector',
    'alert_manager',
    'success_monitoring_hook',
    'failure_monitoring_hook',
    'pipeline_failure_sensor',
    'data_quality_sensor'
]