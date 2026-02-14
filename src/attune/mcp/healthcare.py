"""Healthcare CDS MCP Server Extension.

Extends EmpathyMCPServer with clinical decision support tools.
Enforces Redis requirement and adds HIPAA audit logging.

Entry point: python -m attune.mcp.healthcare

Copyright 2026 Smart AI Memory, LLC
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from attune.mcp.server import EmpathyMCPServer, handle_request

logger = logging.getLogger(__name__)


class HealthcareMCPServer(EmpathyMCPServer):
    """MCP server for healthcare clinical decision support.

    Inherits all 18 attune-ai tools and adds 9 healthcare-specific tools.
    Requires Redis for real-time coordination and audit logging.
    """

    def __init__(self) -> None:
        """Initialize the healthcare MCP server.

        Calls parent init (registers 18 base tools), then adds
        healthcare tools and verifies Redis availability.
        """
        super().__init__()
        self._monitor: Any = None
        self._audit_log: list[dict[str, Any]] = []

        # Register healthcare tools on top of base tools
        healthcare_tools = self._register_healthcare_tools()
        self.tools.update(healthcare_tools)

        # Verify Redis is available (required for healthcare)
        self._check_redis()

    def _check_redis(self) -> None:
        """Verify Redis is available.

        Healthcare CDS requires Redis for real-time coordination,
        audit logging, and distributed state. Logs a warning if
        Redis is not available but does not raise — allows the
        server to start so it can return helpful error messages.
        """
        try:
            import redis

            r = redis.Redis()
            r.ping()
            logger.info("Redis connection verified")
        except ImportError:
            logger.warning(
                "Redis package not installed. Healthcare CDS requires Redis. "
                "Install with: pip install attune-ai[redis]"
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Log but don't crash — server can still return error messages
            logger.warning(f"Redis not available: {e}. Healthcare CDS requires Redis.")

    def _get_monitor(self) -> Any:
        """Lazily initialize ClinicalProtocolMonitor.

        Returns:
            ClinicalProtocolMonitor instance

        Raises:
            ImportError: If attune-healthcare is not installed
        """
        if self._monitor is None:
            from attune_healthcare.monitors import ClinicalProtocolMonitor

            self._monitor = ClinicalProtocolMonitor()
        return self._monitor

    @staticmethod
    def _normalize_sensor_data(sensor_data: str) -> str:
        """Normalize sensor data to the format expected by SimpleJSONParser.

        SimpleJSONParser expects: {"vitals": {"hr": 110, ...}}
        Users may provide flat JSON: {"hr": 110, ...}

        Args:
            sensor_data: Raw sensor data JSON string

        Returns:
            Normalized JSON string
        """
        try:
            parsed = json.loads(sensor_data)
        except json.JSONDecodeError:
            return sensor_data

        if isinstance(parsed, dict) and "vitals" not in parsed:
            vital_keys = {
                "hr",
                "heart_rate",
                "systolic_bp",
                "diastolic_bp",
                "bp",
                "respiratory_rate",
                "rr",
                "temp_f",
                "temp_c",
                "temperature",
                "o2_sat",
                "spo2",
                "mental_status",
                "pain",
            }
            vitals = {k: v for k, v in parsed.items() if k in vital_keys}
            if vitals:
                meta = {k: v for k, v in parsed.items() if k not in vital_keys}
                wrapped = {**meta, "vitals": vitals}
                return json.dumps(wrapped)

        return sensor_data

    def _audit(self, tool_name: str, args: dict[str, Any]) -> None:
        """Record an audit log entry for HIPAA compliance.

        Logs tool invocations with anonymized parameters.
        Does not log actual patient data — only tool name, timestamp,
        and parameter keys.

        Args:
            tool_name: Name of the tool invoked
            args: Tool arguments (only keys are logged, not values)
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "param_keys": list(args.keys()),
        }
        self._audit_log.append(entry)
        logger.info(f"AUDIT: {tool_name} called with params: {list(args.keys())}")

    def _register_healthcare_tools(self) -> dict[str, dict[str, Any]]:
        """Register healthcare-specific MCP tools.

        Returns:
            Dictionary of 9 healthcare tool definitions
        """
        return {
            "healthcare_list_protocols": {
                "name": "healthcare_list_protocols",
                "description": (
                    "List available clinical protocols. Returns protocol names "
                    "that can be loaded for patient monitoring."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            "healthcare_load_protocol": {
                "name": "healthcare_load_protocol",
                "description": (
                    "Load a clinical protocol for a patient. Activates the "
                    "protocol for subsequent analysis calls."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "protocol_name": {
                            "type": "string",
                            "description": "Protocol name (sepsis, cardiac, respiratory, post_operative)",
                        },
                        "patient_context": {
                            "type": "object",
                            "description": "Additional patient context (age, conditions, etc.)",
                        },
                    },
                    "required": ["patient_id", "protocol_name"],
                },
            },
            "healthcare_analyze": {
                "name": "healthcare_analyze",
                "description": (
                    "Full patient analysis: protocol compliance check, trajectory "
                    "prediction, alerts, and recommendations. Requires a loaded protocol."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "sensor_data": {
                            "type": "string",
                            "description": (
                                "Vital signs as JSON string, e.g. "
                                '{"hr": 110, "systolic_bp": 85, "respiratory_rate": 24}'
                            ),
                        },
                        "protocol_name": {
                            "type": "string",
                            "description": "Protocol name (loads automatically if not already loaded)",
                        },
                        "sensor_format": {
                            "type": "string",
                            "description": "Input format: simple_json (default) or fhir",
                            "default": "simple_json",
                        },
                    },
                    "required": ["patient_id", "sensor_data", "protocol_name"],
                },
            },
            "healthcare_check_compliance": {
                "name": "healthcare_check_compliance",
                "description": (
                    "Check protocol compliance for patient vital signs. "
                    "Returns activation status, deviations, and alert level."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "sensor_data": {
                            "type": "string",
                            "description": "Vital signs as JSON string",
                        },
                        "protocol_name": {
                            "type": "string",
                            "description": "Protocol name to check against",
                        },
                    },
                    "required": ["patient_id", "sensor_data", "protocol_name"],
                },
            },
            "healthcare_predict_trajectory": {
                "name": "healthcare_predict_trajectory",
                "description": (
                    "Predict vital sign trajectory and estimate time to critical "
                    "thresholds. Uses Level 4 anticipatory analysis."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "sensor_data": {
                            "type": "string",
                            "description": "Vital signs as JSON string",
                        },
                    },
                    "required": ["patient_id", "sensor_data"],
                },
            },
            "healthcare_ecg_analyze": {
                "name": "healthcare_ecg_analyze",
                "description": (
                    "Analyze ECG metrics from PhysioNet-derived data. Classifies "
                    "arrhythmias, computes HRV, and flags clinical concerns."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ecg_metrics": {
                            "type": "object",
                            "description": (
                                "ECG metrics dict with hr_mean, hr_min, hr_max, "
                                "pvc_burden_pct, rr_std_ms, arrhythmia_events, total_beats"
                            ),
                        },
                        "patient_context": {
                            "type": "object",
                            "description": "Optional patient context (age, sex, medications)",
                        },
                    },
                    "required": ["ecg_metrics"],
                },
            },
            "healthcare_cds_assess": {
                "name": "healthcare_cds_assess",
                "description": (
                    "Full CDS assessment: protocol compliance + ECG analysis + "
                    "clinical reasoning. Orchestrates multiple agents for "
                    "comprehensive clinical decision support."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "sensor_data": {
                            "type": "string",
                            "description": "Vital signs as JSON string",
                        },
                        "protocol_name": {
                            "type": "string",
                            "description": "Protocol name (sepsis, cardiac, respiratory, post_operative)",
                        },
                        "ecg_metrics": {
                            "type": "object",
                            "description": "Optional ECG metrics from PhysioNet converter",
                        },
                        "patient_context": {
                            "type": "object",
                            "description": "Optional patient context (age, sex, medications)",
                        },
                    },
                    "required": ["patient_id", "sensor_data", "protocol_name"],
                },
            },
            "healthcare_fhir_bundle": {
                "name": "healthcare_fhir_bundle",
                "description": (
                    "Convert a CDS decision to a FHIR R4 Bundle. Runs a CDS "
                    "assessment and returns the result as a FHIR Bundle with "
                    "Observations, RiskAssessment, ClinicalImpression, "
                    "DiagnosticReport, and AuditEvent resources."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier",
                        },
                        "sensor_data": {
                            "type": "string",
                            "description": "Vital signs as JSON string",
                        },
                        "protocol_name": {
                            "type": "string",
                            "description": "Protocol name (sepsis, cardiac, respiratory, post_operative)",
                        },
                        "ecg_metrics": {
                            "type": "object",
                            "description": "Optional ECG metrics from PhysioNet converter",
                        },
                        "decision_id": {
                            "type": "string",
                            "description": "Optional decision ID for the FHIR Bundle",
                        },
                    },
                    "required": ["patient_id", "sensor_data", "protocol_name"],
                },
            },
            "healthcare_waveform_analyze": {
                "name": "healthcare_waveform_analyze",
                "description": (
                    "Analyze raw ECG waveform signal data. Extracts QRS duration, "
                    "QT interval, ST deviation, P-wave presence, and signal quality. "
                    "Returns nurse-friendly summary text."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "signal": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Raw ECG signal as array of float values (single lead)",
                        },
                        "sampling_rate": {
                            "type": "integer",
                            "description": "Sampling rate in Hz (default: 360 for MIT-BIH)",
                            "default": 360,
                        },
                    },
                    "required": ["signal"],
                },
            },
        }

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call with audit logging.

        Wraps parent call_tool for base tools and dispatches
        healthcare-specific tools to their handlers.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Audit log all healthcare tool calls
        if tool_name.startswith("healthcare_"):
            self._audit(tool_name, arguments)

        try:
            # Dispatch healthcare tools
            if tool_name == "healthcare_list_protocols":
                return await self._handle_list_protocols()
            elif tool_name == "healthcare_load_protocol":
                return await self._handle_load_protocol(arguments)
            elif tool_name == "healthcare_analyze":
                return await self._handle_analyze(arguments)
            elif tool_name == "healthcare_check_compliance":
                return await self._handle_check_compliance(arguments)
            elif tool_name == "healthcare_predict_trajectory":
                return await self._handle_predict_trajectory(arguments)
            elif tool_name == "healthcare_ecg_analyze":
                return await self._handle_ecg_analyze(arguments)
            elif tool_name == "healthcare_cds_assess":
                return await self._handle_cds_assess(arguments)
            elif tool_name == "healthcare_fhir_bundle":
                return await self._handle_fhir_bundle(arguments)
            elif tool_name == "healthcare_waveform_analyze":
                return await self._handle_waveform_analyze(arguments)
            else:
                # Delegate to parent for base tools
                return await super().call_tool(tool_name, arguments)

        except ImportError as e:
            logger.error(f"Healthcare package not installed: {e}")
            return {
                "success": False,
                "error": (
                    "attune-healthcare package is not installed. "
                    "Run: pip install attune-healthcare"
                ),
            }
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            return {"success": False, "error": f"Invalid input: {e}"}
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            return {"success": False, "error": f"Missing required field: {e}"}

    # -- Healthcare tool handlers --

    async def _handle_list_protocols(self) -> dict[str, Any]:
        """List available clinical protocols."""
        from attune_healthcare.monitors.monitoring.protocol_loader import ProtocolLoader

        loader = ProtocolLoader()
        protocols = loader.list_available_protocols()

        return {
            "success": True,
            "protocols": protocols,
            "count": len(protocols),
        }

    async def _handle_load_protocol(self, args: dict[str, Any]) -> dict[str, Any]:
        """Load a clinical protocol for a patient."""
        monitor = self._get_monitor()
        patient_id = args["patient_id"]
        protocol_name = args["protocol_name"]
        patient_context = args.get("patient_context")

        protocol = monitor.load_protocol(patient_id, protocol_name, patient_context)

        return {
            "success": True,
            "patient_id": patient_id,
            "protocol": {
                "name": protocol.name,
                "version": protocol.version,
                "applies_to": protocol.applies_to,
                "screening_criteria_count": len(protocol.screening_criteria),
                "screening_threshold": protocol.screening_threshold,
                "interventions_count": len(protocol.interventions),
                "monitoring_frequency": protocol.monitoring_frequency,
                "reassessment_timing": protocol.reassessment_timing,
                "escalation_criteria": protocol.escalation_criteria,
            },
        }

    async def _handle_analyze(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run full patient analysis."""
        monitor = self._get_monitor()

        context = {
            "patient_id": args["patient_id"],
            "sensor_data": self._normalize_sensor_data(args["sensor_data"]),
            "protocol_name": args["protocol_name"],
            "sensor_format": args.get("sensor_format", "simple_json"),
        }

        result = await monitor.analyze(context)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {"success": True, **result}

    async def _handle_check_compliance(self, args: dict[str, Any]) -> dict[str, Any]:
        """Check protocol compliance."""
        from attune_healthcare.monitors.monitoring.protocol_checker import ProtocolChecker
        from attune_healthcare.monitors.monitoring.protocol_loader import ProtocolLoader
        from attune_healthcare.monitors.monitoring.sensor_parsers import (
            normalize_vitals,
            parse_sensor_data,
        )

        loader = ProtocolLoader()
        protocol = loader.load_protocol(args["protocol_name"])

        sensor_data = self._normalize_sensor_data(args["sensor_data"])
        readings = parse_sensor_data(sensor_data, "simple_json")
        normalized = normalize_vitals(readings)

        checker = ProtocolChecker()
        result = checker.check_compliance(protocol, normalized)

        return {
            "success": True,
            "patient_id": args["patient_id"],
            "protocol_name": args["protocol_name"],
            "protocol_activated": result.protocol_activated,
            "activation_score": result.activation_score,
            "threshold": result.threshold,
            "alert_level": result.alert_level,
            "deviations": [
                {
                    "action": d.intervention.action,
                    "status": d.status.value,
                    "timing": d.intervention.timing,
                    "reasoning": d.reasoning,
                }
                for d in result.deviations
            ],
            "compliant_items": result.compliant_items,
            "recommendation": result.recommendation,
        }

    async def _handle_predict_trajectory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Predict vital sign trajectory."""
        from attune_healthcare.monitors.monitoring.sensor_parsers import (
            normalize_vitals,
            parse_sensor_data,
        )
        from attune_healthcare.monitors.monitoring.trajectory_analyzer import TrajectoryAnalyzer

        sensor_data = self._normalize_sensor_data(args["sensor_data"])
        readings = parse_sensor_data(sensor_data, "simple_json")
        normalized = normalize_vitals(readings)

        analyzer = TrajectoryAnalyzer()
        prediction = analyzer.analyze_trajectory(normalized, [])

        return {
            "success": True,
            "patient_id": args["patient_id"],
            "trajectory_state": prediction.trajectory_state,
            "estimated_time_to_critical": prediction.estimated_time_to_critical,
            "vital_trends": [
                {
                    "parameter": t.parameter,
                    "current_value": t.current_value,
                    "direction": t.direction,
                    "concerning": t.concerning,
                    "reasoning": t.reasoning,
                }
                for t in prediction.vital_trends
            ],
            "overall_assessment": prediction.overall_assessment,
            "confidence": prediction.confidence,
            "recommendations": prediction.recommendations,
        }

    async def _handle_ecg_analyze(self, args: dict[str, Any]) -> dict[str, Any]:
        """Analyze ECG metrics using ECGAnalyzerAgent."""
        from attune.agents.healthcare.cds_agents import ECGAnalyzerAgent

        ecg_metrics = args.get("ecg_metrics", {})
        patient_context = args.get("patient_context", {})

        if not ecg_metrics:
            return {"success": False, "error": "ecg_metrics is required"}

        agent = ECGAnalyzerAgent()
        result = agent.process(
            {
                "ecg_metrics": ecg_metrics,
                "patient_context": patient_context,
            }
        )

        ecg = agent.result_to_ecg_analysis(result)

        return {
            "success": result.success,
            "heart_rate": ecg.heart_rate,
            "hrv_sdnn": ecg.hrv_sdnn,
            "rhythm_classification": ecg.rhythm_classification,
            "arrhythmia_events": ecg.arrhythmia_events,
            "pvc_burden_pct": ecg.pvc_burden_pct,
            "clinical_flags": ecg.clinical_flags,
            "score": ecg.score,
            "confidence": ecg.confidence,
            "tier_used": result.tier_used.value,
            "cost": result.cost,
        }

    async def _handle_cds_assess(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run full CDS assessment using CDSTeam."""
        from attune.agents.healthcare.cds_team import CDSTeam

        patient_id = args["patient_id"]
        protocol_name = args["protocol_name"]
        ecg_metrics = args.get("ecg_metrics")
        patient_context = args.get("patient_context")

        try:
            sensor_data = json.loads(args["sensor_data"])
        except json.JSONDecodeError:
            return {"success": False, "error": "sensor_data must be valid JSON"}

        if isinstance(sensor_data, dict) and "vitals" in sensor_data:
            sensor_data = sensor_data["vitals"]

        team = CDSTeam()
        decision = await team.assess(
            patient_id=patient_id,
            sensor_data=sensor_data,
            protocol_name=protocol_name,
            ecg_metrics=ecg_metrics,
            patient_context=patient_context,
        )

        return {"success": True, **decision.to_dict()}

    async def _handle_fhir_bundle(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run CDS assessment and convert result to FHIR R4 Bundle."""
        from attune.agents.healthcare.cds_team import CDSTeam
        from attune.healthcare.fhir.resources import decision_to_fhir_bundle

        patient_id = args["patient_id"]
        protocol_name = args["protocol_name"]
        ecg_metrics = args.get("ecg_metrics")
        decision_id = args.get("decision_id")

        try:
            sensor_data = json.loads(args["sensor_data"])
        except json.JSONDecodeError:
            return {"success": False, "error": "sensor_data must be valid JSON"}

        if isinstance(sensor_data, dict) and "vitals" in sensor_data:
            sensor_data = sensor_data["vitals"]

        team = CDSTeam()
        decision = await team.assess(
            patient_id=patient_id,
            sensor_data=sensor_data,
            protocol_name=protocol_name,
            ecg_metrics=ecg_metrics,
        )

        bundle = decision_to_fhir_bundle(decision, decision_id=decision_id)

        return {
            "success": True,
            "bundle": bundle,
            "resource_count": len(bundle.get("entry", [])),
            "resource_types": list(
                {e["resource"]["resourceType"] for e in bundle.get("entry", [])}
            ),
        }

    async def _handle_waveform_analyze(self, args: dict[str, Any]) -> dict[str, Any]:
        """Analyze raw ECG waveform signal."""
        try:
            from attune.healthcare.waveform.ecg_signal import ECGWaveformAnalyzer
        except ImportError:
            return {
                "success": False,
                "error": (
                    "Waveform analysis requires numpy and scipy. "
                    "Install with: pip install attune-ai[healthcare-enterprise]"
                ),
            }

        signal_data = args.get("signal")
        if not signal_data or not isinstance(signal_data, list):
            return {"success": False, "error": "signal must be a non-empty array of numbers"}

        sampling_rate = args.get("sampling_rate", 360)

        try:
            import numpy as np

            signal_array = np.array(signal_data, dtype=np.float64)
        except (ImportError, ValueError) as e:
            return {"success": False, "error": f"Failed to process signal: {e}"}

        analyzer = ECGWaveformAnalyzer(sampling_rate=sampling_rate)
        features = analyzer.analyze_signal(signal_array)

        return {
            "success": True,
            "nurse_summary": analyzer.format_for_nurse(features),
            **features.to_dict(),
        }


async def healthcare_main_loop() -> None:
    """Main MCP server loop for healthcare server using stdio transport."""
    server = HealthcareMCPServer()

    logger.info("Healthcare CDS MCP Server started")
    logger.info(f"Registered {len(server.tools)} tools (base + healthcare)")

    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            request = json.loads(line)
            response = await handle_request(server, request)

            if response:
                print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {"error": {"code": -32700, "message": "Parse error"}}
            print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            logger.info("Healthcare CDS MCP Server stopped")
            break


def main() -> None:
    """Entry point for healthcare MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("/tmp/attune-healthcare-mcp.log")],  # nosec B108
    )

    try:
        asyncio.run(healthcare_main_loop())
    except KeyboardInterrupt:
        logger.info("Healthcare CDS MCP Server stopped")


if __name__ == "__main__":
    main()
