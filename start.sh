#!/bin/bash
nohup python startup.py >/dev/null 2>log/error.log 2>&1 &
