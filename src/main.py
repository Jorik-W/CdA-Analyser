#!/usr/bin/env python3
"""Main entry point for CDA Analyzer"""

import sys
import argparse

def main():
    # First, parse just the interface selection
    parser = argparse.ArgumentParser(description='CdA Analyzer', add_help=False)
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    parser.add_argument('--cli', action='store_true', help='Launch CLI interface')
    
    # Parse known args to get interface selection
    args, remaining_args = parser.parse_known_args()
    
    if args.gui:
        from qt_gui import main as gui_main
        gui_main()
    elif args.cli:
        from cli import main as cli_main
        # Pass remaining args to CLI
        sys.argv = [sys.argv[0]] + remaining_args
        cli_main()
    else:
        # Default to GUI if available, otherwise CLI
        try:
            from qt_gui import main as gui_main
            gui_main()
        except ImportError:
            from cli import main as cli_main
            # Pass all args to CLI
            cli_main()

if __name__ == "__main__":
    main()
