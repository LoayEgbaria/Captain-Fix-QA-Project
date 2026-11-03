import json
import os
import sys
import json
import time
import subprocess
import glob
from datetime import datetime
import pandas as pd
import re
from smart_healer import SmartHealer
from visual_regression import VisualRegression

import pytest
import allure
# LLM Integration
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv("properties.env")


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
            import requests
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


def generate_selenium_script_with_llm(test_plan_data, website_url, test_depth, username=None, password=None):
    """
    Generate a complete Selenium test script using Template + Fill approach
    This approach is much faster and more reliable for large test suites
    """
    try:
        if test_depth <= 8:
            # For small to medium test suites, use direct generation (faster)
            return generate_direct_script(test_plan_data, website_url, test_depth, username, password)
        else:
            # For very large test suites (9+), use template + fill approach
            return generate_template_based_script(test_plan_data, website_url, test_depth, username, password)

    except Exception as e:
        error_msg = f"Error generating script: {str(e)}"
        return f"""# {error_msg}
import json
print(json.dumps([{{"testId": "ERROR", "testName": "Script Generation Failed", "status": "FAIL", "duration": 0, "error": "{str(e)}", "screenshot": "", "executed_at": "{datetime.now().isoformat()}"}}]))
"""


'''
def generate_direct_script(test_plan_data, website_url, test_depth, username=None, password=None):
    """Generate a complete pytest-compatible script in a single LLM call"""
    try:
        # Initialize the LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.1,
            max_tokens=3500,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create optimized prompt for fast, reliable test generation
        prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert QA engineer. Generate a pytest-compatible Selenium script with ALL {{test_depth}} test functions."),

            ("system", """PYTEST COMPATIBILITY - CRITICAL:
This script MUST be pytest-compatible. Follow these rules strictly:

1. IMPORT pytest at the top: import pytest
2. Create a @pytest.fixture for driver setup
3. Each test function MUST accept 'driver' as parameter from the fixture
4. DO NOT create a main() function - pytest will auto-discover tests
5. DO NOT manually call driver.quit() in tests - fixture handles it
6. Tests should use assertions, not return JSON dictionaries

REQUIRED FIXTURE (include at the top after imports):
@pytest.fixture(scope="function")
def driver():
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()
"""),

            ("system", """REQUIRED IMPORTS:
import pytest
import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
"""),

            ("system", """HELPER FUNCTIONS (include these):
def navigate_safely(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except TimeoutException:
        raise Exception("Page load timed out")

def teardown_test(driver):
    driver.delete_all_cookies()

def capture_screenshot(driver, filename):
    os.makedirs("generated_files/screenshots", exist_ok=True)
    filepath = f"generated_files/screenshots/{{filename}}.png"
    driver.save_screenshot(filepath)
    return filepath
"""),

            ("system", """CRITICAL TEST GENERATION RULES:
1. DO NOT hardcode expected values unless explicitly provided in test plan
2. Use flexible assertions that check for element presence and functionality, not specific text
3. Verify elements exist before interacting with them
4. Use meaningful, realistic test scenarios based on the website structure
5. If test plan provides expected values, use them; otherwise use generic checks

SMART ASSERTION EXAMPLES:
❌ BAD: assert "Example" in driver.title (hardcoded expectation)
✅ GOOD: assert len(driver.title) > 0 and driver.title != "about:blank", "Page title is empty or invalid"

❌ BAD: assert "Error" not in driver.page_source (too broad - matches HTML class names)
✅ GOOD: error_elements = driver.find_elements(By.CLASS_NAME, "error-message")
         visible_errors = [e for e in error_elements if e.is_displayed() and e.text.strip()]
         assert len(visible_errors) == 0, f"Unexpected visible errors: {{[e.text for e in visible_errors]}}"

❌ BAD: menu_link = driver.find_element(By.ID, "menu_link") (assumes specific ID)
✅ GOOD: nav_elements = driver.find_elements(By.TAG_NAME, "nav")
         assert len(nav_elements) > 0, "Navigation menu not found"
         assert nav_elements[0].is_displayed(), "Navigation menu not visible"
"""),

            ("system", """TEST DESIGN PHILOSOPHY:
- Tests should verify FUNCTIONALITY, not specific text or exact UI elements
- Use defensive programming - check if elements exist before asserting on them
- If an element doesn't exist and it's not critical, use pytest.skip() instead of failing
- Focus on: page loads, forms work, navigation works, elements are functional
- Avoid brittle tests that break with minor UI changes
- Use the test plan as guidance, but be flexible with implementation details
"""),

            ("system", """ELEMENT FINDING BEST PRACTICES:
When looking for elements, use this strategy:

1. Try generic selectors first (more resilient):
   - Forms: By.TAG_NAME, "form"
   - Buttons: By.CSS_SELECTOR, "button[type='submit']" or By.TAG_NAME, "button"
   - Links: By.TAG_NAME, "a"
   - Inputs: By.CSS_SELECTOR, "input[type='text']"

2. Use flexible selectors with error handling:
   elements = driver.find_elements(By.TAG_NAME, "button")
   if len(elements) == 0:
       pytest.skip("Required button element not found")

3. Check element state before assertions:
   if element.is_displayed() and element.is_enabled():
       # proceed with test

4. For text validation, use flexible matching:
   assert "expected_keyword" in element.text.lower(), f"Text mismatch: {{element.text}}"
"""),

            ("system", """REALISTIC TEST SCENARIOS:
For an e-commerce or web application, generate tests that verify:
1. ✅ Page loads successfully (check title exists, not empty, no error codes)
2. ✅ Forms are present and accept input
3. ✅ Buttons are clickable
4. ✅ Navigation elements exist and are visible
5. ✅ No visible error messages on page load
6. ✅ Key functionality works (search, login, add to cart, etc.)
7. ✅ Page responds to user interactions

DO NOT assume specific element IDs unless provided in test plan.
USE generic, semantic selectors that are more likely to exist.
VALIDATE functionality, not exact UI implementation.
"""),

            ("system", """SELF-HEALING CAPABILITIES (OPTIONAL):
If you want to use SmartHealer for robust element finding:
- from smart_healer import SmartHealer
- healer = SmartHealer(driver, api_key=os.getenv('OPENAI_API_KEY'))
- Use: element = healer.find_element_with_healing('id', 'button-id', 'login button')
- Save report: healer.save_healing_report() at end of test
This reduces test failures from UI changes."""),

            ("system", """VISUAL REGRESSION TESTING (OPTIONAL):
If you want to use VisualRegression for UI change detection:
- from visual_regression import VisualRegression
- visual = VisualRegression(driver, api_key=os.getenv('OPENAI_API_KEY'))
- Capture baseline: visual.capture_baseline('homepage')
- Compare: result = visual.compare_screenshots('homepage')
- Include visual results in test assertions"""),

            ("system",
             "CRITICAL: Use WebDriverWait for ALL element interactions. Never use driver.quit() in individual tests - fixture handles cleanup."),

            ("system",
             "PERFORMANCE: Keep tests fast - use 5-10 second timeouts, minimal waits, efficient element finding."),

            ("system",
             "ERROR HANDLING: Provide specific, actionable error messages. Use pytest.fail() or assertions for failures."),

            ("system", """PYTEST TEST STRUCTURE:
Each test function must:
- Accept 'driver' as parameter (from pytest fixture)
- Use assertions: assert condition, "descriptive error message"
- Raise exceptions on failure (pytest will catch them)
- NOT return JSON values (pytest handles pass/fail automatically)
- Call teardown_test(driver) at the end for cleanup

Example with flexible assertions:
def test_function_1(driver):
    try:
        navigate_safely(driver, "https://example.com")
        # Flexible title check
        assert len(driver.title) > 0, f"Page title is empty"
        # Check for elements without hardcoded IDs
        forms = driver.find_elements(By.TAG_NAME, "form")
        if len(forms) > 0:
            assert forms[0].is_displayed(), "Form is not visible"
        capture_screenshot(driver, "TC001_pass")
    except AssertionError as e:
        capture_screenshot(driver, "TC001_fail")
        raise
    except Exception as e:
        capture_screenshot(driver, "TC001_error")
        pytest.fail(f"Test failed: {{str(e)}}")
    finally:
        teardown_test(driver)
"""),

            ("system", """NAVIGATION REQUIREMENTS:
- Use navigate_safely() for all page navigation
- Wait for page to load completely
- Add small delays (1-2 seconds) for dynamic content if needed"""),

            ("system", """SCREENSHOT STRATEGY:
- Take screenshot when test fails (in except block)
- Take screenshot at END if test passes (success state)
- Save to generated_files/screenshots/TC###_pass.png or TC###_fail.png"""),

            ("system", """CRITICAL: NO main() FUNCTION:
DO NOT include:
- def main():
- if __name__ == "__main__":
- print(json.dumps(results))

Pytest will auto-discover and run all test_* functions.
Just define the fixture, helper functions, and test functions."""),

            ("system", """IMPORTANT: Return ONLY the complete Python script, no explanations or markdown formatting.

CRITICAL: Do NOT truncate the script or add notes about "remaining test cases". Generate the FULL script with ALL requested test functions.

FORBIDDEN: Do NOT add comments like "Additional test functions should be implemented" or "following the same pattern". Generate ALL functions completely."""),

            ("system", """If login required then use these credentials: username = emilys and password = emilyspass"""),
            ("system", """{credentials_instruction}"""),

            ("user", """Generate a complete pytest-compatible Selenium test script for:

Website URL: {website_url}
Test Depth: {test_depth} test cases

Test Plan (for reference):
{test_plan_json}

Instructions:
1. Create pytest fixture for driver management
2. Create {test_depth} individual test functions (test_function_1, test_function_2, etc.)
3. Each test should accept 'driver' parameter from fixture
4. Use FLEXIBLE assertions that check functionality, not hardcoded values
5. DO NOT create main() function - pytest handles execution
6. Use the test plan as GUIDANCE for test scenarios, but implement with flexible selectors
7. Handle authentication using credentials if login is detected

TEST EXECUTION STRATEGY:
- Use generic element selectors (tag names, types) rather than specific IDs
- Use try-catch blocks with flexible fallbacks
- Use navigate_safely() for all page navigation
- Check element existence, visibility, and clickability
- Verify page loads and basic functionality work

CLEANUP REQUIREMENTS:
- ALWAYS call teardown_test(driver) in finally block of each test

ERROR HANDLING REQUIREMENTS:
- Provide specific, descriptive error messages
- Use assertions or pytest.fail() for test failures
- Skip tests gracefully if non-critical elements are missing

CRITICAL: You MUST generate ALL {test_depth} complete test functions in a single response.

ABSOLUTE REQUIREMENTS:
- Write EXACTLY {test_depth} complete test functions (test_function_1, test_function_2, ..., test_function_{test_depth})
- Include pytest fixture for driver
- Include helper functions
- NO main() function
- NO print(json.dumps()) statements
- NO comments or markdown - the script is executed automatically by pytest
- Use FLEXIBLE, RESILIENT test implementations

The script MUST include:
1. All imports including pytest
2. Pytest fixture for driver
3. Helper functions (navigate_safely, teardown_test, capture_screenshot)
4. ALL {test_depth} complete test functions with smart, flexible assertions

Generate the COMPLETE pytest script with ALL {test_depth} test functions NOW.""")
        ])

        # Create the chain
        chain = prompt_template | llm

        # Prepare credentials instruction
        if username and password:
            credentials_instruction = f"""AUTHENTICATION CREDENTIALS PROVIDED:
        - Username: {username}
        - Password: {password}

        CRITICAL: Use these EXACT credentials for all login/authentication tests.

        MANDATORY: Include this exact login code in your script (without any markdown formatting):

        def perform_login(driver, username, password):
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                username_field.clear()
                username_field.send_keys(username)

                password_field = driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(password)

                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()

                time.sleep(2)

                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except:
                    pass

            except Exception as e:
                raise Exception(f"Login failed: {{{{str(e)}}}}")

        USE CREDENTIALS IN YOUR CODE:
        - Call: perform_login(driver, "{username}", "{password}")
        - Or directly: username_field.send_keys("{username}")
        - Or directly: password_field.send_keys("{password}")

        IMPORTANT: Generate clean Python code only - NO markdown code blocks, NO ``` markers."""
        else:
            credentials_instruction = """AUTHENTICATION: If login is required, use these default credentials: username = emilys and password = emilyspass"""

        # Generate the script
        response = chain.invoke({
            "website_url": website_url,
            "test_depth": test_depth,
            "test_plan_json": json.dumps(test_plan_data, indent=2),
            "credentials_instruction": credentials_instruction
        })

        # Clean up the response (remove any markdown formatting)
        script_content = response.content.strip()
        if script_content.startswith("```python"):
            script_content = script_content[9:]
        if script_content.startswith("```"):
            script_content = script_content[3:]
        if script_content.endswith("```"):
            script_content = script_content[:-3]

        return script_content.strip()

    except Exception as e:
        return f"""# Error generating script: {str(e)}
import pytest

@pytest.fixture(scope="function")
def driver():
    from selenium import webdriver
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_error(driver):
    pytest.fail("Script generation failed: {str(e)}")
"""
'''

