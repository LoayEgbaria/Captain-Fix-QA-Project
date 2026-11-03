import json
import uuid
import zipfile
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
#script to create the report for the test execution
import shutil

load_dotenv('properties.env')

    
''' 
def create_zip_folder(base_filename, folder_path="generated_files"):
    # Create reports folder if it doesn't exist
    reports_folder = f"{folder_path}/reports"
    if not os.path.exists(reports_folder):
        os.makedirs(reports_folder)
    
    # Generate unique name for the zip folder with new naming convention
    zip_filename = f"{reports_folder}/CaptinAiReport_{base_filename}.zip"
    
    # Expected files with their subfolder paths (excluding MD file)
    expected_files = [
        {
            "file": f"{base_filename}_plan.xlsx",
            "path": f"{folder_path}/plans/{base_filename}_plan.xlsx"
        },
        {
            "file": f"{base_filename}_result.xlsx", 
            "path": f"{folder_path}/results/{base_filename}_result.xlsx"
        },
        {
            "file": f"{base_filename}_summary.html",
            "path": f"{folder_path}/summaries_files/{base_filename}_summary.html"
        }
    ]
    
    # Create the zip folder 
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in expected_files:
            file_path = item["path"]
            arcname = item["file"]
            
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=arcname)
                print(f"Added to zip: {arcname}")
            else:
                print(f"WARNING: Skipping missing file: {file_path}")
                print(f"  Expected at: {os.path.abspath(file_path)}")


                # Add Allure report folder if it exists
                allure_report_path = f"{folder_path}/allure-report"
                if os.path.exists(allure_report_path):
                    print("Adding Allure report to ZIP...")
                    for root, dirs, files in os.walk(allure_report_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Create relative path inside ZIP: allure-report/...
                            arcname = os.path.relpath(file_path, folder_path)
                            zipf.write(file_path, arcname=arcname)
                            print(f"Added to zip: {arcname}")
                    print("Allure report added successfully!")
                else:
                    print(f"WARNING: Allure report not found at: {allure_report_path}")


                        
    print(f"Created zip: {zip_filename}")
    return zip_filename          
'''

'''
def create_zip_folder(base_filename, folder_path="generated_files"):
    # Create reports folder if it doesn't exist
    reports_folder = f"{folder_path}/reports"
    if not os.path.exists(reports_folder):
        os.makedirs(reports_folder)

    # Generate unique name for the zip folder with new naming convention
    zip_filename = f"{reports_folder}/CaptinAiReport_{base_filename}.zip"

    # Expected files with their subfolder paths
    expected_files = [
        {
            "file": f"{base_filename}_plan.xlsx",
            "path": f"{folder_path}/plans/{base_filename}_plan.xlsx"
        },
        {
            "file": f"{base_filename}_result.xlsx",
            "path": f"{folder_path}/results/{base_filename}_result.xlsx"
        },
        {
            "file": f"{base_filename}_summary.html",
            "path": f"{folder_path}/summaries_files/{base_filename}_summary.html"
        },
        {
            "file": f"{base_filename}_summary.md",
            "path": f"{folder_path}/summaries_files/{base_filename}_summary.md"
        },
        {
            "file": f"{base_filename}_result.json",
            "path": f"{folder_path}/results/{base_filename}_result.json"
        }
    ]

    # Create the zip folder
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add expected files
        for item in expected_files:
            file_path = item["path"]
            arcname = item["file"]

            if os.path.exists(file_path):
                zipf.write(file_path, arcname=arcname)
                print(f"Added to zip: {arcname}")
            else:
                print(f"WARNING: Skipping missing file: {file_path}")
                print(f"  Expected at: {os.path.abspath(file_path)}")

        # Add Allure report folder if it exists
        allure_report_path = f"{folder_path}/allure-report"
        if os.path.exists(allure_report_path):
            print("Adding Allure report to ZIP...")
            for root, dirs, files in os.walk(allure_report_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create relative path inside ZIP: allure-report/...
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname=arcname)
            print("Allure report added successfully!")
        else:
            print(f"WARNING: Allure report not found at: {allure_report_path}")

        # Add screenshots folder if it exists
        screenshots_path = f"{folder_path}/screenshots"
        if os.path.exists(screenshots_path):
            print("Adding screenshots to ZIP...")
            screenshot_count = 0
            for root, dirs, files in os.walk(screenshots_path):
                for file in files:
                    if file.endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(root, file)
                        # Create relative path inside ZIP: screenshots/...
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname=arcname)
                        screenshot_count += 1
            print(f"Added {screenshot_count} screenshots to ZIP!")
        else:
            print(f"WARNING: Screenshots folder not found at: {screenshots_path}")

        # Add html.results folder (evidence) if it exists
        html_results_path = "html.results"
        if os.path.exists(html_results_path):
            print("Adding HTML evidence to ZIP...")
            evidence_count = 0
            for root, dirs, files in os.walk(html_results_path):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        # Create relative path inside ZIP: html.results/...
                        arcname = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arcname=arcname)
                        evidence_count += 1
            print(f"Added {evidence_count} HTML evidence files to ZIP!")
        else:
            print(f"WARNING: HTML evidence folder not found at: {html_results_path}")

    print(f"Created zip: {zip_filename}")
    return zip_filename
'''


