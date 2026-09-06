import json


DEFAULT_MODEL_PATH = "mlx-community/Qwen2.5-3B-Instruct-bf16"


class RescueLLM:
    """Local conversational Qwen2.5-3B responder used by Falcon."""

    def __init__(self, model_path=DEFAULT_MODEL_PATH, max_tokens=700):
        self.model_path = model_path
        self.max_tokens = max_tokens
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            from mlx_lm import load
        except ImportError as exc:
            raise RuntimeError(
                "mlx_lm is not installed. Install it with: pip install mlx-lm"
            ) from exc

        try:
            print(f"[FALCON LLM] Loading {self.model_path}...")
            self.model, self.tokenizer = load(self.model_path)
            print("[FALCON LLM] Model loaded.")
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Falcon LLM model '{self.model_path}': {exc}"
            ) from exc

    def _build_prompt(self, question, context):
        system_prompt = (
            "You are Falcon, a local AI assistant for a search-and-rescue drone. "
            "Use only the structured rescue information supplied in the context. "
            "Do not invent observations, identities, locations, hazards, or medical facts. "
            "Clearly distinguish observed facts from possibilities and uncertainty. "
            "Your job is to synthesize information for the human rescue operator."
        )

        if isinstance(context, str):
            context_text = context
        else:
            try:
                context_text = json.dumps(
                    context,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            except Exception:
                context_text = str(context)

        user_prompt = (
            f"Operator request:\n{question}\n\n"
            "Structured rescue context:\n"
            f"{context_text}\n\n"
            "Respond directly to the operator request."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        return (
            f"System: {system_prompt}\n\n"
            f"User: {user_prompt}\n\n"
            "Assistant:"
        )

    def respond(self, question, context=None):
        if not question or not str(question).strip():
            raise ValueError("Falcon question cannot be empty.")

        prompt = self._build_prompt(str(question).strip(), context or {})

        try:
            from mlx_lm import generate

            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=self.max_tokens,
                verbose=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Falcon generation failed: {exc}") from exc

        if response is None:
            raise RuntimeError("Falcon returned no response.")

        return str(response).strip()



_rescue_llm = None


def get_rescue_llm():
    """Return one shared Falcon LLM instance, loading it only once."""
    global _rescue_llm

    if _rescue_llm is None:
        _rescue_llm = RescueLLM()

    return _rescue_llm


def run_falcon_answer(question, state):
    """Send structured rescue state plus the operator question to Falcon's RescueLLM."""
    try:
        responder = get_rescue_llm()
        result = responder.respond(
            question=question,
            context=state,
        )
    except Exception as exc:
        raise RuntimeError(f"Falcon LLM generation failed: {exc}") from exc

    if result is None:
        raise RuntimeError("Falcon LLM returned no response.")

    if isinstance(result, dict):
        answer = (
            result.get("answer")
            or result.get("response")
            or result.get("message")
        )
        if answer is not None:
            return str(answer)
        return result

    return str(result)