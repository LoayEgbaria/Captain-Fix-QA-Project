# Captain Fix - Autonomous QA Testing

An AI-powered autonomous QA testing platform that generates test plans, executes automated tests, collects evidence, and manages bug reports.

## Requirements

### Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

**Required packages:**
- `langchain==0.1.0` - LLM framework for AI integration
- `langchain-openai==0.0.5` - OpenAI integration for LangChain
- `openai==1.3.0` - OpenAI API client
- `python-dotenv==1.0.0` - Environment variable management
- `pandas==2.1.0` - Data manipulation and Excel export
- `openpyxl==3.1.2` - Excel file handling
- `selenium==4.15.0` - Web browser automation
- `requests==2.31.0` - HTTP requests for web crawling
- `jira==3.5.0` - For Jira integration 
- `beautifulsoup4==4.12.2` - HTML parsing

### Environment Setup

1. **Create API Key**: Get your OpenAI API key from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. **Create Environment File**: Create `properties.env` with your API key and email credentials:
   ```env
   OPENAI_API_KEY=sk-your-api-key-here
   CAPTAIN_FIX_EMAIL=your-email@gmail.com
   CAPTAIN_FIX_EMAIL_PASSWORD=your-app-password
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

### Browser Setup

**Chrome WebDriver**: Ensure Chrome browser is installed. The system will automatically download the appropriate ChromeDriver.

### Clone and Setup

**Option 1: Clone from Development Environment**  
- Open your development environment (VS Code, IntelliJ, etc.)  
- Go to Source Control or Git menu  
- Select "Clone Repository"  
- Enter repository URL: `https://github.com/yourusername/captain-fix.git`  
- Choose local folder and click "Clone"  
- Open the cloned project in your workspace  

**Option 2: Clone from Command Line**  
```bash
git clone https://github.com/yourusername/captain-fix.git
cd captain-fix 
```

### Continue setup (both options):

python -m venv venv

### Windows:
venv\Scripts\activate

### Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

cp properties.env.example properties.env
### Edit properties.env with your credentials

python server.py

### Keeping Your Fork Updated :
```
git checkout main

git fetch upstream

git merge upstream/main

git push origin main

git branch -d feature/your-feature-name

git push origin --delete feature/your-feature-name
```

### Quick Start for Contributors :
```
git clone https://github.com/yourusername/captain-fix.git && cd captain-fix && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

## Quick Start

### Web Interface

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start the server**: Double-click `start_server.bat` or run `python server.py`
3. **Open browser**: Go to [http://localhost:8000/index.html](http://localhost:8000/index.html)
4. **Fill out the form** with your website URL and settings
5. **Use the workflow buttons**:
   - **📋 Create Plan Excel File** - Generate test plans
   - **🚀 Execute Tests** - Run automated tests
   - **📊 Collect Evidence** - Generate HTML reports
   - **📧 Send Email** - Send results via email

> **Quick Link**: [http://localhost:8000/index.html](http://localhost:8000/index.html) (only works when server is running)

### Available Options

- **Website URL** (required): Target website to test
- **Email Address** (optional): Email for receiving test reports
- **Project Management Tool** (optional): Jira, Trello, or None
- **Test Depth** (optional): Number of test cases (default: 12)
- **Browser** (optional): Chrome, Firefox, or Edge

## Project Management Integration Setup :
### Option 1 - `Jira Integration` :

**Step 1: Get Jira Credentials**

1. **JIRA_SERVER**: 
   - Log into your Jira account
   - Look at browser URL: `https://yourname.atlassian.net`
   - Copy this URL

2. **JIRA_EMAIL**: 
   - The email you used to create your Jira account

3. **JIRA_API_TOKEN**: 
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Give it a name like "QA Captain"
   - Copy the token (it only shows once!)

4. **JIRA_PROJECT_KEY**: 
   - Open your Jira project
   - Look at the URL or project settings
   - Find the 2-4 letter code (e.g., "TEST", "QA")

