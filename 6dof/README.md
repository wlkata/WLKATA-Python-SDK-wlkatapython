# Mirobot Web UI

- Required package: 'assimp' for STL model conversion

```
git clone git@github.com:wlkata/Mirobot-STL.git
for x in Mirobot-STL/*.STL; do assimp export $x ${x/.STL/.glb}; done
python3 cors_server.py
```
### View local server at http://localhost:8000
