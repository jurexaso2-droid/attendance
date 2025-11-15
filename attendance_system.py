import http.server
import socketserver
import threading
import qrcode
import json
import os
import socket
import time
from datetime import datetime
import sys

# Data storage
USERS_FILE = "users.json"
ATTENDANCE_DIR = "attendance_records"

class AttendanceSystem:
    def __init__(self):
        self.users = self.load_users()
        self.current_event = None
        self.server_port = 8080
        self.server_thread = None
        self.create_directories()
    
    def create_directories(self):
        if not os.path.exists(ATTENDANCE_DIR):
            os.makedirs(ATTENDANCE_DIR)
    
    def load_users(self):
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def save_users(self):
        with open(USERS_FILE, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def register_user(self):
        print("\n=== Register New User ===")
        name = input("Enter user name: ").strip()
        user_id = input("Enter user ID: ").strip()
        
        if user_id in self.users:
            print("User ID already exists!")
            return
        
        self.users[user_id] = {
            "name": name,
            "id": user_id,
            "qr_data": f"USER_{user_id}"
        }
        self.save_users()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(user_id)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_filename = f"qr_{user_id}.png"
        qr_img.save(qr_filename)
        
        print(f"User {name} registered successfully!")
        print(f"QR code saved as: {qr_filename}")
    
    def list_users(self):
        print("\n=== Registered Users ===")
        if not self.users:
            print("No users registered.")
            return
        
        for user_id, user_data in self.users.items():
            print(f"ID: {user_id} | Name: {user_data['name']}")
    
    def start_web_server(self, event_name):
        self.current_event = event_name
        handler = self.create_handler()
        
        self.server_thread = threading.Thread(target=self.run_server, args=(handler,))
        self.server_thread.daemon = True
        self.server_thread.start()
        
        local_ip = self.get_local_ip()
        print(f"\n=== {event_name} Attendance Started ===")
        print(f"Web server running at: http://{local_ip}:{self.server_port}")
        print("Scan QR codes using the web interface")
        print("Press Enter to stop attendance tracking...")
        input()
        
        self.stop_server()
    
    def create_handler(self):
        class AttendanceHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=os.getcwd(), **kwargs)
            
            def do_GET(self):
                if self.path == '/':
                    self.send_html_interface()
                elif self.path.startswith('/scan'):
                    self.handle_scan()
                else:
                    super().do_GET()
            
            def send_html_interface(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>{self.server.system.current_event} Attendance</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
                        .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
                        .scanner {{ width: 100%; height: 300px; border: 2px dashed #ccc; margin: 20px 0; text-align: center; line-height: 300px; }}
                        .result {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                        .success {{ background: #d4edda; color: #155724; }}
                        .error {{ background: #f8d7da; color: #721c24; }}
                        button {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>{self.server.system.current_event} Attendance</h2>
                        <div id="scanner" class="scanner">
                            <button onclick="startScanner()">Start QR Scanner</button>
                        </div>
                        <div id="result"></div>
                    </div>
                    
                    <script>
                        function startScanner() {{
                            document.getElementById('scanner').innerHTML = 'Point camera at QR code...';
                            
                            // Simple QR code input simulation (for demo)
                            let qrCode = prompt("Enter QR Code Data (or user ID):");
                            if (qrCode) {{
                                processQRCode(qrCode);
                            }}
                        }}
                        
                        function processQRCode(qrData) {{
                            fetch('/scan?data=' + encodeURIComponent(qrData))
                                .then(response => response.json())
                                .then(data => {{
                                    const resultDiv = document.getElementById('result');
                                    if (data.success) {{
                                        resultDiv.innerHTML = '<div class="success">' + data.message + '</div>';
                                    }} else {{
                                        resultDiv.innerHTML = '<div class="error">' + data.message + '</div>';
                                    }}
                                    setTimeout(() => {{
                                        document.getElementById('scanner').innerHTML = '<button onclick="startScanner()">Start QR Scanner</button>';
                                        resultDiv.innerHTML = '';
                                    }}, 3000);
                                }});
                        }}
                    </script>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
            
            def handle_scan(self):
                import urllib.parse
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                
                qr_data = params.get('data', [''])[0]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                result = self.server.system.record_attendance(qr_data)
                self.wfile.write(json.dumps(result).encode())
        
        return AttendanceHandler
    
    def run_server(self, handler):
        with socketserver.TCPServer(("", self.server_port), handler) as httpd:
            httpd.system = self
            httpd.serve_forever()
    
    def stop_server(self):
        print(f"\n{self.current_event} attendance tracking stopped.")
        self.current_event = None
    
    def record_attendance(self, user_id):
        if user_id in self.users:
            user = self.users[user_id]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Record in event-specific file
            event_file = os.path.join(ATTENDANCE_DIR, f"{self.current_event.lower().replace(' ', '_')}.txt")
            
            record = f"{timestamp} | ID: {user_id} | Name: {user['name']} | Event: {self.current_event}\n"
            
            with open(event_file, 'a') as f:
                f.write(record)
            
            # Also record in main log
            main_log = os.path.join(ATTENDANCE_DIR, "all_attendance.txt")
            with open(main_log, 'a') as f:
                f.write(record)
            
            return {
                "success": True,
                "message": f"Attendance recorded for {user['name']} at {timestamp}"
            }
        else:
            return {
                "success": False,
                "message": "User not found! Please register first."
            }
    
    def show_attendance_records(self, event_name):
        event_file = os.path.join(ATTENDANCE_DIR, f"{event_name.lower().replace(' ', '_')}.txt")
        
        print(f"\n=== {event_name} Attendance Records ===")
        if os.path.exists(event_file):
            with open(event_file, 'r') as f:
                print(f.read())
        else:
            print("No attendance records found.")
    
    def main_menu(self):
        while True:
            print("\n" + "="*50)
            print("        ATTENDANCE MONITORING SYSTEM")
            print("="*50)
            print("1. List Users")
            print("2. Thanksgiving")
            print("3. Worship")
            print("4. Prayer Meeting")
            print("5. Register New User")
            print("6. View Attendance Records")
            print("7. Exit")
            print("-"*50)
            
            choice = input("Enter your choice (1-7): ").strip()
            
            if choice == '1':
                self.list_users()
            elif choice == '2':
                self.start_web_server("Thanksgiving")
            elif choice == '3':
                self.start_web_server("Worship")
            elif choice == '4':
                self.start_web_server("Prayer Meeting")
            elif choice == '5':
                self.register_user()
            elif choice == '6':
                self.view_records_menu()
            elif choice == '7':
                print("Goodbye!")
                break
            else:
                print("Invalid choice! Please try again.")
    
    def view_records_menu(self):
        print("\n=== View Attendance Records ===")
        print("1. Thanksgiving")
        print("2. Worship")
        print("3. Prayer Meeting")
        print("4. All Records")
        print("5. Back to Main Menu")
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            self.show_attendance_records("Thanksgiving")
        elif choice == '2':
            self.show_attendance_records("Worship")
        elif choice == '3':
            self.show_attendance_records("Prayer Meeting")
        elif choice == '4':
            self.show_all_records()
        elif choice == '5':
            return
        else:
            print("Invalid choice!")
    
    def show_all_records(self):
        main_log = os.path.join(ATTENDANCE_DIR, "all_attendance.txt")
        
        print("\n=== All Attendance Records ===")
        if os.path.exists(main_log):
            with open(main_log, 'r') as f:
                print(f.read())
        else:
            print("No attendance records found.")

if __name__ == "__main__":
    system = AttendanceSystem()
    system.main_menu()
