"""Mirobot forward / inverse kinematics, matched to the real arm.

Measured on a Mirobot (firmware ``Mirobot,20240820``, ``EXbox,20230710``)
through its status reports; the measurements are in
``tests/data/mirobot_hardware_poses.json``:

- Geometry (mm): J1 is vertical through the base; J2 sits ``A1`` in front of it
  and ``D1`` above the floor; the upper arm is ``A2`` long; the forearm starts
  ``A3`` above the elbow and reaches ``D4`` to the wrist centre, where J4, J5
  and J6 meet; the TCP is ``TOOL`` below the wrist centre. At zero joints the
  arm reports X 198.67, Y 0, Z 230.72 and the tool points straight down.
- Orientation: the reported (Rx, Ry, Rz) are Z-Y-X Euler angles,
  R = Rz(Rz) Ry(Ry) Rx(Rx), of the tool frame, which is the base frame at zero
  joints. In joint terms R = Rz(J1) Ry(J2 + J3) Rx(J4) Ry(J5) Rz(J6). Of the two
  triples that give the same R, the arm reports the one whose Rx is nearest J4
  (e.g. (0, -100, 0) at J5 = -100°, not (180, -80, 180)).
- Coordinate moves: the firmware solves them with a ``IK_TOOL`` (24.0 mm) tool
  but reports positions with ``TOOL`` (24.28 mm), so a pose it reaches with the
  tool pointing down reads about 0.28 mm low (M20 to Z 200 reports Z 199.713).
  Of the solutions within the joint limits it takes the one nearest the
  current joints (a wrist turned past J5 = -90° stays there), and it rejects
  a pose outside the workspace (``Error,E118``) without moving.

The 3D model in wlkata_arm_virtual-reality (URDF ``wlkata_mirobot_description``,
loaded with three.js Euler 'XYZ' rpy) has the same joints; its forearm is
0.23 mm shorter (168.75 mm), so its TCP is 0.23 mm short of the arm's.

Joint order (degrees in simulator state):
    J1..J6  <->  angle_X, angle_Y, angle_Z, angle_A, angle_B, angle_C

Cartesian state (mm / degrees):
    X, Y, Z, Rx, Ry, Rz  <->  coordinate_* fields
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

# Geometry the firmware uses (mm), fitted to measured poses within 0.002 mm
D1 = 127.0      # floor to the J2 axis
A1 = 29.69      # J1 axis to the J2 axis
A2 = 108.0      # upper arm: J2 axis to J3 axis
A3 = 20.0       # J3 axis to the forearm axis
D4 = 168.98     # forearm: J3 axis to the wrist centre
TOOL = 24.28    # wrist centre to the TCP in the poses the arm reports
IK_TOOL = 24.0  # ... and in the coordinate moves it solves

# Joint limits (degrees). Placeholder: the 3D model's URDF limits until the
# arm's own are measured.
JOINT_LIMITS_DEG: Tuple[Tuple[float, float], ...] = (
    (-110.0, 160.0),
    (-35.0, 70.0),
    (-120.0, 60.0),
    (-180.0, 145.0),
    (-200.0, 30.0),
    (-360.0, 360.0),
)

_L3 = math.hypot(A3, D4)        # J3 axis to the wrist centre
_PHI = math.atan2(A3, D4)       # ... above the forearm axis
_EPS = 1e-9
_LIMIT_TOL_DEG = 1e-6

Matrix = List[List[float]]


# ---------------------------------------------------------------------------
# 3x3 rotations
# ---------------------------------------------------------------------------

def _rx(a: float) -> Matrix:
    c, s = math.cos(a), math.sin(a)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _ry(a: float) -> Matrix:
    c, s = math.cos(a), math.sin(a)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rz(a: float) -> Matrix:
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _mul(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] for j in range(3)] for i in range(3)]


def _transpose(a: Matrix) -> Matrix:
    return [[a[j][i] for j in range(3)] for i in range(3)]


def _apply(a: Matrix, v: Sequence[float]) -> Tuple[float, float, float]:
    return tuple(a[i][0] * v[0] + a[i][1] * v[1] + a[i][2] * v[2] for i in range(3))


def _wrap_deg(a: float) -> float:
    """Angle in (-180, 180]."""
    a = math.fmod(a + 180.0, 360.0)
    if a <= 0.0:
        a += 360.0
    return a - 180.0


def euler_to_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> Matrix:
    """R = Rz(Rz) Ry(Ry) Rx(Rx), the Mirobot's (A, B, C) convention."""
    return _mul(_rz(math.radians(rz_deg)), _mul(_ry(math.radians(ry_deg)), _rx(math.radians(rx_deg))))


