from __future__ import annotations

import random
from typing import Optional

from algorithms import MyQueue, rotate_judges_left
from battle_algorithms import CardHashTable, msort
from engine import Deck

ATTACK, DEFENSE, TRICK, SKIP = "ATTACK", "DEFENSE", "TRICK", "SKIP"
MOVES = (ATTACK, DEFENSE, TRICK, SKIP)

START_HEALTH = 5
FIRST_HAND = 4
SECOND_HAND = 5
LOG_SIZE = 8

# ======================================================================
# CARD TYPES — change a card's type here.
# Every Attribute card from cards.json needs one of: ATTACK, DEFENSE, TRICK.
# (Taken from the colours in Battle_Mode.pdf: red = ATTACK, blue = DEFENSE,
#  purple = TRICK.)
# ======================================================================
ATTRIBUTE_TYPES = {
    "Crossdresser": TRICK,
    "Fallen and can’t get up": ATTACK,
    "Heterosexual": TRICK,
    "Doing drugs": DEFENSE,
    "Swears every other word": ATTACK,
    "Kleptomaniac": TRICK,
    "Takes everything literally": ATTACK,
    "Loves Astrology": TRICK,
    "Believes in Superstition": DEFENSE,
    "Forgetful": TRICK,
    "Afraid of women": DEFENSE,
    "Emophiliac": ATTACK,
    "Very allergic to wood": DEFENSE,
    "Misses their parents": ATTACK,
    "Has a Poor Sense of Direction": ATTACK,
    "Fearless": DEFENSE,
    "Illiterate": TRICK,
    "Deaf in one ear": ATTACK,
    "Homesick": DEFENSE,
    "Lonely": DEFENSE,
    "Famous Online Meme": TRICK,
    "Teamplayer who can’t do a thing alone": DEFENSE,
    "Extremely introverted and unsocial": DEFENSE,
    "Wears a hood indoors": DEFENSE,
    "Insecure about their body": DEFENSE,
    "Overly Trustful of what is written online": TRICK,
    "Hyper-fixated on number 3": ATTACK,
    "Was abducted by Aliens a week ago": DEFENSE,
    "Knows how to ride a unicycle": ATTACK,
    "Fears germs": DEFENSE,
    "Has a Tourette syndrome": ATTACK,
    "Talks to animals (they don’t talk back)": TRICK,
    "Has an issues with controlling the volume of their voice": ATTACK,
    "Listens to questionable music": DEFENSE,
    "Has a weird laugh": TRICK,
    "Knows too much": ATTACK,
    "Wears at all times a mask of a president (person to your left decides which president)": ATTACK,
    "Speaks through singing": TRICK,
    "Has trouble with time management": TRICK,
    "Talks too much": ATTACK,
    "Has over 5 fake IDs": DEFENSE,
    "Pretends to be a dog": TRICK,
    "Has a Tattoo of which they are ashamed (person to your right decides what Tattoo looks like)": DEFENSE,
    "Apologies for everything": DEFENSE,
    "Never Lies": DEFENSE,
    "Wears sandals with socks on": ATTACK,
    "Often forgets to do basic human things (eg: Blink, walk, breath)": TRICK,
    "Pretends to be dead whenever they feel danger": DEFENSE,
    "Helps EVERY elder in their vision": ATTACK,
    "Cries instead of laughing and backwards": ATTACK,
    "Talks about politics in worst moments": ATTACK,
    "Doesn’t Fact check a thing": TRICK,
    "Drunk": ATTACK,
    "Wears Glasses although their sight is perfect": TRICK,
    "Gets Rickrolled by everyone": ATTACK,
    "Perfectionist": DEFENSE,
    "Doesn’t speak any language, but at every opportunity pretends to talk it to avoid dialogues.": TRICK,
    "Made a blood pact with the wrong demon": ATTACK,
    "Received a Black Mark from the Pirate": ATTACK,
    "Is Nerd about the least interesting topic (Current Judge picks the least interesting topic)": TRICK,
    "Watched too much Sci Fi": DEFENSE,
    "Trained a dog to throw the bricks on people": ATTACK,
    "Believes that the Godfather Insists Upon Itself": TRICK,
    "Is a boogle of weasels in a trench coat": TRICK,
    "Thinks that the only game in the …… EXISTENCE IS MONOPOLY. I MEAN YEAH. SURE BUD. DON’T LOOK OUTSIDE YOU ………!!!": ATTACK,
    "Impersonates Danny DeVito": TRICK,
    "Doesn’t know the Political situation around": ATTACK,
    "Watches only remakes of the movies": DEFENSE,
    "Has a SUPERPOWER!!! To Boil Water": ATTACK,
    "Only knows how to count with a calculator": DEFENSE,
    "Listens to Guru online": TRICK,
    "Waits for the Apocalypse": ATTACK,
    "Is unable to keep a secret": ATTACK,
    "Seems rude to others": ATTACK,
    "Kisses others babies without permission": ATTACK,
    "Creates Board Games for Living, and as it is natural for the market you see, Hasbro buys his game and creates 20 trillion dollars on it, while paying them with the mac’n’cheese": DEFENSE,
    "Is Obsessed with the character to your left": DEFENSE,
    "Pretends to be the character to your right": TRICK,
    "Trust phishing messages": TRICK,
    "Has Maria 30 m away from them": TRICK,
    "Took a bite of a boneless wing": DEFENSE,
    "Asks to be read a fairytale before every sleep": DEFENSE,
    "Has a raw Chicken": ATTACK,
    "Was the first to get out of Master Chef": DEFENSE,
    "Tolerates too much": DEFENSE,
    "Has a Scottish accent": ATTACK,
    "Notices a JoJo reference in everything": TRICK,
    "Wants to be a catgirl": DEFENSE,
    "Is weird": ATTACK,
    "Believes that they are as swift as a ninja.": DEFENSE,
    "Can’t express emotions properly with a voice": DEFENSE,
    "Acts faster than thinks": ATTACK,
    "Acts with adults as if they were infants": DEFENSE,
    "Has a terrible secret": DEFENSE,
    "Cheated on the behind-the-wheel test": TRICK,
    "Doesn’t sleep well": DEFENSE,
    "Thinks toilet humour is hilarious": DEFENSE,
    "Loves Bureaucracy": TRICK,
    "Believes in benefits of urine therapy": DEFENSE,
    "Hates animals": ATTACK,
    "Is stuck in a time loop": ATTACK,
    "Believes that pizza with no toppings is the best": DEFENSE,
    "Watches Cocomelon": DEFENSE,
    "Thinks they are the smartest in the room": DEFENSE,
    "Lost their house": ATTACK,
    "Still waits for their dad with milk.": ATTACK,
    "Carries guilt for something that is clearly not their fault": DEFENSE,
    "Says that they’re fine when their not really fine but they just can’t get into it because no one understands": DEFENSE,
    "Sees the character to your left as their nemesis": ATTACK,
    "Believes that the character to your right is God": TRICK,
    "In search of the meaning of life": DEFENSE,
    "Is constantly under stress": ATTACK,
    "Wishes that they were high on a potenuse": ATTACK,
    "Has a birdbrain": DEFENSE,
    "Is in love with a fairytale (literally)": DEFENSE,
    "Sees everything closer than it appears to be in reality": TRICK,
    "Has disproportionately large body, and small head": ATTACK,
    "Has 9 lines of jaws": ATTACK,
    "Has too many online subscriptions": ATTACK,
    "Is a shopaholic": ATTACK,
}

