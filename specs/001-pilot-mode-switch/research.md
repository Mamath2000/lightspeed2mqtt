# Phase 0 Research Notes

## Task Log

1. Research Pilot switch semantics for Home Assistant MQTT integrations.
2. Find best practices for `paho-mqtt` state synchronization in HA accessory bridges.
3. Find best practices for `logipy` control handoff when resuming Logitech ownership.
4. Research temporary override patterns for alert/warning lighting effects.

---

### Decision: Represent Pilot ownership with a Home Assistant MQTT switch that mirrors the existing `auto` topic

- **Rationale**: HA Switch entities map 1:1 with on/off control, can share the existing `homeassistant/device/<id>/config` discovery payload, and accept retained state updates. Reusing the `auto` topic for command/state keeps Principle II intact and reduces broker churn.
- **Alternatives considered**:
  - Reintroduce a button entity (current behavior) — rejected because buttons do not expose persistent state, so HA cannot reflect whether Logitech or the integration owns the keyboard.
  - Create a brand-new topic namespace for the switch — rejected to avoid violating the explicit MQTT contracts principle.

### Decision: Store last automation color in memory and reapply when Light toggles on while Pilot switch is on

- **Rationale**: Maintaining a cached `{rgb, brightness}` payload ensures that light-off/on cycles restore the user-selected color without waiting for HA to resend commands. This also allows overrides to resume the prior look instantly.
- **Alternatives considered**:
  - Request HA to resend state via MQTT retained message — rejected because HA only retains discovery/config, not every light command, and would reapply stale colors after overrides.

### Decision: Use `paho-mqtt` retained state topics plus optimistic writes for switch/light entities

- **Rationale**: Publishing retained state to `status` and new switch state topics gives HA immediate awareness after reconnects. Optimistic writes (log state locally before HA ack) avoid blocking the MQTT loop.
- **Alternatives considered**:
  - Implement request/response ack topics — overkill for a single-peripheral integration and introduces extra schemas disallowed by Principle II.

### Decision: Manage temporary Alert/Warning overrides via asyncio-like timers (threading.Timer) with a shared controller lock

- **Rationale**: Timers let us bound override duration and ensure only one override runs at a time, while the shared state machine cleanly resumes prior mode.
- **Alternatives considered**:
  - Busy-wait loops within the MQTT handler — rejected: would block message processing and violate the <100 ms handling constraint.
  - External scheduler — rejected: adds dependencies beyond allowed stack.

### Decision: Use `logipy` stop/start calls to release or reclaim Logitech control

- **Rationale**: `logipy` already exposes `LogiLedRestoreLighting()` and `LogiLedSetLighting()`; calling restore when Off mode triggers ensures Logitech Options+ regains control, while Pilot mode reclaims via the standard set functions. This approach satisfies Principle I without persisting extra DLL state.
- **Alternatives considered**:
  - Restarting Logitech LED SDK each time — rejected due to performance and risk of DLL instability.

### Decision: Default override duration to 10 seconds with validation range [1, 300]

- **Rationale**: Matches user request while bounding exposures per Principle IV; 300 s upper limit prevents runaway overrides while still allowing future tuning.
- **Alternatives considered**:
  - Unlimited duration — rejected: conflicts with Momentary Control.
  - Fixed duration baked into code — rejected: configuration file already drives behaviors and needs this knob.