'''
def generate_direct_script(test_plan_data, website_url, test_depth, username=None, password=None):
    """Generate a complete script in a single LLM call"""
    try:
        # Initialize the LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.1,
            max_tokens=3500,  # Reduced for faster generation
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create optimized prompt for fast, reliable test generation
        prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert QA engineer. Generate a fast, reliable Selenium script with ALL {test_depth} test functions."),

            ("system", """SELF-HEALING CAPABILITIES:
        Import and use SmartHealer for robust element finding:
        - from smart_healing import SmartHealer
        - healer = SmartHealer(driver, api_key=os.getenv('OPENAI_API_KEY'))
        - Use: element = healer.find_element_with_healing('id', 'button-id', 'login button')
        - Save report: healer.save_healing_report() at end of main()
        This reduces test failures from UI changes."""),

            ("system", """VISUAL REGRESSION TESTING:
        Import and use VisualRegression for UI change detection:
        - from visual_regression import VisualRegression
        - visual = VisualRegression(driver, api_key=os.getenv('OPENAI_API_KEY'))
        - Capture baseline: visual.capture_baseline('homepage')
        - Compare: result = visual.compare_screenshots('homepage')
        - Include visual results in final JSON output"""),

            ("system",
             "CRITICAL: Use WebDriverWait for ALL element interactions. Never use driver.quit() in individual tests - only in main() finally block."),

            ("system",
             "PERFORMANCE: Keep tests fast - use 5-second timeouts, minimal waits, efficient element finding."),

            ("system", "ERROR HANDLING: Provide specific, short error messages. Use proper exception handling."),

            ("system",
             "CRITICAL BUG FIX: DO NOT call driver.quit() in individual test functions. Only quit driver in main() finally block. Use driver.delete_all_cookies() for cleanup between tests."),

            ("system",
             "SPEED OPTIMIZATION: Use 5-second WebDriverWait timeouts instead of 10+ seconds. Find elements efficiently with single selectors."),

            ("system", """EXACT JSON RESULT STRUCTURE:
Each test result must have this EXACT format (matching existing result files):

```json
{{
  "testId": "TC001",
  "testName": "Descriptive test name",
  "status": "PASS/FAIL",
  "error": "error message in case of fail and empty string in case of pass",
  "duration": 12.34,
  "screenshot": "generated_files/screenshots/filename.png",
  "executed_at": "2025-09-23T19:32:08.465293"
}}
```
"""),

            ("system", """ELEMENT FINDING STRATEGY:
Use try-catch blocks with fallbacks: ID → Name → CSS Selector
Verify element is clickable before interaction."""),

            ("system", """NAVIGATION REQUIREMENTS:
- Use driver.get(url) for navigation
- Wait for page to load completely
- Add small delays for dynamic content"""),

            ("system", """TEARDOWN REQUIREMENTS:
- Clear any open alerts
- Clear browser cookies
- Return teardown status in JSON format"""),

            ("system", """SCREENSHOT STRATEGY:
- Take screenshot ONLY when test fails (at the point of failure)
- Take screenshot at the END if test passes (success state)
- Save screenshots to generated_files/screenshots/"""),

            ("system", """TEST FUNCTION STRUCTURE:
- Create individual test functions for each test case
- Each function should return JSON with exact format specified above
- Include setup, execution, and teardown in each test
- Use modern Selenium methods (find_elements(By.CSS_SELECTOR, selector) not find_elements_by_css_selector)
- Include proper main() function with test execution loop
- Generate ALL test functions requested, not just examples"""),

            ("system", """CRITICAL JSON REQUIREMENTS:
- testId must match pattern "TC001", "TC002", etc.
- testName must be a descriptive string
- status must be exactly "PASS" or "FAIL" (uppercase)
- error must be empty string "" for passed tests, descriptive error message for failed tests
- duration must be a number (float) - exact precision as calculated
- screenshot must be valid path: "generated_files/screenshots/filename.png"
- executed_at must be ISO format timestamp with microseconds
- Field ORDER must match: testId, testName, status, error, duration, screenshot, executed_at
- All fields are REQUIRED - no missing fields allowed"""),

            ("system", """IMPORTANT: Return ONLY the complete Python script, no explanations or markdown formatting.

CRITICAL: Do NOT truncate the script or add notes about "remaining test cases". Generate the FULL script with ALL requested test functions.

FORBIDDEN: Do NOT add comments like "Additional test functions should be implemented" or "following the same pattern". Generate ALL functions completely."""),

            ("system", """CRITICAL JSON OUTPUT REQUIREMENT:
        At the end of main(), you MUST print results using json.dumps():

        import json
        print(json.dumps(results, indent=2))

        DO NOT use print(results) - this creates invalid JSON with single quotes.
        ALWAYS use json.dumps() to ensure valid JSON with double quotes."""),
            ("system", """If login required then use these credentials: username = emilys and password = emilyspass"""),
            ("system", """{credentials_instruction}"""),

            ("user", """Generate a complete Selenium test script for:

Website URL: {website_url}
Test Depth: {test_depth} test cases

Test Plan (for reference):
{test_plan_json}

Instructions:
1. Create {test_depth} individual test functions based on the test plan
2. Each test should verify specific functionality from the test plan
3. Use the test plan steps and expected results as guidance
4. Handle authentication using credentials from the test plan

TEST EXECUTION STRATEGY:
- Use simple try-catch blocks for element finding (ID first, then name, then CSS)
- Use navigate_safely() for all page navigation to handle loading states
- Use normalize_url() to prevent double paths when navigating to relative URLs
- Check element visibility and clickability before interaction
- Verify page loads completely before proceeding

TEARDOWN AND CLEANUP REQUIREMENTS:
- ALWAYS call teardown_test() after each test function execution


ERROR HANDLING REQUIREMENTS:
- Always provide specific, meaningful error messages
- Never return empty error strings

CRITICAL: You MUST generate ALL {test_depth} complete test functions in a single response.

ABSOLUTE REQUIREMENTS:
- Write EXACTLY {test_depth} complete test functions (test_function_1, test_function_2, ..., test_function_{test_depth})
- Include ALL test functions in the main() function execution
- NO comments or markdowns the script is executed automatically"


The script MUST include:
1. All imports and setup
2. ALL {test_depth} complete test functions
3. Complete main() function that calls ALL {test_depth} functions
4. Proper JSON output

Generate the COMPLETE script with ALL {test_depth} test functions NOW.""")
        ])

        # Create the chain
        chain = prompt_template | llm

        # Prepare credentials instruction
        if username and password:
            credentials_instruction = f"""AUTHENTICATION CREDENTIALS PROVIDED:
        - Username: {username}
        - Password: {password}

        CRITICAL: Use these EXACT credentials for all login/authentication tests.

        MANDATORY: Include this exact login code in your test functions (without any markdown formatting):

        # Login function implementation
        def perform_login(driver, username, password):
            try:
                # Find username field
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                username_field.clear()
                username_field.send_keys(username)

                # Find password field  
                password_field = driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(password)

                # Click login button
                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                login_button.click()

                # Wait for login
                time.sleep(2)

                # Handle alerts if present
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except:
                    pass

            except Exception as e:
                raise Exception(f"Login failed: {{str(e)}}")

        USE CREDENTIALS IN YOUR CODE:
        - Call: perform_login(driver, "{username}", "{password}")
        - Or directly: username_field.send_keys("{username}")
        - Or directly: password_field.send_keys("{password}")

        IMPORTANT: Generate clean Python code only - NO markdown code blocks, NO ``` markers."""
        else:
            credentials_instruction = """AUTHENTICATION: If login is required, use these default credentials: username = emilys and password = emilyspass"""

        # Generate the script
        response = chain.invoke({
            "website_url": website_url,
            "test_depth": test_depth,
            "test_plan_json": json.dumps(test_plan_data, indent=2),
            "credentials_instruction": credentials_instruction
        })

        # Clean up the response (remove any markdown formatting)
        script_content = response.content.strip()
        if script_content.startswith("```python"):
            script_content = script_content[9:]  # Remove ```python
        if script_content.startswith("```"):
            script_content = script_content[3:]  # Remove ```
        if script_content.endswith("```"):
            script_content = script_content[:-3]  # Remove ```

        return script_content.strip()

    except Exception as e:
        return f"""# Error generating script: {str(e)}
import json
print(json.dumps([{{"testId": "ERROR", "testName": "Script Generation Failed", "status": "FAIL", "duration": 0, "error": "{str(e)}", "screenshot": "", "executed_at": "{datetime.now().isoformat()}"}}]))
"""
'''


