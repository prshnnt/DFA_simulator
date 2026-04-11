"""DFA Logic Module - Core automata engine."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Transition:
    """Represents a DFA transition."""
    from_state: str
    to_state: str
    symbol: str


@dataclass
class DFA:
    """Deterministic Finite Automaton."""
    states: set[str] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[tuple[str, str], str] = field(default_factory=dict)
    start_state: str = ""
    final_states: set[str] = field(default_factory=set)

    def add_transition(self, from_state: str, symbol: str, to_state: str) -> None:
        """Add a transition to the DFA."""
        self.states.add(from_state)
        self.states.add(to_state)
        self.alphabet.add(symbol)
        self.transitions[(from_state, symbol)] = to_state

    def get_transition(self, state: str, symbol: str) -> Optional[str]:
        """Get the next state for a given state and symbol."""
        return self.transitions.get((state, symbol))

    def validate_string(self, input_string: str) -> bool:
        """Check if input string contains only valid symbols."""
        return all(c in self.alphabet for c in input_string)

    def reset(self) -> None:
        """Reset DFA to initial state."""
        pass  # DFA structure doesn't change


class SimulationState:
    """Tracks the current state of a DFA simulation."""

    def __init__(self, dfa: DFA):
        self.dfa = dfa
        self.current_state: str = dfa.start_state
        self.previous_state: Optional[str] = None
        self.input_string: str = ""
        self.current_index: int = 0
        self.is_running: bool = False
        self.is_finished: bool = False
        self.accepted: bool = False

    def start(self, input_string: str) -> bool:
        """Initialize simulation with input string."""
        if not self.dfa.validate_string(input_string):
            return False
        self.input_string = input_string
        self.current_state = self.dfa.start_state
        self.previous_state = None
        self.current_index = 0
        self.is_running = True
        self.is_finished = False
        return True

    def step(self) -> Optional[tuple[str, str, str]]:
        """
        Execute one step of the simulation.
        Returns (from_state, symbol, to_state) if successful, None if finished.
        """
        if not self.is_running or self.current_index >= len(self.input_string):
            self.is_running = False
            self.is_finished = True
            self.accepted = self.current_state in self.dfa.final_states
            return None

        symbol = self.input_string[self.current_index]
        self.previous_state = self.current_state
        next_state = self.dfa.get_transition(self.current_state, symbol)

        if next_state is None:
            self.is_running = False
            self.is_finished = True
            self.accepted = False
            return None

        self.current_state = next_state
        self.current_index += 1
        return (self.previous_state, symbol, self.current_state)

    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.current_state = self.dfa.start_state
        self.previous_state = None
        self.input_string = ""
        self.current_index = 0
        self.is_running = False
        self.is_finished = False
        self.accepted = False


def create_example_dfa() -> DFA:
    """Create an example DFA that accepts strings with even number of 'a's."""
    dfa = DFA()
    dfa.start_state = "q0"
    dfa.final_states = {"q0"}

    # Even number of a's (including zero)
    dfa.add_transition("q0", "a", "q1")
    dfa.add_transition("q1", "a", "q0")
    dfa.add_transition("q0", "b", "q0")
    dfa.add_transition("q1", "b", "q1")

    return dfa


def create_binary_dfa() -> DFA:
    """Create a DFA that accepts binary strings ending with '01'."""
    dfa = DFA()
    dfa.start_state = "q0"
    dfa.final_states = {"q0"}

    # Ends with 01
    dfa.add_transition("q0", "0", "q1")
    dfa.add_transition("q0", "1", "q0")
    dfa.add_transition("q1", "0", "q1")
    dfa.add_transition("q1", "1", "q2")
    dfa.add_transition("q2", "0", "q1")
    dfa.add_transition("q2", "1", "q0")

    return dfa
