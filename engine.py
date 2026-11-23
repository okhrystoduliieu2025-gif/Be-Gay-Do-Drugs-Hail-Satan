from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Optional
from algorithms import MyStack, MyQueue, count_recipients, rotate_judges_left

DECK_SIZES = {"characters": 120, "attributes": 120, "goals": 50}


@dataclass
class Player:
    name: str
    score: int = 0


@dataclass
class Hand:
    characters: list[str]
    attributes: list[str]
    chosen_character: Optional[str] = None


class Deck:
    def __init__(self, cards: list[str], rng: random.Random):
        if not cards or len(cards) != len(set(cards)):
            raise ValueError("Deck cards must be unique, nonempty strings")
        self.original_cards = cards[:]
        self.draw_pile = []
        self.stack = MyStack(self.draw_pile)
        for card in cards:
            self.stack.push(card)
        self.discard_pile: list[str] = []
        self.rng = rng
        self.rng.shuffle(self.draw_pile)

    def draw(self, amount: int = 1) -> list[str]:
        result = []
        for _ in range(amount):
            if self.stack.empty():
                if not self.discard_pile:
                    raise RuntimeError("No cards left to draw, including discards")
                self.draw_pile, self.discard_pile = self.discard_pile, []
                self.stack = MyStack(self.draw_pile)
                self.rng.shuffle(self.draw_pile)
            result.append(self.stack.pull())
        return result

    def discard(self, cards: list[str]) -> None:
        self.discard_pile.extend(cards)


class Game:
    def __init__(self, names: list[str], mode: str, card_data: dict[str, list[str]],
                 rng: Optional[random.Random] = None, first_judge: Optional[int] = None):
        if mode not in ("main", "battle"):
            raise ValueError("mode must be 'main' or 'battle'")
        if not 3 <= len(names) <= 5:
            raise ValueError("3-5 players are required (including judge)")
        if not all(name.strip() for name in names):
            raise ValueError("Player names cannot be blank")
        if len(set(name.casefold() for name in names)) != len(names):
            raise ValueError("Player names must be unique")
        for name, expected in DECK_SIZES.items():
            cards = card_data.get(name)
            if not isinstance(cards, list) or len(cards) != expected:
                raise ValueError(f"Expected exactly {expected} {name}")
            if not all(isinstance(c, str) and c.strip() for c in cards):
                raise ValueError(f"Empty or invalid {name} entry")
        self.rng = rng or random.Random()
        self.mode = mode
        self.players = [Player(name.strip()) for name in names]
        self.decks = {key: Deck(card_data[key], self.rng) for key in DECK_SIZES}
        initial_judge = self.rng.randrange(len(names)) if first_judge is None else first_judge
        if not 0 <= initial_judge < len(names):
            raise ValueError("Invalid initial judge")
        self.judge_queue = MyQueue(len(names))
        for i in range(len(names)):
            self.judge_queue.enque(i)
        rotate_judges_left(self.judge_queue, initial_judge)
        self.rounds_completed = 0
        self.total_rounds = len(names) * 2
        self.round_active = False
        self.goal: Optional[str] = None
        self.hands: dict[int, Hand] = {}
        self.distributions: dict[int, list[int]] = {}
        self.final_attributes: dict[int, list[str]] = {}

    @property
    def judge(self) -> int:
        return self.judge_queue.front()

    @property
    def competitors(self) -> list[int]:
        j = self.judge
        return [(j + distance) % len(self.players)
                for distance in range(1, len(self.players))]

    @property
    def game_over(self) -> bool:
        return self.rounds_completed == self.total_rounds

    def keep_quota(self) -> int:
        return {3: 2, 4: 2, 5: 1}[len(self.players)]

    def give_quota(self) -> int:
        return {3: 2, 4: 1, 5: 1}[len(self.players)]

    def start_round(self) -> None:
        if self.game_over or self.round_active:
            raise RuntimeError("Cannot begin a round now")
        self.goal = (self.decks["goals"].draw()[0] if self.mode == "main"
                     else "Win a battle against the other characters")
        self.hands = {}
        self.distributions = {}
        self.final_attributes = {}
        for pid in self.competitors:
            self.hands[pid] = Hand(
                characters=self.decks["characters"].draw(2),
                attributes=self.decks["attributes"].draw(4),
            )
        self.round_active = True

    def choose_character(self, pid: int, card_index: int) -> None:
        if not self.round_active or pid not in self.hands:
            raise ValueError("Not a competitor in the current round")
        if card_index not in (0, 1):
            raise ValueError("Choose character 0 or 1")
        if pid in self.distributions:
            raise ValueError("Character choice is already locked")
        self.hands[pid].chosen_character = self.hands[pid].characters[card_index]

    def set_distribution(self, pid: int, recipients: list[int]) -> None:
        if not self.round_active or pid not in self.hands:
            raise ValueError("Not a competitor")
        if self.hands[pid].chosen_character is None:
            raise ValueError("Select a character first")
        if len(recipients) != 4:
            raise ValueError("Each of four attributes needs a recipient")
        counts = count_recipients(recipients)
        if set(recipients) - set(self.competitors):
            raise ValueError("Only non-judge players can receive cards")
        if counts[pid] != self.keep_quota():
            raise ValueError("Incorrect number of kept cards")
        for other in self.competitors:
            if other != pid and counts[other] != self.give_quota():
                raise ValueError("Incorrect number of cards given to a player")
        self.distributions[pid] = recipients[:]

    @property
    def ready_to_argue(self) -> bool:
        return (self.round_active and
                len(self.distributions) == len(self.competitors))

    def build_characters(self) -> dict[int, list[str]]:
        if not self.ready_to_argue:
            raise RuntimeError("Everyone must distribute attributes first")
        self.final_attributes = {pid: [] for pid in self.competitors}
        for source, recipients in self.distributions.items():
            for card, recipient in zip(self.hands[source].attributes, recipients):
                self.final_attributes[recipient].append(card)
        if any(len(cards) != 4 for cards in self.final_attributes.values()):
            raise AssertionError("Each competitor must have four final attributes")
        return self.final_attributes

    def award_point(self, winner: int) -> None:
        if not self.ready_to_argue or winner not in self.competitors:
            raise ValueError("Judge must choose a competing player")
        self.players[winner].score += 1

        for hand in self.hands.values():
            self.decks["characters"].discard(hand.characters)
            self.decks["attributes"].discard(hand.attributes)
        if self.mode == "main" and self.goal is not None:
            self.decks["goals"].discard([self.goal])
        self.hands = {}
        self.distributions = {}
        self.final_attributes = {}
        self.goal = None
        self.round_active = False
        self.rounds_completed += 1
        rotate_judges_left(self.judge_queue)

    def top_scorers(self) -> list[int]:
        highest_score = max(player.score for player in self.players)
        return [pid for pid, player in enumerate(self.players)
                if player.score == highest_score]

    def final_winners(self) -> list[int]:
        if not self.game_over:
            raise RuntimeError("Game is not finished")
        return self.top_scorers()


def load_cards(path: Path | str) -> dict[str, list[str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