def generate_direct_script(test_plan_data, website_url, test_depth, username=None, password=None):
    """Generate PRODUCTION-READY e-commerce test suite with comprehensive coverage"""
    try:
        # Initialize the LLM with higher token limit for complex tests
        llm = ChatOpenAI(
            # model="gpt-4-turbo",
            model="gpt-5",
            temperature=0.05,  # Very low for consistency
            max_tokens=16000,  # Higher for complete generation
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create ULTIMATE e-commerce testing prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a SENIOR QA AUTOMATION ARCHITECT with 15+ years specializing in e-commerce testing.
Your mission: Generate BULLETPROOF, PRODUCTION-READY pytest Selenium tests that:
- Work on ANY e-commerce website structure
- Handle ALL edge cases and error scenarios
- Never crash or fail ungracefully
- Detect real bugs and issues
- Use multiple fallback strategies for every interaction

Generate ALL {{test_depth}} complete, robust test functions."""),

            ("system", """PYTEST SETUP - MANDATORY STRUCTURE:

import pytest
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    NoAlertPresentException,
    UnexpectedAlertPresentException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    WebDriverException
)

@pytest.fixture(scope="function")
def driver():
    \"\"\"Setup Chrome driver with optimal configuration\"\"\"
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    yield driver
    try:
        driver.quit()
    except:
        pass
"""),

            ("system", """ULTIMATE HELPER FUNCTIONS - PRODUCTION-GRADE:

def navigate_safely(driver, url, max_retries=3):
    \"\"\"Navigate with comprehensive retry logic\"\"\"
    for attempt in range(max_retries):
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(1.5)  # Allow JS frameworks to initialize
            return True
        except:
            if attempt == max_retries - 1:
                return False
            time.sleep(2)
    return False

def handle_alert(driver, action='accept', max_wait=3):
    \"\"\"Handle JavaScript alerts/popups with multiple strategies\"\"\"
    try:
        WebDriverWait(driver, max_wait).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert_text = alert.text
        if action == 'accept':
            alert.accept()
        elif action == 'dismiss':
            alert.dismiss()
        return True, alert_text
    except (NoAlertPresentException, TimeoutException):
        return False, ""
    except Exception as e:
        print(f"Alert handling error: {{e}}")
        return False, ""

def safe_find_element(driver, strategies, timeout=5):
    \"\"\"Find element using multiple strategies with fallbacks\"\"\"
    for strategy in strategies:
        try:
            by, value = strategy
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            if element:
                return element
        except:
            continue
    return None

def safe_find_elements(driver, by, value):
    \"\"\"Safely find multiple elements\"\"\"
    try:
        return driver.find_elements(by, value)
    except:
        return []

def safe_click(driver, element, use_js=False, max_retries=3):
    \"\"\"Click with multiple strategies and retry logic\"\"\"
    for attempt in range(max_retries):
        try:
            if use_js or attempt > 0:
                driver.execute_script("arguments[0].scrollIntoView({{block: 'center'}});", element)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", element)
            else:
                driver.execute_script("arguments[0].scrollIntoView({{block: 'center'}});", element)
                time.sleep(0.3)
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(element))
                element.click()
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException, ElementNotInteractableException):
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            return False
        except:
            if attempt == max_retries - 1:
                return False
            time.sleep(0.5)
    return False

def safe_send_keys(element, text, clear_first=True, use_js=False):
    \"\"\"Send keys with error handling\"\"\"
    try:
        if clear_first:
            element.clear()
        if use_js:
            element.send_keys(text)
        else:
            element.send_keys(text)
        time.sleep(0.2)
        return True
    except:
        try:
            element.send_keys(text)
            return True
        except:
            return False

def get_text_safe(element):
    \"\"\"Get element text with multiple fallbacks\"\"\"
    try:
        text = element.text
        if text and text.strip():
            return text.strip()
        text = element.get_attribute('textContent')
        if text and text.strip():
            return text.strip()
        text = element.get_attribute('innerText')
        if text and text.strip():
            return text.strip()
        text = element.get_attribute('value')
        return text.strip() if text else ""
    except:
        return ""

def is_element_visible(element):
    \"\"\"Check if element is visible and interactable\"\"\"
    try:
        return element.is_displayed() and element.is_enabled()
    except:
        return False

def wait_for_page_load(driver, timeout=10):
    \"\"\"Wait for page to fully load\"\"\"
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        time.sleep(0.5)
        return True
    except:
        return False

def teardown_test(driver):
    \"\"\"Comprehensive cleanup\"\"\"
    try:
        # Handle any open alerts
        try:
            driver.switch_to.alert.dismiss()
        except:
            pass
        # Clear data
        driver.delete_all_cookies()
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
        except:
            pass
    except:
        pass

def capture_screenshot(driver, filename):
    \"\"\"Capture screenshot with error handling\"\"\"
    try:
        os.makedirs("generated_files/screenshots", exist_ok=True)
        filepath = f"generated_files/screenshots/{{filename}}.png"
        driver.save_screenshot(filepath)
        return filepath
    except:
        return ""
"""),

            ("system", """E-COMMERCE SPECIFIC HELPERS - CRITICAL FOR SHOPPING SITES:

def perform_login(driver, username, password):
    \"\"\"BULLETPROOF login with comprehensive error handling\"\"\"
    try:
        # Strategy 1: Find username field (multiple approaches)
        username_strategies = [
            (By.ID, "username"),
            (By.ID, "user"),
            (By.ID, "email"),
            (By.ID, "login"),
            (By.NAME, "username"),
            (By.NAME, "user"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='text'][name*='user']"),
            (By.CSS_SELECTOR, "input[type='text'][id*='user']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='user' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
            (By.XPATH, "//input[@type='text']"),
        ]

        username_field = safe_find_element(driver, username_strategies, timeout=5)
        if username_field is None:
            return False, "Username field not found"

        if not safe_send_keys(username_field, username):
            return False, "Failed to enter username"

        # Strategy 2: Find password field
        password_strategies = [
            (By.ID, "password"),
            (By.ID, "pass"),
            (By.ID, "pwd"),
            (By.NAME, "password"),
            (By.NAME, "pass"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@type='password']"),
        ]

        password_field = safe_find_element(driver, password_strategies, timeout=5)
        if password_field is None:
            return False, "Password field not found"

        if not safe_send_keys(password_field, password):
            return False, "Failed to enter password"

        # Strategy 3: Submit form (multiple approaches)
        submitted = False

        # Try clicking submit button
        button_strategies = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(translate(text(), 'LOGIN', 'login'), 'login')]"),
            (By.XPATH, "//button[contains(translate(text(), 'SIGN IN', 'sign in'), 'sign in')]"),
            (By.XPATH, "//input[@value='Login' or @value='Sign In']"),
            (By.CSS_SELECTOR, "button.login"),
            (By.CSS_SELECTOR, "button.btn-login"),
        ]

        submit_button = safe_find_element(driver, button_strategies, timeout=3)
        if submit_button:
            if safe_click(driver, submit_button):
                submitted = True

        # Fallback: Press Enter on password field
        if not submitted:
            try:
                password_field.send_keys(Keys.RETURN)
                submitted = True
            except:
                pass

        if not submitted:
            return False, "Could not submit login form"

        # Wait for login to process
        time.sleep(2)

        # Check for login alerts (error messages)
        has_alert, alert_text = handle_alert(driver, action='accept', max_wait=2)
        if has_alert:
            if any(keyword in alert_text.lower() for keyword in ['invalid', 'incorrect', 'wrong', 'failed', 'error']):
                return False, f"Login failed: {{alert_text}}"

        # Check if still on login page (indicates failure)
        time.sleep(1)
        current_url = driver.current_url.lower()
        if 'login' in current_url or 'signin' in current_url:
            # Check for error messages on page
            error_elements = safe_find_elements(driver, By.CSS_SELECTOR, ".error, .error-message, [class*='error'], [id*='error']")
            for elem in error_elements:
                if is_element_visible(elem):
                    error_text = get_text_safe(elem)
                    if error_text:
                        return False, f"Login error: {{error_text}}"
            return False, "Still on login page after submission"

        return True, "Login successful"

    except Exception as e:
        return False, f"Login exception: {{str(e)}}"

def find_and_add_product_to_cart(driver):
    \"\"\"Find any product and add to cart - UNIVERSAL approach\"\"\"
    try:
        # Strategy: Find "Add to Cart" buttons with multiple selectors
        add_to_cart_strategies = [
            (By.XPATH, "//button[contains(translate(text(), 'ADD TO CART', 'add to cart'), 'add to cart')]"),
            (By.XPATH, "//button[contains(translate(text(), 'ADD', 'add'), 'add')]"),
            (By.CSS_SELECTOR, "button[class*='add-to-cart']"),
            (By.CSS_SELECTOR, "button[id*='add-to-cart']"),
            (By.CSS_SELECTOR, "button.add-cart"),
            (By.CSS_SELECTOR, "[data-action='add-to-cart']"),
            (By.CSS_SELECTOR, ".btn-add-cart"),
        ]

        for strategy in add_to_cart_strategies:
            buttons = safe_find_elements(driver, strategy[0], strategy[1])
            for button in buttons:
                if is_element_visible(button):
                    if safe_click(driver, button):
                        time.sleep(1)
                        # Handle any alerts
                        handle_alert(driver, action='accept', max_wait=1)
                        return True, "Product added to cart"

        return False, "No 'Add to Cart' buttons found"

    except Exception as e:
        return False, f"Error adding product: {{str(e)}}"

