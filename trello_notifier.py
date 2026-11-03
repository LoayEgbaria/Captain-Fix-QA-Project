# trello_notifier.py
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import glob
import requests

# Load environment variables
load_dotenv('properties.env')


class TrelloNotifier:
    def __init__(self):
        """Initialize Trello connection from properties.env"""
        self.api_key = os.getenv('TRELLO_API_KEY')
        self.token = os.getenv('TRELLO_TOKEN')
        self.board_id = os.getenv('TRELLO_BOARD_ID')
        self.base_url = "https://api.trello.com/1"

    def connect(self):
        """Test Trello connection"""
        try:
            url = f"{self.base_url}/boards/{self.board_id}"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            response = requests.get(url, params=params)

            #if response.status_code == 200:
            if response.status_code in (200, 201):

                print("Connected to Trello")
                return True
            else:
                print(f"Trello connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"Trello connection failed: {e}")
            return False


    def check_project_exists(self):
        """Check if the Trello board (project) exists, otherwise show error with fix instructions"""
        try:
            url = f"{self.base_url}/boards/{self.board_id}"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            response = requests.get(url, params=params)

            if response.status_code in (200, 201):
                return True
            else:
                print("\n### ERROR: Trello project not found or invalid Board ID.\n")
                print("Please create the board manually:")
                print("1. Go to Trello (https://trello.com/) and log in.")
                print("2. Create a new board (e.g., 'QA Captain Fix').")
                print("3. Open the board and copy its ID from the URL:")
                print("   Example: https://trello.com/b/<BOARD_ID>/board-name")
                print("   Here, <BOARD_ID> is what you need.")
                print("4. Update your `properties.env` file with:")
                print("   TRELLO_BOARD_ID=<BOARD_ID>")
                print("5. Re-run this script after saving the file.\n")
                return False
        except Exception as e:
            print(f"Error checking project existence: {e}")
            return False


    def process_test_results(self, results_json_path, test_plan_json_path):
        """Main method to process results and create Trello cards"""

        # Load results and test plan
        with open(results_json_path, 'r') as f:
            results_data = json.load(f)

        with open(test_plan_json_path, 'r') as f:
            plan_data = json.load(f)

        # Store test plan for use in other methods
        self.test_plan = plan_data.get('testPlan', plan_data)

        #check if project exists
        if not self.check_project_exists():
            return False

        #test connection
        if not self.connect():
            return False

        # Create main test execution card
        main_card = self.create_test_execution_card(results_data, self.test_plan)

        # Create cards for failed tests only
        failed_tests = [test for test in results_data['test_results'] if test['status'] == 'FAIL']

        if not failed_tests:
            print("No failed tests - no Trello cards needed")
            return True

        print(f"Creating {len(failed_tests)} Trello cards for failed tests...")

        created_cards = []
        for failed_test in failed_tests:
            card = self.create_failed_test_card(failed_test, results_data['websiteUrl'])
            if card:
                created_cards.append({
                    'test_id': failed_test['testId'],
                    'card_id': card['id'],
                    'card_url': card['url']
                })

        # Save Trello integration results
        self.save_trello_results(main_card, created_cards)

        print(f"Created {len(created_cards)} Trello cards")
        return True

    def create_test_execution_card(self, results_data, test_plan):
        """Create main card for test execution overview"""
        try:
            website = results_data['websiteUrl']
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

            # Get failed tests details for overview
            failed_tests = [test for test in results_data['test_results'] if test['status'] == 'FAIL']
            failed_summary = []
            if failed_tests:
                for failed_test in failed_tests:
                    failed_summary.append(f"- {failed_test['testId']}: {failed_test['testName']}")

            # Card name
            status_indicator = "FAILED" if results_data['failed'] > 0 else "PASSED"
            card_name = f"[{status_indicator}] QA Test Execution: {test_plan.get('websiteAnalysis', {}).get('title', 'Website')} - {datetime.now().strftime('%Y-%m-%d')}"

            # Card description
            description = f"""
AUTOMATED QA TEST EXECUTION REPORT
==================================================

WEBSITE INFORMATION:
- URL: {website}
- Title: {test_plan.get('websiteAnalysis', {}).get('title', 'N/A')}
- Description: {test_plan.get('websiteAnalysis', {}).get('description', 'N/A')}
- Execution Time: {timestamp}
- Test Depth Level: {test_plan.get('testDepth')}

RESULTS SUMMARY:
- Total Tests: {results_data['total_tests']}
- Passed: {results_data['passed']} 
- Failed: {results_data['failed']}
- Pass Rate: {results_data['pass_rate']}

FAILED TESTS:
{chr(10).join(failed_summary) if failed_summary else 'No failed tests - All tests passed!'}

TEST SUITES:
{self.format_test_suites(test_plan)}


This card was automatically created by QA Captain.
For questions or issues, please review the individual test case ticket.
            """.strip()

            # Get first list (To Do)
            lists = self.get_board_lists()
            if not lists:
                print("No lists found on board")
                return None

            list_id = lists[0]['id']

            # Create card
            card = self.create_card(card_name, list_id, description)

            if card:
                print(f"Created Trello execution card: {card['name']}")

            return card

        except Exception as e:
            print(f"Failed to create Trello execution card: {e}")
            return None

    def create_failed_test_card(self, failed_test, website_url):
        """Create Trello card for failed test"""
        try:
            # Find test case details from plan
            test_case_details = {}
            try:
                for suite in self.test_plan.get('testSuites', []):
                    for test_case in suite['testCases']:
                        if test_case['testId'] == failed_test['testId']:
                            test_case_details = test_case.copy()
                            test_case_details['suiteName'] = suite['suiteName']
                            test_case_details['suiteType'] = suite['suiteType']
                            break
            except:
                test_case_details = {}

            # Extract details
            expected_result = test_case_details.get('expectedResult', 'Not specified')
            test_description = test_case_details.get('description', 'No description available')
            test_steps = test_case_details.get('steps', [])
            test_priority = test_case_details.get('priority', 'medium')
            suite_name = test_case_details.get('suiteName')
            suite_type = test_case_details.get('suiteType')

            # Format test steps
            formatted_steps = []
            for i, step in enumerate(test_steps, 1):
                formatted_steps.append(f"{i}. {step}")

            # Determine severity
            error_lower = failed_test['error'].lower()
            if any(keyword in error_lower for keyword in ['timeout', 'not found', 'no such element']):
                severity = 'HIGH'
            elif any(keyword in error_lower for keyword in ['failed at step', 'navigation', 'click']):
                severity = 'MEDIUM'
            elif any(keyword in error_lower for keyword in ['warning', 'minor']):
                severity = 'LOW'
            else:
                severity = 'MEDIUM'

            # Classify error type
            if 'timeout' in error_lower:
                error_type = 'Timeout Error'
            elif 'no such element' in error_lower or 'not found' in error_lower:
                error_type = 'Element Not Found'
            elif 'navigation' in error_lower or 'page' in error_lower:
                error_type = 'Navigation/Page Load Error'
            elif 'click' in error_lower:
                error_type = 'Interaction Error'
            elif 'step' in error_lower:
                error_type = 'Test Step Execution Error'
            else:
                error_type = 'General Test Execution Error'

            # Suggest likely cause
            if 'navigation' in error_lower or 'page' in error_lower:
                likely_cause = 'Page may not be loading correctly or URL is incorrect'
            elif 'not found' in error_lower or 'no such element' in error_lower:
                likely_cause = 'Web element may have changed or page structure modified'
            elif 'timeout' in error_lower:
                likely_cause = 'Page loading too slowly or element not appearing in time'
            elif 'click' in error_lower:
                likely_cause = 'Element may not be clickable or obscured by other elements'
            else:
                likely_cause = 'Test logic may need review or website functionality changed'

            # Card name
            priority_indicator = test_priority.upper()[:1]  # H, M, L
            card_name = f"[{priority_indicator}] [{severity}] Test Failure: {failed_test['testName']} - {failed_test['testId']}"

            # Card description
            description = f"""
TEST FAILURE REPORT
==================

BASIC INFORMATION:
- Test ID: {failed_test['testId']}
- Test Name: {failed_test['testName']}
- Test Suite: {suite_name} ({suite_type})
- Priority Level: {test_priority.upper()}
- Failure Severity: {severity}

EXECUTION DETAILS:
- Website: {website_url}
- Execution Time: {failed_test['executed_at']}
- Test Duration: {failed_test.get('duration', 0):.2f} seconds

TEST DESCRIPTION:
{test_description}

EXPECTED RESULT:
{expected_result}

ACTUAL ERROR:
{failed_test.get('error', 'No error message available')}

REPRODUCTION STEPS:
{chr(10).join(formatted_steps) if formatted_steps else 'Steps not available'}

FAILURE ANALYSIS:
- Error Type: {error_type}
- Likely Cause: {likely_cause}
- Impact: This failure prevents the test case from completing successfully

EVIDENCE:
- Screenshot: {failed_test.get('screenshot', 'Not available')}

RECOMMENDED ACTIONS:
1. Review the error message and screenshot
2. Verify the website/page is accessible
3. Check if the expected elements exist on the page
4. Test manually to reproduce the issue
5. Fix the underlying issue
6. Re-run the automated test to verify the fix

This card was automatically created by QA Captain Fix Team.
Please investigate and resolve this test failure promptly.
            """.strip()

            # Get first list (To Do)
            lists = self.get_board_lists()
            if not lists:
                return None

            list_id = lists[0]['id']

            # Create card
            card = self.create_card(card_name, list_id, description)

            if card:
                print(f"Created Trello failure card: {card['name']}")

            return card

        except Exception as e:
            print(f"Failed to create Trello card for {failed_test['testId']}: {e}")
            return None

    def get_board_lists(self):
        """Get all lists from the board"""
        try:
            url = f"{self.base_url}/boards/{self.board_id}/lists"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            response = requests.get(url, params=params)

            #if response.status_code == 200:
            if response.status_code in (200, 201):
                return response.json()
            else:
                print(f"Failed to get board lists: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting board lists: {e}")
            return []

    def create_card(self, name, list_id, description):
        """Create a card in specified list"""
        try:
            url = f"{self.base_url}/cards"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idList': list_id,
                'name': name,
                'desc': description
            }
            response = requests.post(url, params=params)

            #if response.status_code == 200:
            if response.status_code in (200, 201):
                return response.json()
            else:
                print(f"Failed to create card: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error creating card: {e}")
            return None

    def format_test_suites(self, test_plan):
        """Format test suites for display"""
        suites = []
        for suite in test_plan.get('testSuites', []):
            suites.append(
                f"- {suite['suiteName']} ({suite['suiteType']}) - Priority: {suite['priority']} - {len(suite['testCases'])} test cases")
        return '\n'.join(suites) if suites else 'No test suites found'


    # saving the trello results : in case we need it
    def save_trello_results(self, main_card, created_cards):
        """Save Trello integration results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trello_results = {
            'integration_timestamp': timestamp,
            'main_card': {
                'id': main_card['id'] if main_card else None,
                'name': main_card['name'] if main_card else None,
                'url': main_card['url'] if main_card else None
            },
            'failed_test_cards': created_cards,
            'summary': {
                'total_cards_created': len(created_cards),
                'main_card_created': main_card is not None
            }
        }

        os.makedirs('generated_files/Trello', exist_ok=True)
        results_file = f"generated_files/Trello/trello_integration_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(trello_results, f, indent=2)

        print(f"Trello integration results saved: {results_file}")


def run_trello_integration(results_json, test_plan_json):
    """Main function to run Trello integration"""
    print("Starting Trello Integration...")

    # Check if files exist
    if not os.path.exists(results_json):
        print(f"Results file not found: {results_json}")
        return False

    if not os.path.exists(test_plan_json):
        print(f"Test plan file not found: {test_plan_json}")
        return False

    # Run the integration
    notifier = TrelloNotifier()
    success = notifier.process_test_results(results_json, test_plan_json)

    if success:
        print("Trello integration completed successfully!")
    else:
        print("Trello integration failed!")

    return success


def main():
    # Find newest .json file in generated_files/plans folder
    plans_folder = "generated_files/plans"
    json_files = glob.glob(os.path.join(plans_folder, "*.json"))

    if json_files:
        # Sort by creation time (newest last) and take the newest
        json_files.sort(key=os.path.getctime, reverse=True)
        plan_file = json_files[0]
        print(f"Using latest test plan: {plan_file}")

        # Find newest .json file in generated_files/results folder
        results_folder = "generated_files/results"
        json_files = glob.glob(os.path.join(results_folder, "*.json"))
        if json_files:
            json_files.sort(key=os.path.getctime, reverse=True)
            result_file = json_files[0]
            print(f"Using latest result file: {result_file}")

            # Run Trello integration
            run_trello_integration(result_file, plan_file)
        else:
            print("No JSON files found in generated_files/results folder.")
            return
    else:
        print("No JSON files found in generated_files/plans folder.")
        return


if __name__ == "__main__":
    main()