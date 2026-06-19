# Architecture

This document explains how the simulator is wired together. It is meant for
contributors who want to change rendering, add features, or extract parts of
the app into separate modules.

## High-level data flow

```
user input ─► InputBox ─► DFASimulator ─► SimState.step ─► Animator ─► Renderer ─► screen
                  ▲                                                        │
                  └────────────────── pygame events ◄──────────────────────┘
```

The `DFASimulator` class is the single owner of the main loop and the bridge
between pygame events and the pure-logic core.

## Modules

Although the whole app currently lives in `main.py`, the file is divided into
logically distinct sections.

### Core (no pygame dependency)

These types can be imported and tested without a display:

| Class         | Responsibility                                               |
|---------------|--------------------------------------------------------------|
| `DFA`         | Storage of states, alphabet, transitions, final states      |
| `SimState`    | Single-step execution of the DFA on an input string          |
| `calc_positions` | Circular layout helper for placing states on screen      |
| `create_binary_dfa` | Factory that builds the bundled example DFA            |

### UI / pygame

| Class         | Responsibility                                               |
|---------------|--------------------------------------------------------------|
| `Mode` / `AnimState` | Enumerations describing execution and animation phases |
| `Button`      | Hit-testable, optionally disabled rectangle with a label    |
| `InputBox`    | Text input restricted to characters from the DFA alphabet    |
| `Animator`    | Cubic-ease token motion, pulsing highlight, result fade-in   |
| `Renderer`    | All drawing routines (states, edges, arrows, UI chrome)      |
| `DFASimulator` | Main loop: events, simulation steps, rendering               |

## Rendering pipeline

Each frame `DFASimulator.render` does, in order:

1. Clear the screen with the background colour.
2. Draw the status text at the top.
3. Draw every transition, highlighting the currently active one.
4. Draw every state (with pulse / accept / reject colouring as appropriate).
5. Draw the token if the animator is in the `MOVING` state.
6. Draw the current input symbol counter.
7. Draw the result banner if the animator is `FINISHED`.
8. Draw the input box and buttons.

## Animation easing

The token follows a cubic ease-in-out:

```
if t < 0.5:
    eased = 4 * t ** 3
else:
    eased = 1 - ((-2 * t + 2) ** 3) / 2
```

This produces slow start, fast middle, slow end — visually less jerky than a
linear interpolation.

## State machine semantics

`SimState.step` is intentionally explicit:

- Returns `(prev, symbol, next)` on a successful transition.
- Returns `None` and marks the simulation as finished when the input is
  consumed *or* the current state has no outgoing transition for the next
  symbol.
- The caller (`DFASimulator.do_step`) decides what to do with the result —
  typically starting a new animation and queueing the next step in `AUTO`
  mode, or waiting for the user in `STEP` mode.

## Adding a new DFA

The simplest way to add a custom DFA is to replace the call inside
`DFASimulator.__init__`:

```python
self.dfa = create_binary_dfa()
```

with a builder of your own, e.g.:

```python
def create_ends_in_one() -> DFA:
    dfa = DFA()
    dfa.start_state = "q0"
    dfa.final_states = {"q1"}
    dfa.add("q0", "0", "q0")
    dfa.add("q0", "1", "q1")
    dfa.add("q1", "0", "q0")
    dfa.add("q1", "1", "q1")
    return dfa
```

The simulator only relies on `dfa.states`, `dfa.alphabet`,
`dfa.transitions`, `dfa.start_state`, and `dfa.final_states`. Keep the
alphabet small (1–4 symbols) for readable edge labels.

## Testing strategy

Pure-logic classes (`DFA`, `SimState`, `calc_positions`) are covered by
`tests/test_dfa.py`. These tests never open a pygame window, so they run on
any CI machine without an X server or display.

Anything that requires a real `pygame.Surface` (rendering, animation) is
verified manually via `uv run python main.py`.