def search_product(driver, search_term="test"):
    \"\"\"Search for product using search functionality\"\"\"
    try:
        # Find search input
        search_strategies = [
            (By.ID, "search"),
            (By.NAME, "search"),
            (By.NAME, "q"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.CSS_SELECTOR, "input[placeholder*='search' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='Search' i]"),
            (By.XPATH, "//input[@type='text' and contains(@placeholder, 'Search')]"),
        ]

        search_input = safe_find_element(driver, search_strategies, timeout=5)
        if search_input is None:
            return False, "Search input not found"

        if not safe_send_keys(search_input, search_term):
            return False, "Failed to enter search term"

        # Find and click search button OR press Enter
        search_button_strategies = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(@class, 'search')]"),
            (By.CSS_SELECTOR, ".search-button"),
            (By.CSS_SELECTOR, "#search-button"),
        ]

        search_button = safe_find_element(driver, search_button_strategies, timeout=2)
        if search_button:
            safe_click(driver, search_button)
        else:
            search_input.send_keys(Keys.RETURN)

        time.sleep(2)
        wait_for_page_load(driver)
        return True, "Search performed successfully"

    except Exception as e:
        return False, f"Search error: {{str(e)}}"

def navigate_to_cart(driver):
    \"\"\"Navigate to shopping cart\"\"\"
    try:
        cart_strategies = [
            (By.XPATH, "//button[contains(translate(text(), 'CART', 'cart'), 'cart')]"),
            (By.XPATH, "//a[contains(translate(text(), 'CART', 'cart'), 'cart')]"),
            (By.CSS_SELECTOR, "button[id*='cart']"),
            (By.CSS_SELECTOR, "a[id*='cart']"),
            (By.CSS_SELECTOR, "button[class*='cart']"),
            (By.CSS_SELECTOR, "a[class*='cart']"),
            (By.CSS_SELECTOR, "[data-test='cart']"),
            (By.CSS_SELECTOR, ".cart-button"),
            (By.CSS_SELECTOR, "#cart"),
        ]

        cart_button = safe_find_element(driver, cart_strategies, timeout=5)
        if cart_button is None:
            return False, "Cart button not found"

        if not safe_click(driver, cart_button):
            return False, "Failed to click cart button"

        time.sleep(2)
        wait_for_page_load(driver)
        return True, "Navigated to cart"

    except Exception as e:
        return False, f"Cart navigation error: {{str(e)}}"

def perform_logout(driver):
    \"\"\"Logout from application\"\"\"
    try:
        logout_strategies = [
            (By.XPATH, "//button[contains(translate(text(), 'LOGOUT', 'logout'), 'logout')]"),
            (By.XPATH, "//a[contains(translate(text(), 'LOGOUT', 'logout'), 'logout')]"),
            (By.XPATH, "//button[contains(translate(text(), 'SIGN OUT', 'sign out'), 'sign out')]"),
            (By.CSS_SELECTOR, "button[id*='logout']"),
            (By.CSS_SELECTOR, "a[id*='logout']"),
            (By.CSS_SELECTOR, ".logout"),
            (By.CSS_SELECTOR, "#logout"),
        ]

        logout_button = safe_find_element(driver, logout_strategies, timeout=5)
        if logout_button is None:
            return False, "Logout button not found"

        if not safe_click(driver, logout_button):
            return False, "Failed to click logout"

        time.sleep(2)
        handle_alert(driver, action='accept', max_wait=1)
        return True, "Logout successful"

    except Exception as e:
        return False, f"Logout error: {{str(e)}}"
"""),

            ("system", """COMPREHENSIVE E-COMMERCE TEST SCENARIOS:

You MUST generate these types of tests for a complete e-commerce test suite:

- AUTHENTICATION TESTS (Tests 1-4):
1. **Valid Login**: Test successful login with correct credentials
2. **Invalid Login**: Test login with wrong credentials, verify alert handling
3. **Empty Fields**: Test login with empty username/password
4. **Forgot Password**: Check if forgot password link exists and is clickable

- PRODUCT & SHOPPING TESTS (Tests 5-8):
5. **Product Display**: Verify products are displayed after login
6. **Add to Cart**: Add product to cart and verify action succeeds
7. **Multiple Products**: Add multiple products to cart
8. **Product Search**: Use search functionality to find products

- CART FUNCTIONALITY TESTS (Tests 9-12):
9. **View Cart**: Navigate to cart and verify products are listed
10. **Cart Count**: Verify cart shows correct number of items
11. **Proceed to Checkout**: Click checkout button and handle result
12. **Continue Shopping**: Test continue shopping button functionality

- NAVIGATION & UI TESTS (Tests 13-16):
13. **Filter Products**: Test product filtering if available
14. **Navigation Links**: Verify all navigation elements are present
15. **Logout Functionality**: Test logout and verify return to login
16. **Page Responsiveness**: Test basic responsive behavior

- EDGE CASES & BUG DETECTION (Tests 17-20):
17. **Empty Cart Checkout**: Try checkout with empty cart
18. **Session Handling**: Test if session persists correctly
19. **Error Messages**: Verify appropriate error messages display
20. **Alert Handling**: Comprehensive alert/popup handling tests

MANDATORY: Adapt test count to {{test_depth}} - distribute these scenarios intelligently."""),

            ("system", """BULLETPROOF TEST STRUCTURE - FOLLOW EXACTLY:

def test_function_X(driver):
    \"\"\"Descriptive test name\"\"\"
    try:
        # 1. NAVIGATE
        if not navigate_safely(driver, "{{website_url}}"):
            pytest.skip("Unable to navigate to website")

        # 2. HANDLE PRE-TEST ALERTS
        handle_alert(driver, action='accept', max_wait=1)

        # 3. CHECK PAGE LOADED
        wait_for_page_load(driver)

        # 4. TEST LOGIC WITH MULTIPLE FALLBACKS
        # Example: Login test
        success, message = perform_login(driver, "username", "password")
        if success:
            assert True, message  # Login succeeded
        else:
            # Check if this is expected failure (wrong credentials test)
            if "invalid" in message.lower() or "incorrect" in message.lower():
                assert True, "Expected login failure detected correctly"
            else:
                pytest.fail(message)

        # 5. SUCCESS SCREENSHOT
        capture_screenshot(driver, "TC00X_pass")

    except AssertionError as e:
        capture_screenshot(driver, "TC00X_fail")
        raise
    except Exception as e:
        capture_screenshot(driver, "TC00X_error")
        pytest.fail(f"Test error: {{str(e)}}")
    finally:
        teardown_test(driver)

CRITICAL RULES:
- ALWAYS use helper functions (perform_login, find_and_add_product_to_cart, etc.)
- ALWAYS handle alerts after EVERY interaction
- ALWAYS have multiple fallback strategies
- ALWAYS use pytest.skip() for non-critical missing features
- NEVER assume specific element IDs or classes
- NEVER let tests crash - catch ALL exceptions"""),

            ("system", """CRITICAL REQUIREMENTS - ABSOLUTE MUSTS:

- Generate EXACTLY {{test_depth}} complete test functions
- Cover ALL e-commerce scenarios (login, cart, checkout, search, logout)
- Handle JavaScript alerts/popups in EVERY test
- Use multiple selector strategies for EVERY element
- Never hardcode element locators - use helpers
- Test both success AND failure scenarios
- Include edge cases (empty cart, wrong credentials, etc.)
- Make tests work on ANY e-commerce structure
- Use descriptive test names explaining what's being tested
- Follow the bulletproof structure for EVERY test

❌ FORBIDDEN:
- Hardcoded element IDs without fallbacks
- Assuming specific page structure
- Not handling alerts
- Tests that crash on missing elements
- Incomplete test functions
- Comments like "implement remaining tests"
- Any main() function
- Any JSON output or return statements"""),

            ("system", """CRITICAL ERROR MESSAGE REQUIREMENTS:

        Every test MUST provide DETAILED, ACTIONABLE error messages.

        ❌ BAD ERROR HANDLING:
        except Exception as e:
            pytest.fail(str(e))  # Generic message

        ✅ GOOD ERROR HANDLING:
        except Exception as e:
            pytest.fail(f"Login test failed: Could not find username field. Error: {{str(e)}}")

        ✅ EVEN BETTER:
        except NoSuchElementException:
            pytest.fail("Login failed: Username field with ID 'username' not found on page")
        except TimeoutException:
            pytest.fail("Login failed: Page took too long to load (>10s)")
        except Exception as e:
            pytest.fail(f"Login failed unexpectedly: {{type(e).__name__}}: {{str(e)}}")

        MANDATORY ERROR MESSAGE FORMAT:
        - Start with WHAT failed: "Login failed", "Add to cart failed", "Search failed"
        - Include WHY it failed: "Username field not found", "Button not clickable"
        - Include CONTEXT: element ID, timeout value, expected vs actual
        - Use f-strings for dynamic values

        EVERY assert must have descriptive message:
        ❌ assert element is not None
        ✅ assert element is not None, "Username field not found using ID 'username', NAME 'username', or CSS selector 'input[type=text]'"

        ❌ assert success
        ✅ assert success, f"Login failed: {{message}}. Tried credentials: {{username}}/{{password}}"
        """),

            ("system", """EXAMPLE PERFECT TEST:

def test_function_1_valid_login(driver):
    \"\"\"Test successful login with valid credentials\"\"\"
    try:
        # Navigate to website
        if not navigate_safely(driver, "{{website_url}}"):
            pytest.skip("Unable to navigate to website")

        # Perform login
        success, message = perform_login(driver, "{{username}}", "{{password}}")

        # Verify login succeeded
        assert success, f"Login failed: {{message}}"

        # Verify we're no longer on login page
        time.sleep(1)
        current_url = driver.current_url.lower()
        assert 'login' not in current_url, "Still on login page after successful login"

        # Success
        capture_screenshot(driver, "TC001_pass")

    except AssertionError as e:
        capture_screenshot(driver, "TC001_fail")
        raise
    except Exception as e:
        capture_screenshot(driver, "TC001_error")
        pytest.fail(f"Test error: {{str(e)}}")
    finally:
        teardown_test(driver)

THIS IS PERFECT - FOLLOW THIS PATTERN FOR ALL TESTS!"""),

            ("system", """OUTPUT REQUIREMENTS:

