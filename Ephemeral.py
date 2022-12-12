from time import sleep
from constants import GameState
from collections import defaultdict
from Strategy import Strategy


class Ephemeral(Strategy):
    def __init__(self, mouse_handler):
        super().__init__(mouse_handler)

        self.mulligan_cards = ("Gwen", "Shark Chariot", "Boisterous Host")
        self.graveyard = defaultdict(int)  # Counter of dead cards used for Harrowing
        self.spawn_on_attack = 0  # Increments when Shark Chariot dies
        self.gwen_backed = False

    def block(self, cards_on_board, window_x, window_y, window_height, harrowingTurn):
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        for i, blocking_card in enumerate(cards_on_board["cards_board"]):
            if i < self.block_counter or "Can't Block" in blocking_card.keywords:
                continue
            if self.blocked_with(blocking_card, cards_on_board["opponent_cards_attk"], cards_on_board["cards_attk"], cards_on_board["cards_hand"], harrowingTurn):
                self.block_counter = (self.block_counter + 1) % len(cards_on_board["cards_board"])
                return True

        self.block_counter = 0
        return False

    def blocked_with(self, blocking_card, enemy_cards, ally_cards, cards_on_board, harrowingTurn):
        if(harrowingTurn):
            print(" Harrowing Is Coming")
        for enemy_card in enemy_cards:
            # Elusive and Fearsome check
            if "Elusive" in enemy_card.keywords or "Fearsome" in enemy_card.keywords and blocking_card.attack < 3:
                continue
            is_blockable = True
            if (harrowingTurn):
                for ally_card in ally_cards:  # Check if card is already blocked
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    print("                        Harrowing  Blocker: ", blocking_card.get_name())
                    print("                        Harrowing  Attacker: ", enemy_card.get_name())
                    return True
                
            # if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health:  # Defensive block
            if "Ephemeral" in blocking_card.keywords or enemy_card.attack < blocking_card.health or ((blocking_card.health*3) < enemy_card.attack and "Overwhelm" not in enemy_card.keywords) or ((enemy_card.health == blocking_card.attack) and "Elusive" not in blocking_card.keywords and blocking_card.get_name() != "Zed"): 
                
                for ally_card in ally_cards:  # Check if card is already blocked
                    if abs(ally_card.get_pos()[0] - enemy_card.get_pos()[0]) < 10:
                        is_blockable = False
                        break
                if is_blockable:
                    self.drag_card_from_to(blocking_card.get_pos(), enemy_card.get_pos())
                    print("                          Blocker: ", blocking_card.get_name())
                    print("                          Attacker: ", enemy_card.get_name())
                    return True
        return False

    def playable_card(self, playable_cards, game_state, cards_on_board, turn, harrowingTurn, mana):
        attack_sort = sorted(playable_cards, key=lambda attack_card: attack_card.cost + 3 * int(attack_card.is_spell()) +
                            3 * int("Ephemeral" in attack_card.keywords) - 6 * int(game_state == GameState.Defend_Turn and attack_card.name == "Shark Chariot") + 
                            3 * int(attack_card.is_champion()) + 3  * int(game_state == GameState.Attack_Turn and attack_card.name == "Shark Chariot") +
                            6  * int(attack_card.name == "The Harrowing") , reverse=True)
        print(*attack_sort)
        for playable_card_in_hand in attack_sort:
            name = playable_card_in_hand.get_name()
            if mana <= 3 and harrowingTurn and game_state == GameState.Defend_Turn:
                print("it's harrowingTurn and mana is ", mana);
                continue
            if name == "Shadowshift" or name == "Thread the Needle":
                continue
            if name == "Darkwater Scourge" or name == "Silent Shadowseer" and turn < 4:
                continue;
            if game_state == GameState.Defend_Turn:
                if name == "Shark Chariot":
                    return playable_card_in_hand
                if name == "Dragon Ambush" and turn >= 4:
                    return playable_card_in_hand 
                if name == "Strike Up The Band" and turn >= 6:
                    return playable_card_in_hand 
            if game_state == GameState.Attack_Turn or game_state == GameState.Defend_Turn and ("Ephemeral" not in playable_card_in_hand.keywords and not playable_card_in_hand.is_spell()):
                if not playable_card_in_hand.is_spell():
                    # Assume a unit is dead as soon as you play it (its an Ephemeral deck anyways)
                    self.graveyard[playable_card_in_hand.get_name()] += 1
                if playable_card_in_hand.is_spell() and turn <= 3:
                    continue
                return playable_card_in_hand
                
        return None

    def reorganize_attack(self, cards_on_board, window_x, window_y, window_height, harrowingTurnAttack):
        self.window_x = window_x
        self.window_y = window_y
        self.window_height = window_height

        n_attackers = len(cards_on_board["cards_attk"])
        n_non_ephemeral = sum(1 for attack_card in cards_on_board["cards_attk"] if "Ephemeral" not in attack_card.keywords and attack_card.get_name(
        ) != "Zed" and attack_card.get_name() != "Hecarim")
        n_to_be_spawned = self.spawn_on_attack
        for attack_card in cards_on_board["cards_attk"]:
            name = attack_card.get_name()
            if name == "Zed":
                n_to_be_spawned += 1
            elif name == "Hecarim":
                n_to_be_spawned += 2
        print("to be spawned: ", n_to_be_spawned)

        # Check if non-ephemeral unit is in danger
        for attack_card in cards_on_board["cards_attk"]:
            unit_in_danger = attack_card.attack == 0 or attack_card.name == "Soul Shepherd" or "Ephemeral" not in attack_card.keywords and any(map(
                lambda enemy_card: enemy_card.attack >= attack_card.health + 3, cards_on_board["opponent_cards_board"]))
            if unit_in_danger and not harrowingTurnAttack and (attack_card.get_name() != "Zed" or attack_card.get_name() != "Gwen") and "Elusive" not in attack_card.keywords:
                print("                          Protecting Attacker: ", attack_card.get_name())
                self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], 100))
                return False

        # If attack would overflow
        if n_attackers + n_to_be_spawned > 6 and n_non_ephemeral > 0:
            for attack_card in cards_on_board["cards_attk"]:
                if "Ephemeral" not in attack_card.keywords and attack_card.get_name() != "Zed" and attack_card.get_name() != "Hecarim":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0], 100))
                    return False
        
        # Position Gwen to the right for max damage output
        if any(map(lambda attk_card: attk_card.get_name() == "Gwen", cards_on_board["cards_attk"])) and not self.gwen_backed :  # Retreat Gwen from attack if it is on board
            for attack_card in cards_on_board["cards_attk"]:
                if attack_card.get_name() == "Gwen":
                    self.drag_card_from_to(attack_card.get_pos(), (attack_card.get_pos()[0],  100))
                    self.gwen_backed = True
                    print("moving Gwen back")
                    sleep(1)
                    return False  # Not done yet
        elif self.gwen_backed:  # Put Gwen back in attack to the last position
            for unit_card in cards_on_board["cards_board"]:
                if unit_card.get_name() == "Gwen":
                    self.drag_card_from_to(unit_card.get_pos(), (unit_card.get_pos()[0], window_height // 2))
                    self.gwen_backed = False
                    print("moving Gwen foward")
                    sleep(1)
                    break

        n_shark_chariots = sum(
            1 for attack_card in cards_on_board["cards_attk"] if attack_card.get_name() == "Shark Chariot")
        self.spawn_on_attack = max(self.spawn_on_attack, n_shark_chariots)
        print("spawn on attack: ", self.spawn_on_attack)
        return True

    def get_card_in_hand(self, units_in_hand, select_ephemeral):
        if select_ephemeral:
            ephemerals = filter(lambda card_in_hand: "Ephemeral" in card_in_hand.keywords, units_in_hand)
            return next(ephemerals, units_in_hand[0])
        # Select the strongest
        return max(units_in_hand, key=lambda card_in_hand: card_in_hand.attack + card_in_hand.health)

    def Harrow_is_coming(self, cards_on_board, turn) -> bool:
            for card_in_hand in cards_on_board["cards_hand"]:
                name = card_in_hand.get_name()
                if name == "The Harrowing" and turn >= 6 :
                    return True;
            return False