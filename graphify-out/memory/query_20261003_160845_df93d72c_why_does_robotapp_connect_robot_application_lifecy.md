---
type: "query"
date: "2026-10-03T16:08:45.057693+00:00"
question: "Why does RobotApp connect Robot Application Lifecycle to Reactive Strategy, Camera Acquisition, Camera Test Doubles, Arduino Command Telemetry, Vision Frame Geometry, Camera Preview UI, Robot Runtime Context, Robot Control Flow, Vision Execution Loop, Ultrasonic Monitoring, PID Motor Control, Test Configuration, Serial Manager?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["RobotApp", "RobotContext", "Strategy", "VisionPipeline", "RobotStateMachine", "SerialManager", "UltrasonicMonitor", "PreviewWindow", "ExecutionLoopController", "CameraManager"]
---

# Q: Why does RobotApp connect Robot Application Lifecycle to Reactive Strategy, Camera Acquisition, Camera Test Doubles, Arduino Command Telemetry, Vision Frame Geometry, Camera Preview UI, Robot Runtime Context, Robot Control Flow, Vision Execution Loop, Ultrasonic Monitoring, PID Motor Control, Test Configuration, Serial Manager?

## Answer

Expanded from the original query via graph vocabulary: [robot, app, strategy, camera, vision, serial, control, ultrasonic, manager, lifecycle, runtime, frame]. The graph places RobotApp in Robot Application Lifecycle at raspberry/main.py:L97, with degree 42. Extracted method edges connect it to orchestration methods including .run (L151), ._vision_loop (L177), ._process_cycle (L271), ._process_messages (L333), ._ensure_sensors_armed (L362), and .stop (L373). Inferred uses edges connect it to RobotContext (raspberry/config.py:L247), Strategy (raspberry/strategy.py:L18), VisionPipeline (raspberry/vision/pipeline.py:L64), RobotStateMachine (raspberry/state_machine.py:L14), SerialManager, UltrasonicMonitor, PreviewWindow, ExecutionLoopController, and CameraManager. RobotApp has direct neighbors in 13 other communities, including camera acquisition, vision geometry, strategy, runtime context, serial, ultrasonic monitoring, preview UI, execution loop, control flow, PID, Arduino telemetry, test doubles, and test configuration. This makes it an assembly/orchestration hub rather than a single algorithm. The uses edges are INFERRED; they should be confirmed against source before treating them as definitive.

## Outcome

- Signal: useful

## Source Nodes

- RobotApp
- RobotContext
- Strategy
- VisionPipeline
- RobotStateMachine
- SerialManager
- UltrasonicMonitor
- PreviewWindow
- ExecutionLoopController
- CameraManager