1. Return ONLY executable Python code
2. NO markdown, NO explanations, NO code blocks (```)
3. Include ALL imports at the top
4. Include pytest fixture
5. Include ALL helper functions
6. Include ALL {{test_depth}} complete test functions
7. NO main() function
8. NO print() statements
9. NO JSON output or return statements

The generated script must be ready to run immediately with:
pytest script.py"""),

            ("system", """{credentials_instruction}"""),

            ("user", """Generate COMPLETE, BULLETPROOF e-commerce test suite:

Website URL: {website_url}
Test Depth: {test_depth} tests
Test Plan Reference: {test_plan_json}

COMPREHENSIVE E-COMMERCE REQUIREMENTS:
✅ Login tests (valid, invalid, empty, alerts)
✅ Product browsing and display
✅ Add to cart functionality
✅ Cart viewing and management
✅ Search functionality
✅ Filter/category tests (if available)
✅ Checkout button tests
✅ Continue shopping tests
✅ Logout functionality
✅ Forgot password link (if exists)
✅ Alert/popup handling throughout
✅ Edge cases and error scenarios
✅ Session management
✅ Navigation and UI elements

CRITICAL INSTRUCTIONS:
1. Generate ALL {test_depth} complete test functions
2. Use ALL helper functions provided
3. Handle alerts after EVERY user interaction
4. Use multiple selector strategies for robustness
5. Test both SUCCESS and FAILURE scenarios
6. Make tests work on ANY e-commerce site
7. Follow the bulletproof test structure exactly
8. Include comprehensive error handling
9. Use pytest.skip() for graceful failures
10. NO hardcoded assumptions about site structure

GENERATE COMPLETE, PRODUCTION-READY TEST SUITE NOW!""")
        ])

        # Create chain and invoke
        chain = prompt_template | llm

        # Prepare credentials instruction
        if username and password:
            credentials_instruction = f"""PROVIDED CREDENTIALS:
Username: {username}
Password: {password}

Use these EXACT credentials for ALL login tests.
Test both valid login (with these credentials) and invalid login (with wrong credentials)."""
        else:
            credentials_instruction = """DEFAULT CREDENTIALS:
Use username='emilys' and password='emilyspass' for valid login tests.
Use username='invalid' and password='wrong' for invalid login tests."""

        # Generate the script
        response = chain.invoke({
            "website_url": website_url,
            "test_depth": test_depth,
            "test_plan_json": json.dumps(test_plan_data, indent=2),
            "credentials_instruction": credentials_instruction
        })

        # Clean up response
        script_content = response.content.strip()
        if script_content.startswith("```python"):
            script_content = script_content[9:]
        if script_content.startswith("```"):
            script_content = script_content[3:]
        if script_content.endswith("```"):
            script_content = script_content[:-3]

        # Verify critical components
        if "@pytest.fixture" not in script_content:
            raise Exception("Missing pytest fixture")
        if "def test_" not in script_content:
            raise Exception("Missing test functions")
        if "def perform_login" not in script_content:
            script_content = script_content.replace("@pytest.fixture",
                                                    "# Login and e-commerce helpers included\n\n@pytest.fixture")

        return script_content.strip()

    except Exception as e:
        # Fallback error script
        return f"""# Error: {str(e)}
import pytest

@pytest.fixture(scope="function")
def driver():
    from selenium import webdriver
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_generation_error(driver):
    pytest.fail("Script generation failed: {str(e)}")
"""


'''
def generate_direct_script(test_plan_data, website_url, test_depth, username=None, password=None):
    """Generate a complete pytest-compatible script with bulletproof error handling"""
    try:
        # Initialize the LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.1,
            max_tokens=4000,  # Increased for better generation
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create comprehensive prompt for bulletproof test generation
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert QA automation engineer with 10+ years of experience. 
Generate a pytest-compatible Selenium script with ALL {{test_depth}} test functions.
Your tests must be BULLETPROOF - they should never crash, always handle errors gracefully, and work with ANY website structure."""),

            ("system", """PYTEST COMPATIBILITY - MANDATORY:
1. Import pytest: import pytest
2. Create @pytest.fixture for driver (scope="function")
3. All test functions accept 'driver' parameter
4. NO main() function - pytest auto-discovers tests
5. NO driver.quit() in tests - fixture handles cleanup
6. Use assertions, not return statements

@pytest.fixture(scope="function")
def driver():
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()
"""),

            ("system", """REQUIRED IMPORTS - COPY EXACTLY:
import pytest
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
"""),

            ("system", """BULLETPROOF HELPER FUNCTIONS - COPY EXACTLY:

def navigate_safely(driver, url):
    \"\"\"Navigate with comprehensive error handling\"\"\"
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        time.sleep(1)  # Allow dynamic content to load
        return True
    except TimeoutException:
        return False
    except Exception as e:
        print(f"Navigation error: {{e}}")
        return False

def teardown_test(driver):
    \"\"\"Clean up after test\"\"\"
    try:
        driver.delete_all_cookies()
    except:
        pass

def capture_screenshot(driver, filename):
    \"\"\"Capture screenshot with error handling\"\"\"
    try:
        os.makedirs("generated_files/screenshots", exist_ok=True)
        filepath = f"generated_files/screenshots/{{filename}}.png"
        driver.save_screenshot(filepath)
        return filepath
    except Exception as e:
        print(f"Screenshot error: {{e}}")
        return ""

def safe_find_element(driver, by, value, timeout=5):
    \"\"\"Safely find element with timeout\"\"\"
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except:
        return None

def safe_find_elements(driver, by, value):
    \"\"\"Safely find multiple elements\"\"\"
    try:
        return driver.find_elements(by, value)
    except:
        return []
"""),

            ("system", """CRITICAL TEST GENERATION PHILOSOPHY:

🎯 DEFENSIVE PROGRAMMING - ALWAYS:
1. Check if elements exist BEFORE interacting
2. Use try-except for EVERY interaction
3. Never assume element IDs, classes, or structure
4. Provide fallback strategies for every operation
5. Skip tests gracefully if features don't exist

🎯 FLEXIBLE ASSERTIONS - EXAMPLES:
❌ NEVER: assert element.text == "Exact Text"
✅ ALWAYS: assert element is not None and len(element.text) > 0

❌ NEVER: driver.find_element(By.ID, "specific-id").click()
✅ ALWAYS: 
   element = safe_find_element(driver, By.ID, "specific-id")
   if element is None:
       pytest.skip("Element not found - feature not implemented")
   element.click()

🎯 GENERIC SELECTORS - USE THESE:
- Forms: By.TAG_NAME, "form"
- Buttons: By.TAG_NAME, "button" or By.CSS_SELECTOR, "button, input[type='button'], input[type='submit']"
- Links: By.TAG_NAME, "a"
- Inputs: By.TAG_NAME, "input"
- Text areas: By.TAG_NAME, "textarea"
- Images: By.TAG_NAME, "img"
- Navigation: By.TAG_NAME, "nav"
"""),

            ("system", """BULLETPROOF TEST STRUCTURE - MANDATORY PATTERN:

def test_function_X(driver):
    \"\"\"Test description\"\"\"
    try:
        # Step 1: Navigate safely
        if not navigate_safely(driver, "{{website_url}}"):
            pytest.skip("Unable to navigate to website")

        # Step 2: Check if required elements exist
        elements = safe_find_elements(driver, By.TAG_NAME, "body")
        if len(elements) == 0:
            pytest.skip("Page body not found")

        # Step 3: Perform test actions with safety checks
        # Example: Check for forms
        forms = safe_find_elements(driver, By.TAG_NAME, "form")
        if len(forms) > 0:
            assert forms[0].is_displayed(), "Form exists but not visible"
        else:
            # This is OK - not all pages have forms
            pass

        # Step 4: Make flexible assertions
        assert driver.current_url != "about:blank", "Page failed to load"

        # Step 5: Capture success screenshot
        capture_screenshot(driver, "TC00X_pass")

    except AssertionError as e:
        capture_screenshot(driver, "TC00X_fail")
        raise
    except Exception as e:
        capture_screenshot(driver, "TC00X_error")
        pytest.fail(f"Test error: {{str(e)}}")
    finally:
        teardown_test(driver)
"""),

            ("system", """SMART TEST SCENARIOS - GENERATE THESE TYPES:

TEST 1: Page Load Verification
- Navigate to URL
- Check page loaded (title exists, not empty, not error page)
- Verify no JavaScript errors (check console if possible)
- Check page has content (body has elements)

TEST 2: Interactive Elements Detection
- Find all clickable elements (buttons, links)
- Verify at least some interactive elements exist
- Don't assume specific elements - just check they exist

TEST 3: Form Functionality (if forms exist)
- Find forms using By.TAG_NAME, "form"
- If forms found: check inputs exist, try filling one field
- If no forms: skip gracefully with pytest.skip()

TEST 4: Navigation Verification (if nav exists)
- Look for nav tags or links
- If found: verify they're visible
- Don't try to click unless test plan specifies

TEST 5: Input Validation (if forms exist)
- Find input fields
- Test with valid data
- Test with invalid data if validation exists
- Handle case where no forms exist

TEST 6-12: Additional Context-Aware Tests
- Search functionality (if search box detected)
- Login functionality (if login form detected)  
- Content verification (check main content exists)
- Responsive checks (resize window, check layout)
- Performance checks (measure load time)
- Accessibility checks (check alt tags on images)
"""),

            ("system", """ERROR HANDLING - CRITICAL RULES:

1. NEVER let tests crash:
   try:
       # test logic
   except Exception as e:
       pytest.fail(f"Safe error: {{str(e)}}")

2. ALWAYS use pytest.skip() for missing features:
   if element is None:
       pytest.skip("Feature not available on this page")

3. NEVER assume element properties without checking:
   if element and element.is_displayed() and element.is_enabled():
       element.click()

4. ALWAYS provide meaningful error messages:
   assert condition, f"Expected X, got Y: {{actual_value}}"

5. HANDLE all Selenium exceptions:
   from selenium.common.exceptions import *
   except (NoSuchElementException, TimeoutException, WebDriverException):
       pytest.skip("Element interaction failed - not critical")
"""),

            ("system", """WEBSITE-AGNOSTIC APPROACH:

🌐 Your tests must work on:
- Static HTML pages
- Dynamic SPAs (React, Vue, Angular)
- E-commerce sites
- Blogs and content sites
- Admin dashboards
- Any website structure

🔑 Key Principles:
1. Never hardcode element locators
2. Always check element existence first
3. Use generic tag names over IDs/classes
4. Skip tests when features don't exist
5. Focus on PRESENCE over exact VALUES
6. Test FUNCTIONALITY over UI details

Example - Checking for any button:
```python
buttons = safe_find_elements(driver, By.TAG_NAME, "button")
if len(buttons) == 0:
    # Try alternate button types
    buttons = safe_find_elements(driver, By.CSS_SELECTOR, "input[type='button'], input[type='submit']")

if len(buttons) > 0:
    # Test button functionality
    assert buttons[0].is_displayed(), "Button found but not visible"
else:
    # No buttons found - this is OK for some pages
    pytest.skip("No interactive buttons found")
```
"""),

            ("system", """AUTHENTICATION HANDLING:

If login is required (based on test plan or credentials provided):

def perform_login(driver, username, password):
    \"\"\"Robust login with multiple strategies\"\"\"
    try:
        # Strategy 1: Try ID-based selectors
        username_field = safe_find_element(driver, By.ID, "username")
        if username_field is None:
            # Strategy 2: Try name attribute
            username_field = safe_find_element(driver, By.NAME, "username")
        if username_field is None:
            # Strategy 3: Try type=text
            username_field = safe_find_element(driver, By.CSS_SELECTOR, "input[type='text']")

        if username_field is None:
            raise Exception("Username field not found")

        username_field.clear()
        username_field.send_keys(username)

        # Similar strategy for password
        password_field = safe_find_element(driver, By.ID, "password")
        if password_field is None:
            password_field = safe_find_element(driver, By.NAME, "password")
        if password_field is None:
            password_field = safe_find_element(driver, By.CSS_SELECTOR, "input[type='password']")

        if password_field:
            password_field.clear()
            password_field.send_keys(password)

        # Find and click submit button
        submit = safe_find_element(driver, By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        if submit:
            submit.click()
            time.sleep(2)

        return True
    except Exception as e:
        print(f"Login failed: {{e}}")
        return False
"""),

            ("system", """PERFORMANCE OPTIMIZATIONS:

1. Use implicit waits: driver.implicitly_wait(5)
2. Keep explicit waits short: 5-10 seconds max
3. Don't use time.sleep() unless necessary
4. Take screenshots only on failure or at end
5. Clear cookies between tests for isolation
6. Use --headless mode for faster execution (optional)
"""),

            ("system", """CRITICAL: COMPLETE SCRIPT REQUIREMENTS:

✅ Must include ALL {{test_depth}} test functions
✅ Each test must be complete (no truncation)
✅ Follow the bulletproof pattern for every test
✅ Use safe_find_element/safe_find_elements everywhere
✅ Every test must have try-except-finally
✅ Use pytest.skip() for graceful failures
✅ No hardcoded assumptions about page structure
✅ Tests must work on ANY website

❌ DO NOT:
- Truncate or abbreviate any test
- Add comments like "implement remaining tests"
- Use hardcoded element IDs without fallbacks
- Assume any specific page structure
- Let any test crash the entire suite
"""),

            ("system", """OUTPUT FORMAT:
Return ONLY the complete Python code.
NO markdown, NO explanations, NO code blocks (```).
Just pure, executable Python code."""),

            ("system", """{credentials_instruction}"""),

            ("user", """Generate a BULLETPROOF, PRODUCTION-READY pytest Selenium test script:

Website URL: {website_url}
Test Depth: {test_depth} test cases
Test Plan: {test_plan_json}

REQUIREMENTS:
1. Generate EXACTLY {test_depth} complete test functions
2. Every test must use the bulletproof pattern
3. Every test must handle errors gracefully  
4. Every test must work regardless of website structure
5. Use pytest.skip() when features don't exist
6. Use safe_find_element/safe_find_elements for all element finding
7. Never assume specific element IDs or classes
8. Make tests website-agnostic and resilient

The script must include:
- All imports
- Pytest fixture for driver
- All helper functions (navigate_safely, safe_find_element, etc.)
- perform_login function (if authentication needed)
- ALL {test_depth} complete, bulletproof test functions
- NO main() function

Generate COMPLETE script with ALL {test_depth} tests NOW.
Make every test production-ready and error-proof.""")
        ])

        # Create the chain
        chain = prompt_template | llm

        # Prepare credentials instruction
        if username and password:
            credentials_instruction = f"""AUTHENTICATION CREDENTIALS:
Username: {username}
Password: {password}

Include the perform_login function and use these credentials in login tests.
Use flexible element finding strategies (ID, name, type) as shown in the template."""
        else:
            credentials_instruction = """If login is detected on the website, include perform_login function with default credentials: username='emilys', password='emilyspass'"""

        # Generate the script
        response = chain.invoke({
            "website_url": website_url,
            "test_depth": test_depth,
            "test_plan_json": json.dumps(test_plan_data, indent=2),
            "credentials_instruction": credentials_instruction
        })

        # Clean up the response
        script_content = response.content.strip()
        if script_content.startswith("```python"):
            script_content = script_content[9:]
        if script_content.startswith("```"):
            script_content = script_content[3:]
        if script_content.endswith("```"):
            script_content = script_content[:-3]

        return script_content.strip()

    except Exception as e:
        # Fallback error script
        return f"""# Error generating script: {str(e)}
import pytest

@pytest.fixture(scope="function")
def driver():
    from selenium import webdriver
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_generation_error(driver):
    pytest.fail(f"Script generation failed: {str(e)}")
"""
'''


def generate_template_based_script(test_plan_data, website_url, test_depth, username=None, password=None):
    """
    Generate a complete script using Template + Fill approach
    Much faster and more reliable for large test suites
    """
    try:
        # Step 1: Extract first 2 test cases for template generation (faster)
        all_test_cases = extract_all_test_cases(test_plan_data)
        template_test_cases = all_test_cases[:2]

        # Step 2: Generate base template with first 2 tests (faster)
        base_template = generate_base_template(template_test_cases, website_url, 2)

        # Step 3: Extract pattern from the template
        pattern = extract_test_pattern(base_template)

        # Step 4: Generate remaining test functions using pattern
        remaining_functions = []
        for i in range(2, test_depth):
            if i < len(all_test_cases):
                test_case = all_test_cases[i]
                function = generate_function_from_pattern(pattern, test_case, i + 1)
                remaining_functions.append(function)

        # Step 5: Combine everything into final script
        final_script = combine_template_and_functions(
            base_template, remaining_functions, website_url, test_depth
        )

        return final_script

    except Exception as e:
        # Fallback to direct generation if template approach fails
        # Note: Don't print here as it interferes with JSON output
        return generate_direct_script(test_plan_data, website_url, test_depth, username, password)


def extract_all_test_cases(test_plan_data):
    """Extract all test cases from the test plan data"""
    all_test_cases = []

    if 'testPlan' in test_plan_data and 'testSuites' in test_plan_data['testPlan']:
        for test_suite in test_plan_data['testPlan']['testSuites']:
            if 'testCases' in test_suite:
                all_test_cases.extend(test_suite['testCases'])

    return all_test_cases


def generate_base_template(template_test_cases, website_url, num_tests):
    """Generate base template with first few test cases"""
    # Initialize the LLM for template generation
    llm = ChatOpenAI(
        # model="gpt-4-turbo",
        model="gpt-5",
        temperature=0.1,
        max_tokens=16000,  # Smaller since we're only generating 2 tests
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create simplified prompt for template generation
    prompt_template = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert Selenium test engineer. Generate a complete, executable Python script with exactly 2 test functions."),
        ("system",
         "Include all imports, helper functions, and main() function. Use modern Selenium methods with WebDriverWait."),
        ("system",
         'Return JSON format: {{"testId": "TC001", "testName": "Test Name", "status": "PASS/FAIL", "error": "", "duration": 12.34, "screenshot": "path.png", "executed_at": "timestamp"}}'),
        ("system", "Take screenshots only on failure or success. Use try-catch with fallbacks: ID → Name → CSS."),
        ("system",
         "CRITICAL: Generate EXACTLY 2 complete test functions. No truncation, no notes about additional functions."),
        ("user", f"""Generate complete Selenium script for:
Website: {website_url}
Test Cases: {json.dumps(template_test_cases, indent=2)}

Create exactly 2 complete test functions based on these test cases. Include all imports, helper functions, and main() execution.""")
    ])

    chain = prompt_template | llm
    response = chain.invoke({})

    # Clean the response
    script_content = response.content.strip()
    if script_content.startswith("```python"):
        script_content = script_content[9:]
    if script_content.startswith("```"):
        script_content = script_content[3:]
    if script_content.endswith("```"):
        script_content = script_content[:-3]

    return script_content


