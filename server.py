import http.server
import socketserver
import json
import subprocess
import urllib.parse
import os
from datetime import datetime

class CaptainFixHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/run-create-plan':
            # Read the form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                # Run the create_plan.py script with the form data
                result = subprocess.run([
                    'python', 'create_plan.py', json.dumps(data)
                ], capture_output=True, text=True, cwd='.')
                
                # Debug: Print what we got from the script
                print(f"Script stdout: {result.stdout}")
                print(f"Script stderr: {result.stderr}")
                print(f"Script return code: {result.returncode}")
                
                # Send the output from the Python script
                if result.stdout:
                    self.wfile.write(result.stdout.encode('utf-8'))
                else:
                    self.wfile.write("No output from Python script".encode('utf-8'))
                
            except Exception as e:
                # If Python script fails, send error message
                error_msg = f"Error running create_plan.py: {str(e)}"
                print(f"Error: {error_msg}")
                self.wfile.write(error_msg.encode('utf-8'))
        
        elif self.path == '/api/generate-report':
            # Read the form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            try:
                website_url = data.get('websiteUrl', '')
                test_depth = data.get('testDepth', 8)
                
                if not website_url:
                    error_response = json.dumps({
                        "error": "Missing websiteUrl in request data.",
                        "details": "Please provide a valid website URL."
                    })
                    self.wfile.write(error_response.encode('utf-8'))
                    return

                # Create base filename from URL and test depth (same method as create_plan.py)
                clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')
                base_filename = f"{clean_url}_{test_depth}"
                
                # Check if required files exist (plan and result)
                plan_json_path = f"generated_files/plans/{base_filename}_plan.json"
                result_json_path = f"generated_files/results/{base_filename}_result.json"
                
                if not os.path.exists(plan_json_path):
                    error_response = json.dumps({
                        "error": "Test plan file not found.",
                        "details": f"Please run 'Create Plan' first. Looking for: {plan_json_path}"
                    })
                    self.wfile.write(error_response.encode('utf-8'))
                    return
                
                if not os.path.exists(result_json_path):
                    error_response = json.dumps({
                        "error": "Test result file not found.",
                        "details": f"Please run 'Run Executor' first. Looking for: {result_json_path}"
                    })
                    self.wfile.write(error_response.encode('utf-8'))
                    return

                # Load the JSON files
                with open(plan_json_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                
                with open(result_json_path, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)

                # Run the create_reports.py script
                result = subprocess.run(
                    ['python', 'create_reports.py', json.dumps(plan_data), json.dumps(result_data)],
                    capture_output=True, text=True, cwd='.'
                )

                print(f"Report stdout: {result.stdout}")
                print(f"Report stderr: {result.stderr}")
                print(f"Report return code: {result.returncode}")

                if result.returncode == 0:
                    # Success response
                    response_data = {
                        "success": True,
                        "message": "Report generated successfully",
                        "website": website_url,
                        "test_count": test_depth,
                        "markdown_file": f"{base_filename}_summary.md",
                        "html_file": f"{base_filename}_summary.html",
                        "zip_file": f"CaptinAiReport_{base_filename}.zip",
                        "base_filename": base_filename
                    }
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    # Error in script execution
                    error_response = json.dumps({
                        "error": "Failed to generate report",
                        "details": result.stderr or result.stdout or "Unknown error occurred"
                    })
                    self.wfile.write(error_response.encode('utf-8'))

            except Exception as e:
                error_response = json.dumps({
                    "error": f"Server error: {str(e)}",
                    "details": "An unexpected error occurred while generating the report"
                })
                print(f"Report Error: {error_response}")
                self.wfile.write(error_response.encode('utf-8'))

        elif self.path == '/api/send-email':
            # Read the form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                # Add URL and test depth for ZIP file identification
                email_data = data.copy()
                
                # If websiteUrl and testDepth are provided, add them to email data
                if 'websiteUrl' in data and 'testDepth' in data:
                    email_data['websiteUrl'] = data['websiteUrl']
                    email_data['testDepth'] = data['testDepth']
                
                # Run the send_email.py script with the enhanced data
                result = subprocess.run([
                    'python', 'send_email.py', json.dumps(email_data)
                ], capture_output=True, text=True, cwd='.')
                
                # Debug: Print what we got from the script
                print(f"Email Script stdout: {result.stdout}")
                print(f"Email Script stderr: {result.stderr}")
                print(f"Email Script return code: {result.returncode}")
                
                # Send the output from the Python script
                if result.stdout:
                    self.wfile.write(result.stdout.encode('utf-8'))
                else:
                    self.wfile.write("No output from email script".encode('utf-8'))
                
            except Exception as e:
                # If Python script fails, send error message
                error_msg = f"Error running send_email.py: {str(e)}"
                print(f"Email Error: {error_msg}")
                self.wfile.write(error_msg.encode('utf-8'))



        elif self.path == '/api/run-executor':
            # Read the form data (if needed)
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            if post_data:
                data = json.loads(post_data.decode('utf-8'))
            else:
                data = {}

            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            try:
                # Run the qa_executor.py script
                result = subprocess.run(
                    ['python', 'qa_executor.py', json.dumps(data)],
                    capture_output=True, text=True, cwd='.'
                )

                print(f"Executor stdout: {result.stdout}")
                print(f"Executor stderr: {result.stderr}")
                print(f"Executor return code: {result.returncode}")

                if result.stdout:
                    self.wfile.write(result.stdout.encode('utf-8'))
                else:
                    self.wfile.write("No output from qa_executor.py".encode('utf-8'))

            except Exception as e:
                error_msg = f"Error running qa_executor.py: {str(e)}"
                print(f"Executor Error: {error_msg}")
                self.wfile.write(error_msg.encode('utf-8'))



        elif self.path == '/api/collect-evidence':
            # Read the form data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                # Parse the JSON data
                if post_data:
                    json_data = json.loads(post_data.decode('utf-8'))
                else:
                    json_data = {}
                
                # Run the collect-evidence.py script with the data (json_data is already a dict)
                result = subprocess.run(
                    ['python', 'collect-evidence.py', json.dumps(json_data)],
                    capture_output=True, text=True, cwd='.'
                )
                
                print(f"Evidence Script stdout: {result.stdout}")
                print(f"Evidence Script stderr: {result.stderr}")
                print(f"Evidence Script return code: {result.returncode}")
                
                # Send the output from the Python script
                if result.stdout:

                    try:
                        # Try parsing stdout as JSON to ensure it's valid
                        json_output = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        # If not valid JSON, wrap it inside a JSON object
                        json_output = {
                            "status": "success",
                            "message": result.stdout.strip()
                        }
                else:
                    json_output = {
                        "status": "error",
                        "message": "No output from evidence script",
                        "action": "Please try again."
                    }


            except Exception as e:
                json_output = {
                    "status": "error",
                    "message": f"Error running collect-evidence.py: {str(e)}",
                    "action": "Please try again or check the logs."
                }
                print(f"Evidence Error: {json_output}")
                # Always send a valid JSON response

            self.wfile.write(json.dumps(json_output).encode('utf-8'))



        elif self.path == '/api/run-pm-integration':
            # Read the form data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''

            # Prepare the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            try:
                # Run the pm_integration.py script
                result = subprocess.run(
                    ['python', 'pm_integration.py'],
                    capture_output=True, text=True, cwd='.', timeout=120
                )

                print(f"PM Integration stdout: {result.stdout}")
                print(f"PM Integration stderr: {result.stderr}")
                print(f"PM Integration return code: {result.returncode}")

                if result.returncode == 0:
                    json_output = {
                        "status": "success",
                        "message": "PM integration completed successfully",
                        "output": result.stdout.strip(),
                        "data": {
                            "completed": True,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                else:
                    json_output = {
                        "status": "error",
                        "message": "PM integration failed",
                        "error": result.stderr or "Unknown error occurred",
                        "data": {
                            "completed": False
                        }
                    }

            except subprocess.TimeoutExpired:
                json_output = {
                    "status": "error",
                    "message": "PM integration timed out after 120 seconds",
                    "action": "Please check your PM tool configuration"
                }
            except Exception as e:
                json_output = {
                    "status": "error",
                    "message": f"Error running pm_integration.py: {str(e)}",
                    "action": "Please try again or check the logs."
                }
                print(f"PM Integration Error: {json_output}")

            self.wfile.write(json.dumps(json_output).encode('utf-8'))



        elif self.path == '/api/create-reports':
            # Read the form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Prepare the response
            self.send_response(200)
            # self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                
                result_plan = subprocess.run([
                    'python','create_plan.py', json.dumps(data)
                ],apture_output=True, text=True, cwd='.')
                
                data1 = json.loads(result_plan.stdout)
                
                result_evidence = subprocess.run([
                    'python','collect-evidence.py'
                ], capture_output=True , text=True , cwd='.')
                
                data2 = json.loads(result_evidence.stdout)
                
                result = subprocess.run([
                    'python', 'create_reports.py', json.dumps(data1) , json.dumps(data2)
                ], capture_output=True, text=True, cwd='.')
                
                # Debug: Print what we got from the script
                print(f"Script stdout: {result.stdout}")
                print(f"Script stderr: {result.stderr}")
                print(f"Script return code: {result.returncode}")
                
                # Send the output from the Python script
                if result.stdout:
                    self.wfile.write(result.stdout.encode('utf-8'))
                else:
                    self.wfile.write("No output from Python script".encode('utf-8'))
                
            except Exception as e:
                # If Python script fails, send error message
                error_msg = f"Error running create_plan.py: {str(e)}"
                print(f"Error: {error_msg}")
                self.wfile.write(error_msg.encode('utf-8'))

        def do_GET(self):
            # Handle GET requests for API endpoints
            if self.path == '/api/get-healing-report':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                try:
                    report_path = 'generated_files/healing_report.json'
                    if os.path.exists(report_path):
                        with open(report_path, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)
                        self.wfile.write(json.dumps(report_data).encode('utf-8'))
                    else:
                        response = {
                            "error": "No healing report found",
                            "message": "Run tests first to generate healing data",
                            "total_healing_attempts": 0,
                            "successful_heals": 0,
                            "success_rate": "0%",
                            "healing_log": []
                        }
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    error_response = {
                        "error": f"Error reading healing report: {str(e)}",
                        "total_healing_attempts": 0,
                        "successful_heals": 0,
                        "success_rate": "0%",
                        "healing_log": []
                    }
                    self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return

            elif self.path == '/api/get-visual-report':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                try:
                    report_path = 'generated_files/visual_regression_report.json'
                    if os.path.exists(report_path):
                        with open(report_path, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)
                        self.wfile.write(json.dumps(report_data).encode('utf-8'))
                    else:
                        response = {
                            "error": "No visual regression report found",
                            "message": "Run visual regression tests first",
                            "total_pages_tested": 0,
                            "pages_with_changes": 0,
                            "pages_unchanged": 0,
                            "results": []
                        }
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    error_response = {
                        "error": f"Error reading visual report: {str(e)}",
                        "total_pages_tested": 0,
                        "pages_with_changes": 0,
                        "pages_unchanged": 0,
                        "results": []
                    }
                    self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return

            # For all other GET requests, serve files normally
            else:
                return http.server.SimpleHTTPRequestHandler.do_GET(self)

              
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    PORT = 8000
    
    with socketserver.TCPServer(("", PORT), CaptainFixHandler) as httpd:
        print(f"🚀 Captain Fix Server running on http://localhost:{PORT}")
        print(f"📱 Open http://localhost:{PORT}/index.html in your browser")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()


if __name__ == '__main__':
    main()
