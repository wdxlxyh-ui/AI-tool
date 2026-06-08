#!/usr/bin/env python3
"""Project Management Platform — Entry point."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app

app = create_app()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Project Management Platform Server')
    parser.add_argument('--host', default='0.0.0.0', help='Bind address')
    parser.add_argument('--port', type=int, default=8080, help='Listen port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