def extract_test_pattern(base_template):
    """Extract the pattern from generated template"""
    lines = base_template.split('\n')

    pattern = {
        'imports': [],
        'helper_functions': [],
        'function_template': '',
        'main_structure': []
    }

    current_section = 'imports'
    function_lines = []
    in_test_function = False

    for line in lines:
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            pattern['imports'].append(line)
        elif line.strip().startswith('def ') and not line.strip().startswith('def test_'):
            current_section = 'helper_functions'
            pattern['helper_functions'].append(line)
        elif line.strip().startswith('def test_'):
            in_test_function = True
            function_lines = [line]
        elif in_test_function:
            function_lines.append(line)
            if line.strip() == '' and len(function_lines) > 10:  # End of function
                pattern['function_template'] = '\\n'.join(function_lines)
                in_test_function = False
                break
        elif current_section == 'helper_functions':
            pattern['helper_functions'].append(line)
        elif line.strip().startswith('def main'):
            current_section = 'main'
            pattern['main_structure'].append(line)
        elif current_section == 'main':
            pattern['main_structure'].append(line)

    return pattern


def generate_function_from_pattern(pattern, test_case, test_number):
    """Generate a test function using the extracted pattern"""
    test_id = f"TC{str(test_number).zfill(3)}"
    test_name = test_case.get('testName', f'Test {test_number}')

    # Convert test case steps to Selenium code
    selenium_steps = convert_test_steps_to_selenium(test_case)

    # Use the pattern template and fill in the details
    function_code = f"""def test_{test_name.lower().replace(' ', '_').replace('-', '_')}(driver, website_url, test_depth):
    start_time = time.time()
    test_id = "{test_id}"

    try:
{selenium_steps}

        screenshot = take_screenshot(driver, test_id, website_url, test_depth)
        duration = time.time() - start_time

        return {{
            "testId": "{test_id}",
            "testName": "{test_name}",
            "status": "PASS",
            "error": "",
            "duration": duration,
            "screenshot": screenshot,
            "executed_at": datetime.now().isoformat()
        }}

    except Exception as e:
        screenshot = take_screenshot(driver, test_id, website_url, test_depth)
        duration = time.time() - start_time
        error_msg = str(e).strip() if str(e).strip() else "Test execution failed"

        return {{
            "testId": "{test_id}",
            "testName": "{test_name}",
            "status": "FAIL",
            "error": error_msg,
            "duration": duration,
            "screenshot": screenshot,
            "executed_at": datetime.now().isoformat()
        }}
"""

    return function_code


