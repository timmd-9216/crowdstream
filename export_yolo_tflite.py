#!/usr/bin/env python3
"""
Export YOLOv8n-pose to TFLite INT8 for Raspberry Pi optimization
Run this once to create optimized model
"""

from ultralytics import YOLO

print("🚀 Exporting YOLOv8n-pose to TFLite INT8...")
print("This will create an optimized model for Raspberry Pi 4")
print("")

# Load the model
model = YOLO('yolov8n-pose.pt')

# Export to TFLite with INT8 quantization
print("📦 Exporting (this may take a few minutes)...")
model.export(
    format='tflite',
    int8=True,
    imgsz=416,  # Input size
)

print("")
print("✅ Export complete!")
print("")
print("Model saved as: yolov8n-pose_saved_model/yolov8n-pose_int8.tflite")
print("")
print("To use this model, update your config:")
print('  "model": "yolov8n-pose_saved_model/yolov8n-pose_int8.tflite"')
print("")
print("Expected performance on RPi4:")
print("  • PyTorch (.pt): 3-5 FPS")
print("  • TFLite INT8:  12-18 FPS (3-4x faster!)")
print("")