# ======================================================================
# RESULT TABLE (2D array) — RESULTS[attacker move][defender move]
# Each entry: (attacker loses HP, defender loses HP,
#              attacker draws, defender draws)
# Row/column order: ATTACK, DEFENSE, TRICK, SKIP
# ======================================================================
RESULTS = [
    #  defender: ATTACK        DEFENSE       TRICK         SKIP
    [(0, 1, 0, 0), (0, 0, 0, 0), (0, 1, 0, 0), (0, 1, 0, 1)],  # attacker ATTACK
    [(0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 2), (0, 0, 0, 1)],  # attacker DEFENSE
    [(2, 0, 0, 0), (0, 0, 2, 0), (0, 0, 2, 0), (0, 0, 2, 1)],  # attacker TRICK
    [(2, 0, 1, 0), (0, 0, 1, 0), (0, 0, 1, 2), (0, 0, 1, 1)],  # attacker SKIP
]

BATTLE_RULES = """
BATTLE MODE — BATTLE OF IMAGINATION (2 players)

Every Attribute card is an ATTACK, DEFENSE or TRICK card.
Both players start with 5 health. There is no hand limit.
The first player starts with 4 cards, the second player with 5.
Each player may take one mulligan at the start: shuffle the hand back and draw the same number of cards.

Each round one player is the attacker and the other the defender (the roles swap every round).
The attacker secretly picks a card or SKIP, then the defender secretly picks a card or SKIP.
Both cards are revealed and the result comes from this table:

Attacker  Defender  Result
ATTACK    ATTACK    Defender loses 1 health
ATTACK    DEFENSE   No damage dealt
ATTACK    TRICK     Defender loses 1 health
ATTACK    SKIP      Defender loses 1 health and draws 1 card
DEFENSE   ATTACK    No damage dealt
DEFENSE   DEFENSE   Nothing happens
DEFENSE   TRICK     Defender draws 2 cards
DEFENSE   SKIP      Defender draws 1 card
TRICK     ATTACK    Attacker loses 2 health
TRICK     DEFENSE   Attacker draws 2 cards
TRICK     TRICK     Attacker draws 2 cards
TRICK     SKIP      Attacker draws 2 cards and defender draws 1 card
SKIP      ATTACK    Attacker loses 2 health and draws 1 card
SKIP      DEFENSE   Attacker draws 1 card
SKIP      TRICK     Attacker draws 1 card and defender draws 2 cards
SKIP      SKIP      Both draw 1 card

A player at 0 health loses.
If the deck runs out, the player with less health loses; equal health is a tie.
Pass the computer to the named player before pressing REVEAL; the hand is private.
""".strip()