def create_zip_folder(base_filename, url_part, test_depth, folder_path="generated_files"):
    """
    Create a zip file containing all files related to the given URL and test depth.
    It dynamically finds files that contain both the URL and test depth in their names.
    """
    reports_folder = f"{folder_path}/reports"
    os.makedirs(reports_folder, exist_ok=True)

    zip_filename = f"{reports_folder}/CaptinAiReport_{url_part}_{test_depth}.zip"
    keywords = [url_part, str(test_depth)]

    # Define subfolders to search
    search_folders = {
        "plans": f"{folder_path}/plans",
        "results": f"{folder_path}/results",
        "summaries": f"{folder_path}/summaries_files",
    }

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for label, path in search_folders.items():
            if not os.path.exists(path):
                print(f"WARNING: Missing folder: {path}")
                continue

            for file in os.listdir(path):
                #if all(k in file for k in keywords):
                if (url_part in file) and (f"_{test_depth}_" in file):
                    file_path = os.path.join(path, file)
                    arcname = f"{label}/{file}"
                    zipf.write(file_path, arcname=arcname)
                    print(f"Added to zip: {arcname}")
        '''
        # Add Allure report
        allure_report_path = f"{folder_path}/allure-report"
        if os.path.exists(allure_report_path):
            print("Adding Allure report...")
            for root, dirs, files in os.walk(allure_report_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname=arcname)
            print("Allure report added successfully!")
        else:
            print(f"WARNING: Allure report not found at: {allure_report_path}")
        '''
        # Add screenshots
        screenshots_path = f"{folder_path}/screenshots"
        if os.path.exists(screenshots_path):
            print("Adding screenshots...")
            for root, dirs, files in os.walk(screenshots_path):
                for file in files:
                    if file.endswith(('.png', '.jpg', '.jpeg')) and all(k in file for k in keywords):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname=arcname)
            print("Screenshots added!")
        else:
            print(f"WARNING: Screenshots not found at: {screenshots_path}")

        # Add HTML results (evidence)
        html_results_path = "html.results"
        if os.path.exists(html_results_path):
            print("Adding HTML evidence...")
            for root, dirs, files in os.walk(html_results_path):
                for file in files:
                    if file.endswith('.html') and all(k in file for k in keywords):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, '.')
                        zipf.write(file_path, arcname=arcname)
            print("HTML evidence added!")
        else:
            print(f"WARNING: HTML evidence folder not found at: {html_results_path}")

    print(f"Created zip: {zip_filename}")
    return zip_filename







def create_md_file (content ,baseName ,folder_path = "generated_files"):
    fileName = f"{baseName}_summary.md"
    
    try:
        with open (f"{folder_path}/{fileName}",'w' , encoding= "utf-8") as f:
            f.write(content)
            return {"success": f"{fileName} created"} 
        
    except Exception as e:
        error_msg = f"Error generating {fileName} {str (e)}"
        return {"error": error_msg}
            


