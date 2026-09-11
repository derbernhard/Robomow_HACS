from __future__ import annotations
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

STORE_VERSION=1
STORE_KEY_PREFIX='robomow_bridge_rain_'
class RobomowRainManager:
    def __init__(self,hass,coordinator,entry_id,entity_id,dry_delay_minutes):
        self.hass=hass; self.coordinator=coordinator; self.entity_id=entity_id; self.dry_delay_seconds=max(0,dry_delay_minutes)*60
        self.rain_disabled=False; self._listeners=[]; self._cancel_timer=None; self._callbacks=[]
        self._store=Store(hass,STORE_VERSION,f'{STORE_KEY_PREFIX}{entry_id}')
    async def async_start(self):
        saved=await self._store.async_load() or {}; self.rain_disabled=bool(saved.get('rain_disabled',False))
        self._listeners.append(async_track_state_change_event(self.hass,[self.entity_id],self._state_changed))
        state=self.hass.states.get(self.entity_id)
        if state and state.state==STATE_ON: await self._handle_wet()
        elif state and state.state==STATE_OFF and self.rain_disabled: self._schedule_dry()
    async def async_stop(self):
        for unsub in self._listeners: unsub()
        self._listeners.clear(); self._cancel_dry_timer()
    def add_listener(self,callback): self._callbacks.append(callback); return lambda:self._callbacks.remove(callback)
    async def _set_flag(self,value):
        if self.rain_disabled==value: return
        self.rain_disabled=value; await self._store.async_save({'rain_disabled':value})
        for cb in list(self._callbacks): cb()
    def _schedule_dry(self):
        self._cancel_dry_timer()
        if self.dry_delay_seconds==0: self.hass.async_create_task(self._enable_if_still_dry())
        else: self._cancel_timer=async_call_later(self.hass,self.dry_delay_seconds,self._dry_timer_finished)
    def _cancel_dry_timer(self):
        if self._cancel_timer: self._cancel_timer(); self._cancel_timer=None
    async def _state_changed(self,event):
        ns=event.data.get('new_state')
        if not ns:return
        if ns.state==STATE_ON: await self._handle_wet()
        elif ns.state==STATE_OFF and self.rain_disabled: self._schedule_dry()
    async def _handle_wet(self):
        self._cancel_dry_timer()
        schedule_on=str(self.coordinator.data.get('once',{}).get('50','0'))=='1'
        if schedule_on:
            await self._ensure_ble(); await self.coordinator.async_command(50,0); await self._set_flag(True)
        elif not self.rain_disabled:
            await self._set_flag(False)
    async def _dry_timer_finished(self,_now): self._cancel_timer=None; await self._enable_if_still_dry()
    async def _enable_if_still_dry(self):
        if not self.rain_disabled or not self.hass.states.is_state(self.entity_id,STATE_OFF): return
        await self._ensure_ble(); await self.coordinator.async_command(50,1); await self._set_flag(False)
    async def _ensure_ble(self):
        if str(self.coordinator.data.get('renew',{}).get('cBLEsw','')).lower()!='lightgreen': await self.coordinator.api.command(250,1)

