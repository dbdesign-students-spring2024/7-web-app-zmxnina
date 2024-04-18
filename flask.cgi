#!/Users/mingxinzhu/.local/share/virtualenvs/7-web-app-zmxnina-1hVd9f1M/bin/python3
import sys
#!/usr/bin/env python3
sys.path.insert(0, '/misc/linux/centos7/x86_64/local/stow/python-3.6/lib/python3.6/site-packages/')
from wsgiref.handlers import CGIHandler
from app import app
CGIHandler().run(app)