**Step 2: Configure `properties.env` (jira part)**:
```env
JIRA_SERVER=https://yourname.atlassian.net
JIRA_EMAIL=your-email@gmail.com
JIRA_API_TOKEN=ATATT3xFfGF0...
JIRA_PROJECT_KEY=TEST
```
### Option 2 - `Trello Integration` :

**Step 1: Create Trello Account and Board**
- If you don't have a Trello account, create one at https://trello.com
- Create a new board for your QA testing (or use an existing one)

**Step 2: Get Trello API Key**
1. Make sure you're logged into Trello
2. Go to https://trello.com/app-key
   - Alternative if not working: https://trello.com/1/appKey/generate
3. You'll see your API Key displayed on the page
4. Copy the entire key (it looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)
5. This is your **TRELLO_API_KEY**

**Step 3: Generate Trello Token**
1. On the same page (https://trello.com/app-key), look for a link that says **"Token"** or **"generate a Token"**
2. Click on it
3. Review the permissions and click **"Allow"**
4. Copy the long token that appears (starts with `ATTA` and is very long)
5. This is your **TRELLO_TOKEN**
6. Important: Save this token - you won't be able to see it again

**Step 4: Get Board ID**
1. Open the Trello board you want to use in your browser
2. Look at the URL in the address bar
3. The URL will look like: `https://trello.com/b/XXXXXXXX/your-board-name`
4. Copy only the part after `/b/` and before the next `/` (the `XXXXXXXX` part)
5. Example: If URL is `https://trello.com/b/5f9a8b7c/qa-testing`, your board ID is `5f9a8b7c`
6. This is your **TRELLO_BOARD_ID**

**Step 5: Configure properties.env**:
Add/update these lines to your `properties.env` file (trello part):
```env
TRELLO_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
TRELLO_TOKEN=ATTAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TRELLO_BOARD_ID=5f9a8b7c6d5e4f3g
```
## Features

- ✅ **Complete QA Workflow** - Plan → Execute → Evidence → Report
- ✅ **AI-Powered Test Generation** - LLM creates comprehensive test plans
- ✅ **Automated Test Execution** - Selenium-based browser automation
- ✅ **Evidence Collection** - Screenshots and detailed HTML reports
- ✅ **Email Integration** - Automated result distribution
- ✅ **Organized File Structure** - Clean separation of plans, results, evidence
- ✅ **Professional UI** - Modern, responsive web interface
- ✅ **JSON Data Flow** - Structured data passed between all components

## Project Structure

```
AI-Captin/
├── index.html              # Web interface
├── create_plan.py          # Test plan generation with LLM
├── qa_executor.py          # Automated test execution with Selenium
├── collect-evidence.py     # Evidence collection and HTML reports
├── email_sender.py         # Email functionality
├── send_email.py           # Email API endpoint
├── server.py               # HTTP server for API calls
├── start_server.bat        # Easy server starter (double-click this!)
├── requirements.txt        # Python dependencies
├── properties.env          # Environment variables (API keys, email)
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── generated_files/       # Organized output files
    ├── plans/             # Test plans (Excel + JSON)
    ├── results/           # Execution results (Excel + JSON)
    ├── screenshots/       # Test execution screenshots
    ├── evidence/          # HTML evidence reports
    ├── scripts/           # Generated Python scripts
    └── mockzipfile.zip    # Email attachments
```

## How It Works

### Complete QA Workflow

1. **Start the server** - Run `start_server.bat` or `python server.py`
2. **Open web interface** - Navigate to `http://localhost:8000/index.html`
3. **Fill out the form** - Enter website URL and configuration options
4. **Execute workflow steps**:
   - **📋 Create Plan** → Generates test plans with LLM
   - **🚀 Execute Tests** → Runs automated tests with Selenium
   - **📊 Collect Evidence** → Creates HTML reports and screenshots
   - **📧 Send Email** → Distributes results via email

### File Naming Convention

All generated files follow a consistent naming pattern:
- **Plans**: `url_numberoftests_plan.xlsx` & `.json`
- **Results**: `url_numberoftests_result.xlsx` & `.json`
- **Screenshots**: `url_numberoftests_testid.png`

Example: `https_mytodolist-beryl-nine_vercel_app_30_plan.xlsx`

## Current Functionality

### 📋 Create Plan Excel File
- **Input**: Website URL, test depth, browser, PM tool, email
- **Process**: Uses LLM to analyze website and generate test plans
- **Output**: Excel and JSON files with structured test cases
- **Location**: `generated_files/plans/`

### 🚀 Execute Tests
- **Input**: Test plan from previous step
- **Process**: Runs Selenium WebDriver to execute test cases
- **Output**: Test results with pass/fail status and screenshots
- **Location**: `generated_files/results/` and `generated_files/screenshots/`

### 📊 Collect Evidence
- **Input**: Test execution results
- **Process**: Generates professional HTML reports using LLM
- **Output**: Detailed evidence reports with screenshots
- **Location**: `generated_files/evidence/`

### 📧 Send Email
- **Input**: Test results and evidence files
- **Process**: Sends comprehensive email reports via SMTP
- **Output**: Email with attachments and summary

### JSON Data Structure
```json
{
  "status": "success",
  "message": "Test plan created successfully",
  "data": {
    "websiteUrl": "https://example.com",
    "testDepth": "basic",
    "browser": "chrome",
    "pmTool": "jira",
    "email": "user@example.com",
    "testPlanFile": "test_plan.xlsx",
    "testCases": {
      "total": 15,
      "smoke": 5,
      "navigation": 4,
      "forms": 3,
      "ui": 0,
      "performance": 0
    },
    "createdAt": "2025-01-09T19:30:45.123456",
    "nextStep": "execute_tests"
  }
}
```

## Development

### Adding New Scripts
1. Create new Python script (e.g., `execute_tests.py`)
2. Add new API endpoint in `server.py`
3. Add new button in `index.html`
4. Pass JSON data from previous step to new script

### Future Enhancements
1. **PM Tool Integration** - Connect to Jira/Trello APIs for bug tracking
2. **Advanced Test Types** - Performance, security, accessibility testing
3. **Multi-Browser Support** - Firefox, Edge, Safari automation
4. **CI/CD Integration** - GitHub Actions, Jenkins pipeline support
5. **Test Analytics** - Historical trends and coverage reports
6. **Parallel Execution** - Run multiple tests simultaneously

## Troubleshooting

### Server Not Starting
- Make sure Python is installed and in PATH
- Check if port 8000 is available
- Run `python server.py` directly to see error messages

### Browser Automation Issues
- Ensure Chrome browser is installed
- Check if ChromeDriver is compatible with your Chrome version
- Verify Selenium WebDriver installation

### LLM API Issues
- Verify OpenAI API key is valid and has sufficient credits
- Check `properties.env` file exists and contains correct API key
- Monitor API usage limits

### Email Issues
- Verify Gmail App Password is correct (not regular password)
- Ensure 2-Factor Authentication is enabled on Gmail
- Check SMTP settings in `properties.env`

### File Generation Issues
- Ensure `generated_files/` folder has write permissions
- Check if target directories exist (plans/, results/, screenshots/, evidence/)
- Verify Python packages are installed: `pip install -r requirements.txt`

### JSON Not Displaying
- Open browser developer tools (F12)
- Check Console tab for JSON output
- Verify server is running and receiving requests

### Script Errors
- Check terminal where server is running for error messages
- Verify Python script syntax and dependencies



## 📜 License

### Captain Fix Custom License

**Copyright (c) 2025 Captain Fix Team**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, **only after explicit written permission from the full Captain Fix Team or unanimous agreement from all team members.**

#### TEAM AGREEMENT CLAUSE
Any modifications, changes, or derivatives of this Software require full team approval or unanimous agreement. Once approved, this includes but is not limited to:  
- Code modifications  
- Feature additions or removals  
- Architecture changes  
- Distribution of modified versions  
- Commercial use modifications  

**Unauthorized modifications or use of the Software without the agreement of the full Captain Fix Team will be considered a violation and may result in disciplinary action, legal consequences, or other punishments as deemed appropriate by the team.**

The above copyright notice, this permission notice, and the team agreement clause shall be included in all copies or substantial portions of the Software.

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**
