"""
Orchestrator: runs one full ScanRun end-to-end.

Flow:
  1. Planner Agent analyzes the TargetProfile -> attack_plan (list of vectors)
  2. For each vector:
       a. dispatch to the mapped specialist -> generate payload
       b. send payload to target via TargetClient
       c. Sentinel Agent evaluates target's response
       d. persist AttackLog (+ Vulnerability if succeeded)
       e. if not succeeded and attempts < MAX_ATTACK_ATTEMPTS_PER_VECTOR:
            feed Sentinel's mutation_hint back to the same specialist and
            retry (this is the adaptive feedback loop), incrementing
            `generation` and setting `parent_attempt_id`
  3. Compute aggregate risk_score, mark ScanRun completed

Every step publishes an AgentLogEvent to the event bus so the SSE route
can stream it live to the frontend.
"""
import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.planner import PlannerAgent
from app.agents.sentinel import SentinelAgent
from app.agents.specialists.prompt_injection import PromptInjectionSpecialist
from app.agents.specialists.jailbreak import JailbreakSpecialist
from app.agents.specialists.tool_abuse import ToolAbuseSpecialist
from app.agents.specialists.data_exfiltration import DataExfiltrationSpecialist
from app.agents.specialists.privilege_escalation import PrivilegeEscalationSpecialist
from app.core.config import settings
from app.models.attack import AgentType, AttackLog
from app.models.scan import ScanRun, ScanStatus
from app.models.target import TargetProfile
from app.models.vulnerability import Severity, Vulnerability
from app.schemas.attack import AgentLogEvent
from app.services import event_bus
from app.services.target_client import TargetClient

SPECIALIST_REGISTRY = {
    "prompt_injection_specialist": (PromptInjectionSpecialist, AgentType.PROMPT_INJECTION),
    "jailbreak_specialist": (JailbreakSpecialist, AgentType.JAILBREAK),
    "tool_abuse_specialist": (ToolAbuseSpecialist, AgentType.TOOL_ABUSE),
    "data_exfiltration_specialist": (DataExfiltrationSpecialist, AgentType.DATA_EXFILTRATION),
    "privilege_escalation_specialist": (PrivilegeEscalationSpecialist, AgentType.PRIVILEGE_ESCALATION),
}


async def _emit(scan_id: uuid.UUID, event_type: str, message: str, agent_type: str | None = None, data: dict | None = None):
    await event_bus.publish(
        scan_id,
        AgentLogEvent(
            event_type=event_type,
            agent_type=agent_type,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
        ),
    )


async def run_scan(scan_id: uuid.UUID, db: Session) -> None:
    scan = db.query(ScanRun).filter(ScanRun.id == scan_id).one()
    target = db.query(TargetProfile).filter(TargetProfile.id == scan.target_id).one()

    try:
        # --- 1. Planning phase ---
        scan.status = ScanStatus.PLANNING
        db.commit()
        await _emit(scan_id, "scan_status", "Planner Agent analyzing attack surface...", agent_type="planner")

        planner = PlannerAgent()
        target_desc = json.dumps({
            "name": target.name,
            "declared_tools": target.declared_tools,
            "permission_map": target.permission_map,
        })
        plan = planner.plan(target_desc)
        scan.attack_plan = plan
        db.commit()

        await _emit(
            scan_id, "agent_action",
            f"Plan ready: {len(plan.get('vectors', []))} vectors identified.",
            agent_type="planner", data=plan,
        )

        # --- 2. Attack + adaptive feedback loop ---
        scan.status = ScanStatus.ATTACKING
        db.commit()

        sentinel = SentinelAgent()
        attack_surface_summary = plan.get("attack_surface_summary", "")

        for vector in plan.get("vectors", []):
            specialist_key = vector.get("specialist")
            registry_entry = SPECIALIST_REGISTRY.get(specialist_key)
            if not registry_entry:
                continue  # Planner hallucinated an unknown specialist key; skip safely
            specialist_cls, agent_type_enum = registry_entry
            specialist = specialist_cls()

            client = TargetClient(target)

            parent_id = None
            mutation_hint = None
            previous_payload = None
            succeeded = False

            for generation in range(settings.MAX_ATTACK_ATTEMPTS_PER_VECTOR):
                context = {
                    "vector": vector,
                    "attack_surface_summary": attack_surface_summary,
                }
                if mutation_hint:
                    context["previous_attempt"] = previous_payload
                    context["mutation_hint"] = mutation_hint

                attack_gen = specialist.generate_attack(json.dumps(context))
                payload = attack_gen.get("payload", "")

                await _emit(
                    scan_id, "agent_action",
                    f"{specialist_key} attempt #{generation + 1} on '{vector.get('vector_id')}'",
                    agent_type=specialist_key, data={"payload": payload},
                )

                target_result = await client.send(payload)

                sentinel_context = json.dumps({
                    "agent_type": specialist_key,
                    "owasp_category": vector.get("owasp_category"),
                    "payload": payload,
                    "target_response": target_result.get("output"),
                })
                verdict = sentinel.evaluate(sentinel_context)
                succeeded = bool(verdict.get("violation_detected"))

                log = AttackLog(
                    id=uuid.uuid4(),
                    scan_id=scan_id,
                    agent_type=agent_type_enum,
                    owasp_category=vector.get("owasp_category"),
                    parent_attempt_id=parent_id,
                    generation=generation,
                    payload=payload,
                    target_response=target_result.get("output"),
                    sentinel_verdict=verdict,
                    succeeded=succeeded,
                )
                db.add(log)
                scan.total_attempts += 1
                db.commit()
                db.refresh(log)

                await _emit(
                    scan_id, "sentinel_verdict",
                    f"Sentinel verdict on '{vector.get('vector_id')}' gen {generation}: "
                    f"{'VIOLATION' if succeeded else 'no violation'}",
                    agent_type="sentinel", data=verdict,
                )

                if succeeded:
                    vuln = Vulnerability(
                        id=uuid.uuid4(),
                        scan_id=scan_id,
                        source_attack_id=log.id,
                        title=f"{vector.get('owasp_category', 'Unknown')} via {specialist_key}",
                        owasp_category=vector.get("owasp_category", "Unknown"),
                        severity=Severity(verdict.get("severity") or "medium"),
                        description=verdict.get("reasoning", ""),
                        evidence=(target_result.get("output") or "")[:2000],
                    )
                    db.add(vuln)
                    scan.successful_attacks += 1
                    db.commit()

                    await _emit(
                        scan_id, "vulnerability_found",
                        f"Vulnerability confirmed: {vuln.title}",
                        agent_type=specialist_key, data={"vulnerability_id": str(vuln.id)},
                    )
                    break  # vector proven vulnerable, move to next vector

                # not succeeded -> prepare mutation for next generation
                mutation_hint = verdict.get("mutation_hint")
                previous_payload = payload
                parent_id = log.id

                if not mutation_hint:
                    break  # Sentinel had nothing to suggest; stop retrying this vector

        # --- 3. Finalize ---
        total = scan.total_attempts or 1
        scan.risk_score = round((scan.successful_attacks / total) * 100, 1)
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()
        db.commit()

        await _emit(
            scan_id, "scan_status",
            f"Scan completed. Risk score: {scan.risk_score}/100 "
            f"({scan.successful_attacks}/{scan.total_attempts} attempts succeeded).",
        )

    except Exception as e:  # noqa: BLE001 - hackathon: surface any failure to the stream
        scan.status = ScanStatus.FAILED
        db.commit()
        await _emit(scan_id, "scan_status", f"Scan failed: {e}")
        raise
