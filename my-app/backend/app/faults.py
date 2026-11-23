from .models import FaultState


class FaultController:
    def __init__(self):
        self._state = FaultState()

    def get(self) -> FaultState:
        return self._state.model_copy()

    def update(self, patch: dict) -> FaultState:
        payload = self._state.model_dump()
        payload.update(patch)
        self._state = FaultState.model_validate(payload)
        return self.get()

