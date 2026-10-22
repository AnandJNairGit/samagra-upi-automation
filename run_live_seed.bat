@echo off
title Samagra UPI - Live Test Seeder
color 0A

echo ===========================================================================
echo  SAMAGRA UPI - RUNNING LIVE TEST SEEDER (DOCKER)
echo ===========================================================================
echo  Syncing live_test_seed.json and executing seeder in container...
echo.

docker compose cp seed_live_test.py backend:/tmp/seed_live_test.py
docker compose cp live_test_seed.json backend:/tmp/live_test_seed.json
docker compose exec backend python /tmp/seed_live_test.py

echo.
echo ===========================================================================
echo  Completed! Edit 'live_test_seed.json' and run this file again anytime.
echo ===========================================================================
echo.
pause