def create_html (data , baseName, folder_path= 'generated_files' ):
    
    llm = ChatOpenAI(
        model= "gpt-4o-mini",
        temperature= 0.7,
        api_key= os.getenv("OPENAI_API_KEY")
        )
    
    
    prompt_tamplete  = ChatPromptTemplate.from_messages([
        ("system", """You are an expert front-end developer and UI/UX designer.
        Your task is to generate a **modern, professional HTML page with CSS** based ONLY on the {data} provided by the user.

        **Key Requirements:**
        - Use clean, semantic HTML structure.
        - Apply modern CSS techniques: Flexbox, Grid, CSS variables, and responsive units.
        - Ensure the design is fully responsive (mobile, tablet, desktop) with a mobile-first approach.
        - Use a **modern, relaxing color palette** (soft pastels, muted tones) to give the user a sense of calm, as if viewing an artwork.
        - Design content as **cards** with shadows,button ,rounded corners with colored , padding, and subtle hover animations.
        - Use readable typography and proper hierarchy.
        - Include subtle hover effects, transitions, or simple animations to enhance UX.
        - Keep the code clean, well-organized, and readable; include comments where helpful.
        - If the content includes steps, display them as numbered points.
        
        Cards should have only their rounded corners highlighted with color, rather than filling the entire background.
        Cards with minimal information should appear smaller and positioned more compactly inside the layout.
        for responsive you can use for example 
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        .container {{
        max-width: 90%;   /* scales with screen */
        padding: 2rem;    /* relative spacing */
        }}
        
        
        .cards {{
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        }}

        .card {{
                flex: 1 1 300px; /* grow, shrink, base width */
                }}

        @media (max-width: 768px) {{
        .navbar {{
            flex-direction: column;
        }}
        }}
        @media (max-width: 480px) {{
        body {{
            font-size: 0.9rem;
        }}
        }}
        
        YOU can use  the following color palettes
        1. Warm & Bold:
        #F9DBBD, #FFA5AB, #DA627D, #A53860, #450920

        2. Soft Pastels:
        #CDB4DB, #FFC8DD, #FFAFCC, #BDE0FE, #A2D2FF

        3. Earthy Greens:
        #DAD7CD, #A3B18A, #588157, #3A5A40, #344E41

        4. Minimal Neutral:
        #EDAFB8, #F7E1D7, #DEDBD2, #B0C4B1, #4A5759
        

        **Output:**  
        - Output only valid HTML and CSS inside a single <html> file.
        - Assume that the user has no knowledge of coding, and therefore do not show any unnecessary technical information
        """),
            ("user", "Please create the HTML page based on the following data:\n{data}")
    ])
    
    chain = prompt_tamplete | llm
    
    
    # try:
        
    response = chain.invoke({"data": data})
    fileName = f"{baseName}_summary.html"
    
        
    with open(f"{folder_path}/{fileName}" , "w" , encoding = "utf-8") as f:
        f.write(response.content)
        return {"success": f"{fileName} created"} 
            
    # except Exception as e:
    #     error_meg = f"Error generating html with LLM: {str(e)}"
    #     return{  "error" : error_meg }
    
 

