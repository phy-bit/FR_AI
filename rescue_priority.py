class RescuePriorityEngine:

    def __init__(self):
        pass

    # ========================================================
    # CALCULATE PRIORITY
    # ========================================================

    def calculate(
        self,
        person,
        qwen_result=None
    ):

        if qwen_result is None:
            qwen_result = {}

        score = 0
        reasons = []

        # ====================================================
        # POSTURE
        # ====================================================

        posture = person.get(
            "posture",
            "unknown"
        )

        if posture == "lying":
            score += 35
            reasons.append("person is lying")

        elif posture == "sitting":
            score += 10
            reasons.append("person is sitting")

        # ====================================================
        # MOVEMENT
        # ====================================================

        movement = person.get(
            "movement",
            "unknown"
        )

        if movement == "none":
            score += 30
            reasons.append("no detected movement")

        elif movement == "low":
            score += 15
            reasons.append("low movement")

        # ====================================================
        # EXISTING CONDITION
        # ====================================================

        condition = person.get(
            "condition",
            "unknown"
        )

        if condition == "possible_distress":
            score += 25
            reasons.append(
                "computer vision indicates possible distress"
            )

        elif condition == "attention_required":
            score += 10
            reasons.append(
                "computer vision indicates attention required"
            )

        # ====================================================
        # QWEN OBSERVATIONS
        # ====================================================

        # Person-specific Qwen observations should be supplied by
        # rescue_context.py under this person's record. These are
        # safe to use for a person-specific priority adjustment.
        person_qwen = person.get(
            "qwen_observations",
            {}
        )

        if isinstance(person_qwen, dict):
            qwen_distress = person_qwen.get(
                "possible_distress_cues",
                []
            )

            qwen_rescue = person_qwen.get(
                "rescue_observations",
                []
            )

            qwen_hazards = person_qwen.get(
                "hazards",
                []
            )

        else:
            qwen_distress = []
            qwen_rescue = []
            qwen_hazards = []

        # Backward-compatible support for a directly supplied
        # person-specific Qwen result.
        if not isinstance(person_qwen, dict) and isinstance(qwen_result, dict):
            qwen_distress = qwen_result.get(
                "possible_distress_cues",
                []
            )
            qwen_rescue = qwen_result.get(
                "rescue_observations",
                []
            )

        # ----------------------------------------------------
        # Person-specific distress cues
        # ----------------------------------------------------

        if qwen_distress:
            score += 15
            reasons.append(
                "visual analysis detected possible distress cues"
            )

        # ----------------------------------------------------
        # Person-specific rescue observations
        # ----------------------------------------------------

        if qwen_rescue:
            score += 10
            reasons.append(
                "visual analysis reported rescue-relevant observations"
            )

        # ----------------------------------------------------
        # Environmental hazards
        # ----------------------------------------------------

        # Hazards are scene-level information. They are intentionally
        # not applied automatically to every person. A caller may
        # explicitly attach a relevant hazard to this person's record.
        relevant_hazards = person.get(
            "relevant_hazards",
            qwen_hazards
        )

        if relevant_hazards:
            score += 10
            reasons.append(
                "person is exposed to a visible environmental hazard"
            )

        # ====================================================
        # CAP SCORE
        # ====================================================

        score = min(score, 100)

        # ====================================================
        # PRIORITY LEVEL
        # ====================================================

        if score >= 75:
            priority = "CRITICAL"

        elif score >= 50:
            priority = "HIGH"

        elif score >= 25:
            priority = "MEDIUM"

        else:
            priority = "LOW"

        # ====================================================
        # RESULT
        # ====================================================

        return {
            "score": score,
            "priority": priority,
            "reasons": reasons
        }