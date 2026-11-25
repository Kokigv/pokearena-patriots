"""Pruebas puras del Sprint 3, sin servicios externos."""
import pytest

from pokearena.gameplay.domain.rules import RuleViolation, elo_window, prepare_state, turn_start, validate_deck


def test_deck_validates_count_duplicates_and_ownership():
    valid = [f'C{i}' for i in range(12)]
    validate_deck(valid, set(valid))
    with pytest.raises(RuleViolation, match='12 cartas'):
        validate_deck(valid[:-1], set(valid))
    with pytest.raises(RuleViolation, match='repetidas'):
        validate_deck(valid[:-1] + [valid[0]], set(valid))
    with pytest.raises(RuleViolation, match='no poseídas'):
        validate_deck(valid, set(valid[:-1]))


def test_window_is_bounded():
    assert elo_window(0) == 100
    assert elo_window(15) == 150
    assert elo_window(9999) == 500


def test_match_initial_state_and_turn():
    cards = [f'C{i}' for i in range(12)]
    locations = [{'id': str(i), 'assignable_to_matches': True, 'image_status': 'READY', 'card_limit': i} for i in range(1, 5)]
    state = prepare_state(cards, cards, locations, 123)
    assert len(set(state['locations'])) == 3
    assert len(state['hand_one']) == len(state['hand_two']) == 3
    assert state['energy'] == 2 and state['turn_seconds'] == 30
    assert state == prepare_state(cards, cards, locations, 123)
    next_state = turn_start(state, 1)
    assert len(next_state['hand_one']) == 4
    assert next_state['energy'] == 3


def test_location_requirements():
    cards = [str(i) for i in range(12)]
    places = [{'id': str(i), 'card_limit': 0, 'image_status': 'READY', 'assignable_to_matches': True} for i in range(3)]
    with pytest.raises(RuleViolation, match='dos ubicaciones'):
        prepare_state(cards, cards, places, 4)


def test_hand_size_never_exceeds_seven():
    cards = [str(i) for i in range(12)]
    places = [{'id': str(i), 'card_limit': 2, 'image_status': 'READY', 'assignable_to_matches': True} for i in range(3)]
    state = prepare_state(cards, cards, places, 3)
    for _ in range(20):
        state = turn_start(state, 1)
    assert len(state['hand_one']) == 7
    assert state['energy'] == 7