def matrix_to_euler(R: Matrix, near_rx_deg: float = 0.0) -> Tuple[float, float, float]:
    """(Rx, Ry, Rz) degrees with R = Rz(Rz) Ry(Ry) Rx(Rx).

    Of the two triples that give R, the one whose Rx is nearest
    ``near_rx_deg`` (the arm reports the one nearest J4). With Ry = ±90°
    only Rx ∓ Rz is fixed, and Rx is ``near_rx_deg``.
    """
    s_pitch = -R[2][0]
    c_pitch = math.hypot(R[0][0], R[1][0])
    if c_pitch < _EPS:
        rx = math.radians(near_rx_deg)
        if s_pitch > 0:     # Ry = +90°: R depends on Rx - Rz
            rz = rx - math.atan2(R[0][1], R[1][1])
            ry = 90.0
        else:               # Ry = -90°: R depends on Rx + Rz
            rz = math.atan2(-R[0][1], R[1][1]) - rx
            ry = -90.0
        return (_wrap_deg(near_rx_deg), ry, _wrap_deg(math.degrees(rz)))
    pitch = math.degrees(math.atan2(s_pitch, c_pitch))
    roll = math.degrees(math.atan2(R[2][1], R[2][2]))
    yaw = math.degrees(math.atan2(R[1][0], R[0][0]))
    other = (_wrap_deg(roll + 180.0), _wrap_deg(180.0 - pitch), _wrap_deg(yaw + 180.0))
    if abs(_wrap_deg(other[0] - near_rx_deg)) < abs(_wrap_deg(roll - near_rx_deg)):
        return other
    return (roll, pitch, yaw)


