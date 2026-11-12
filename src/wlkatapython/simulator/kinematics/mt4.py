"""MT4 forward / inverse kinematics and motion bookkeeping, matched to the real arm.

Measured on an MT4 (firmware ``MT4,20240820``) through its status reports and
its ``$$`` settings; the measurements are in ``tests/data/mt4_hardware_poses.json``:

- Geometry (mm, the arm's ``$29``-``$34``): J1 is vertical through the base; J2
  sits ``CENTER_OFFSET`` in front of it and ``CENTER_HEIGHT`` above the floor;
  the upper arm is ``LINK1`` long and vertical at J2 = 0, tipping forward as J2
  grows; the forearm is ``LINK2`` long and horizontal at J3 = 0, and J3 is its
  angle below horizontal whatever J2 is (the parallelogram keeps it); the tool
  flange is ``HEAD_OFFSET`` in front of the forearm's end and ``HEAD_HEIGHT``
  below it, always level. At zero joints the arm reports X 230, Y 0, Z 255.57.
- Orientation: the flange only turns about the vertical. The arm reports that
  angle, J1 + J4, as Rz; Rx and Ry are always 0. A coordinate move's A is that
  angle: J4 = A - J1.
- Steps: every joint stops on a whole motor step (``STEPS_PER_DEG``, the arm's
  ``$104``-``$106`` and ``$100``), and the arm reports the angles and the pose
  of those steps: a move to J1 = 30 reports 30.009, a move to X 200 Z 150
  reports X 200.012 Z 150.024.
- Limits: a joint target outside ``JOINT_LIMITS_DEG`` (``$130``-``$146``) gets
  ``Error,A102,Soft limit:<axis>``; J2 - J3 above ``MAX_J2_MINUS_J3`` or
  J3 - J2 above ``MAX_J3_MINUS_J2`` (``$53``, ``$54``) gets ``Error,A107``. A
  coordinate target the two links cannot reach prints ``The Cartesian position
  exceeds the boundary.`` The arm does not move in any of these cases, and
  still ends its reply with ``ok`` (half a second after an error).
- Reports: the arm sends its status by itself ($40=1) once it stops after a
  move. A move that turns no motor (refused, or already there) reports nothing.

``MT4Motion`` keeps what the firmware keeps between moves, which decides where
an incremental (G91) move or a move that leaves axes out ends, and which way a
linear (G01) move turns the flange; see its docstring.

The 3D model in wlkata_arm_virtual-reality (URDF ``wlkata_mt4_description``) is
built from the CAD assembly: its J2 axis is 46 mm from J1 and its flange
35.003 mm in front of and 14.476 mm below the forearm's end, so its flange is
1.0 mm further out and 0.05 mm lower than the pose the arm reports.

Joint order (degrees in simulator state):
    J1..J4  <->  angle_X, angle_Y, angle_Z, angle_A

Cartesian state (mm / degrees):
    X, Y, Z  <->  coordinate_X, coordinate_Y, coordinate_Z
    J1 + J4  <->  coordinate_RZ   (coordinate_RX and coordinate_RY stay 0)
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

# Geometry the firmware uses (mm): the arm's $29-$34
LINK1 = 130.0           # upper arm: J2 axis to the elbow
LINK2 = 150.0           # forearm: elbow to the wrist bracket pin
CENTER_OFFSET = 45.0    # J1 axis to the J2 axis
HEAD_OFFSET = 35.0      # wrist bracket pin to the tool axis
CENTER_HEIGHT = 140.0   # floor to the J2 axis
HEAD_HEIGHT = 14.43     # wrist bracket pin down to the tool flange

# Motor steps per degree of J1..J4 ($104, $105, $106, $100)
STEPS_PER_DEG: Tuple[float, ...] = (35.556, 35.556, 35.556, 44.001)

# Joint limits (degrees) of J1..J4 ($144/$134, $145/$135, $146/$136, $140/$130)
JOINT_LIMITS_DEG: Tuple[Tuple[float, float], ...] = (
    (-124.0, 145.0),
    (-36.0, 80.0),
    (-16.0, 110.0),
    (-180.0, 180.0),
)
MAX_J2_MINUS_J3 = 60.0  # $53
MAX_J3_MINUS_J2 = 60.0  # $54

# What the arm prints
CARTESIAN_MODE_INFO = "Info,M20: Cartesian mode start."
ANGLE_MODE_INFO = "Info,M21: Angle mode start."
OUTSIDE_BOUNDARY = "The Cartesian position exceeds the boundary."
SOFT_LIMIT = "Error,A102,Soft limit:{axis}"
ANGLES_TOO_BIG = "Error,A107,Axis 2 and 3 have conflicting angles.:Axis 2 and 3 angles are too big."
ANGLES_TOO_SMALL = "Error,A107,Axis 2 and 3 have conflicting angles.:Axis 2 and 3 angles are too small."

# The order the firmware checks the soft limits in (its axis order: A B C D X Y Z)
_LIMIT_ORDER: Tuple[Tuple[str, int], ...] = (("A", 3), ("X", 0), ("Y", 1), ("Z", 2))
_JOINT_AXES = ("X", "Y", "Z", "A")
_CART_AXES = ("X", "Y", "Z", "A")
_SYNC_TOL_DEG = 1e-9


def _to_steps(angle_deg: float, joint: int) -> int:
    """Whole motor steps of a joint angle, halves away from zero (C's lround)."""
    value = angle_deg * STEPS_PER_DEG[joint]
    return int(math.floor(value + 0.5)) if value >= 0 else -int(math.floor(-value + 0.5))


class MT4Kinematics:
    """FK / IK of the WLKATA MT4 as its firmware computes them."""

    limits_deg = JOINT_LIMITS_DEG

    def forward(self, joint_deg: Sequence[float]) -> Tuple[float, float, float, float, float, float]:
        """FK: joint degrees → (X, Y, Z mm, Rx, Ry, Rz deg), as the arm reports it."""
        j1, j2, j3 = (math.radians(float(a)) for a in joint_deg[:3])
        reach = CENTER_OFFSET + HEAD_OFFSET + LINK1 * math.sin(j2) + LINK2 * math.cos(j3)
        height = CENTER_HEIGHT - HEAD_HEIGHT + LINK1 * math.cos(j2) - LINK2 * math.sin(j3)
        return (reach * math.cos(j1), reach * math.sin(j1), height,
                0.0, 0.0, float(joint_deg[0]) + float(joint_deg[3]))

    def inverse(self, x: float, y: float, z: float) -> Optional[Tuple[float, float, float]]:
        """IK: flange position (mm) → (J1, J2, J3) degrees, or None when the links cannot reach it.

        The arm has one way to reach a position (elbow up, J1 facing it); the
        joint limits are not checked here (see ``limit_error``).
        """
        u = math.hypot(x, y) - CENTER_OFFSET - HEAD_OFFSET   # from the J2 axis to the wrist pin
        v = z - (CENTER_HEIGHT - HEAD_HEIGHT)
        d = math.hypot(u, v)
        if d <= 0.0:
            return None
        cos_upper = (LINK1 * LINK1 + d * d - LINK2 * LINK2) / (2.0 * LINK1 * d)
        cos_fore = (LINK2 * LINK2 + d * d - LINK1 * LINK1) / (2.0 * LINK2 * d)
        if abs(cos_upper) > 1.0 or abs(cos_fore) > 1.0:
            return None
        lift = math.atan2(v, u)   # of the wrist pin, seen from the J2 axis
        j2 = math.pi / 2.0 - (lift + math.acos(cos_upper))
        j3 = math.acos(cos_fore) - lift
        return (math.degrees(math.atan2(y, x)), math.degrees(j2), math.degrees(j3))

    def limit_error(self, joint_deg: Sequence[float]) -> Optional[str]:
        """The error the arm prints for a joint target it refuses, or None."""
        for axis, i in _LIMIT_ORDER:
            lo, hi = self.limits_deg[i]
            if not lo <= joint_deg[i] <= hi:
                return SOFT_LIMIT.format(axis=axis)
        if joint_deg[1] - joint_deg[2] > MAX_J2_MINUS_J3:
            return ANGLES_TOO_BIG
        if joint_deg[2] - joint_deg[1] > MAX_J3_MINUS_J2:
            return ANGLES_TOO_SMALL
        return None

    def within_limits(self, joint_deg: Sequence[float]) -> bool:
        return self.limit_error(joint_deg) is None


class MoveResult(NamedTuple):
    """What a move command did: the lines the arm prints, and whether it moved.

    ``lines`` always ends with "ok"; a refused move has the arm's message before it.
    """
    lines: List[str]
    moved: bool


class MT4Motion:
    """What the MT4 firmware keeps between moves, as measured on the arm.

    - ``steps``: where the motors are. The arm reports these.
    - ``mode``: 0 after a joint (M21) move, 1 after a coordinate (M20) move
      (the status's Motion_MODE). The arm prints an Info line when a move
      changes it, and takes its bearings again from where it is:
    - ``joint_target``: the angles the last joint move asked for. G91 joint
      steps and axes a joint move leaves out start from it, not from the
      reported angles (three G91 steps of 0.01° move the arm one motor step).
      The first joint move after coordinate moves starts from the reported
      angles.
    - ``cart_target``: X, Y, Z, A of the last coordinate move, used the same
      way. The first coordinate move after joint moves starts from the
      reported position with A = 0: it turns the flange back to Rz 0 unless it
      names an A.
    - ``linear_rz``: the flange's direction (Rz) when the arm last went from
      joint to coordinate moves. Linear moves (G01) turn the flange to it
      whatever their A is, even after G00 / G05 moves turned it elsewhere;
      their A is only remembered for the next G00 / G05 move.
    - A refused move leaves traces. Beyond the boundary or with conflicting
      J2 / J3 angles (A107), the refused target stays the target: a G91 move
      after it steps from there. Past a soft limit (A102) the target goes
      back to what it was. A coordinate target beyond the boundary is not
      solved at all: the arm checks the joints of the move before it again,
      repeats that move's error if it was refused, and otherwise replies ok.
    """

    def __init__(self, kin: Optional[MT4Kinematics] = None):
        self.kin = kin or MT4Kinematics()
        self.home()

    # ── State ──────────────────────────────────────────────────────────

    @property
    def joints(self) -> List[float]:
        """J1..J4 in degrees, as the arm reports them (whole motor steps)."""
        return [s / per for s, per in zip(self.steps, STEPS_PER_DEG)]

    @property
    def pose(self) -> Tuple[float, float, float, float, float, float]:
        """(X, Y, Z mm, Rx, Ry, Rz deg), as the arm reports it."""
        return self.kin.forward(self.joints)

    def home(self) -> None:
        """Zero joints in angle mode, as after homing."""
        self.sync([0.0, 0.0, 0.0, 0.0])

    def sync(self, joint_deg: Sequence[float], mode: int = 0) -> None:
        """Put the arm at ``joint_deg`` with no history: the targets are that pose.

        ``mode`` 0 is an arm that last made a joint move; 1 one that last made
        a coordinate move, whose flange keeps its direction (A = J1 + J4).
        """
        joints = [float(a) for a in joint_deg[:4]]
        self.steps = [_to_steps(a, i) for i, a in enumerate(joints)]
        self.mode = 1 if mode == 1 else 0
        self.joint_target = list(joints)
        self.planned = list(joints)
        x, y, z, _, _, rz = self.kin.forward(joints)
        self.cart_target = [x, y, z, rz]
        self.linear_rz = rz

    # ── Moves ──────────────────────────────────────────────────────────

    @staticmethod
    def _apply(target: List[float], axes: Sequence[str], values: Dict[str, float], incremental: bool) -> List[float]:
        out = list(target)
        for axis, value in values.items():
            axis = axis.upper()
            if axis in axes:
                i = axes.index(axis)
                out[i] = out[i] + float(value) if incremental else float(value)
        return out

    def _go(self, joints: Sequence[float]) -> bool:
        steps = [_to_steps(a, i) for i, a in enumerate(joints)]
        moved = steps != self.steps
        self.steps = steps
        return moved

    def joint_move(self, values: Dict[str, float], incremental: bool = False) -> MoveResult:
        """An M21 move: ``values`` maps X, Y, Z, A (J1..J4) to the command's degrees."""
        lines: List[str] = []
        if self.mode != 0:
            self.mode = 0
            lines.append(ANGLE_MODE_INFO)
            self.joint_target = self.joints
        target = self._apply(self.joint_target, _JOINT_AXES, values, incremental)
        self.planned = list(target)
        error = self.kin.limit_error(target)
        if error:
            if error.startswith("Error,A107"):
                self.joint_target = target
            return MoveResult(lines + [error, "ok"], False)
        moved = self._go(target)
        self.joint_target = target
        return MoveResult(lines + ["ok"], moved)

    def cartesian_move(self, values: Dict[str, float], incremental: bool = False, linear: bool = False) -> MoveResult:
        """An M20 move: ``values`` maps X, Y, Z (mm) and A (deg) to the command's numbers.

        ``linear`` is G01; G00 and G05 end at the same pose as each other.
        """
        lines: List[str] = []
        if self.mode != 1:
            self.mode = 1
            lines.append(CARTESIAN_MODE_INFO)
            x, y, z, _, _, rz = self.pose
            self.cart_target = [x, y, z, 0.0]
            self.linear_rz = rz
        before = list(self.cart_target)
        target = self._apply(before, _CART_AXES, values, incremental)
        self.cart_target = target
        arm = self.kin.inverse(*target[:3])
        if arm is None:
            lines.append(OUTSIDE_BOUNDARY)
        else:
            self.planned = [arm[0], arm[1], arm[2], (self.linear_rz if linear else target[3]) - arm[0]]
        error = self.kin.limit_error(self.planned)
        if error:
            if error.startswith("Error,A102"):
                self.cart_target = before
            return MoveResult(lines + [error, "ok"], False)
        moved = self._go(self.planned)
        return MoveResult(lines + ["ok"], moved)


# ---------------------------------------------------------------------------
# Simulator state (RobotState) helpers
# ---------------------------------------------------------------------------

def joints_from_state(state) -> List[float]:
    """Map simulator state joint fields → [J1..J4] degrees."""
    return [float(state.angle_X), float(state.angle_Y), float(state.angle_Z), float(state.angle_A)]


def _to_state(state, motion: MT4Motion) -> None:
    state.angle_X, state.angle_Y, state.angle_Z, state.angle_A = motion.joints
    (state.coordinate_X, state.coordinate_Y, state.coordinate_Z,
     state.coordinate_RX, state.coordinate_RY, state.coordinate_RZ) = motion.pose
    state.motion_mode = motion.mode


def motion_of(state) -> MT4Motion:
    """The state's MT4 motion bookkeeping, started from its joints when someone edited them."""
    motion = getattr(state, "mt4_motion", None)
    if motion is None:
        motion = state.mt4_motion = MT4Motion()
        motion.sync(joints_from_state(state), state.motion_mode)
    elif (state.motion_mode != motion.mode
          or any(abs(a - b) > _SYNC_TOL_DEG for a, b in zip(joints_from_state(state), motion.joints))):
        motion.sync(joints_from_state(state), state.motion_mode)
    return motion


def home(state) -> None:
    """After homing: zero joints, X 230, Y 0, Z 255.57, angle mode."""
    motion = getattr(state, "mt4_motion", None)
    if motion is None:
        motion = state.mt4_motion = MT4Motion()
    motion.home()
    _to_state(state, motion)


def joint_move(state, values: Dict[str, float], incremental: bool = False) -> MoveResult:
    """Run an M21 joint move on the state the way the MT4 firmware does."""
    motion = motion_of(state)
    result = motion.joint_move(values, incremental)
    _to_state(state, motion)
    return result


def cartesian_move(state, values: Dict[str, float], incremental: bool = False, linear: bool = False) -> MoveResult:
    """Run an M20 coordinate move on the state the way the MT4 firmware does."""
    motion = motion_of(state)
    result = motion.cartesian_move(values, incremental, linear)
    _to_state(state, motion)
    return result


_AXIS_WORD = re.compile(r"([XYZA])\s*(-?\d*\.?\d+)", re.IGNORECASE)
_LINEAR_WORD = re.compile(r"G0?1(?!\d)", re.IGNORECASE)


def move_from_command(state, command: str) -> MoveResult:
    """Run an ``M20…`` / ``M21…`` move line (G90 / G91, G00 / G01 / G05, X Y Z A) on the state."""
    text = command.strip()
    values = {axis.upper(): float(value) for axis, value in _AXIS_WORD.findall(text[3:])}
    incremental = "G91" in text.upper()
    if text.upper().startswith("M21"):
        return joint_move(state, values, incremental)
    return cartesian_move(state, values, incremental, linear=bool(_LINEAR_WORD.search(text)))
