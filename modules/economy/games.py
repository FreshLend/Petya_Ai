import random
from typing import Dict, List

class SlotsGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.symbols = list(settings["slots"]["symbols"].keys())
        self.weights = [settings["slots"]["symbols"][s]["weight"] for s in self.symbols]
        self.payouts = {s: settings["slots"]["symbols"][s]["payout"] for s in self.symbols}
        self.jackpot_combination = settings["slots"]["jackpot_combination"]
        self.jackpot_payout = settings["slots"]["jackpot_payout"]
    
    def spin(self) -> tuple:
        result = random.choices(self.symbols, weights=self.weights, k=3)
        
        if result == self.jackpot_combination:
            return result, self.jackpot_payout
        
        if result[0] == result[1] == result[2]:
            return result, self.payouts[result[0]]
        
        if result[0] == result[1] or result[0] == result[2] or result[1] == result[2]:
            for symbol in result:
                if result.count(symbol) == 2:
                    return result, self.payouts[symbol] // 2
        
        return result, 0

class ThimblesGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.win_multiplier = settings["thimbles"]["win_multiplier"]
    
    def play(self, player_choice: int) -> tuple:
        ball_position = random.randint(1, 3)
        return player_choice == ball_position, ball_position

class BlackjackGame:
    def __init__(self, settings: Dict):
        self.settings = settings
        self.deck = self.create_deck()
        self.shuffle_deck()
    
    def create_deck(self) -> List[str]:
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        return deck * 4
    
    def shuffle_deck(self):
        random.shuffle(self.deck)
    
    def draw_card(self) -> str:
        if len(self.deck) < 10:
            self.deck = self.create_deck()
            self.shuffle_deck()
        return self.deck.pop()
    
    def card_value(self, card: str) -> int:
        rank = card[:-1]
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)
    
    def calculate_hand_value(self, hand: List[str]) -> int:
        value = 0
        aces = 0
        
        for card in hand:
            card_val = self.card_value(card)
            if card_val == 11:
                aces += 1
            value += card_val
        
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def dealer_turn(self, dealer_hand: List[str]) -> List[str]:
        while self.calculate_hand_value(dealer_hand) < self.settings["blackjack"]["dealer_stop"]:
            dealer_hand.append(self.draw_card())
        return dealer_hand