def generate_test_report_with_llm(combined_data):
    
    """
    Generate the Test Report with LLM using both plan and result data
    """

    # Initialize the LLM Model 
    
    llm = ChatOpenAI(
        model = "gpt-4o-mini",
        temperature= 0.7,
        api_key= os.getenv("OPENAI_API_KEY")
    )
    
    prompt_template = ChatPromptTemplate.from_messages ([
        ("system", """You are a QA testing expert. Generate a comprehensive test report for a website.
         IMPORTANT: Your job is to generate a **professional test report** based on the combined plan and result data provided.
         
         The data contains:
         - "plan": Original test plan with website analysis and test cases
         - "results": Actual test execution results with pass/fail status and errors
         - "websiteUrl": The website that was tested
         - "testDepth": Number of test cases executed
         
         IMPORTANT: Extract ALL details directly from the JSON data.
         DO NOT invent or assume information not present in the data.
         If a field is missing, write "Not Provided".
         The report must be structured and human-readable.
         
        Expected Report Format:
        1. **Executive Summary**
        - Website URL
        - Test Execution Date
        - Total Test Cases
        - Pass Rate
        - Overall Status (Pass/Fail/Needs Review)

        2. **Test Environment**
        - Target Website
        - Test Depth
        - Execution Tool: Autonomous QA Captain
        - Browser: Chrome (Selenium WebDriver)

        3. **Test Execution Summary**
        - Total test cases planned: [from plan data]
        - Total test cases executed: [count from results]
        - Passed: [count passed tests from results]
        - Failed: [count failed tests from results]
        - Pass Rate: [percentage]
        
        4. **Website Analysis** (from plan data)
        - Website Title
        - Description
        - Key Features Identified
        - Main Pages
        - Forms Detected
        - Navigation Items

        5. **Test Results Details**
        Create a detailed table for each test case:
        | Test ID | Test Name | Status | Duration | Error Details | Screenshot |
        
        For failed tests, include error analysis and recommendations.

        6. **Defect Summary**
        - Critical Issues: [count and list]
        - Major Issues: [count and list] 
        - Minor Issues: [count and list]
        - Recommendations for fixes

        7. **Test Coverage Analysis**
        - Features tested
        - Test types executed (UI, functional, etc.)
        - Areas not covered (if any)

        8. **Conclusion & Recommendations**
        - Overall assessment
        - Priority fixes needed
        - Next steps
        - Quality score/rating
          
         """),
        ("user", "Please generate a comprehensive test report based on the following combined data:\n{combined_data}")
    ])
    

    chain = prompt_template | llm
    
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"error": "OpenAI API key not found in environment variables"}
        
        # Invoke the chain with combined data
        response = chain.invoke({'combined_data': combined_data})
        content = response.content
        return content 
    
    
    except Exception as e:
            error_msg = f"Error generating test report with LLM: {str(e)}"
            return {"error": error_msg}
    
    
    
def main():
    
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Two JSON arguments required"}))
        sys.exit(1)

    try:
        # Load the JSON strings into Python dictionaries
        plan_data = json.loads(sys.argv[1])
        result_data = json.loads(sys.argv[2])  # Changed from evidence_data to result_data
        folder = 'generated_files'
        
        # Extract website URL and test depth
        websiteUrl = plan_data.get("websiteUrl", "")
        test_depth = plan_data.get("testDepth", 8)
        
        # Create clean filename (same method as create_plan.py and qa_executor.py)
        clean_url = websiteUrl.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')
        base_filename = f"{clean_url}_{test_depth}"
        
        # Combine plan and result data for comprehensive report
        combined_data = {
            "plan": plan_data,
            "results": result_data,
            "websiteUrl": websiteUrl,
            "testDepth": test_depth
        }
        
        # Generate the report using combined data
        response = generate_test_report_with_llm(combined_data)
        
        # Create summaries_files folder if it doesn't exist
        summaries_folder = "generated_files/summaries_files"
        if not os.path.exists(summaries_folder):
            os.makedirs(summaries_folder)
        
        # Create markdown file in summaries_files folder
        md_result = create_md_file(response, base_filename, summaries_folder)
        print(f"Markdown: {md_result}")
        
        # Create HTML file in summaries_files folder
        html_result = create_html(response, base_filename, summaries_folder)
        print(f"HTML: {html_result}")
        
        # Create ZIP package
        #zip_file = create_zip_folder(base_filename, folder)
        zip_file = create_zip_folder(base_filename, clean_url, test_depth, folder)

        '''
        # Rename .zip → .zipx to avoid Gmail security block
        safe_zip_path = zip_file.replace(".zip", ".zipx")
        shutil.copy(zip_file, safe_zip_path)
        print(f"ZIP (safe for email): {safe_zip_path}")
        '''

        print(f"ZIP: {zip_file}")
        
        # Print success message for server
        print(json.dumps({
            "success": True,
            "message": "Report generated successfully",
            "files": {
                "markdown": f"summaries_files/{base_filename}_summary.md",
                "html": f"summaries_files/{base_filename}_summary.html", 
                "zip": f"CaptinAiReport_{base_filename}.zip"
            }
        }))
        
    except Exception as e:
        error_msg = f"Error in create_reports.py: {str(e)}"
        print(json.dumps({"error": error_msg}))
        sys.exit(1)
  
    

if __name__ == '__main__':
    main()
