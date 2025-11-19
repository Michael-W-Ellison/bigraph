#!/usr/bin/env python3
"""
Bigraph Cryptography System
Main entry point for the GUI application
"""

import sys
import os
import tkinter as tk

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gui.main_window import BigramCryptoGUI


def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = BigramCryptoGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
