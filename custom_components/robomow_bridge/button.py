from homeassistant.components.button import ButtonEntity
from .entity import RobomowEntity
COMMANDS={"edge":("Mow edge",1,1),"mow":("Mow area",3,1),"home":("Go home",2,1),"stop":("Stop",4,1),"start":("Start",4,0),"forward":("Forward",200,1),"backward":("Backward",203,90),"left":("Left",201,-120),"right":("Right",202,35),"change_zone":("Change zone",4,1)}
async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RobomowButton(entry.runtime_data,entry,k,*v) for k,v in COMMANDS.items()])
class RobomowButton(RobomowEntity, ButtonEntity):
    def __init__(self,c,e,key,name,cmd,val): super().__init__(c,e,key); self._attr_name=name; self.cmd=cmd; self.val=val
    async def async_press(self): await self.coordinator.async_command(self.cmd,self.val)
