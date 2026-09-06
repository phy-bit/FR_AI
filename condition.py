class ConditionAnalyzer:

    def analyze(self, movement, posture, confidence):

        score = 0
        reasons = []

        # --------------------------------
        # POSTURE
        # --------------------------------

        if posture == "lying":
            score += 40
            reasons.append("person is lying")

        elif posture == "sitting":
            score += 10

        elif posture == "standing":
            score += 0

        # --------------------------------
        # MOVEMENT
        # --------------------------------

        if movement == "none":
            score += 30
            reasons.append("no detected movement")

        elif movement == "low":
            score += 15
            reasons.append("low movement")

        elif movement == "high":
            score += 0

        # --------------------------------
        # DETECTION CONFIDENCE
        # --------------------------------

        if confidence < 0.50:
            reasons.append("low detection confidence")

        # --------------------------------
        # CONDITION
        # --------------------------------

        if score >= 60:

            condition = "possible_distress"

        elif score >= 30:

            condition = "attention_required"

        else:

            condition = "no_obvious_distress"

        return {
            "condition": condition,
            "score": score,
            "reasons": reasons
        }