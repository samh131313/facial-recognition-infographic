#!/usr/bin/env python3
"""Summarize Liquidity SMP player stats for the website (runs on the host every 5 minutes).

Reads world/stats/<uuid>.json, world/advancements/<uuid>.json and usercache.json, writes a
compact JSON and copies it into the website container (/data/mysite/smp_stats.json).
No passwords, IPs or coordinates are included.
"""
import glob
import json
import os
import subprocess
import time

SRV = os.environ.get('MC_DIR', '/opt/minecraft/server')
OUT = os.environ.get('MC_STATS_OUT', '/var/lib/liquidity/smp_stats.json')
DRY = os.environ.get('MC_DRYRUN') == '1'

MOVE = ('walkOneCm', 'sprintOneCm', 'crouchOneCm', 'swimOneCm', 'flyOneCm', 'climbOneCm',
        'fallOneCm', 'diveOneCm', 'boatOneCm', 'horseOneCm', 'pigOneCm', 'minecartOneCm',
        'aviateOneCm', 'walkOnWaterOneCm', 'walkUnderWaterOneCm')
ORES = ('diamond_ore', 'emerald_ore', 'gold_ore', 'iron_ore', 'coal_ore', 'redstone_ore',
        'lit_redstone_ore', 'lapis_ore', 'quartz_ore')


def stat(d, key):
    v = d.get('stat.' + key, 0)
    return v if isinstance(v, int) else 0


def sum_prefix(d, prefix):
    out = {}
    for k, v in d.items():
        if k.startswith(prefix) and isinstance(v, int):
            out[k[len(prefix):]] = out.get(k[len(prefix):], 0) + v
    return out


def summarize(d):
    mined = sum_prefix(d, 'stat.mineBlock.')
    mined = {k.replace('minecraft.', ''): v for k, v in mined.items()}
    kills = sum_prefix(d, 'stat.killEntity.')
    killed_by = sum_prefix(d, 'stat.entityKilledBy.')
    crafted = sum_prefix(d, 'stat.craftItem.')
    used = sum_prefix(d, 'stat.useItem.')
    broken = sum_prefix(d, 'stat.breakItem.')
    top = lambda m, n=5: sorted(([k, v] for k, v in m.items()), key=lambda x: -x[1])[:n]
    ores = {o: mined.get(o, 0) for o in ORES if mined.get(o, 0)}
    if 'lit_redstone_ore' in ores:
        ores['redstone_ore'] = ores.get('redstone_ore', 0) + ores.pop('lit_redstone_ore')
    return {
        'playtime_min': stat(d, 'playOneMinute') // 1200,          # ticks -> minutes
        'deaths': stat(d, 'deaths'),
        'player_kills': stat(d, 'playerKills'),
        'mob_kills': stat(d, 'mobKills'),
        'damage_dealt_hearts': stat(d, 'damageDealt') // 20,       # stored as half-hearts x10
        'damage_taken_hearts': stat(d, 'damageTaken') // 20,
        'blocks_mined': sum(mined.values()),
        'items_crafted': sum(crafted.values()),
        'distance_m': sum(stat(d, m) for m in MOVE) // 100,
        'jumps': stat(d, 'jump'),
        'fish_caught': stat(d, 'fishCaught'),
        'animals_bred': stat(d, 'animalsBred'),
        'trades': stat(d, 'tradedWithVillager'),
        'enchants': stat(d, 'itemEnchanted') or stat(d, 'enchantItem'),
        'tools_broken': sum(broken.values()),
        'times_joined': stat(d, 'leaveGame'),
        'since_death_min': stat(d, 'timeSinceDeath') // 1200,
        'ores': ores,
        'top_mobs_killed': top(kills),
        'top_killed_by': top(killed_by, 3),
        'top_blocks_mined': top({k: v for k, v in mined.items() if k not in ORES}),
        'top_items_used': top(used, 3),
    }


def main():
    names = {}
    try:
        for e in json.load(open(os.path.join(SRV, 'usercache.json'))):
            names[e['uuid']] = e['name']
    except Exception:
        pass
    players = []
    for f in glob.glob(os.path.join(SRV, 'world', 'stats', '*.json')):
        u = os.path.basename(f)[:-5]
        try:
            d = json.load(open(f))
        except Exception:
            continue
        s = summarize(d)
        adv = 0
        try:
            a = json.load(open(os.path.join(SRV, 'world', 'advancements', u + '.json')))
            adv = sum(1 for k, v in a.items() if isinstance(v, dict) and v.get('done')
                      and not k.startswith('minecraft:recipes/'))
        except Exception:
            pass
        s['advancements'] = adv
        s['name'] = names.get(u, u[:8])
        players.append(s)
    players.sort(key=lambda p: -p['playtime_min'])
    data = {'updated': int(time.time()), 'players': players}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.tmp', 'w') as fh:
        json.dump(data, fh, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    if not DRY:
        subprocess.run(['docker', 'cp', OUT, 'liquidity_web:/data/mysite/smp_stats.json'],
                       check=False, stdout=subprocess.DEVNULL)
    print('players:', len(players))


if __name__ == '__main__':
    main()
