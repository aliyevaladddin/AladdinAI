# NOTICE: This file is protected under RCF-PL
# [RCF:PROTECTED]
import os
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)

# [RCF:PROTECTED]
def run_tools_audit() -> Dict[str, Any]:
    """Run NVIDIA SkillSpector static security scan on the tools directory.

    Returns a dictionary with safety status, risk score, and any findings.
    """
    try:
        from skillspector import graph
    except ImportError as e:
        log.error("skillspector is not installed: %s", e)
        return {
            "success": False,
            "error": "NVIDIA SkillSpector library is not installed in the environment."
        }

    tools_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tools"
    )
    if not os.path.isdir(tools_dir):
        return {
            "success": False,
            "error": f"Tools directory not found at path: {tools_dir}"
        }

    try:
        log.info("Running SkillSpector security audit on: %s", tools_dir)
        # Invoke static analysis using use_llm=False
        result = graph.invoke({"input_path": tools_dir, "use_llm": False})
        
        # Format findings for UI consumption
        raw_findings = result.get("findings") or []
        formatted_findings = []
        for finding in raw_findings:
            if isinstance(finding, dict):
                formatted_findings.append({
                    "file": finding.get("file") or finding.get("skill_path") or "unknown",
                    "category": finding.get("category") or "General vulnerability",
                    "description": finding.get("description") or finding.get("message") or "",
                    "severity": finding.get("severity") or "MEDIUM",
                    "line": finding.get("line") or finding.get("line_number"),
                })
            else:
                formatted_findings.append({
                    "file": "unknown",
                    "category": "Raw warning",
                    "description": str(finding),
                    "severity": "UNKNOWN",
                })

        return {
            "success": True,
            "risk_score": result.get("risk_score", 0),
            "risk_severity": result.get("risk_severity", "LOW"),
            "risk_recommendation": result.get("risk_recommendation", "SAFE"),
            "findings": formatted_findings
        }
    except Exception as e:
        log.exception("SkillSpector execution failed")
        return {
            "success": False,
            "error": f"An error occurred during SkillSpector scan execution: {str(e)}"
        }
