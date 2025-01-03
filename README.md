# Habit Tracker

- Simple habit tracker that displays 7 days x 14 weeks
- After 14 weeks it refreshes to show the next 14 weeks
- Exposes a simple web app that displays the whole calendar year
- Saves data in simple json file: `{"2025-01-01": 1}`



https://github.com/user-attachments/assets/108dc2b5-f7cf-4107-b306-1868ccce7f69



## systemd file

```
[Unit]
Description=Habit Tracker Web Application
After=network.target pigpiod.service
Requires=pigpiod.service

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/habitTracker
ExecStart=/usr/bin/python3 /home/username/habitTracker/habit.py
Restart=always
RestartSec=3
SupplementaryGroups=spi gpio

[Install]
WantedBy=multi-user.target
```

# BOM

1. [Raspberry Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)
2. [Waveshare 2.13 in e-ink](https://www.waveshare.com/2.13inch-e-paper-hat.htm)
3. [$4 acrylic sheet](https://www.lowes.com/pd/OPTIX-0-08-in-T-x-8-in-W-x-10-in-L-Clear-Acrylic-Sheet/3143395)
4. $1-$2 in nuts and bolts

