import os
import sys

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.mobile_main import main

if __name__ == '__main__':
    main()
