# -*- coding: utf-8 -*-
import datetime
import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict


class Player:
    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name
        self.money = 0
        self.inventory = {}
        self.first_seen = None
        self.last_seen = None

    def update_seen(self, timestamp):
        if self.first_seen is None or timestamp < self.first_seen:
            self.first_seen = timestamp
        if self.last_seen is None or timestamp > self.last_seen:
            self.last_seen = timestamp

    def add_item(self, item_type_id, amount):
        self.inventory[item_type_id] = self.inventory.get(item_type_id, 0) + amount
        if self.inventory[item_type_id] <= 0:
            del self.inventory[item_type_id]

    def remove_item(self, item_type_id, amount):
        self.inventory[item_type_id] = self.inventory.get(item_type_id, 0) - amount
        if self.inventory[item_type_id] <= 0:
            del self.inventory[item_type_id]


def load_player_names(db_file='db.json'):
    player_names = {}
    try:
        with open(db_file, 'r') as f:
            data = json.load(f)
            for player in data['players']:
                player_names[player['id']] = player['name']
    except Exception as e:
        print("Ошибка загрузки {}: {}".format(db_file, e))
    return player_names


def load_item_names(xml_file='items.xml'):
    item_names = {}
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        for item in root.findall('item'):
            item_id_elem = item.find('item_type_id')
            name_elem = item.find('item_name')
            if item_id_elem is not None and name_elem is not None:
                item_id = int(item_id_elem.text)
                item_names[item_id] = name_elem.text.strip()
    except Exception as e:
        print("Ошибка загрузки {}: {}".format(xml_file, e))
    return item_names


def parse_inventory_log(line):
    try:
        if ']' not in line or '|' not in line:
            return None
        timestamp_end = line.index(']')
        timestamp = datetime.datetime.fromtimestamp(int(line[1:timestamp_end]))
        rest = line[timestamp_end + 1:].strip()
        parts = rest.split('|', 1)
        if len(parts) < 2:
            return None
        action_type = parts[0].strip()
        player_and_items = parts[1].strip()
        comma_pos = player_and_items.find(',')
        if comma_pos == -1:
            return None
        player_id = int(player_and_items[:comma_pos].strip())
        items_str = player_and_items[comma_pos + 1:].strip()
        if items_str.startswith('(') and items_str.endswith(')'):
            items_str = items_str[1:-1]
        items = []
        parts = items_str.split(',')
        for i in range(0, len(parts) - 1, 2):
            try:
                item_type_id = int(parts[i].strip())
                amount = int(parts[i + 1].strip())
                items.append((item_type_id, amount))
            except (ValueError, IndexError):
                continue
        return timestamp, action_type, player_id, items
    except Exception:
        return None


def parse_money_log(line):
    try:
        parts = line.strip().split('|')
        if len(parts) < 3:
            return None
        timestamp = datetime.datetime.fromtimestamp(int(parts[0]))
        player_id = int(parts[1])
        action_parts = parts[2].split(',', 2)
        action_type = action_parts[0].strip()
        amount = int(action_parts[1])
        reason = action_parts[2] if len(action_parts) > 2 else ''
        return timestamp, action_type, player_id, amount, reason
    except Exception:
        return None


