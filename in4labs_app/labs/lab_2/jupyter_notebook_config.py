import os

c = get_config()
# Set options for certfile, ip, password, and toggle off
# browser auto-opening
c.NotebookApp.certfile = u'/home/jovyan/.jupyter/mycert.pem'
c.NotebookApp.keyfile = u'/home/jovyan/.jupyter/mykey.key'
# Set ip to '*' to bind on all interfaces (ips) for the public server
c.NotebookApp.ip = '*'
c.NotebookApp.port = 8000
c.NotebookApp.password = os.environ['NOTEBOOK_PASSWORD']
c.NotebookApp.open_browser = False
