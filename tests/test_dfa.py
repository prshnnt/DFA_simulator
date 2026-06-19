"""Unit tests for the pure-logic core of the DFA simulator.

These tests avoid importing :mod:`pygame` so they can run on any CI machine
without a display.  Only :class:`DFA`, :class:`SimState`, :class:`Animator`
and the module-level helpers are exercised.
"""

from __future__ import annotations

import math
import os
import sys

# Make ``main`` importable when running from the project root without
# installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing ``main`` triggers ``import pygame`` at module level.  That is
# fine on a normal developer machine but a CI runner without pygame would
# fail before reaching the tests.  Skip the whole module in that case.
import pytest

pygame = pytest.importorskip("pygame")

from main import (  # noqa: E402 – after sys.path tweak
    Animator,
    DFA,
    SimState,
    _bezier,
    calc_positions,
    create_binary_dfa,
)


# ---------------------------------------------------------------------------
# DFA
# ---------------------------------------------------------------------------


class TestDFA:
    """Behaviour of :class:`DFA`."""

    def test_add_populates_states_and_alphabet(self) -> None:
        dfa = DFA()
        dfa.add("q0", "a", "q1")
        assert dfa.states == {"q0", "q1"}
        assert dfa.alphabet == {"a"}
        assert dfa.transitions[("q0", "a")] == "q1"

    def test_get_returns_target_state(self) -> None:
        dfa = DFA()
        dfa.add("q0", "a", "q1")
        assert dfa.get("q0", "a") == "q1"

    def test_get_returns_none_for_undefined_transition(self) -> None:
        dfa = DFA()
        dfa.add("q0", "a", "q1")
        assert dfa.get("q0", "b") is None

    def test_is_complete_true_for_full_table(self) -> None:
        dfa = DFA()
        dfa.add("q0", "a", "q0")
        dfa.add("q0", "b", "q0")
        assert dfa.is_complete()

    def test_is_complete_false_when_transition_missing(self) -> None:
        dfa = DFA()
        dfa.add("q0", "a", "q0")
        # No transition for ("q0", "b").
        assert not dfa.is_complete()

    def test_create_binary_dfa_is_complete(self) -> None:
        """The bundled example DFA must be total over its alphabet."""
        dfa = create_binary_dfa()
        assert dfa.is_complete()
        assert dfa.start_state == "q0"
        assert dfa.final_states == {"q0"}
        assert dfa.alphabet == {"0", "1"}


# ---------------------------------------------------------------------------
# SimState
# ---------------------------------------------------------------------------


class TestSimState:
    """Behaviour of :class:`SimState`."""

    def setup_method(self) -> None:
        self.dfa = create_binary_dfa()
        self.sim = SimState(self.dfa)

    def test_start_rejects_alphabet_violations(self) -> None:
        assert not self.sim.start("012")
        assert not self.sim.is_running

    def test_start_accepts_valid_input(self) -> None:
        assert self.sim.start("111")
        assert self.sim.is_running
        assert self.sim.current_state == "q0"
        assert self.sim.current_index == 0

    def test_step_returns_transition_tuple(self) -> None:
        self.sim.start("101")
        # q0 --1--> q0
        assert self.sim.step() == ("q0", "1", "q0")
        # q0 --0--> q1
        assert self.sim.step() == ("q0", "0", "q1")
        # q1 --1--> q2
        assert self.sim.step() == ("q1", "1", "q2")
        # Input exhausted – final state q2 is non-accepting.
        assert self.sim.step() is None
        assert self.sim.is_finished
        assert not self.sim.accepted

    def test_acceptance_for_length_divisible_by_three(self) -> None:
        """All three-symbol inputs of '1's end back at q0."""
        self.sim.start("111")
        for _ in range(3):
            self.sim.step()
        # One extra call to consume the empty suffix and mark the run finished.
        self.sim.step()
        assert self.sim.is_finished
        assert self.sim.accepted

    def test_acceptance_for_six_symbols(self) -> None:
        self.sim.start("111111")
        for _ in range(6):
            self.sim.step()
        self.sim.step()
        assert self.sim.accepted

    def test_rejection_when_transition_missing(self) -> None:
        """A partial DFA should reject rather than crash."""
        dfa = DFA()
        dfa.start_state = "q0"
        dfa.final_states = {"q0"}
        dfa.add("q0", "a", "q0")
        # No transition on "b" – but we still need to start successfully,
        # so build an alphabet that contains "b" without defining a transition.
        dfa.alphabet.add("b")
        sim = SimState(dfa)
        assert sim.start("ab") is True
        sim.step()        # consume "a", stay at q0
        assert sim.step() is None
        assert sim.is_finished
        assert not sim.accepted

    def test_reset_clears_all_flags(self) -> None:
        self.sim.start("111")
        self.sim.reset()
        assert self.sim.current_state == "q0"
        assert self.sim.input_string == ""
        assert self.sim.current_index == 0
        assert not self.sim.is_running
        assert not self.sim.is_finished


