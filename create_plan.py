import sys
import json
import os
import pandas as pd
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import re

# Load environment variables from .env file
load_dotenv('properties.env')


def read_credentials_from_file(credentials_file):
    """
    Read username and password from a markdown-style credentials file
    Format expected:
    # Login Hints
    ## Test Credentials
    - **Username:** myusername
    - **Password:** mypass
    """
    if not credentials_file or not credentials_file.strip():
        return None, None

    try:
        import re

        # Handle local file paths
        if credentials_file.startswith('file:///'):
            file_path = credentials_file.replace('file:///', '').replace('file://', '')
            # Handle Windows paths (remove leading slash before drive letter)
            if file_path.startswith('/') and len(file_path) > 2 and file_path[2] == ':':
                file_path = file_path[1:]
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        # Handle URLs
        elif credentials_file.startswith('http://') or credentials_file.startswith('https://'):
            response = requests.get(credentials_file)
            content = response.text
        else:
            # Try as direct file path
            with open(credentials_file, 'r', encoding='utf-8') as f:
                content = f.read()

        # Parse username and password using regex
        username_match = re.search(r'\*\*Username:\*\*\s*(\S+)', content)
        password_match = re.search(r'\*\*Password:\*\*\s*(\S+)', content)

        username = username_match.group(1) if username_match else None
        password = password_match.group(1) if password_match else None

        if username and password:
            print(f"Credentials loaded - Username: {username} , Password: {password}", file=sys.stderr)
            return username, password
        else:
            print("Warning: Could not parse credentials from file", file=sys.stderr)
            return None, None

    except FileNotFoundError:
        print(f"✗ Error: Credentials file not found: {credentials_file}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"✗ Error reading credentials: {e}", file=sys.stderr)
        return None, None


def scrape_website_content(website_url):
    """
    Scrape the website HTML content to provide real data to the LLM
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract key information
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # Find all links
        links = soup.find_all('a', href=True)
        link_texts = [link.get_text().strip() for link in links if link.get_text().strip()]
        
        # Find all forms
        forms = soup.find_all('form')
        form_info = []
        for form in forms:
            form_inputs = form.find_all(['input', 'select', 'textarea'])
            input_types = [inp.get('type', 'text') for inp in form_inputs if inp.get('type')]
            form_info.append(f"Form with inputs: {', '.join(input_types)}")
        
        # Find all buttons
        buttons = soup.find_all(['button', 'input[type="submit"]', 'input[type="button"]'])
        button_texts = [btn.get_text().strip() or btn.get('value', '') for btn in buttons if btn.get_text().strip() or btn.get('value')]
        
        # Find all headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading_texts = [h.get_text().strip() for h in headings if h.get_text().strip()]
        
        # Extract page content (first 1000 characters)
        page_text = soup.get_text()[:1000].strip()
        
        website_content = {
            "title": title_text,
            "links": link_texts[:10],  # Limit to first 10 links
            "forms": form_info,
            "buttons": button_texts[:5],  # Limit to first 5 buttons
            "headings": heading_texts[:5],  # Limit to first 5 headings
            "page_content_preview": page_text
        }
        
        return website_content
        
    except Exception as e:
        # Silently handle scraping errors to avoid interfering with JSON output
        return {
            "title": "Unknown",
            "links": [],
            "forms": [],
            "buttons": [],
            "headings": [],
            "page_content_preview": f"Error scraping website: {str(e)}"
        }

def generate_filename_from_url(website_url, test_depth):
    """
    Generate filename based on the website URL and number of test cases
    Format: url_numberoftests_plan.xlsx
    Example: https://mytodolist-beryl-nine.vercel.app/ + 30 -> generated_files/plans/https_mytodolist-beryl-nine_vercel_app_30_plan.xlsx
    """
    try:
        # Create generated_files/plans directory if it doesn't exist
        os.makedirs('generated_files/plans', exist_ok=True)
        
        # Replace special characters that can't be in filenames with underscores
        clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')
        
        # Create filename: url_numberoftests_plan.xlsx
        filename = f"generated_files/plans/{clean_url}_{test_depth}_plan.xlsx"
        
        # Remove existing file if it exists
        if os.path.exists(filename):
            os.remove(filename)
        
        return filename
    except Exception as e:
        # Fallback if URL processing fails
        filename = f"generated_files/plans/website_{test_depth}_plan.xlsx"
        
        # Remove existing file if it exists
        if os.path.exists(filename):
            os.remove(filename)
            
        return filename

def save_test_plan_to_json(test_plan_data, excel_filename):
    """
    Save test plan data to JSON file with the same name as Excel file
    
    Args:
        test_plan_data (dict): Complete test plan data including website info
        excel_filename (str): Excel filename to derive JSON filename from
        
    Returns:
        tuple: (success: bool, message: str, json_filename: str)
    """
    try:
        # Create JSON filename from Excel filename
        json_filename = excel_filename.replace('.xlsx', '.json')
        
        # Remove existing JSON file if it exists
        if os.path.exists(json_filename):
            os.remove(json_filename)
        
        # Save test plan data to JSON file
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(test_plan_data, json_file, indent=2, ensure_ascii=False)
        return True, f"JSON file created successfully: {json_filename}", json_filename
        
    except Exception as e:
        error_msg = f"Error creating JSON file: {str(e)}"
        return False, error_msg, None

def export_test_plan_to_excel(test_plan, filename):
    """
    Export test plan to Excel file with multiple sheets
    """
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            
            # Sheet 1: Test Plan Summary
            summary_data = {
                'Property': ['Website URL', 'Test Depth', 'pmTool', 'Website Title', 'Description', 'Total Test Cases'],
                'Value': [
                    test_plan['websiteUrl'],
                    test_plan['testDepth'],
                    test_plan['pmTool'],
                    test_plan['websiteAnalysis']['title'],
                    test_plan['websiteAnalysis']['description'],
                    sum(len(suite['testCases']) for suite in test_plan['testSuites'])
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Website Analysis
            analysis_data = {
                'Analysis Type': ['Main Pages', 'Forms', 'Navigation', 'Key Features'],
                'Items': [
                    ', '.join(test_plan['websiteAnalysis']['mainPages']),
                    ', '.join(test_plan['websiteAnalysis']['forms']),
                    ', '.join(test_plan['websiteAnalysis']['navigation']),
                    ', '.join(test_plan['websiteAnalysis']['keyFeatures'])
                ]
            }
            analysis_df = pd.DataFrame(analysis_data)
            analysis_df.to_excel(writer, sheet_name='Website Analysis', index=False)
            
            # Sheet 3: All Test Cases
            all_test_cases = []
            for suite in test_plan['testSuites']:
                for test_case in suite['testCases']:
                    all_test_cases.append({
                        'Test ID': test_case['testId'],
                        'Test Name': test_case['testName'],
                        'Description': test_case['description'],
                        'Steps': ' | '.join(test_case['steps']),
                        'Expected Result': test_case['expectedResult'],
                        'Priority': test_case['priority'],
                        'Page URL': test_case['pageUrl'],
                        'Test Suite': suite['suiteName'],
                        'Suite Type': suite['suiteType']
                    })
            
            test_cases_df = pd.DataFrame(all_test_cases)
            test_cases_df.to_excel(writer, sheet_name='All Test Cases', index=False)
            
            # Sheet 4: Test Suites Summary
            suites_summary = []
            for suite in test_plan['testSuites']:
                suites_summary.append({
                    'Suite Name': suite['suiteName'],
                    'Suite Type': suite['suiteType'],
                    'Priority': suite['priority'],
                    'Test Cases Count': len(suite['testCases'])
                })
            
            suites_df = pd.DataFrame(suites_summary)
            suites_df.to_excel(writer, sheet_name='Test Suites', index=False)
        
        return True, f"Excel file created successfully: {filename}"
        
    except Exception as e:
        return False, f"Error creating Excel file: {str(e)}"

def calculate_test_distribution(total_cases):
    """
    Calculate exact distribution of test cases across different test suite types
    """
    # Calculate percentages and round to integers
    smoke_count = max(1, int(total_cases * 0.25))  # 25% for smoke tests
    nav_count = max(1, int(total_cases * 0.20))    # 20% for navigation
    form_count = max(1, int(total_cases * 0.25))   # 25% for forms
    ui_count = max(1, int(total_cases * 0.20))     # 20% for UI/UX
    perf_count = max(1, total_cases - smoke_count - nav_count - form_count - ui_count)  # Remaining for performance
    
    # Ensure total equals the requested number
    current_total = smoke_count + nav_count + form_count + ui_count + perf_count
    if current_total != total_cases:
        # Adjust the largest category to match
        diff = total_cases - current_total
        if diff > 0:
            smoke_count += diff
        else:
            smoke_count = max(1, smoke_count + diff)
    
    return smoke_count, nav_count, form_count, ui_count, perf_count

def generate_test_plan_with_llm(website_url, test_depth, pm_tool, username=None, password=None):
    """
    Use LLM to analyze website and generate structured test plan
    """
    # Calculate exact distribution for the requested number of test cases
    smoke_count, nav_count, form_count, ui_count, perf_count = calculate_test_distribution(test_depth)
    
    # Scrape the actual website content
    website_content = scrape_website_content(website_url)
    
    # Calculate dynamic max_tokens based on REAL JSON analysis
    # Actual data from 8-test JSON: 1,550 total tokens
    # Website analysis: 135 tokens
    # Average per test case: 139 tokens (actual measurement)
    # Our formula was 33.5% too low, need to adjust
    
    base_tokens = 500  # Website analysis + JSON structure overhead (actual: 135, adding buffer)
    tokens_per_test = 250  # Actual measured tokens per test case (was 139, now 200 for maximum quality)
    dynamic_tokens = test_depth * tokens_per_test
    
    # Calculate total tokens needed
    total_tokens = base_tokens + dynamic_tokens
    
    # Set reasonable limits based on real usage
    max_tokens = min(total_tokens, 16000)  # Increased cap for large test suites
    max_tokens = max(max_tokens, 8000)    # Minimum 1000 tokens
    
    # Initialize the LLM
    llm = ChatOpenAI(
        #model="gpt-3.5-turbo",  # Faster and cheaper than gpt-4o-mini
        model="gpt-5",
        temperature=0.7,
        max_tokens=max_tokens,  # Dynamic based on test count
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the prompt template
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a QA testing expert. Generate a comprehensive test plan for a website.

        IMPORTANT: You will analyze the website yourself and extract its structure
         and identify the elements and the actions that can be performed in the website,
         then generate appropriate test cases.

         IMPORTANT: You will analyze the website yourself and extract its structure and dont add anything that u dont see and dont make stuff up.
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "testPlan": {{
                "websiteUrl": "string",
                "testDepth": {test_depth},
                "pmTool": "string",
                "websiteAnalysis": {{
                    "title": "string",
                    "description": "string",
                    "mainPages": ["page1", "page2"],
                    "forms": ["form1", "form2"],
                    "navigation": ["nav1", "nav2"],
                    "keyFeatures": ["feature1", "feature2"]
                }},
                "testSuites": [
                    {{
                        "suiteName": "string",
                        "suiteType": "smoke|navigation|forms|ui|performance",
                        "priority": "high|medium|low",
                        "testCases": [
                            {{
                                "testId": "TC001",
                                "testName": "string",
                                "description": "string",
                                "steps": ["step1", "step2", "step3"],
                                "expectedResult": "string",
                                "priority": "high|medium|low",
                                "pageUrl": "string"
                            }}
                        ]
                    }}
                ]
            }}
        }}"""),

        ("system", """AUTHENTICATION CREDENTIALS:
    {credentials_info}

    When generating test cases that involve login/authentication:
    - Use the provided credentials EXACTLY as specified
    - Create test cases for both valid and invalid login scenarios
    - Include the exact username and password in test steps
    - Test password visibility toggle if present
    - Test "remember me" functionality if available
    - LIMIT authentication tests to MAXIMUM 2 test cases regardless of credentials provided"""),
        
        ("user", """Generate a test plan for:
        Website: {website_url}
        Number of Test Cases: {test_depth}
        PM Tool: {pm_tool}
        
        ACTUAL WEBSITE CONTENT:
        Title: {website_title}
        Available Links: {website_links}
        Available Forms: {website_forms}
        Available Buttons: {website_buttons}
        Available Headings: {website_headings}
        Page Content Preview: {website_content_preview}
        
        CRITICAL REQUIREMENT: You MUST generate EXACTLY {test_depth} test cases. No more, no less.
        
        AUTHENTICATION GUIDELINES:
        - If you encounter login/authentication features, search for credentials in the page content
        - Look for text like "user and pass:", "username:", "password:", "demo account", "test login"
        - Extract exact credentials when found (e.g., "admin/admin", "tomsmith/SuperSecretPassword!")
        - LIMIT authentication tests to MAXIMUM 2 test cases:
          * 1 test for successful login with valid credentials
          * 1 test for failed login with invalid credentials
        - Do NOT make all test cases about authentication - focus on diverse website features
        
        Please analyze the ACTUAL website content provided above and:
        1. Use the ACTUAL page title, links, forms, and buttons listed above
        2. Generate test cases based on what actually exists on the website
        3. Test only the elements that are actually present (links, forms, buttons from the scraped content)
        4. Search for any displayed credentials in the page content preview
        5. Generate EXACTLY {test_depth} test cases with detailed, specific steps based on REAL website content
        
        DETAILED TEST CASE REQUIREMENTS:
        - Include exact credentials when found (e.g., "Enter username 'admin'")
        - Provide step-by-step actions with specific details
        - Include verification steps with expected content/text
        - Use specific URLs, button names, form fields, and expected messages
        
        MANDATORY: The total count of ALL test cases across ALL test suites MUST equal {test_depth}.
        
        For {test_depth} test cases, create this exact distribution:
        - Smoke Tests: {smoke_count} test cases (core functionality, basic navigation)
        - Navigation Tests: {nav_count} test cases (page links, menu navigation, breadcrumbs)
        - Form Tests: {form_count} test cases (form validation, submission, input fields)
        - UI/UX Tests: {ui_count} test cases (layout, responsiveness, visual elements)
        - Performance/Error Tests: {perf_count} test cases (loading times, error handling, edge cases)
        
        Total: {smoke_count} + {nav_count} + {form_count} + {ui_count} + {perf_count} = {test_depth} test cases
        
        DIVERSITY PRIORITY: Create realistic test cases that explore the website's diverse features:
        - Test different pages, forms, interactive elements
        - Cover various user workflows and scenarios
        - Include edge cases and error scenarios
        - Focus on the most important functionality first
        
        REMINDER: You must generate EXACTLY {test_depth} test cases total with detailed, specific steps.""")
    ])
    
    # Create the chain
    chain = prompt_template | llm
    
    try:
        # Check if API key is loaded
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"error": "OpenAI API key not found in environment variables"}

        # Prepare credentials info for prompt
        if username and password:
            credentials_info = f"""PROVIDED CREDENTIALS:
        - Username: {username}
        - Password: {password}

        IMPORTANT: Use these EXACT credentials in all login-related test cases.
        Example: "Enter username '{username}' and password '{password}'"
        Do NOT use generic credentials - use these specific ones."""
        else:
            credentials_info = """No authentication credentials provided.
        If login features are detected, search the page content for any displayed credentials or use generic test credentials."""

        # Generate the test plan
        response = chain.invoke({
            "website_url": website_url,
            "test_depth": test_depth,
            "pm_tool": pm_tool,
            "credentials_info": credentials_info,
            "smoke_count": smoke_count,
            "nav_count": nav_count,
            "form_count": form_count,
            "ui_count": ui_count,
            "perf_count": perf_count,
            "website_title": website_content["title"],
            "website_links": ", ".join(website_content["links"]) if website_content["links"] else "No links found",
            "website_forms": ", ".join(website_content["forms"]) if website_content["forms"] else "No forms found",
            "website_buttons": ", ".join(website_content["buttons"]) if website_content["buttons"] else "No buttons found",
            "website_headings": ", ".join(website_content["headings"]) if website_content["headings"] else "No headings found",
            "website_content_preview": website_content["page_content_preview"]
        })
        
        # Clean the response content (remove markdown code blocks if present)
        content = response.content.strip()
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.startswith('```'):
            content = content[3:]   # Remove ```
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()
        
        # Parse the JSON response
        test_plan_json = json.loads(content)
        
        # Extract the inner testPlan if it exists
        if "testPlan" in test_plan_json:
            return test_plan_json["testPlan"]
        else:
            return test_plan_json
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing error: {str(e)}. LLM response: {response.content if 'response' in locals() else 'No response'}"
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error generating test plan with LLM: {str(e)}"
        return {"error": error_msg}