def card_order(card: tuple[str, str]) -> tuple:
    # sort a hand by type first, then alphabetically
    text, kind = card
    return (MOVES.index(kind), text)


class BattlePlayer:
    def __init__(self, name: str):
        self.name = name
        self.health = START_HEALTH
        self.hand: list[tuple[str, str]] = []      # (card text, card type)
        self.mulligan_used = False


class BattleGame:
    def __init__(self, names: list[str], card_data: dict[str, list[str]],
                 rng: Optional[random.Random] = None,
                 first_player: Optional[int] = None,
                 card_types: Optional[dict[str, str]] = None):
        if len(names) != 2:
            raise ValueError("Battle Mode needs exactly 2 players")
        names = [name.strip() for name in names]
        if not all(names):
            raise ValueError("Every player needs a name.")
        if names[0].casefold() == names[1].casefold():
            raise ValueError("Player names must be different.")
        attributes = card_data.get("attributes")
        if not isinstance(attributes, list) or not attributes:
            raise ValueError("cards.json needs a list of attributes")
        card_types = ATTRIBUTE_TYPES if card_types is None else card_types

        # Hash table: Attribute text -> ATTACK / DEFENSE / TRICK
        self.types = CardHashTable(53)
        missing = []
        for text in attributes:
            kind = card_types.get(text)
            if kind not in (ATTACK, DEFENSE, TRICK):
                missing.append(text)
            self.types.put(text, kind)
        if missing:
            raise ValueError(f"No ATTACK/DEFENSE/TRICK type for: {missing[0]}")

        self.rng = rng or random.Random()
        self.deck = Deck(attributes, self.rng)      # draw pile is a MyStack
        self.players = [BattlePlayer(names[0]), BattlePlayer(names[1])]

        first = self.rng.randrange(2) if first_player is None else first_player
        if first not in (0, 1):
            raise ValueError("first_player must be 0 or 1")
        # Queue of turns: the front is the attacker of this round.
        self.turn_order = MyQueue(2)
        self.turn_order.enque(first)
        self.turn_order.enque(1 - first)
        self._draw(first, FIRST_HAND)
        self._draw(1 - first, SECOND_HAND)

        self.mulligan_queue = [first, 1 - first]
        self.phase = "mulligan"          # mulligan -> attack -> defend -> reveal
        self.round_number = 0
        self.deck_ended = False
        self.attack_card: Optional[tuple[str, str]] = None
        self.defend_card: Optional[tuple[str, str]] = None
        self.last_result = ""
        self.log: list[str] = []

    # ----- whose turn ---------------------------------------------------
    @property
    def attacker(self) -> int:
        return self.turn_order.front()

    @property
    def defender(self) -> int:
        return 1 - self.attacker

    @property
    def actor(self) -> int:
        # the player who has to act now
        if self.phase == "mulligan":
            return self.mulligan_queue[0]
        if self.phase == "defend":
            return self.defender
        return self.attacker

    @property
    def game_over(self) -> bool:
        return self.phase == "over"

    def cards_left(self) -> int:
        return len(self.deck.stack.data)

    # ----- mulligan -------------------------------------------------------
    def keep_hand(self, pid: int) -> None:
        self._check_mulligan_turn(pid)
        self._next_mulligan()

    def mulligan(self, pid: int) -> None:
        self._check_mulligan_turn(pid)
        player = self.players[pid]
        amount = len(player.hand)
        # put the hand back on the draw pile, shuffle, draw the same number
        for text, kind in player.hand:
            self.deck.stack.push(text)
        player.hand = []
        self.rng.shuffle(self.deck.stack.data)
        self._draw(pid, amount)
        player.mulligan_used = True
        self._say(f"{player.name} takes a mulligan.")
        self._next_mulligan()

    def _check_mulligan_turn(self, pid: int) -> None:
        if self.phase != "mulligan" or self.mulligan_queue[0] != pid:
            raise ValueError("It is not this player's mulligan")

    def _next_mulligan(self) -> None:
        self.mulligan_queue.pop(0)
        if not self.mulligan_queue:
            self.round_number = 1
            self.phase = "attack"

    # ----- a round --------------------------------------------------------
    def choose(self, pid: int, index: Optional[int]) -> None:
        """index = position of the card in the hand, or None for SKIP."""
        if self.phase not in ("attack", "defend") or pid != self.actor:
            raise ValueError("It is not this player's turn")
        player = self.players[pid]
        if index is None:
            card = ("", SKIP)
        else:
            if not 0 <= index < len(player.hand):
                raise ValueError("No such card in hand")
            card = player.hand.pop(index)
        if self.phase == "attack":
            self.attack_card = card
            self.phase = "defend"
        else:
            self.defend_card = card
            self._resolve()

    def _resolve(self) -> None:
        a, d = self.attacker, self.defender
        attacker, defender = self.players[a], self.players[d]
        a_move = self.attack_card[1]
        d_move = self.defend_card[1]
        a_damage, d_damage, a_draws, d_draws = RESULTS[MOVES.index(a_move)][MOVES.index(d_move)]

        attacker.health -= a_damage
        defender.health -= d_damage
        a_drawn = self._draw(a, a_draws)
        d_drawn = self._draw(d, d_draws)

        # played cards go to the discard pile
        for text, kind in (self.attack_card, self.defend_card):
            if kind != SKIP:
                self.deck.discard([text])

        parts = []
        if a_damage:
            parts.append(f"{attacker.name} loses {a_damage} health")
        if d_damage:
            parts.append(f"{defender.name} loses {d_damage} health")
        if a_drawn:
            parts.append(f"{attacker.name} draws {a_drawn}")
        if d_drawn:
            parts.append(f"{defender.name} draws {d_drawn}")
        if parts:
            result = ", ".join(parts)
        elif ATTACK in (a_move, d_move):
            result = "no damage dealt"
        else:
            result = "nothing happens"
        # message after the round: who played what kind of card, and what happened
        self.last_result = (f"{attacker.name} (attacker) played {a_move}.\n"
                            f"{defender.name} (defender) played {d_move}.\n"
                            f"Result: {result}.")
        self._say(f"Round {self.round_number}: {attacker.name} played {a_move}, "
                  f"{defender.name} played {d_move} — {result}.")

        if (attacker.health <= 0 or defender.health <= 0 or self.deck_ended):
            self.phase = "over"
        else:
            self.phase = "reveal"

    def next_round(self) -> None:
        if self.phase != "reveal":
            raise RuntimeError("Finish the round first")
        rotate_judges_left(self.turn_order)      # attacker and defender swap
        self.attack_card = None
        self.defend_card = None
        self.round_number += 1
        self.phase = "attack"

    # ----- end of the game ------------------------------------------------
    def winner(self) -> Optional[int]:
        """Winner's player index, or None for a tie."""
        if not self.game_over:
            raise RuntimeError("The game is not finished")
        h0, h1 = self.players[0].health, self.players[1].health
        if h0 <= 0:
            return 1
        if h1 <= 0:
            return 0
        # the deck ended: less health loses, equal health is a tie
        if h0 == h1:
            return None
        return 0 if h0 > h1 else 1

    # ----- helpers ----------------------------------------------------------
    def _draw(self, pid: int, amount: int) -> int:
        player = self.players[pid]
        drawn = 0
        for _ in range(amount):
            if self.deck.stack.empty():
                # no reshuffle: an empty deck ends the game
                self.deck_ended = True
                break
            text = self.deck.stack.pull()
            player.hand.append((text, self.types.get(text)))
            drawn += 1
        player.hand = msort(player.hand, card_order)
        return drawn

    def _say(self, line: str) -> None:
        self.log.insert(0, line)
        if len(self.log) > LOG_SIZE:
            self.log.pop(len(self.log) - 1)