def main():

    # Загрузка данных
    player_names = load_player_names()
    item_names = load_item_names()

    players = {}
    item_stats = defaultdict(int)
    all_item_mentions = []


    inventory_count = 0
    if os.path.exists('inventory_logs.txt'):
        with open('inventory_logs.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = parse_inventory_log(line)
                if data:
                    timestamp, action_type, player_id, items = data
                    inventory_count += 1
                    if player_id not in players:
                        name = player_names.get(player_id, "Player_{}".format(player_id))
                        players[player_id] = Player(player_id, name)
                    players[player_id].update_seen(timestamp)
                    for item_type_id, amount in items:
                        item_stats[item_type_id] += 1
                        all_item_mentions.append((item_type_id, timestamp))
                        if action_type == 'ITEM_ADD':
                            players[player_id].add_item(item_type_id, amount)
                        elif action_type == 'ITEM_REMOVE':
                            players[player_id].remove_item(item_type_id, amount)

    money_count = 0
    if os.path.exists('money_logs.txt'):
        with open('money_logs.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = parse_money_log(line)
                if data:
                    timestamp, action_type, player_id, amount, _ = data
                    money_count += 1
                    if player_id not in players:
                        name = player_names.get(player_id, "Player_{}".format(player_id))
                        players[player_id] = Player(player_id, name)
                    players[player_id].update_seen(timestamp)
                    if action_type == 'MONEY_ADD':
                        players[player_id].money += amount
                    elif action_type == 'MONEY_REMOVE':
                        players[player_id].money -= amount

    combined_log = []
    if os.path.exists('inventory_logs.txt'):
        with open('inventory_logs.txt', 'r') as f:
            for line in f:
                data = parse_inventory_log(line.strip())
                if data:
                    timestamp, action_type, player_id, items = data
                    ts = timestamp.strftime('[%y-%m-%d %H:%M:%S]')
                    items_str = ' '.join("({}, {})".format(i, a) for i, a in items)
                    combined_log.append((timestamp, 0, "{} {} | {} {}".format(ts, player_id, action_type, items_str)))
    if os.path.exists('money_logs.txt'):
        with open('money_logs.txt', 'r') as f:
            for line in f:
                data = parse_money_log(line.strip())
                if data:
                    timestamp, action_type, player_id, amount, reason = data
                    ts = timestamp.strftime('[%y-%m-%d %H:%M:%S]')
                    combined_log.append((timestamp, 1, "{} {} | {} | {} | {}".format(ts, player_id, action_type, amount, reason)))
    combined_log.sort(key=lambda x: (x[0], x[1]))
    with open('combined_log.txt', 'w') as f:
        for _, _, entry in combined_log:
            f.write(entry + '\n')


    with open('output.txt', 'w') as f:
        f.write("Топ 10 предметов по количеству встречаемости:\n")
        top_items = sorted(item_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_items:
            for item_id, count in top_items:
                name = item_names.get(item_id, "Item {}".format(item_id))
                f.write("{}, {}\n".format(name, count))
        else:
            f.write("Нет данных\n")
        f.write("\n")

        # Топ 10 игроков по деньгам
        f.write("Топ 10 игроков по количеству денег:\n")
        top_players = sorted(players.values(), key=lambda p: p.money, reverse=True)[:10]
        for p in top_players:
            first = p.first_seen.strftime('[%y-%m-%d %H:%M:%S]') if p.first_seen else 'N/A'
            last = p.last_seen.strftime('[%y-%m-%d %H:%M:%S]') if p.last_seen else 'N/A'
            f.write("{}, {}, {}, {}\n".format(p.name, p.money, first, last))
        if not top_players:
            f.write("Нет данных\n")
        f.write("\n")

        # Первые 10 предметов
        f.write("Первые 10 предметов в исходном порядке:\n")
        seen = set()
        first_items = []
        for item_id, ts in all_item_mentions:
            if item_id not in seen and len(first_items) < 10:
                seen.add(item_id)
                first_items.append((item_id, ts))
        for item_id, ts in first_items:
            name = item_names.get(item_id, "Item {}".format(item_id))
            f.write("{}, {}\n".format(name, ts.strftime('[%y-%m-%d %H:%M:%S]')))
        if not first_items:
            f.write("Нет данных\n")
        f.write("\n")

        # Последние 10 предметов
        f.write("Последние 10 предметов в исходном порядке:\n")
        seen = set()
        last_items = []
        for item_id, ts in reversed(all_item_mentions):
            if item_id not in seen and len(last_items) < 10:
                seen.add(item_id)
                last_items.append((item_id, ts))
        last_items.reverse()
        for item_id, ts in last_items:
            name = item_names.get(item_id, "Item {}".format(item_id))
            f.write("{}, {}\n".format(name, ts.strftime('[%y-%m-%d %H:%M:%S]')))
        if not last_items:
            f.write("Нет данных\n")

    print("   Файл output.txt создан")


    # Интерактивный режим
    if item_stats:
        print("\nИНТЕРАКТИВНЫЙ РЕЖИМ ЗАПРОСОВ")
        print("Введите item_type_id (или 'exit' для выхода):")
        while True:
            try:
                user_input = raw_input("> ").strip()
                if user_input.lower() == 'exit':
                    break
                item_id = int(user_input)
                total = sum(p.inventory.get(item_id, 0) for p in players.values())
                owners = sum(1 for p in players.values() if item_id in p.inventory)
                top = sorted(
                    [(p, p.inventory[item_id]) for p in players.values() if item_id in p.inventory],
                    key=lambda x: x[1], reverse=True
                )[:10]
                name = item_names.get(item_id, str(item_id))
                print("Название предмета: {}".format(name))
                print("Общее количество: {}".format(total))
                print("Игроков с предметом: {}".format(owners))
                if top:
                    print("Топ 10 игроков:")
                    for p, cnt in top:
                        print("  {}: {}".format(p.name, cnt))
                else:
                    print("  Ни у кого нет")
                print()
            except ValueError:
                print("Ошибка: введите число или 'exit'")
            except EOFError:
                break
    else:
        print("Интерактивный режим недоступен — нет данных о предметах")


if __name__ == '__main__':
    main()