class MirobotKinematics:
    """FK / IK of the WLKATA Mirobot as its firmware computes them."""

    def __init__(
        self,
        tool_mm: float = TOOL,
        ik_tool_mm: float = IK_TOOL,
        limits_deg: Sequence[Tuple[float, float]] = JOINT_LIMITS_DEG,
    ):
        self.tool_mm = float(tool_mm)
        self.ik_tool_mm = float(ik_tool_mm)
        self.limits_deg = tuple((float(lo), float(hi)) for lo, hi in limits_deg)

    # ── Forward ────────────────────────────────────────────────────────

    def rotation(self, joint_deg: Sequence[float]) -> Matrix:
        """Tool orientation in the base frame: Rz(J1) Ry(J2+J3) Rx(J4) Ry(J5) Rz(J6)."""
        j = [math.radians(float(a)) for a in joint_deg[:6]]
        return _mul(_mul(_rz(j[0]), _ry(j[1] + j[2])), _mul(_rx(j[3]), _mul(_ry(j[4]), _rz(j[5]))))

    def wrist_centre(self, joint_deg: Sequence[float]) -> Tuple[float, float, float]:
        """Where J4, J5 and J6 meet (mm)."""
        j1, j2, j3 = (math.radians(float(a)) for a in joint_deg[:3])
        t = j2 + j3
        r = A1 + A2 * math.sin(j2) + A3 * math.sin(t) + D4 * math.cos(t)
        h = D1 + A2 * math.cos(j2) + A3 * math.cos(t) - D4 * math.sin(t)
        return (r * math.cos(j1), r * math.sin(j1), h)

    def forward(
        self, joint_deg: Sequence[float], tool_mm: Optional[float] = None
    ) -> Tuple[float, float, float, float, float, float]:
        """FK: joint degrees → (X, Y, Z mm, Rx, Ry, Rz deg), as the arm reports it."""
        tool = self.tool_mm if tool_mm is None else float(tool_mm)
        R = self.rotation(joint_deg)
        w = self.wrist_centre(joint_deg)
        d = _apply(R, (0.0, 0.0, -tool))
        rx, ry, rz = matrix_to_euler(R, near_rx_deg=float(joint_deg[3]))
        return (w[0] + d[0], w[1] + d[1], w[2] + d[2], rx, ry, rz)

    # ── Inverse ────────────────────────────────────────────────────────

    def within_limits(self, joint_deg: Sequence[float]) -> bool:
        return all(lo - _LIMIT_TOL_DEG <= q <= hi + _LIMIT_TOL_DEG
                   for q, (lo, hi) in zip(joint_deg, self.limits_deg))

    def clamp_joints_rad(self, q: Sequence[float]) -> List[float]:
        out = []
        for i, qi in enumerate(q):
            lo, hi = (math.radians(v) for v in self.limits_deg[i])
            out.append(max(lo, min(hi, float(qi))))
        return out

    def _turns(self, index: int, angle: float, seed: float) -> List[float]:
        """``angle`` and its whole turns within the joint's limits, nearest ``seed`` first."""
        lo, hi = self.limits_deg[index]
        base = angle + 360.0 * round((seed - angle) / 360.0)
        out = [base + 360.0 * k for k in (-1, 0, 1)]
        out = [a for a in out if lo - _LIMIT_TOL_DEG <= a <= hi + _LIMIT_TOL_DEG]
        return sorted(out, key=lambda a: abs(a - seed))

    def solutions(
        self,
        target_mm_rpy: Sequence[float],
        tool_mm: Optional[float] = None,
        seed_deg: Optional[Sequence[float]] = None,
    ) -> List[List[float]]:
        """Every joint solution (degrees) within the limits for a pose, nearest ``seed_deg`` first."""
        tool = self.tool_mm if tool_mm is None else float(tool_mm)
        seed = [float(a) for a in (seed_deg if seed_deg is not None else [0.0] * 6)]
        x, y, z, rx, ry, rz = (float(v) for v in target_mm_rpy[:6])
        R = euler_to_matrix(rx, ry, rz)
        dx, dy, dz = _apply(R, (0.0, 0.0, tool))
        wx, wy, wz = x + dx, y + dy, z + dz

        found: List[List[float]] = []
        # J1 facing the wrist centre, or turned away with the arm reaching back over the base
        for j1, reach in ((math.atan2(wy, wx), 1.0), (math.atan2(-wy, -wx), -1.0)):
            u = reach * math.hypot(wx, wy) - A1
            v = wz - D1
            s = (u * u + v * v - A2 * A2 - _L3 * _L3) / (2.0 * A2 * _L3)
            if abs(s) > 1.0:
                continue
            for j3 in (_PHI - math.asin(s), _PHI - math.pi + math.asin(s)):
                bend = math.pi / 2.0 + j3 - _PHI
                j2 = math.atan2(u, v) - math.atan2(_L3 * math.sin(bend), A2 + _L3 * math.cos(bend))
                W = _mul(_transpose(_mul(_rz(j1), _ry(j2 + j3))), R)   # = Rx(J4) Ry(J5) Rz(J6)
                c5 = math.hypot(W[0][0], W[0][1])
                if c5 < _EPS:
                    # J5 = ±90°: J4 and J6 turn about one axis; keep J4 where it is
                    j4 = math.radians(seed[3])
                    if W[0][2] > 0:
                        wrists = [(j4, math.pi / 2, math.atan2(W[1][0], W[1][1]) - j4)]
                    else:
                        wrists = [(j4, -math.pi / 2, math.atan2(W[1][0], W[1][1]) + j4)]
                else:
                    wrists = [
                        (math.atan2(-W[1][2] * sign, W[2][2] * sign),
                         math.atan2(W[0][2], c5 * sign),
                         math.atan2(-W[0][1] * sign, W[0][0] * sign))
                        for sign in (1.0, -1.0)
                    ]
                arm = []
                for i, a in enumerate((j1, j2, j3)):
                    turns = self._turns(i, math.degrees(a), seed[i])
                    if not turns:
                        break
                    arm.append(turns[0])
                if len(arm) < 3:
                    continue    # J1-J3 outside their limits
                for j4, j5, j6 in wrists:
                    for a4 in self._turns(3, math.degrees(j4), seed[3]):
                        for a5 in self._turns(4, math.degrees(j5), seed[4]):
                            for a6 in self._turns(5, math.degrees(j6), seed[5]):
                                found.append(arm + [a4, a5, a6])
        found.sort(key=lambda q: sum(abs(a - b) for a, b in zip(q, seed)))
        return found

    def inverse(
        self,
        target_mm_rpy: Sequence[float],
        seed_deg: Optional[Sequence[float]] = None,
        max_iter: Optional[int] = None,
        tol: Optional[float] = None,
        tool_mm: Optional[float] = None,
    ) -> Tuple[List[float], bool]:
        """IK: Cartesian (mm, deg) → joint degrees, the solution nearest ``seed_deg``.

        Returns (joints_deg, reachable); when no solution is within the
        limits the joints are ``seed_deg`` (or zero) and reachable is False.
        ``max_iter`` / ``tol`` are ignored: the solution is closed form.
        """
        seed = [float(a) for a in (seed_deg if seed_deg is not None else [0.0] * 6)]
        found = self.solutions(target_mm_rpy, tool_mm=tool_mm, seed_deg=seed)
        if not found:
            return seed, False
        return found[0], True


