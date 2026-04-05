class LLMClient:
    def __init__(self, config: dict):
        self.config = config

    def complete_json(self, prompt_name: str, payload: dict) -> dict:
        return {}