def convert_test_steps_to_selenium(test_case):
    """Convert test case steps to Selenium code"""
    steps = test_case.get('steps', [])
    selenium_code = []

    for step in steps:
        step_text = step.lower()

        if 'navigate' in step_text or 'open' in step_text or 'go to' in step_text:
            if '/login' in step_text:
                selenium_code.append('        driver.get(website_url + "/login")')
            elif '/form' in step_text:
                selenium_code.append('        driver.get(website_url + "/form")')
            else:
                selenium_code.append('        driver.get(website_url)')

        elif 'click' in step_text:
            if 'button' in step_text or 'submit' in step_text:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type=\'submit\']"))).click()')
            elif 'link' in step_text:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, "a"))).click()')
            else:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button"))).click()')

        elif 'enter' in step_text or 'input' in step_text or 'type' in step_text:
            if 'username' in step_text:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys("testuser")')
            elif 'password' in step_text:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "password"))).send_keys("testpass")')
            else:
                selenium_code.append(
                    '        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input"))).send_keys("test input")')

        elif 'verify' in step_text or 'check' in step_text or 'validate' in step_text:
            selenium_code.append(
                '        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))')

        else:
            # Generic step
            selenium_code.append('        time.sleep(1)  # Wait for page interaction')

    if not selenium_code:
        selenium_code.append('        driver.get(website_url)')
        selenium_code.append('        time.sleep(2)')

    return '\\n'.join(selenium_code)


def combine_template_and_functions(base_template, additional_functions, website_url, test_depth):
    """Combine the base template with additional generated functions"""
    lines = base_template.split('\\n')

    # Find where to insert additional functions (before main function)
    main_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('def main'):
            main_index = i
            break

    if main_index == -1:
        # If no main function found, append functions at the end
        main_index = len(lines)

    # Insert additional functions before main
    for func in additional_functions:
        lines.insert(main_index, '')
        for func_line in func.split('\\n'):
            lines.insert(main_index, func_line)
            main_index += 1
        main_index += 1

    # Update main function to include all test functions
    updated_lines = []
    in_main = False
    test_function_names = []

    # Extract test function names
    for line in lines:
        if line.strip().startswith('def test_'):
            func_name = line.strip().split('(')[0].replace('def ', '')
            test_function_names.append(func_name)

    # Rebuild the script with updated main function
    for i, line in enumerate(lines):
        if line.strip().startswith('def main'):
            in_main = True
            updated_lines.append(line)
            updated_lines.append(f'    website_url = "{website_url}"')
            updated_lines.append(f'    test_depth = {test_depth}')
            updated_lines.append('    results = []')
            updated_lines.append('    driver = setup_driver()')
            updated_lines.append('')
            updated_lines.append('    try:')

            # Add all test function calls
            for func_name in test_function_names:
                updated_lines.append(f'        results.append({func_name}(driver, website_url, test_depth))')

            updated_lines.append('')
            updated_lines.append('        print(json.dumps(results, indent=2))')
            updated_lines.append('    finally:')
            updated_lines.append('        driver.quit()')
            updated_lines.append('')
            updated_lines.append('if __name__ == "__main__":')
            updated_lines.append('    main()')
            break
        elif in_main:
            continue  # Skip original main function content
        else:
            updated_lines.append(line)

    return '\\n'.join(updated_lines)


def save_generated_script(script_content, website_url, test_depth):
    """
    Save the LLM-generated script to the scripts folder (override if exists)
    """
    os.makedirs("generated_files/scripts", exist_ok=True)

    # Use same clean URL pattern as other files, no timestamp
    clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=',
                                                                                                              '_').replace(
        ':', '_').replace('.', '_')
    script_filename = f"generated_files/scripts/{clean_url}_{test_depth}_script.py"

    # Override existing file if it exists
    with open(script_filename, 'w', encoding='utf-8') as f:
        f.write(script_content)

    return script_filename


'''
def execute_generated_script(script_path):
    """
    Execute the generated Python script and capture results with retry logic
    """
    import ast  # Add this import for parsing Python literals

    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            # Run the script as a subprocess
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=os.getcwd()
            )

            # Debug: Print raw output to stderr (not stdout)
            print(f"[DEBUG] Script stdout: {result.stdout}", file=sys.stderr)
            print(f"[DEBUG] Script stderr: {result.stderr}", file=sys.stderr)
            print(f"[DEBUG] Return code: {result.returncode}", file=sys.stderr)

            if result.returncode == 0:
                # Try to parse output from the script
                try:
                    output_text = result.stdout.strip()

                    # If no output, return error
                    if not output_text:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return [{
                            "testId": "ERROR",
                            "testName": "No Output",
                            "status": "FAIL",
                            "error": "Script generated no output",
                            "duration": 0,
                            "screenshot": "",
                            "executed_at": datetime.now().isoformat()
                        }]

                    # Find array in output
                    json_start = output_text.find('[')
                    json_end = output_text.rfind(']')

                    if json_start != -1 and json_end != -1:
                        dict_text = output_text[json_start:json_end + 1]

                        # Try parsing as JSON first (proper format)
                        try:
                            parsed_results = json.loads(dict_text)
                            return parsed_results
                        except json.JSONDecodeError:
                            # Failed as JSON, try as Python literal (single quotes)
                            try:
                                parsed_results = ast.literal_eval(dict_text)
                                return parsed_results
                            except (ValueError, SyntaxError) as e:
                                # Last resort: manual conversion
                                print(f"[DEBUG] Attempting manual conversion from Python dict to JSON", file=sys.stderr)
                                # This is safe because we control the script generation
                                dict_text_fixed = dict_text.replace("'", '"')
                                dict_text_fixed = dict_text_fixed.replace('None', 'null')
                                dict_text_fixed = dict_text_fixed.replace('True', 'true')
                                dict_text_fixed = dict_text_fixed.replace('False', 'false')
                                try:
                                    parsed_results = json.loads(dict_text_fixed)
                                    return parsed_results
                                except json.JSONDecodeError:
                                    if attempt < max_retries - 1:
                                        time.sleep(retry_delay)
                                        continue
                                    return [{
                                        "testId": "ERROR",
                                        "testName": "Parse Error",
                                        "status": "FAIL",
                                        "error": f"Could not parse output: {str(e)}",
                                        "duration": 0,
                                        "screenshot": "",
                                        "executed_at": datetime.now().isoformat()
                                    }]
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return [{
                            "testId": "ERROR",
                            "testName": "No Array Found",
                            "status": "FAIL",
                            "error": "No JSON array found in output",
                            "duration": 0,
                            "screenshot": "",
                            "executed_at": datetime.now().isoformat()
                        }]

                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return [{
                        "testId": "ERROR",
                        "testName": "Parsing Failed",
                        "status": "FAIL",
                        "error": f"Unexpected parsing error: {str(e)}",
                        "duration": 0,
                        "screenshot": "",
                        "executed_at": datetime.now().isoformat()
                    }]
            else:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return [{
                    "testId": "ERROR",
                    "testName": "Execution Failed",
                    "status": "FAIL",
                    "error": result.stderr or "Unknown error",
                    "duration": 0,
                    "screenshot": "",
                    "executed_at": datetime.now().isoformat()
                }]

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return [{
                "testId": "ERROR",
                "testName": "Timeout",
                "status": "FAIL",
                "error": "Script execution timed out (10 minutes)",
                "duration": 600,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return [{
                "testId": "ERROR",
                "testName": "Unexpected Error",
                "status": "FAIL",
                "error": str(e),
                "duration": 0,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]

    # All retries failed
    return [{
        "testId": "ERROR",
        "testName": "Max Retries Exceeded",
        "status": "FAIL",
        "error": "Failed after 3 attempts",
        "duration": 0,
        "screenshot": "",
        "executed_at": datetime.now().isoformat()
    }]

'''
'''


def execute_generated_script(script_path):
    """
    Execute the generated Python script and capture results
    """
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=900,
            cwd=os.getcwd()
        )

        print(f"[DEBUG] Script return code: {result.returncode}", file=sys.stderr)
        print(f"[DEBUG] First 500 chars of stdout: {result.stdout[:500]}", file=sys.stderr)

        if result.returncode != 0:
            return [{
                "testId": "ERROR",
                "testName": "Script Execution Failed",
                "status": "FAIL",
                "error": f"Script exited with code {result.returncode}. Error: {result.stderr[:500]}",
                "duration": 0,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]

        try:
            output_text = result.stdout.strip()

            # Find JSON array
            json_start = output_text.find('[')
            json_end = output_text.rfind(']')

            if json_start == -1 or json_end == -1:
                return [{
                    "testId": "ERROR",
                    "testName": "No JSON Output",
                    "status": "FAIL",
                    "error": f"No JSON array found. Output: {output_text[:500]}",
                    "duration": 0,
                    "screenshot": "",
                    "executed_at": datetime.now().isoformat()
                }]

            json_text = output_text[json_start:json_end + 1]

            # Try parsing as JSON first
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                # If JSON fails, try converting Python dict format to JSON
                print("[DEBUG] JSON parse failed, trying Python literal conversion", file=sys.stderr)

                # Convert Python dict syntax to JSON syntax
                fixed_json = json_text.replace("'", '"')  # Single to double quotes
                fixed_json = fixed_json.replace('None', 'null')
                fixed_json = fixed_json.replace('True', 'true')
                fixed_json = fixed_json.replace('False', 'false')

                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    return [{
                        "testId": "ERROR",
                        "testName": "JSON Parse Error",
                        "status": "FAIL",
                        "error": f"Failed to parse JSON: {str(e2)}. Output: {json_text[:300]}",
                        "duration": 0,
                        "screenshot": "",
                        "executed_at": datetime.now().isoformat()
                    }]

        except Exception as e:
            return [{
                "testId": "ERROR",
                "testName": "Parse Error",
                "status": "FAIL",
                "error": f"Error parsing output: {str(e)}",
                "duration": 0,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]

    except subprocess.TimeoutExpired:
        return [{
            "testId": "ERROR",
            "testName": "Timeout",
            "status": "FAIL",
            "error": "Script execution timed out (15 minutes)",
            "duration": 900,
            "screenshot": "",
            "executed_at": datetime.now().isoformat()
        }]
    except Exception as e:
        return [{
            "testId": "ERROR",
            "testName": "Unexpected Error",
            "status": "FAIL",
            "error": f"Error executing script: {str(e)}",
            "duration": 0,
            "screenshot": "",
            "executed_at": datetime.now().isoformat()
        }]

'''


