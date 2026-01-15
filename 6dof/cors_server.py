import http.server
import socketserver
import mimetypes

# Add correct MIME type for .glb files
mimetypes.add_type('model/gltf-binary', '.glb')
socketserver.TCPServer.allow_reuse_address = True

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

PORT = 8000
with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
    print("Serving on http://127.0.0.1:" + str(PORT))
    httpd.serve_forever()
