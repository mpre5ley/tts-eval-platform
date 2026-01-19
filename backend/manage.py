# Imports Django's Command Line Utility

import os
import sys
from django.core.management import execute_from_command_line

def main():
    # set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    # execute Django commands through the command line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()