def main():
    # Get the data from command line arguments
    if len(sys.argv) > 1:
        try:
            data = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    
    website_url = data.get('websiteUrl', '')
    test_depth = int(data.get('testDepth', 12))
    pm_tool = data.get('pmTool')

    credentials_file = data.get('credentialsFile', '')

    # Read credentials from file if provided
    username, password = read_credentials_from_file(credentials_file)

    if username and password:
        print(f"Using credentials from file - Username: {username} , Password: {password}", file=sys.stderr)

    # Generate test plan using LLM (LLM will analyze website itself)
    test_plan = generate_test_plan_with_llm(website_url, test_depth, pm_tool, username, password)
    
    if test_plan and "error" not in test_plan:
        # Generate unique filename for Excel export
        excel_filename = generate_filename_from_url(website_url, test_depth)
        
        # Export test plan to Excel
        excel_success, excel_message = export_test_plan_to_excel(test_plan, excel_filename)
        
        # Save test plan to JSON file
        json_success, json_message, json_filename = save_test_plan_to_json({
            "websiteUrl": website_url,
            "testDepth": test_depth,
            "pmTool": pm_tool,
            "testPlan": test_plan,
            "createdAt": datetime.now().isoformat()
        }, excel_filename)
        
        # Store test plan data globally for email functionality
        # This will be used by the separate email endpoint
        
        # Success response
        result = {
            "status": "success",
            "message": "Test plan generated successfully using LLM",
            "data": {
                "websiteUrl": website_url,
                "testDepth": test_depth,
                "pmTool": pm_tool,
                "testPlan": test_plan,
                "excelFile": excel_filename,
                "excelExport": {
                    "success": excel_success,
                    "message": excel_message
                },
                "jsonExport": {
                    "success": json_success,
                    "message": json_message,
                    "filename": json_filename
                },
                "createdAt": datetime.now().isoformat(),
                "nextStep": "execute_tests"
            }
        }
    else:
        # Error response
        result = {
            "status": "error",
            "message": "Failed to generate test plan with LLM",
            "data": {
                "websiteUrl": website_url,
                "error": "LLM generation failed",
                "createdAt": datetime.now().isoformat()
            }
        }
    
    print(json.dumps(result))

if __name__ == '__main__':
    main()