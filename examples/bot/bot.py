from __future__ import print_function

import os
import sys
import time
import json
import math
import random

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))
from pgoapi import pgoapi

from s2sphere import CellId, LatLng

from gmap import Map

class PoGoBot(object):

    def __init__(self, config):
        self.config = config
        self.api = pgoapi.PGoApi()
        self.api.set_position(*self.config["location"])
        self.angle = random.uniform(0,360)

        self.coords = [{'latitude': self.config["location"][0], 'longitude': self.config["location"][1]}]
        self.catches = []
        self.spins = []

        self.last_move_time = time.time()
        self.change_dir_time = self.last_move_time + random.uniform(60,300)

    def login(self, retries=-1):
        ret = False
        attempts = 0
        while True:
            sys.stdout.write("Performing authentication (attempt %d)..." % (attempts+1))
            if not self.api.login(self.config["auth_service"],
                                  self.config["username"],
                                  self.config["password"]):
                sys.stdout.write("failed.\n")
                attempts += 1
                if retries>=0 and attempts < retries:
                    time.sleep(1)
                else:
                    break
            else:
                sys.stdout.write("succeeded.\n")
                ret = True
                break
        return ret

    def process_player(self, player):
        self.player = player["player_data"]

    def process_inventory(self, inventory):
        ni = {
            "items": {},
            "candies": {},
            "pokemon": {},
            "eggs": {},
            #"pokedex": {},
            "stats": {},
            #"applied": {},
            "incubators": {}
        }
        balls = []
        for item in inventory["inventory_delta"]["inventory_items"]:
            item = item["inventory_item_data"]
            if "item" in item:
                if "count" in item["item"]:
                    if item["item"]["item_id"] in [1,2,3]:
                        balls.append(item["item"]["item_id"])
                    ni["items"][str(item["item"]["item_id"])] = item["item"]["count"]
            elif "candy" in item:
                if "candy" in item["candy"]:
                    ni["candies"][str(item["candy"]["family_id"])] = item["candy"]["candy"]
            elif "pokemon_data" in item:
                if "is_egg" in item["pokemon_data"] and item["pokemon_data"]["is_egg"]:
                    ni["eggs"][str(item["pokemon_data"]["id"])] = item["pokemon_data"]
                else:
                    ni["pokemon"][str(item["pokemon_data"]["id"])] = item["pokemon_data"]
            elif "egg_incubators" in item:
                for incubator in item["egg_incubators"]["egg_incubator"]:
                    ni["incubators"][str(incubator["id"])] = incubator
            elif "player_stats" in item:
                ni["stats"] = item["player_stats"]
        self.balls = sorted(balls)
        self.inventory = ni

    def get_trainer_info(self, delay):
        sys.stdout.write("Getting trainer information...\n")
        req = self.api.create_request()
        req.get_player()
        req.get_inventory()
        ret = req.call()
        if ret and ret["responses"]:
            self.process_player(ret["responses"]["GET_PLAYER"])
            self.process_inventory(ret["responses"]["GET_INVENTORY"])

    def get_hatched_eggs(self, delay):
        sys.stdout.write("Getting hatched eggs...\n")
        ret = self.api.get_hatched_eggs()
        if ret and ret["responses"]:
            pass#print(ret["responses"]["GET_HATCHED_EGGS"])
        time.sleep(delay)

    def get_rewards(self, delay):
        sys.stdout.write("Getting level-up rewards...\n")
        ret = self.api.level_up_rewards(level=self.inventory["stats"]["level"])
        if ret and ret["responses"]:
            pass#print(ret["responses"]["LEVEL_UP_REWARDS"])
        time.sleep(delay)

    def get_cell_ids(self, lat, lng, radius=10):
        origin = CellId.from_lat_lng(LatLng.from_degrees(lat, lng)).parent(15)
        walk = [origin.id()]
        right = origin.next()
        left = origin.prev()
        for _ in range(radius):
            walk.append(right.id())
            walk.append(left.id())
            right = right.next()
            left = left.prev()
        return sorted(walk)

    def get_pois(self, delay):
        sys.stdout.write("Getting POIs...\n")
        pois = {"pokemon": [], "forts": []}
        lat, lng, alt = self.api.get_position()
        cell_ids = self.get_cell_ids(lat, lng)
        timestamps = [0,] * len(cell_ids)
        ret = self.api.get_map_objects(latitude=lat, longitude=lng, since_timestamp_ms=timestamps, cell_id=cell_ids)
        if ret and ret["responses"] and "GET_MAP_OBJECTS" in ret["responses"] and ret["responses"]["GET_MAP_OBJECTS"]["status"] == 1:
            for map_cell in ret["responses"]["GET_MAP_OBJECTS"]["map_cells"]:
                if "wild_pokemons" in map_cell:
                    for pokemon in map_cell["wild_pokemons"]:
                        pois["pokemon"].append(pokemon)
                if 'forts' in map_cell:
                    for fort in map_cell['forts']:
                        pois['forts'].append(fort)
        self.pois = pois
        time.sleep(delay)


    def spin_forts(self, delay):
        sys.stdout.write("Spinning forts...\n")
        lat, lng, alt = self.api.get_position()
        for fort in self.pois["forts"]:
            if "type" in fort and fort["type"] == 1 and not "cooldown_complete_timestamp_ms" in fort:
                if math.hypot(fort['latitude'] - lat, fort['longitude'] - lng) < 0.0004495:
                    ret = self.api.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'], fort_longitude=fort['longitude'], player_latitude=lat, player_longitude=lng)
                    time.sleep(delay)
                    if ret and ret["responses"] and "FORT_SEARCH" in ret["responses"] and ret["responses"]["FORT_SEARCH"]["result"] == 1:
                        self.spins.append(fort)
                        print(ret)

    def catch_pokemon(self, eid, spid, kind, pokemon, balls, delay):
        while True:
            normalized_reticle_size = 1.950 - random.uniform(0, .5)
            normalized_hit_position = 1.0
            spin_modifier = 1.0 - random.uniform(0, .1)
            if len(balls) == 0:
                break
            ret = self.api.catch_pokemon(encounter_id=eid, spawn_point_id=spid, pokeball=balls.pop(0), normalized_reticle_size = normalized_reticle_size, hit_pokemon=True, spin_modifier=spin_modifier, normalized_hit_position=normalized_hit_position)
            time.sleep(delay)
            if "status" in ret["responses"]["CATCH_POKEMON"]:
                if ret["responses"]["CATCH_POKEMON"]["status"] == 1:
                    self.catches.append(pokemon)
                    print(kind, ret)
                    break
                elif ret["responses"]["CATCH_POKEMON"]["status"] == 0 or ret["responses"]["CATCH_POKEMON"]["status"] == 3:
                    break

    def catch_wild_pokemon(self, delay):
        sys.stdout.write("Catching wild pokemon...\n")
        lat, lng, alt = self.api.get_position()
        for pokemon in self.pois["pokemon"]:
            ret = self.api.encounter(encounter_id=pokemon['encounter_id'], spawn_point_id=pokemon['spawn_point_id'], player_latitude = lat, player_longitude = lng)
            time.sleep(delay)
            self.catch_pokemon(pokemon['encounter_id'], pokemon['spawn_point_id'], "wild", pokemon, self.balls, delay)

    def catch_incense_pokemon(self, delay):
        sys.stdout.write("Catching incense pokemon...\n")
        lat, lng, alt = self.api.get_position()
        ret = self.api.get_incense_pokemon(player_latitude=lat, player_longitude=lng)
        time.sleep(delay)
        if ret and "GET_INCENSE_POKEMON" in ret["responses"] and ret["responses"]["GET_INCENSE_POKEMON"]["result"] == 1:
            pokemon = ret["responses"]["GET_INCENSE_POKEMON"]
            ret = api.incense_encounter(encounter_id=pokemon["encounter_id"], encounter_location=pokemon["encounter_location"])
            time.sleep(delay)
            if ret and "INCENSE_ENCOUNTER" in enc["responses"] and ret["responses"]["INCENSE_ENCOUNTER"]["result"] == 1:
                self.catch_pokemon(pokemon["encounter_id"], pokemon["encounter_location"], "incense", pokemon, self.balls, delay)

    def move(self, mph=5):
        sys.stdout.write("Moving...\n")
        now = time.time()
        delta = now - self.last_move_time
        if now > self.change_dir_time:
            self.angle = (self.angle + random.gauss(45,30)) % 360
            self.change_dir_time = now + 60 + random.gauss(120,60)
        lat, lng, alt = self.api.get_position()
        r = 1.0/69.0/60.0/60.0*mph*delta
        lat += math.cos(self.angle)*r
        lng += math.sin(self.angle)*r
        self.api.set_position(lat, lng, alt)
        self.config["location"] = "%f,%f" % (lat, lng)
        self.coords.append({'latitude': lat, 'longitude': lng})
        self.last_move_time = now

    def save_map(self):
        sys.stdout.write("Saving map...\n")
        lat, lng, alt = self.api.get_position()
        map = Map()
        map._player = [lat, lng]
        for coord in self.coords:
            map.add_position((coord['latitude'], coord['longitude']))
        for catch in self.catches:
            map.add_point((catch['latitude'], catch['longitude']), "http://pokeapi.co/media/sprites/pokemon/%d.png" % catch["pokemon_data"]["pokemon_id"])
        for spin in self.spins:
            map.add_point((spin['latitude'], spin['longitude']), "http://maps.google.com/mapfiles/ms/icons/blue.png")

        with open("%s.html" % self.player["username"], "w") as out:
            print(map, file=out)

    def save_config(self):
        with open("config.json", "w") as out:
            json.dump(self.config, out, indent=2, sort_keys=True)

    def load_incubators(self):
        sys.stdout.write("Loading incubators...\n")
        for ib in self.inventory["incubators"]:
            if not 'pokemon_id' in ib:
                ib = self.inventory["incubators"][ib]
                if len(self.inventory["eggs"]) > 0:
                    bestegg = (None,0)
                    for egg in self.inventory["eggs"]:
                        egg = self.inventory["eggs"][egg]
                        if egg["egg_km_walked_target"] > bestegg[1]:
                            bestegg = (egg, egg["egg_km_walked_target"])
                    ret = self.api.use_item_egg_incubator(item_id=ib['id'], pokemon_id=bestegg[0]['id'])
                    if ret and "USE_ITEM_EGG_INCUBATOR" in ret['responses'] and ret["responses"]['USE_ITEM_EGG_INCUBATOR']["result"] == 1:
                        print(ret)

    def play(self):
        delay = 1
        while True:
            self.get_hatched_eggs(delay)
            self.get_trainer_info(delay)
            self.get_rewards(delay)
            self.get_pois(delay)
            self.spin_forts(delay)
            self.catch_wild_pokemon(delay)
            self.catch_incense_pokemon(delay)
            self.load_incubators()
            self.save_map()
            self.move()
            self.save_config()
