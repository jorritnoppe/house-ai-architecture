# Pi Netdata Retention Policy

## Goal
Prevent Raspberry Pi nodes from filling local storage with oversized Netdata dbengine caches.

## Standard config

    [global]
        update every = 2

    [db]
        mode = dbengine
        storage tiers = 1
        dbengine page cache size = 32
        dbengine disk space MB = 256

## Why
- reduce SD wear
- prevent silent disk growth
- keep enough local retention for short diagnostics
- avoid multi-GB cache growth on Pi nodes

## Applied nodes
- AttackPi
- DiscoverPi

## Observed result
After clearing old dbengine caches and restarting:
- cache size dropped to only a few MB on validated nodes

## Special note
LuifelPI did not have Netdata config/cache paths present during verification, so it was not handled in the same way during this pass.