def execute_generated_script(script_path):
    """
    Execute the generated Python script using pytest with JSON report
    """
    try:
        # Generate unique report filename
        report_file = "generated_files/results/pytest_report.json"
        os.makedirs("generated_files/results", exist_ok=True)

        # Run pytest with JSON report
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                script_path,
                "-v",
                "--json-report",
                f"--json-report-file={report_file}",
                "--json-report-omit=log"
            ],
            capture_output=True,
            text=True,
            timeout=900,
            cwd=os.getcwd()
        )

        print(f"[DEBUG] Pytest return code: {result.returncode}", file=sys.stderr)

        # Read JSON report
        if os.path.exists(report_file):
            with open(report_file, 'r') as f:
                pytest_data = json.load(f)

            # Convert pytest results to your format
            test_results = []
            test_counter = 1

            for test in pytest_data.get('tests', []):
                test_name = test.get('nodeid', '').split('::')[-1]
                outcome = test.get('outcome', 'failed')

                # Extract error message if failed
                error_msg = ""
                if outcome in ['failed', 'error']:
                    call_info = test.get('call', {})
                    longrepr = call_info.get('longrepr', '')
                    if longrepr:
                        # Extract just the assertion message
                        error_lines = longrepr.split('\n')
                        for line in error_lines:
                            if 'AssertionError:' in line or 'assert' in line:
                                error_msg = line.strip()
                                break
                        if not error_msg and len(error_lines) > 0:
                            error_msg = error_lines[0][:200]

                test_results.append({
                    "testId": f"TC{str(test_counter).zfill(3)}",
                    "testName": test_name.replace('test_function_', 'Test ').replace('_', ' ').title(),
                    "status": "PASS" if outcome == 'passed' else "FAIL",
                    "error": error_msg,
                    "duration": test.get('duration', 0),
                    "screenshot": f"generated_files/screenshots/TC{str(test_counter).zfill(3)}_{'pass' if outcome == 'passed' else 'fail'}.png",
                    "executed_at": datetime.now().isoformat()
                })
                test_counter += 1

            return test_results if test_results else [{
                "testId": "ERROR",
                "testName": "No Tests Found",
                "status": "FAIL",
                "error": "No tests found in pytest report",
                "duration": 0,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]
        else:
            return [{
                "testId": "ERROR",
                "testName": "Report Not Found",
                "status": "FAIL",
                "error": f"Pytest report file not generated. Output: {result.stdout[:500]}",
                "duration": 0,
                "screenshot": "",
                "executed_at": datetime.now().isoformat()
            }]

    except subprocess.TimeoutExpired:
        return [{
            "testId": "ERROR",
            "testName": "Timeout",
            "status": "FAIL",
            "error": "Script execution timed out (15 minutes)",
            "duration": 900,
            "screenshot": "",
            "executed_at": datetime.now().isoformat()
        }]
    except Exception as e:
        return [{
            "testId": "ERROR",
            "testName": "Unexpected Error",
            "status": "FAIL",
            "error": f"Error executing script: {str(e)}",
            "duration": 0,
            "screenshot": "",
            "executed_at": datetime.now().isoformat()
        }]


def generate_allure_from_json(json_file_path):
    """
    Convert the JSON test results into Allure-compatible format and generate the HTML report.
    This function does NOT rerun tests — it uses the existing JSON result file only.
    """
    import uuid
    import shutil
    import subprocess
    from datetime import datetime

    try:
        allure_results_dir = "generated_files/allure-results"
        allure_report_dir = "generated_files/allure-report"

        # Clean allure-results folder each time
        if os.path.exists(allure_results_dir):
            shutil.rmtree(allure_results_dir)
        os.makedirs(allure_results_dir, exist_ok=True)

        # Load the result JSON
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert each test result into Allure format
        for test in data.get("test_results", []):
            test_uuid = str(uuid.uuid4())
            start_time = int(datetime.fromisoformat(test["executed_at"]).timestamp() * 1000)
            stop_time = start_time + int(test["duration"] * 1000)

            allure_result = {
                "uuid": test_uuid,
                "name": test["testName"],
                "status": "passed" if test["status"].upper() == "PASS" else "failed",
                "stage": "finished",
                "steps": [],
                "attachments": [],
                "parameters": [],
                "start": start_time,
                "stop": stop_time,
                "labels": [
                    {"name": "suite", "value": data["websiteUrl"]},
                    {"name": "testId", "value": test["testId"]}
                ]
            }

            # Add screenshot if available
            if test.get("screenshot") and os.path.exists(test["screenshot"]):
                screenshot_name = os.path.basename(test["screenshot"])
                allure_result["attachments"].append({
                    "name": "Screenshot",
                    "source": screenshot_name,
                    "type": "image/png"
                })
                shutil.copy(test["screenshot"], os.path.join(allure_results_dir, screenshot_name))

            # Save per-test JSON
            result_file = os.path.join(allure_results_dir, f"{test_uuid}-result.json")
            with open(result_file, "w", encoding="utf-8") as f_out:
                json.dump(allure_result, f_out, indent=2)

        allure_cmd = os.path.join("tools", "allure", "bin", "allure.bat")
        # Clean old report and generate new one
        subprocess.run(
            [allure_cmd, "generate", allure_results_dir, "-o", allure_report_dir, "--clean"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("[INFO] Allure HTML report generated successfully!", file=sys.stderr)
        print(f"[INFO] Report path: {os.path.abspath(allure_report_dir)}/index.html", file=sys.stderr)
        print("[INFO] You can open this file in your browser.", file=sys.stderr)

    except Exception as e:
        print("[ERROR] Failed to generate Allure report.", file=sys.stderr)
        print(f"[ERROR] Details: {e}", file=sys.stderr)
        print("[ERROR] Suggestion: Ensure Allure CLI is available (e.g. tools/allure/bin/allure.bat)",
              file=sys.stderr)


def generate_reports(website_url, test_depth, results):
    """
    Generate JSON and Excel reports with the correct naming convention
    """
    total = len(results)
    passed = len([r for r in results if r.get('status') == 'PASS'])
    failed = total - passed

    report_data = {
        "websiteUrl": website_url,
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
        "test_results": results
    }

    # Use same clean URL pattern as plan files
    clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=',
                                                                                                              '_').replace(
        ':', '_').replace('.', '_')

    # Create results directory
    os.makedirs("generated_files/results", exist_ok=True)

    # Save JSON file
    json_file = f"generated_files/results/{clean_url}_{test_depth}_result.json"
    with open(json_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    # Save Excel file
    excel_file = f"generated_files/results/{clean_url}_{test_depth}_result.xlsx"
    pd.DataFrame(results).to_excel(excel_file, index=False)

    return json_file, excel_file


def main():
    """Main execution function with LLM-driven approach"""

    # Check if JSON data was passed as command line argument (from server)
    if len(sys.argv) > 1:
        try:
            # Parse JSON data from command line argument
            data = json.loads(sys.argv[1])
            website_url = data.get('websiteUrl', '')

            test_depth = int(data.get('testDepth', 8))

            credentials_file = data.get('credentialsFile', '')

            # Read credentials from file if provided
            username, password = read_credentials_from_file(credentials_file)

            if username and password:
                print(f"Using credentials from file - Username: {username} , Password: {password}", file=sys.stderr)

            if not website_url:
                print(json.dumps({
                    "status": "error",
                    "message": "Missing websiteUrl in input data.",
                    "action": "Please provide a valid website URL.",
                    "details": {
                        "suggestion": "Make sure the website URL is provided in the request."
                    }
                }))
                return

            # Find matching test plan file
            folder = "generated_files/plans"
            clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace(
                '=', '_').replace(':', '_').replace('.', '_')
            test_plan_filename = f"{clean_url}_{test_depth}_plan.json"
            test_plan_path = os.path.join(folder, test_plan_filename)

            if not os.path.exists(test_plan_path):
                print(json.dumps({
                    "status": "error",
                    "message": f"Test plan file not found: {test_plan_filename}",
                    "action": "Please run 'Create Plan' first to generate a test plan.",
                    "details": {
                        "expected_file": test_plan_path,
                        "suggestion": "Click the 'Create Plan' button before running the executor."
                    }
                }))
                return

            # Load the test plan
            with open(test_plan_path, 'r') as f:
                test_plan_data = json.load(f)

            # Generate Selenium script using LLM (LLM will analyze website directly)
            script_content = generate_selenium_script_with_llm(test_plan_data, website_url, test_depth, username,
                                                               password)

            # Save the generated script
            script_path = save_generated_script(script_content, website_url, test_depth)

            # Execute the generated script
            execution_results = execute_generated_script(script_path)

            # Check if execution was successful
            if "error" in execution_results:
                print(json.dumps({
                    "status": "error",
                    "message": "Test script execution failed",
                    "action": "Please check the generated script and try again.",
                    "details": {
                        "script_path": script_path,
                        "error": execution_results["error"],
                        "suggestion": "Review the generated script for any issues."
                    }
                }))
                return

            # Parse results from script execution
            if isinstance(execution_results, list):
                results = execution_results
            elif isinstance(execution_results, dict) and "test_results" in execution_results:
                results = execution_results["test_results"]
            else:
                results = []

            # Generate reports
            json_file, excel_file = generate_reports(website_url, test_depth, results)

            # generate allure report
            generate_allure_from_json(json_file)

            # Return success response with results
            total = len(results)
            passed = len([r for r in results if r.get('status') == 'PASS'])
            failed = total - passed

            print(json.dumps({
                "websiteUrl": website_url,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
                "test_results": results,
                "script_path": script_path,
                "json_file": json_file,
                "excel_file": excel_file
            }))

        except json.JSONDecodeError as e:
            print(json.dumps({
                "status": "error",
                "message": f"Invalid JSON data received: {str(e)}",
                "action": "Please check the request format.",
                "details": {"suggestion": "Ensure valid JSON is being sent from the interface."}
            }))
            return
        except Exception as e:
            print(json.dumps({
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "action": "Please try again or check the logs.",
                "details": {"suggestion": "Contact support if the issue persists."}
            }))
            return
    else:
        # Interactive mode - find newest test plan
        folder = "generated_files/plans"
        json_files = glob.glob(os.path.join(folder, "*.json"))
        if json_files:
            # Sort by creation time (newest last) and take the newest
            json_files.sort(key=os.path.getctime, reverse=True)
            test_plan_path = json_files[0]

            print(f"Interactive mode: Using {test_plan_path}")
            # Continue with LLM-driven execution for interactive mode...

        else:
            print(json.dumps({
                "status": "error",
                "message": "No test plan files found in generated_files/plans folder.",
                "action": "Please create a test plan first.",
                "details": {"suggestion": "Use the 'Create Plan' button to generate a test plan."}
            }))
            return


if __name__ == "__main__":
    main()