# Shared instance for the simulator handlers
_DEFAULT_KIN = MirobotKinematics()

_POSE_FIELDS = ("coordinate_X", "coordinate_Y", "coordinate_Z", "coordinate_RX", "coordinate_RY", "coordinate_RZ")
_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2, "A": 3, "B": 4, "C": 5}


def joints_from_state(state) -> List[float]:
    """Map simulator state joint fields → [J1..J6] degrees."""
    return [
        float(state.angle_X),
        float(state.angle_Y),
        float(state.angle_Z),
        float(state.angle_A),
        float(state.angle_B),
        float(state.angle_C),
    ]


def joints_to_state(state, joints_deg: Sequence[float]) -> None:
    state.angle_X = float(joints_deg[0])
    state.angle_Y = float(joints_deg[1])
    state.angle_Z = float(joints_deg[2])
    state.angle_A = float(joints_deg[3])
    state.angle_B = float(joints_deg[4])
    state.angle_C = float(joints_deg[5])


def _pose_from_state(state) -> List[float]:
    return [float(getattr(state, f)) for f in _POSE_FIELDS]


def _pose_to_state(state, pose: Sequence[float]) -> None:
    for f, v in zip(_POSE_FIELDS, pose):
        setattr(state, f, float(v))


def apply_fk_to_state(state, kin: Optional[MirobotKinematics] = None) -> None:
    """After a joint move: report the pose FK gives; coordinate moves continue from it."""
    kin = kin or _DEFAULT_KIN
    pose = kin.forward(joints_from_state(state))
    _pose_to_state(state, pose)
    if hasattr(state, "cartesian_target"):
        state.cartesian_target = list(pose)


def _move_to(state, target: Sequence[float], kin: MirobotKinematics) -> bool:
    q, ok = kin.inverse(target, seed_deg=joints_from_state(state), tool_mm=kin.ik_tool_mm)
    if not ok:
        return False
    joints_to_state(state, q)
    _pose_to_state(state, kin.forward(q))
    if hasattr(state, "cartesian_target"):
        state.cartesian_target = [float(v) for v in target]
    return True


def apply_cartesian_move(
    state,
    values: Dict[str, float],
    incremental: bool = False,
    kin: Optional[MirobotKinematics] = None,
) -> bool:
    """Run an M20 coordinate move the way the Mirobot firmware does.

    ``values`` maps G-code axes (X, Y, Z mm; A, B, C = Rx, Ry, Rz deg) to the
    command's numbers; axes left out keep the current target. G91 steps add
    to the last target, not to the reported pose. Returns False, changing
    nothing, when the pose is outside the workspace or the joint limits.
    """
    kin = kin or _DEFAULT_KIN
    reported = _pose_from_state(state)
    target = list(reported)
    last = getattr(state, "cartesian_target", None)
    # The last target still describes this pose unless someone edited the state
    if last is not None and all(abs(a - b) < 1e-6 for a, b in
                                zip(reported, kin.forward(joints_from_state(state)))):
        target = [float(v) for v in last]
    for axis, value in values.items():
        i = _AXIS_INDEX[axis.upper()]
        target[i] = target[i] + float(value) if incremental else float(value)
    return _move_to(state, target, kin)


def apply_ik_to_state(state, kin: Optional[MirobotKinematics] = None) -> bool:
    """Move to the Cartesian target held in the coordinate fields (IK).

    Returns False and leaves the joints, and the pose they report, as they
    were when the target is unreachable.
    """
    kin = kin or _DEFAULT_KIN
    target = _pose_from_state(state)
    if _move_to(state, target, kin):
        return True
    _pose_to_state(state, kin.forward(joints_from_state(state)))
    return False