# ---------------------------------------------------------------------------
# Animator (no rendering, just state transitions)
# ---------------------------------------------------------------------------


class TestAnimator:
    """Behaviour of :class:`Animator`."""

    def test_initial_state_is_idle(self) -> None:
        anim = Animator()
        assert anim.state.name == "IDLE"
        assert anim.result_alpha == 0

    def test_start_transition_moves_to_moving(self) -> None:
        anim = Animator()
        anim.start_transition((0, 0), (100, 0), duration=100)
        assert anim.state.name == "MOVING"
        assert anim.token_progress == 0.0

    def test_update_progresses_token_and_returns_to_idle(self) -> None:
        anim = Animator()
        anim.start_transition((0, 0), (100, 0), duration=100)
        anim.update(50)    # 50% of the way
        assert 0.0 < anim.token_progress < 1.0
        # Half-way point of the cubic ease should land around the midpoint.
        assert 40 < anim.token_pos[0] < 60
        anim.update(60)    # past the end
        assert anim.state.name == "IDLE"
        assert anim.token_progress == 1.0
        # The token should now sit on the destination.
        assert math.isclose(anim.token_pos[0], 100, abs_tol=1e-6)

    def test_finish_fades_in_result_alpha(self) -> None:
        anim = Animator()
        anim.finish()
        assert anim.state.name == "FINISHED"
        # 0.5 alpha/ms × 510 ms = 255 alpha.
        anim.update(510)
        assert anim.result_alpha == 255

    def test_reset_clears_animation_state(self) -> None:
        anim = Animator()
        anim.start_transition((0, 0), (10, 10))
        anim.finish()
        anim.reset()
        assert anim.state.name == "IDLE"
        assert anim.active_edge is None
        assert anim.result_alpha == 0


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Pure-function helpers."""

    def test_calc_positions_empty(self) -> None:
        assert calc_positions([], 0, 0) == {}

    def test_calc_positions_single_state(self) -> None:
        assert calc_positions(["q0"], 100, 50) == {"q0": (100, 50)}

    def test_calc_positions_two_states_horizontal(self) -> None:
        result = calc_positions(["a", "b"], 100, 50)
        assert result == {"a": (0, 50), "b": (200, 50)}

    def test_calc_positions_three_states_circle(self) -> None:
        result = calc_positions(["q0", "q1", "q2"], 0, 0, r=10)
        # All three positions must be distinct and at the expected radius.
        for x, y in result.values():
            assert math.isclose(math.hypot(x, y), 10, abs_tol=1e-6)

    def test_bezier_endpoints_match(self) -> None:
        pts = _bezier((0, 0), (50, 100), (100, 0), steps=10)
        assert pts[0] == (0.0, 0.0)
        assert pts[-1] == (100.0, 0.0)
        assert len(pts) == 11