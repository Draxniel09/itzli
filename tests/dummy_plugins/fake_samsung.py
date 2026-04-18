from typing import List, Dict, Any
from openunlock.core.interfaces import BaseDevicePlugin

class FakeSamsungPlugin(BaseDevicePlugin):
    @property
    def name(self) -> str:
        return "Fake Samsung Plugin"
        
    @property
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        return [("04e8", "685d")]
        
    def get_supported_actions(self) -> List[str]:
        return ["FRP_BYPASS"]
        
    async def execute_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        return {"status": "success", "action": action}

class NotAPlugin:
    """This should be ignored by the loader."""
    pass
