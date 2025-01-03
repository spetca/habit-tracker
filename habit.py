import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging
import threading
import traceback
import time
from PIL import Image, ImageDraw

def parse_args():
    parser = argparse.ArgumentParser(description='Habit Tracker')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--week', type=int, choices=[0,1,2,3], help='Which 14-week chunk to display (0-3)')
    parser.add_argument('--json', type=str, help='JSON file to use for test data')
    parser.add_argument('--generate-patterns', action='store_true', help='Generate test pattern JSON files')
    return parser.parse_args()

args = parse_args()
TEST_MODE = args.test

# Import waveshare library for both test and normal mode
home = str(Path.home())
libdir = os.path.join(home, 'e-Paper/RaspberryPi_JetsonNano/python/lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
else:
    raise ImportError(f"Waveshare library not found in expected location: {libdir}")
from waveshare_epd import epd2in13_V4

# Only import Flask for web mode
if not TEST_MODE:
    from flask import Flask, render_template, jsonify, request

logging.basicConfig(level=logging.DEBUG)
if not TEST_MODE:
    app = Flask(__name__)

class HabitTracker:
    def __init__(self, test_date=None, test_json=None):
        self.epd = None
        self.test_mode = test_date is not None
        self.test_date = test_date
        self.test_json = test_json
        self._init_display()
        self.SQUARE_SIZE = 16
        self.PADDING = 1
        self.EDGE_PADDING = 2
        self.ROWS = 14
        self.COLS = 7
        self.data_file = test_json if test_json else 'habit_data.json'
        self.lock = threading.Lock()
        self.last_display_start_date = None
        
        if not self.test_mode:
            refresh_thread = threading.Thread(target=self.refresh_display_periodically, daemon=True)
            refresh_thread.start()

    def _init_display(self):
        try:
            self.epd = epd2in13_V4.EPD()
            self.height = self.epd.height
            self.width = self.epd.width
            self.epd.init()
            self.epd.Clear(0xFF)
            # Put display to sleep after initialization
            self.epd.sleep()
        except Exception as e:
            logging.error(f"Error initializing display: {e}")
            traceback.print_exc()

    def get_current_date(self):
        return self.test_date if self.test_mode else datetime.now().date()

    def load_data(self):
        with self.lock:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            return {}

    def save_data(self, data):
        with self.lock:
            with open(self.data_file, 'w') as f:
                json.dump(data, f)

    def mark_date(self, date_str, completed=True):
        data = self.load_data()
        if completed:
            data[date_str] = 1
        else:
            data.pop(date_str, None)
        self.save_data(data)
        # Force a display update by clearing the last display date
        self.last_display_start_date = None
        self.update_display()

    def get_eink_date_range(self):
        """Calculate the 14-week period."""
        new_year = datetime(2025, 1, 1).date()
        first_monday = new_year - timedelta(days=new_year.weekday())
        
        if self.test_mode:
            # For test mode, use the specified week chunk directly
            period_start = first_monday + timedelta(weeks=14 * args.week)
            period_end = period_start + timedelta(weeks=14, days=-1)
        else:
            # For normal mode, calculate based on current date
            today = self.get_current_date()
            current_monday = today - timedelta(days=today.weekday())
            days_since_first_monday = (current_monday - first_monday).days
            current_period = days_since_first_monday // (14 * 7)
            period_start = first_monday + timedelta(weeks=14 * current_period)
            period_end = period_start + timedelta(weeks=14, days=-1)
        
        # Ensure we don't display beyond 2025
        period_end = min(period_end, datetime(2025, 12, 31).date())
        
        return period_start, period_end

    def update_display(self):
        """Update the display with the current 14-week period."""
        logging.info("Starting display update")
        try:
            logging.info("Updating display")
            start_date, end_date = self.get_eink_date_range()
            
            if not self.test_mode and self.last_display_start_date == start_date:
                logging.info("Display is already up-to-date.")
                return
            
            self.last_display_start_date = start_date
            
            if not self.test_mode and self.epd is None:
                self._init_display()
            
            self.epd.init()

            image = Image.new('1', (self.width, self.height), 255)
            draw = ImageDraw.Draw(image)

            data = self.load_data()
            current_date = start_date
            
            # Draw grid until end_date
            for row in range(self.ROWS):
                for col in range(self.COLS):
                    if current_date <= end_date:
                        x = self.EDGE_PADDING + col * (self.SQUARE_SIZE + self.PADDING)
                        y = self.EDGE_PADDING + row * (self.SQUARE_SIZE + self.PADDING)
                        
                        date_str = current_date.strftime('%Y-%m-%d')
                        
                        if date_str in data:
                            draw.rectangle(
                                [x, y, x + self.SQUARE_SIZE - 1, y + self.SQUARE_SIZE - 1],
                                fill=0
                            )
                        else:
                            draw.rectangle(
                                [x, y, x + self.SQUARE_SIZE - 1, y + self.SQUARE_SIZE - 1],
                                outline=0
                            )
                    
                    current_date += timedelta(days=1)
            
            # Rotate image for vertical orientation
            image = image.rotate(90, expand=True)
            
            # Always update the physical display, even in test mode
            self.epd.display(self.epd.getbuffer(image))
            logging.info("Display updated successfully")
            self.epd.sleep()
        except Exception as e:
            logging.error(f"Error updating display: {e}")
            traceback.print_exc()

    def refresh_display_periodically(self):
        """Check daily if a new 14-week period has started and refresh the display."""
        while True:
            try:
                logging.info("Checking if display needs refresh...")
                self.update_display()
                time.sleep(86400)  # Check every 24 hours
            except Exception as e:
                logging.error(f"Error during periodic refresh: {e}")
                traceback.print_exc()

def generate_test_patterns():
    """Generate test JSON files for each 14-week chunk of 2025"""
    print("Generating test pattern files...")
    patterns = {
        '0': {  # First chunk - vertical stripes pattern
            datetime(2025, 1, 1).date() + timedelta(days=i): 1
            for i in range(98) if i % 7 in [0, 1]  # Mark Mondays and Tuesdays
        },
        '1': {  # Second chunk - horizontal stripes pattern
            datetime(2025, 1, 1).date() + timedelta(days=14*7 + i): 1
            for i in range(98) if (i // 7) % 2 == 0  # Mark alternate weeks
        },
        '2': {  # Third chunk - checkerboard pattern
            datetime(2025, 1, 1).date() + timedelta(days=28*7 + i): 1
            for i in range(98) if (i // 7 + i % 7) % 2 == 0
        },
        '3': {  # Fourth chunk - diagonal pattern
            datetime(2025, 1, 1).date() + timedelta(days=42*7 + i): 1
            for i in range(98) if (i // 7 == i % 7)
        }
    }
    
    # Save each pattern to a JSON file
    for chunk, pattern in patterns.items():
        filename = f'test_{chunk}.json'
        with open(filename, 'w') as f:
            json.dump({k.strftime('%Y-%m-%d'): v for k, v in pattern.items()}, f, indent=2)
        print(f"Generated {filename}")

if not TEST_MODE:
    tracker = HabitTracker()
    
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/api/habits', methods=['GET'])
    def get_habits():
        return jsonify(tracker.load_data())

    @app.route('/api/habits', methods=['POST'])
    def update_habit():
        data = request.get_json()
        date_str = data.get('date')
        completed = data.get('completed', True)
        
        if date_str:
            logging.info(f"Updating habit for date {date_str} to {completed}")
            tracker.mark_date(date_str, completed)
            return jsonify({'status': 'success', 'date': date_str, 'completed': completed})
        return jsonify({'status': 'error', 'message': 'Date required'}), 400

def cleanup():
    try:
        if not TEST_MODE and tracker.epd is not None:
            tracker.epd.init()
            tracker.epd.Clear(0xFF)
            tracker.epd.sleep()
            epd2in13_V4.epdconfig.module_exit(cleanup=True)
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    if args.generate_patterns:
        generate_test_patterns()
    elif TEST_MODE:
        if args.week is None:
            print("Please specify which week chunk to test with --week")
            sys.exit(1)
            
        # Calculate test date for the specified chunk
        base_date = datetime(2025, 1, 1).date()
        test_date = base_date + timedelta(weeks=14*args.week)
        
        # Use specified JSON file or default test file for the chunk
        json_file = args.json if args.json else f'test_{args.week}.json'
        
        if not os.path.exists(json_file):
            print(f"Error: Test JSON file {json_file} not found!")
            print("Please run --generate-patterns first to create test files")
            sys.exit(1)
            
        print(f"Testing chunk {args.week} with date {test_date} using {json_file}")
        tracker = HabitTracker(test_date=test_date, test_json=json_file)
        tracker.update_display()
    else:
        try:
            logging.info("Initializing habit tracker")
            tracker.update_display()
            import atexit
            atexit.register(cleanup)
            logging.info("Starting web server")
            app.run(host='0.0.0.0', port=5000)
        except KeyboardInterrupt:
            logging.info("Ctrl+C pressed, cleaning up...")
            cleanup()
