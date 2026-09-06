import json
import re

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template


class QwenAnalyzer:

    def __init__(
        self,
        model_path="mlx-community/Qwen2.5-VL-3B-Instruct-bf16"
    ):
        print("[QWEN] Loading model...")

        self.model, self.processor = load(model_path)

        print("[QWEN] Model loaded successfully.")


    # ========================================================
    # CLEAN MODEL OUTPUT
    # ========================================================

    def _extract_json(self, text):

        text = text.strip()

        # ----------------------------------------------------
        # Remove Markdown code fences
        # ----------------------------------------------------

        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"^```\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        text = text.strip()


        # ----------------------------------------------------
        # Direct JSON parsing
        # ----------------------------------------------------

        try:

            return json.loads(text)

        except json.JSONDecodeError:
            pass


        # ----------------------------------------------------
        # Find JSON object inside additional text
        # ----------------------------------------------------

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:

            json_text = text[start:end + 1]

            try:

                return json.loads(json_text)

            except json.JSONDecodeError:
                pass


        return None


    # ========================================================
    # ANALYZE IMAGE
    # ========================================================

    def analyze(
        self,
        image_path,
        people=None,
        objects=None
    ):

        if people is None:
            people = []

        if objects is None:
            objects = []


        # ====================================================
        # COMPUTER VISION CONTEXT
        # ====================================================

        context = {
            "people": people,
            "objects": objects
        }

        context_json = json.dumps(
            context,
            indent=2,
            default=str
        )


        # ====================================================
        # PROMPT
        # ====================================================

        prompt = f"""
You are the visual intelligence module of an
AI search-and-rescue system.

Analyze the provided image for rescue-relevant
visual information.

Existing computer-vision information:

{context_json}

Analyze only what can reasonably be observed.

Determine:

1. Scene type.

2. Environmental conditions.

3. Visible hazards or obstacles.

4. Important observations about detected people.

5. Visible behavior or expressions that may indicate
   possible distress.

6. Important rescue-related observations.

Do NOT make medical diagnoses.

Do NOT claim that someone is injured unless there
is clear visible evidence.

Do NOT assume information that cannot be observed.

Use uncertainty when appropriate.

Return ONLY valid JSON.

Do not use Markdown code blocks.

Use exactly this structure:

{{
    "scene": "",
    "environment": [],
    "hazards": [],
    "people_observations": [],
    "possible_distress_cues": [],
    "rescue_observations": []
}}
"""


        # ====================================================
        # APPLY CHAT TEMPLATE
        # ====================================================

        try:

            formatted_prompt = apply_chat_template(
                self.processor,
                self.model.config,
                prompt,
                num_images=1
            )

        except Exception as error:

            print(
                f"[QWEN] Chat template error: {error}"
            )

            return self._empty_result(
                error=str(error)
            )


        # ====================================================
        # GENERATE
        # ====================================================

        print("[QWEN] Analyzing image...")

        try:

            output = generate(
                model=self.model,
                processor=self.processor,
                image=image_path,
                prompt=formatted_prompt,
                max_tokens=500,
                temperature=0.1,
                verbose=False
            )

        except Exception as error:

            print(
                f"[QWEN] Generation error: {error}"
            )

            return self._empty_result(
                error=str(error)
            )


        # ====================================================
        # GET TEXT
        # ====================================================

        if hasattr(output, "text"):

            text = output.text

        else:

            text = str(output)

        text = text.strip()


        # ====================================================
        # SHOW RAW OUTPUT
        # ====================================================

        print("\n[QWEN RAW OUTPUT]")
        print(text)


        # ====================================================
        # EXTRACT JSON
        # ====================================================

        result = self._extract_json(text)


        if result is None:

            print(
                "[QWEN] Warning: Could not parse JSON."
            )

            return self._empty_result(
                raw_output=text
            )


        print("\n[QWEN] JSON parsed successfully.")

        return result


    # ========================================================
    # EMPTY RESULT
    # ========================================================

    def _empty_result(
        self,
        error=None,
        raw_output=None
    ):

        result = {
            "scene": "unknown",
            "environment": [],
            "hazards": [],
            "people_observations": [],
            "possible_distress_cues": [],
            "rescue_observations": []
        }

        if error is not None:
            result["error"] = error

        if raw_output is not None:
            result["raw_output"] = raw_output

        return result