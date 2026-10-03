# Graph Report - obr-2026-robot  (2026-10-03)

## Corpus Check
- 137 files · ~104,467 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .ino 7, (none) 2, .service 1)

## Summary
- 1093 nodes · 2335 edges · 67 communities (33 shown, 34 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Behavior State Management
- Camera Acquisition
- Motor Calibration
- Rescue Detection
- Arduino Command Telemetry
- Vision Frame Geometry
- Line Detection
- Camera Preview UI
- Robot Runtime Context
- Obstacle Detection
- Line Following Tests
- Robot Control Flow
- Serial Communication
- Navigation Configuration
- Graphify Documentation
- Vision Execution Loop
- Ultrasonic Monitoring
- Ball Detection
- PID Motor Control
- Sensor Interfaces
- Robot Application Lifecycle
- IMU Measurement
- Monitoring Dashboard
- Arduino Ultrasonic Sensor
- Sensor Management
- Competition State Logic
- Serial Manager
- Ball Tracking
- Distance Measurement
- Reactive Strategy
- Error-Proofing Principles
- Camera Test Doubles
- Future Encoder Sensor
- Encoder Sensor
- Implementation Standards
- Future LiDAR Sensor
- Unavailable Ultrasonic Sensor
- Engineering Reliability
- Logging Configuration
- Robot Context Tests
- Serial Test Doubles
- Skill Discovery
- Quality Playbook
- Dependency Management
- Graph Query Workflow
- Bug Reproduction
- Instruction Blueprinting
- Competition State Machine
- Omni Motion Firmware Tests
- Technical Spike Research
- Mission State Management
- Camera Test Script
- Claude Project Guidance
- Robot Startup Script
- Development Setup Script
- Service Shutdown Script
- Grill Me Metadata
- Rescue Mission Concept

## God Nodes (most connected - your core abstractions)
1. `RobotContext` - 50 edges
2. `StateResult` - 45 edges
3. `CameraManager` - 42 edges
4. `RobotApp` - 42 edges
5. `Behavior` - 35 edges
6. `PreviewWindow` - 33 edges
7. `SerialTransport` - 30 edges
8. `LineDetection` - 30 edges
9. `LineDetector` - 30 edges
10. `VisionPipeline` - 29 edges

## Surprising Connections (you probably didn't know these)
- `CompetitionArchitectureTests` --uses--> `BehaviorManager`  [INFERRED]
  tests/test_competition_architecture.py → competition/behavior_manager.py
- `RobotContextTTLTests` --uses--> `RobotContext`  [INFERRED]
  tests/test_context_ttl.py → raspberry/config.py
- `FollowLineTests` --uses--> `RobotContext`  [INFERRED]
  tests/test_follow_line.py → raspberry/config.py
- `PreviewRenderTests` --uses--> `RobotContext`  [INFERRED]
  tests/test_preview.py → raspberry/config.py
- `Robot` --uses--> `RobotContext`  [INFERRED]
  tests/test_state_flow.py → raspberry/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Extraction and Graph-Build Pipeline** — _claude_skills_graphify_skill_file_detection, _claude_skills_graphify_skill_ast_extraction, _claude_skills_graphify_skill_semantic_extraction, _claude_skills_graphify_skill_graph_build_and_cluster [EXTRACTED 1.00]
- **Robot perception-to-actuation architecture** — readme_computer_vision_pipeline, readme_world_model, readme_strategy, readme_state_machine, readme_serial_transport, readme_arduino_low_level_control [EXTRACTED 1.00]
- **Quality Playbook audit lifecycle** — _github_skills_quality_playbook_skill_exploration_to_requirements, _github_skills_quality_playbook_skill_three_pass_code_review, _github_skills_quality_playbook_skill_council_of_three, _github_skills_quality_playbook_skill_tdd_verified_patches [EXTRACTED 1.00]
- **Robot hardware assembly components** — hardware_physical_assembly, hardware_ultrasonic_sensor, hardware_gripper_servo, hardware_raspberry_pi_arduino_link [EXTRACTED 1.00]

## Communities (67 total, 34 thin omitted)

### Community 0 - "Behavior State Management"
Cohesion: 0.06
Nodes (17): BehaviorManager, AlignBallBehavior, Behavior, CaptureBallBehavior, DropBallBehavior, FinishBehavior, FollowLineBehavior, GapBehavior (+9 more)

### Community 1 - "Camera Acquisition"
Cohesion: 0.06
Nodes (8): apply_camera_orientation(), CameraInterface, CameraManager, opencv_has_gstreamer(), CameraDiagnosticTests, CameraManagerTests, DummyCapture, CameraOrientationTests

### Community 2 - "Motor Calibration"
Cohesion: 0.06
Nodes (53): Bench Validation of Motor Calibration, Motor Calibration Guide, fit_to_motor_deadband, Per-Motor Minimum Duty, Motor Deadband, Relative Motor Gain Calibration, Ultrasonic Reading Bias from Software PWM, Arduino Mega 2560 (+45 more)

### Community 3 - "Rescue Detection"
Cohesion: 0.08
Nodes (9): RescueDetector, SafeZoneDetector, ZoneDetection, BallDetectorTests, floor_frame(), RescueDetectorTests, SafeZoneDetectorTests, with_ball() (+1 more)

### Community 4 - "Arduino Command Telemetry"
Cohesion: 0.08
Nodes (11): apply_motor_orientation(), _clamp(), fit_to_motor_deadband(), _format_component(), _is_expressible(), normalize_motor_command(), _wheel_speeds(), format_arduino_payload() (+3 more)

### Community 5 - "Vision Frame Geometry"
Cohesion: 0.08
Nodes (8): FrameView, VisionPipeline, DummyDetector, VisionPipelineTests, FrameViewMappingTests, LegacyDetector, PerDetectorRoiTests, RecordingDetector

### Community 6 - "Line Detection"
Cohesion: 0.11
Nodes (6): LineDetector, LineBandTests, path_scene(), AdaptiveLineDetectorTests, path_scene(), scene()

### Community 7 - "Camera Preview UI"
Cohesion: 0.12
Nodes (4): PreviewWindow, make_context(), PreviewEnablementTests, PreviewRenderTests

### Community 8 - "Robot Runtime Context"
Cohesion: 0.12
Nodes (5): RobotContext, RobotStateMachine, StateResult, DummyState, RobotStateMachineTests

### Community 9 - "Obstacle Detection"
Cohesion: 0.09
Nodes (5): build_vision_detectors(), ObstacleDetectionResult, ObstacleAnalysis, VisionBasedObstacleDetector, ObstacleDetectorTests

### Community 10 - "Line Following Tests"
Cohesion: 0.15
Nodes (9): LineDetection, VisionResult, FollowLineTests, parse_move(), run_state(), _context(), CornerSteeringTests, parse_move() (+1 more)

### Community 11 - "Robot Control Flow"
Cohesion: 0.23
Nodes (9): AlignBallState, AvoidObstacleState, CalibrationState, CaptureBallState, DropBallState, EnterRescueState, FinishState, build_main_machine() (+1 more)

### Community 13 - "Navigation Configuration"
Cohesion: 0.14
Nodes (7): load_config(), Navigator, SensorFusion, Detector, LineDetector, WorldModel, CompetitionArchitectureTests

### Community 14 - "Graphify Documentation"
Cohesion: 0.08
Nodes (23): Graphify Claude Code Entrypoint, Graphify File Watcher, URL Ingestion, Graph Export Targets, Graphify MCP Server, Entity and Edge Extraction Contract, Cross-Repository Graph Merge, Subfolder Graph Merge (+15 more)

### Community 15 - "Vision Execution Loop"
Cohesion: 0.09
Nodes (5): ExecutionLoopController, FakeTime, RuntimeControllerTests, DummyDetector, VisionResultFreshnessTests

### Community 16 - "Ultrasonic Monitoring"
Cohesion: 0.10
Nodes (5): UltrasonicMonitor, FakeClock, FakeSerial, make_app(), SensorArmingTests

### Community 17 - "Ball Detection"
Cohesion: 0.16
Nodes (6): ground_distance_cm(), clean_mask(), contour_metrics(), looks_like_ball(), looks_like_line(), ShapeMetrics

### Community 20 - "Sensor Interfaces"
Cohesion: 0.13
Nodes (3): DistanceSensor, IMUSensor, ObstacleDetector

### Community 22 - "Robot Application Lifecycle"
Cohesion: 0.18
Nodes (3): RobotApp, update_context_from_serial_message(), UltrasonicObstacleTests

### Community 23 - "IMU Measurement"
Cohesion: 0.13
Nodes (3): IMUMeasurement, get_future_sensor_info(), IMUSensorFuture

### Community 29 - "Serial Manager"
Cohesion: 0.23
Nodes (5): SerialManager, SearchBallState, SearchLineState, SearchSafeZoneState, PIDAndSpeedTests

### Community 30 - "Ball Tracking"
Cohesion: 0.23
Nodes (3): Ball, BallDetector, BallDistanceUsesTheViewTests

### Community 32 - "Reactive Strategy"
Cohesion: 0.17
Nodes (4): Strategy, StrategyDecision, FakeClock, StrategyTests

### Community 33 - "Error-Proofing Principles"
Cohesion: 0.25
Nodes (8): Control-Warning-Detection Ladder, Poka-Yoke Skill, Contact Fixed-Value and Motion-Step Inspection Lenses, Defect-Mistake-Hazard Distinction, Chain of Responsibility Pattern, Refactor Skill, Small-Step Refactoring, Strategy Pattern

### Community 34 - "Camera Test Doubles"
Cohesion: 0.18
Nodes (3): DummyCamera, DummyPreview, make_robot_app()

### Community 37 - "Implementation Standards"
Cohesion: 0.28
Nodes (5): Implement Prompt, Review Prompt, Regression Analysis, Review and Refactor Skill, Review and Refactor Workflow

### Community 44 - "Skill Discovery"
Cohesion: 0.53
Nodes (3): Agent Skill Stack Skill, Skill Routing Recall Check, Agent Skill Stack

### Community 45 - "Quality Playbook"
Cohesion: 0.53
Nodes (5): Council of Three Spec Audit, Quality Playbook Skill, Quality Playbook, TDD-Verified Patches, Three-Pass Code Review

### Community 46 - "Dependency Management"
Cohesion: 0.40
Nodes (5): Desktop Development Dependencies, Development Requirements, Runtime Requirements, Raspberry Pi System Packages, Runtime Python Dependencies

### Community 47 - "Graph Query Workflow"
Cohesion: 0.67
Nodes (4): BFS and DFS Graph Traversal, Query Result Feedback Loop, Graph Vocabulary Query Expansion, Existing-Graph Fast Path

### Community 48 - "Bug Reproduction"
Cohesion: 0.83
Nodes (3): Bug Reproduction Brief Skill, Expected Versus Actual Behavior, Reproducibility Evidence

### Community 49 - "Instruction Blueprinting"
Cohesion: 0.67
Nodes (3): Codebase Pattern Analysis, Copilot Instructions Blueprint, Copilot Instructions Blueprint Generator Skill

### Community 51 - "Omni Motion Firmware Tests"
Cohesion: 0.83
Nodes (3): _read_firmware(), test_legacy_robot_sketch_keeps_the_same_omni_matrix(), test_robot_mega_uses_explicit_omni_motor_matrix()

## Knowledge Gaps
- **31 isolated node(s):** `run_robot.sh script`, `setup_dev_env.sh script`, `stop_robot_service.sh script`, `test_camera.sh script`, `Grill Me Agent Metadata` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 344 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CameraManager` connect `Camera Acquisition` to `Robot Control Flow`, `Python Utility Dependencies`, `Test Configuration`, `Robot Application Lifecycle`, `Serial Manager`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `RobotApp` connect `Robot Application Lifecycle` to `Reactive Strategy`, `Camera Acquisition`, `Camera Test Doubles`, `Arduino Command Telemetry`, `Vision Frame Geometry`, `Camera Preview UI`, `Robot Runtime Context`, `Robot Control Flow`, `Vision Execution Loop`, `Ultrasonic Monitoring`, `PID Motor Control`, `Test Configuration`, `Serial Manager`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `RobotContext` connect `Robot Runtime Context` to `Reactive Strategy`, `Camera Test Doubles`, `Camera Preview UI`, `Robot Context Tests`, `Robot Control Flow`, `Line Following Tests`, `Ultrasonic Monitoring`, `Python Utility Dependencies`, `Test Configuration`, `Robot Application Lifecycle`, `Competition State Logic`, `Vision Image Processing`, `Serial Manager`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `RobotContext` (e.g. with `RobotApp` and `RobotContextTTLTests`) actually correct?**
  _`RobotContext` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `StateResult` (e.g. with `AlignBallState` and `AvoidObstacleState`) actually correct?**
  _`StateResult` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `CameraManager` (e.g. with `RobotApp` and `CameraDiagnosticTests`) actually correct?**
  _`CameraManager` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `RobotApp` (e.g. with `CameraManager` and `RobotContext`) actually correct?**
  _`RobotApp` has 23 INFERRED edges - model-reasoned connections that need verification._