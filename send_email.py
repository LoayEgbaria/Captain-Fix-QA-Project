"""
Captain Fix - Email Sender Script
Independent email functionality for sending test results
"""

import sys
import json
import os
from datetime import datetime
from email_sender import EmailSender

def main():
    """Main function to handle email sending requests"""
    # Get the data from command line arguments
    if len(sys.argv) > 1:
        try:
            data = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    
    # Extract required data
    recipient_email = data.get('email', '').strip()
    website_url = data.get('websiteUrl', '')
    test_depth = data.get('testDepth', 8)
    test_plan_data = data.get('testPlan', {})
    excel_file_path = data.get('excelFile', '')
    
    # Validate required fields
    if not recipient_email or '@' not in recipient_email:
        result = {
            "status": "error",
            "message": "Valid recipient email address is required",
            "data": {
                "emailSent": {
                    "success": False,
                    "message": "No valid recipient email provided",
                    "recipient": None
                }
            }
        }
        print(json.dumps(result))
        return
    
    if not website_url:
        result = {
            "status": "error", 
            "message": "Website URL is required",
            "data": {
                "emailSent": {
                    "success": False,
                    "message": "Website URL not provided",
                    "recipient": recipient_email
                }
            }
        }
        print(json.dumps(result))
        return
    
    try:
        # Create email sender instance
        email_sender = EmailSender()
        
        # Find the generated report ZIP file using same naming pattern as create_reports.py
        clean_url = website_url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace(':', '_').replace('.', '_')
        base_filename = f"{clean_url}_{test_depth}"
        zip_path = f"generated_files/reports/CaptinAiReport_{base_filename}.zip"
        
        # Check if ZIP file exists
        if not os.path.exists(zip_path):
            result = {
                "status": "error",
                "message": f"Report ZIP file not found. Please run 'Generate Report' first.",
                "data": {
                    "emailSent": {
                        "success": False,
                        "message": f"Report ZIP file not found: {zip_path}. Please generate the report first.",
                        "recipient": recipient_email
                    }
                }
            }
            print(json.dumps(result))
            return
        
        # Send email with ZIP attachment only
        email_success, email_message = email_sender.send_test_results(
            recipient_email=recipient_email,
            website_url=website_url,
            test_plan_data={
                "websiteUrl": website_url,
                "testDepth": data.get('testDepth', 12),
                "testPlan": test_plan_data
            },
            zip_file_path=zip_path
        )
        
        # Success response
        result = {
            "status": "success" if email_success else "error",
            "message": email_message,
            "data": {
                "emailSent": {
                    "success": email_success,
                    "message": email_message,
                    "recipient": recipient_email,
                    "attachments": {
                        "zipFile": zip_path
                    }
                },
                "createdAt": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        # Error response
        result = {
            "status": "error",
            "message": f"Failed to send email: {str(e)}",
            "data": {
                "emailSent": {
                    "success": False,
                    "message": f"Email error: {str(e)}",
                    "recipient": recipient_email
                },
                "createdAt": datetime.now().isoformat()
            }
        }
    
    # Output result as JSON
    print(json.dumps(result))

if __name__ == "__main__":
    main()
