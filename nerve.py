import os
import sys
import time
from metrics import SystemMetrics
from ui import render_frame

def print_startup_sequence():
    logo = """
\033[1;36m    _   __                     
   / | / /__  ______   _____  
  /  |/ / _ \\/ ___/ | / / _ \\ 
 / / /  /  __/ /   | |/ /  __/ 
/_/ /_/\\___/_/    |___/\\___/  \033[0m
    """
    sys.stdout.write('\033[2J\033[H') # Clear
    print(logo)
    
    msg = "    // yyy was here."
    for char in msg:
        sys.stdout.write(f"\033[38;2;150;150;150m{char}\033[0m")
        sys.stdout.flush()
        time.sleep(0.04)
    print("\n")
    time.sleep(0.4)
    
    steps = [
        "Initializing Neural Interface...",
        "Establishing telemetry connection...",
        "Calibrating visual sensors...",
        "System Ready."
    ]
    for step in steps:
        time.sleep(0.3)
        print(f" \033[1;37m[\033[1;32m OK \033[1;37m]\033[0m {step}")
        sys.stdout.flush()
    time.sleep(0.8)

def main():
    metrics = SystemMetrics()
    os.system("") # enable ANSI escape sequences on windows terminal
    
    # Enter alt screen buffer and hide cursor
    print('\033[?1049h\033[?25l', end="")
    
    try:
        print_startup_sequence()
        
        # Clear screen for main loop
        print('\033[2J', end="")
        
        last_term_size = (0, 0)
        
        while True:
            try:
                term_size = os.get_terminal_size()
                term_width = term_size.columns
                term_height = term_size.lines
            except OSError:
                term_width = 80
                term_height = 24
                
            if (term_width, term_height) != last_term_size:
                sys.stdout.write('\033[2J')
                last_term_size = (term_width, term_height)
                
            data = metrics.update()
            
            frame = render_frame(data, term_width, term_height)
            
            # Move cursor to top-left and print frame
            sys.stdout.write('\033[H')
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Update at ~50 FPS
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        pass
    finally:
        metrics.stop()
        # Exit alt buffer, Show cursor, reset colors
        print('\033[?1049l\033[?25h\033[0m', end="")
        print("Exited Nerve.")

if __name__ == "__main__":
    main()
