import os
from dotenv import load_dotenv
import glob
import json

load_dotenv('properties.env')

#function to take the client choice(jira/trello from the html), and run the chosen project manager
#PM_TOOL = project manager tool = jira / trello
def run_pm_integration(results_json, test_plan_json):
    # Read the test plan JSON file
    with open(test_plan_json, 'r', encoding='utf-8') as file:
        test_plan_data = json.load(file)

    #extracting the pmTool
    pm_tool = test_plan_data.get('pmTool')

    if pm_tool == 'jira':
        from jira_notifier import run_jira_integration
        return run_jira_integration(results_json, test_plan_json)
    elif pm_tool == 'trello':
        from trello_notifier import run_trello_integration
        return run_trello_integration(results_json, test_plan_json)
    else:
        print(f"PM tool: {pm_tool}, skipped: No PM tool selected.")
        return False








def main():

    # Find newest .json file in generated_files/plans folder
    plans_folder = "generated_files/plans"
    json_files = glob.glob(os.path.join(plans_folder, "*.json"))

    if json_files:
        # Sort by creation time (newest last) and take the newest
        json_files.sort(key=os.path.getctime, reverse=True)
        plan_file = json_files[0]
        print(f"Using latest test plan: {plan_file}")

        #after finding the plan file, checking for the result file...
        # Find newest .json file in generated_files/results folder
        results_folder = "generated_files/results"
        json_files = glob.glob(os.path.join(results_folder, "*.json"))
        if json_files:
            # Sort by creation time (newest last) and take the newest
            json_files.sort(key=os.path.getctime, reverse=True)
            result_file = json_files[0]
            print(f"Using latest result file: {result_file}")

            #both files are found
            run_pm_integration(result_file, plan_file)
        else:
            print("No JSON files found in generated_files/results folder.")
            return

    else:
        print("No JSON files found in generated_files/plans folder.")
        return



if __name__ == "__main__":
    main()