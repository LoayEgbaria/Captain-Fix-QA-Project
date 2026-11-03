# collect-evidence.py
# This script collects evidence of test execution and creates an HTML report using LLM.

import os
import json
import sys
from datetime import datetime
from dotenv import load_dotenv
import openai
import glob
# Load environment variables
load_dotenv('properties.env')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def read_test_results_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_optimized_html_evidence(client, html_template, test_result, clean_url, total_tests):
    """Generate HTML evidence report using optimized LLM with template as system message"""
    # Extract data from test result
    test_id = test_result.get('testId', 'Unknown')
    test_name = test_result.get('testName', 'Test Case')
    status = test_result.get('status', 'UNKNOWN')
    duration = test_result.get('duration', 'N/A')
    error = test_result.get('error', '')

    # Format duration
    if isinstance(duration, (int, float)):
        duration = f"{duration:.2f} seconds"

    # Determine status styling
    status_class = 'status-pass' if status.upper() == 'PASS' else 'status-fail'
    status_text = status.upper()

    # Get screenshot path
    screenshot_path = test_result.get('screenshot', '')
    if screenshot_path:
        screenshot_filename = screenshot_path.split('/')[-1]
        screenshot_src = f"../screenshots/{screenshot_filename}"
    else:
        screenshot_src = f"../screenshots/{clean_url}_{total_tests}_{test_id}.png"

    # Error handling
    error_text = error if error else 'No errors encountered during execution.'
    error_class = 'no-error' if not error else ''

    # Create conditional error section
    if status.upper() == 'PASS':
        error_section = ""  # No error section for passed tests
    else:
        error_section = f"""<div class="error-section">
                <h3>❌ Error Details</h3>
                <p class="{error_class}">{error_text}</p>
            </div>"""

    # Create explicit prompt with clear instructions
    user_prompt = f"""Replace: {{testId}}={test_id}, {{testName}}={test_name}, {{duration}}={duration}, {{statusText}}={status_text}, {{statusClass}}={status_class}, {{screenshotSrc}}={screenshot_src}, {{errorSection}}={error_section}. Return complete HTML only."""

    try:
        # Calculate dynamic max_tokens based on content complexity
        error_length = len(str(error)) if error else 0
        test_name_length = len(str(test_name)) if test_name else 0
        duration_length = len(str(duration)) if duration else 0

        # Base tokens for the HTML template and structure (increased for safety)
        base_tokens = 2000  # Increased from 500 to ensure complete HTML
        
        # Dynamic tokens based on content length
        # Error messages are usually the longest content
        error_tokens = min(error_length // 6, 400)  # Increased from //8 and max 400
        test_name_tokens = min(test_name_length // 10, 100)  # Increased limits
        duration_tokens = min(duration_length // 15, 50)  # Increased limits

        # Calculate total dynamic tokens
        dynamic_tokens = error_tokens + test_name_tokens + duration_tokens
        max_tokens = base_tokens + dynamic_tokens

        # Ensure we don't exceed reasonable limits
        max_tokens = min(max_tokens, 2500)  # Increased cap from 2000 to 2500
        max_tokens = max(max_tokens, 800)   # Increased minimum from 600 to 800

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Faster and cheaper than gpt-4o-mini
            messages=[
                {"role": "system", "content": f"You are a QA HTML generator. Use this exact HTML template and replace placeholders with provided data. Return ONLY the HTML code, no markdown formatting:\n\n{html_template}"},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,  # Dynamic based on content complexity
            temperature=0.1  # Lower temperature for consistent output
        )

        # Clean the response to remove markdown formatting
        html_content = response.choices[0].message.content

        # Remove markdown code blocks if present
        if html_content.startswith('```html'):
            html_content = html_content[7:]  # Remove ```html
        elif html_content.startswith('```'):
            html_content = html_content[3:]   # Remove ```

        if html_content.endswith('```'):
            html_content = html_content[:-3]  # Remove closing ```

        # Strip any leading/trailing whitespace
        html_content = html_content.strip()

        return html_content
    except Exception as e:
        # Fallback HTML if LLM fails
        return generate_fallback_html(test_result, clean_url, total_tests)

def generate_fallback_html(test_result, clean_url, total_tests):
    """Generate fallback HTML if LLM fails"""
    test_id = test_result.get('testId', 'Unknown')
    test_name = test_result.get('testName', 'Test Case')
    status = test_result.get('status', 'UNKNOWN')
    duration = test_result.get('duration', 'N/A')
    error = test_result.get('error', 'No errors encountered')

    status_class = 'status-pass' if status.upper() == 'PASS' else 'status-fail'
    screenshot_path = f"../screenshots/{clean_url}_{total_tests}_{test_id}.png"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Execution Report - {test_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header h2 {{
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
            font-weight: 300;
        }}
        .content {{
            padding: 30px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 12px 24px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
            margin: 10px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .status-pass {{
            background-color: #4CAF50;
            color: white;
        }}
        .status-fail {{
            background-color: #f44336;
            color: white;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .info-card {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        .info-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 1.1em;
        }}
        .info-card p {{
            margin: 0;
            color: #666;
            font-size: 1em;
        }}
        .screenshot-section {{
            margin: 30px 0;
            text-align: center;
        }}
        .screenshot-section img {{
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border: 3px solid #fff;
        }}
        .error-section {{
            background-color: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        .error-section h3 {{
            color: #c53030;
            margin-top: 0;
        }}
        .no-error {{
            color: #38a169;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Test Execution Report</h1>
            <h2>Test ID: {test_id}</h2>
        </div>
        <div class="content">
            <div class="info-grid">
                <div class="info-card">
                    <h3>📋 Test Name</h3>
                    <p>{test_name}</p>
                </div>
                <div class="info-card">
                    <h3>⏱️ Duration</h3>
                    <p>{duration}</p>
                </div>
                <div class="info-card">
                    <h3>🎯 Status</h3>
                    <span class="status-badge {status_class}">{status.upper()}</span>
                </div>
            </div>
            
            <div class="screenshot-section">
                <h3>📸 Screenshot</h3>
                <img src="{screenshot_path}" alt="Test Screenshot">
            </div>
            
            <div class="error-section">
                <h3>❌ Error Details</h3>
                <p class="{'no-error' if not error else ''}">{error if error else 'No errors encountered during execution.'}</p>
            </div>
        </div>
    </div>
</body>
</html>
    """

def generate_html_evidence_reports(results_json_path, output_dir):
    """Generate HTML evidence reports for all test results using optimized LLM"""
    try:
        results = read_test_results_json(results_json_path)
        os.makedirs(output_dir, exist_ok=True)
        html_files = []

        test_results = results.get("test_results", [])
        if not test_results:
            return {"error": "No test results found in JSON file"}

        # Extract URL and test count from the results for filename
        website_url = results.get("websiteUrl", "")
        total_tests = results.get("total_tests", len(test_results))
        clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')

        # Initialize LLM client once before the loop
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        # Define compact HTML template for faster processing and lower token usage
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {testId}</title>
    <style>
        body{{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px}}
        .container{{max-width:800px;margin:0 auto;background:#fff;border-radius:10px;box-shadow:0 4px 6px rgba(0,0,0,0.1);overflow:hidden}}
        .header{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px;text-align:center}}
        .header h1{{margin:0;font-size:2em;font-weight:300}}
        .header h2{{margin:5px 0 0 0;font-size:1em;opacity:0.9}}
        .content{{padding:20px}}
        .status-badge{{display:inline-block;padding:8px 16px;border-radius:20px;font-weight:bold;font-size:0.9em;margin:5px 0;text-transform:uppercase}}
        .status-pass{{background:#4CAF50;color:#fff}}
        .status-fail{{background:#f44336;color:#fff}}
        .info-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0}}
        .info-card{{background:#f8f9fa;padding:15px;border-radius:8px;border-left:4px solid #667eea}}
        .info-card h3{{margin:0 0 8px 0;color:#333;font-size:1em}}
        .info-card p{{margin:0;color:#666;font-size:0.9em}}
        .screenshot-section{{margin:20px 0;text-align:center}}
        .screenshot-section img{{max-width:100%;border-radius:8px;box-shadow:0 4px 8px rgba(0,0,0,0.2);border:2px solid #fff}}
        .error-section{{background:#fff5f5;border:1px solid #fed7d7;border-radius:8px;padding:15px;margin:15px 0}}
        .error-section h3{{color:#c53030;margin-top:0;font-size:1em}}
        .no-error{{color:#38a169;font-style:italic}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Test Report</h1>
            <h2>{testId}</h2>
        </div>
        <div class="content">
            <div class="info-grid">
                <div class="info-card">
                    <h3>📋 Test Name</h3>
                    <p>{testName}</p>
                </div>
                <div class="info-card">
                    <h3>⏱️ Duration</h3>
                    <p>{duration}</p>
                </div>
                <div class="info-card">
                    <h3>🎯 Status</h3>
                    <span class="status-badge {statusClass}">{statusText}</span>
                </div>
            </div>
            <div class="screenshot-section">
                <h3>📸 Screenshot</h3>
                <img src="{screenshotSrc}" alt="Test Screenshot">
            </div>
            {errorSection}
        </div>
    </div>
</body>
</html>"""

        # Process test cases in batches for better performance
        # Adjust batch size based on total number of tests
        total_tests = len(test_results)
        if total_tests <= 50:
            batch_size = 5  # Faster processing for smaller test suites
        elif total_tests <= 100:
            batch_size = 4  # Medium batch size for medium test suites
        else:
            batch_size = 3  # Conservative batch size for large test suites

        import time

        for i in range(0, len(test_results), batch_size):
            batch = test_results[i:i + batch_size]

            for test in batch:
                html_content = generate_optimized_html_evidence(client, html_template, test, clean_url, total_tests)
                test_id = test.get('testId', 'unknown')
                filename = f"{clean_url}_{total_tests}_{test_id}_evidence.html"
                file_path = os.path.join(output_dir, filename)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                html_files.append(file_path)

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(test_results):
                time.sleep(0.2)  # 200ms delay between batches

        return {
            "success": True,
            "htmlFiles": html_files,
            "totalTests": len(test_results)
        }
    except Exception as e:
        return {"error": f"Failed to generate evidence reports: {str(e)}"}

def find_latest_result_file():
    """Find the most recent result JSON file"""
    results_folder = "generated_files/results"
    if not os.path.exists(results_folder):
        return None

    json_files = glob.glob(os.path.join(results_folder, "*_result.json"))
    if not json_files:
        return None

    # Sort by modification time (newest first)
    json_files.sort(key=os.path.getmtime, reverse=True)
    return json_files[0]

def main():
    """Main function to handle evidence collection"""
    try:
        # Check if we have command line arguments (from server)
        if len(sys.argv) > 1:
            try:
                # Server mode - get data from HTML request
                data = json.loads(sys.argv[1])
                website_url = data.get('websiteUrl', '')
                test_depth = data.get('testDepth', 8)

                # Ensure website_url is a string (in case it's nested)
                if isinstance(website_url, dict):
                    website_url = str(website_url)
                elif not isinstance(website_url, str):
                    website_url = str(website_url)

                # Find the matching result file based on URL and test depth
                results_dir = "generated_files/results"
                if not os.path.exists(results_dir):
                    print(json.dumps({
                        "status": "error",
                        "message": "No results directory found",
                        "action": "Please run 'Run Executor' first to generate test results.",
                        "details": {"suggestion": "Execute tests before collecting evidence."}
                    }))
                    return

                # Look for result file matching the URL and test depth
                clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')
                expected_filename = f"{clean_url}_{test_depth}_result.json"
                expected_path = os.path.join(results_dir, expected_filename)

                if os.path.exists(expected_path):
                    results_json_path = expected_path
                else:
                    # Fallback to latest file
                    results_json_path = find_latest_result_file()
                    if not results_json_path:
                        print(json.dumps({
                            "status": "error",
                            "message": f"No result file found for {website_url} with {test_depth} tests",
                            "action": "Please run 'Run Executor' first to generate test results.",
                            "details": {"suggestion": "Execute tests before collecting evidence."}
                        }))
                        return

            except json.JSONDecodeError:
                # If JSON parsing fails, fallback to latest file
                results_json_path = find_latest_result_file()
                if not results_json_path:
                    print(json.dumps({
                        "status": "error",
                        "message": "No result JSON files found in generated_files/results folder",
                        "action": "Please run 'Run Executor' first to generate test results.",
                        "details": {"suggestion": "Execute tests before collecting evidence."}
                    }))
                    return
        else:
            # Interactive mode - find latest result file
            results_json_path = find_latest_result_file()
            if not results_json_path:
                print(json.dumps({
                    "status": "error",
                    "message": "No result JSON files found in generated_files/results folder",
                    "action": "Please run 'Run Executor' first to generate test results.",
                    "details": {"suggestion": "Execute tests before collecting evidence."}
                }))
                return

        output_dir = "generated_files/evidence"
        result = generate_html_evidence_reports(results_json_path, output_dir)

        if "error" in result:
            print(json.dumps({
                "status": "error",
                "message": result["error"],
                "action": "Please check the result JSON file and try again.",
                "details": {"suggestion": "Ensure test execution completed successfully."}
            }))
        else:
            print(json.dumps({
                "status": "success",
                "message": f"Evidence collection completed successfully for {result['totalTests']} test cases",
                "data": {
                    "htmlFiles": result["htmlFiles"],
                    "totalTests": result["totalTests"],
                    "outputDirectory": output_dir,
                    "sourceFile": results_json_path
                },
                "createdAt": datetime.now().isoformat()
            }))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": f"Error collecting evidence: {str(e)}",
            "action": "Please check the logs and try again.",
            "details": {"suggestion": "Contact support if the issue persists."}
        }))

if __name__ == "__main__":
    main()

