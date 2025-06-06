from dotenv import dotenv_values

def get_task_templates(env_vars):
    #Environment variables data
    email = env_vars["LOGIN_EMAIL"]
    password = env_vars["LOGIN_PASSWORD"]

    return {
        
    "auth": f''' 
        Visit the website https://dev.gotrust.tech.
        Login using the following credentials:
        - Email: {email}
        - Password: {password}
        Fill in the login form fields and submit.
        ''',

"account_setup": '''
Go to /crm/role-management
- Click "Add Role"
- Set Role Name to "New Role"
- Set "Module Head" to "Yes"
- Click the first checkbox under "Accesses given to user" (e.g., "Account Setup") to automatically select all others
- Confirm that other checkboxes are selected (optional step for validation)
- Click "Save"

Then go to /crm/user-management
- Click "Add User"
- Enter user details (name, email, phone)
- Select the newly created role
- Select the first group from "Group Assigned"
- Click "Assign/Unassign" and then "Submit"

Then go to /crm/company-structure
- Search for the same "group" that was selected in the previous step snd click if found 
- Click "View Details"
- Check if the new user is listed under "Members of Group"
'''

,
    "policy_and_notice":  '''
You are controlling a browser to manage data mapping for an organization in the application.

Repeat Each Failed Step **only twice**, then **move to the next step** — no infinite retrying!

## General Instructions:
- For every step, if it fails (due to UI issues, no element found, or timeout), retry it up to **2 additional times**.
- After 3 total attempts (initial + 2 retries), **move on** to the next step even if it failed.
- Remember you need to interact with the components to test them , so store the logs accordingly 

## CRITICAL INSTRUCTIONS FOR HANDLING FAILURES:
1. For EACH step, if it fails, try up to 2 more times (3 attempts total)
2. Use DIFFERENT approaches for retries (e.g., try clicking differently, use different selectors)
3. After 3 failed attempts, LOG the failure and MOVE TO THE NEXT STEP
4. Only exit the workflow if you cannot proceed at all after multiple steps

## UI INTERACTION GUIDELINES:
- For dropdowns: First click to open, then click the option (don't use select_dropdown_option)
- For form inputs: Try both by index and by placeholder text
- For buttons: Try clicking by text first, then by index
- Wait 5-10 seconds after page transitions before taking actions
- If elements aren't visible, scroll slowly to find them

## SPECIAL HANDLING FOR FORM FIELDS:
- For date fields: Click the input field first, wait for calendar to appear, then click a visible date
- For dropdowns that don't open: Try clicking elsewhere on the page first, then try again
- If a dropdown has no options after 3 attempts: LOG the issue and continue to the next field
- If you can't find a specific element by index, try looking for it by text or nearby elements

 If a cookie consent popup appears, wait up to 5 seconds and look for a button labeled:
   - "Allow all"
   - "Accept all"
   - "Accept"
   If found, click it. If nothing matches, look for any dismiss or close button.

## Workflow:

1. Navigate to /privacy/privacy-policy/
   Wait at least 10 seconds for the page to fully load.

2. View and analyze the dashboard data on the page
   Take at least 5 seconds to observe the page.

3. Now navigate to /privacy/privacy-policy/policy
   Wait at least 10 seconds for the page to fully load.

4. Select a "Workflow Stage" option from the dropdown:
   - Click on the dropdown field
   - Wait 3 seconds for options to appear
   - Click on any visible option
   - If no options appear, try clicking elsewhere and try again
   - If still no options after 3 attempts, continue to the next step

5. View and remember the existing policies in {existing_policies}
   Take at least 5 seconds to observe and record the data.

6. Click "Create New"
   Wait for the form to load completely (at least 5 seconds).

7. Fill unique entries just like the existing one {existing_policies}:
   
   For each field below, if you encounter issues after 3 attempts, LOG the issue and continue to the next field:
   
   - Fill "Enter Policy Name" with a unique name
   - Fill "Policy Description" with a relevant description
   
   - For "Policy Category" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again
   
   - For "Entity Name" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again
   
   - For "Language" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again
   
   - Fill email for "Policy Reviewer"
   - Fill email for "Policy Approver"
   
   - For "Effective Date":
     * Click the input field
     * Wait for calendar to appear
     * Click any visible date (preferably current date)
     * If calendar doesn't appear, try clicking elsewhere and try again
   
   - For "Tentative Date":
     * Click the input field
     * Wait for calendar to appear
     * Click any visible date (preferably a future date)
     * If calendar doesn't appear, try clicking elsewhere and try again
   
   - For "Recurrence Period" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again
   
   - Fill "Version Number" with a numeric value
   
   - For "Department" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again
   
   - Fill "Policy Id" with a unique ID
   
   - For "Relevant Standard/Law" dropdown:
     * Click the dropdown to open it
     * Wait 3 seconds for options to appear
     * Click any visible option
     * If no options appear, try clicking elsewhere and try again

8. Click "create"
   Wait for the confirmation message or page refresh (at least 10 seconds).

9. Navigate to /privacy/privacy-policy/privacy-notice
   Wait at least 10 seconds for the page to fully load.

10. For "select entity" dropdown:
    - Click the dropdown to open it
    - Wait 3 seconds for options to appear
    - Click any visible option
    - If no options appear, try clicking elsewhere and try again
    - If still no options after 3 attempts, LOG the issue and continue to the next step

11. Click "create"
    Wait for the form to load completely (at least 5 seconds).

12. For "select entity" dropdown:
    - Click the dropdown to open it
    - Wait 3 seconds for options to appear
    - Click any visible option
    - If no options appear, try clicking elsewhere and try again
    - If still no options after 3 attempts, LOG the issue and continue to the next step

13. Fill "Enter Privacy Notice Title" with a unique title
    If you can't find the field, try scrolling down slowly.

14. Click "Add Section" and Fill:
    - If you can't find the button, try scrolling down slowly
    - Fill in any required fields in the section
    - If you can't add a section after 3 attempts, LOG the issue and continue to the next step

15. Click "save changes"
    Wait for the confirmation message or page refresh (at least 10 seconds).

16. Navigate to /privacy/privacy-policy/cookie-policy
    Wait at least 10 seconds for the page to fully load.

17. For "select entity" dropdown:
    - Click the dropdown to open it
    - Wait 3 seconds for options to appear
    - Click any visible option
    - If no options appear, try clicking elsewhere and try again
    - If still no options after 3 attempts, LOG the issue and continue to the next step

18. Click "create"
    Wait for the form to load completely (at least 5 seconds).

19. Fill "Enter Cookie Policy Title" with a unique title
    If you can't find the field, try scrolling down slowly.

20. Click "Add Section" and fill:
    - If you can't find the button, try scrolling down slowly
    - Fill in any required fields in the section
    - If you can't add a section after 3 attempts, LOG the issue and continue to the next step

21. Click "save changes"
''',

"ucm": '''
You are controlling a browser to manage consent settings in the application.
Also wait for 5 seconds while the page is loading 
Repeat Each Failed Step **only twice**, then **move to the next step** — no infinite retrying!

## General Instructions:
- For every step, if it fails (due to UI issues, no element found, or timeout), retry it up to **2 additional times**.
- After 3 total attempts (initial + 2 retries), **move on** to the next step even if it failed.
- Remember you need to interact with the components to test them , so store the logs accordingly 

## CRITICAL INSTRUCTIONS FOR HANDLING FAILURES:
1. For EACH step, if it fails, try up to 2 more times (3 attempts total)
2. Use DIFFERENT approaches for retries (e.g., try clicking differently, use different selectors)
3. After 3 failed attempts, LOG the failure and MOVE TO THE NEXT STEP
4. Only exit the workflow if you cannot proceed at all after multiple steps

## UI INTERACTION GUIDELINES:
- For dropdowns: First click to open, then click the option (don't use select_dropdown_option)
- For form inputs: Try both by index and by placeholder text
- For buttons: Try clicking by text first, then by index
- Wait 1-2 seconds after page transitions before taking actions
- If elements aren't visible, scroll slowly to find them


## Workflow:

1. If a cookie consent popup appears, wait up to 5 seconds and look for a button labeled:
   - "Allow all"
   - "Accept all"
   - "Accept"
   If found, click it. If nothing matches, look for any dismiss or close button.
 
2. Wait for the main page to load.

### -- PROCESSING CATEGORY --
3. Navigate to /consent-management/ucm-lab/processing-category 
   - Explore All existing "Processing Category Name" for all the pages and save in existing_pc

4. Click "Add Processing Category"
 
5. Generate a realistic random value for "processing category name" as {pc_name} and "description" as {pc_desc}.
   Example: Name: Data Analytics | Description: Collecting user data for analysis
   Which does not exists in the list {existing_pc} 
 
6. Fill Name = {pc_name}, Description = {pc_desc}, then click Save.

### -- PROCESSING PURPOSE --
7. Navigate to /consent-management/ucm-lab/processing-purpose 

8. Click "Add Processing Purpose"
 
9. Generate a realistic random value for "processing purpose name" as {pp_name} and "description" as {pp_desc}.
   Example: Name: Data Analytics | Description: Collecting user data for analysis
   Which does not exists in the list {existing_pc}
 
10. For Processing Purpose dropdown:
    - First click on the dropdown field to open it
    - Wait for options to appear
    - Then click directly on the option that matches {pc_name} from previous step
    - If that fails, try clicking any visible option

11. Fill in the name field with {pp_name}

12. Fill in the description field with {pp_desc}

13. Click Save button

### -- CONSENT PURPOSE --
14. Navigate to /consent-management/ucm-lab/consent-purpose 
   - Explore All existing "Consent Purpose" for all the pages and save in {existing_cp}

15. Click "Add Consent Purpose"
 
16. Generate a realistic random value for "consent purpose name" as {cp_name} and "description" as {cp_desc}.
   Example: Name: Storing and verification | Description: Storing and verification of personal data 
   Which does not exists in the list {existing_cp}
 
17. Fill in the name field with {cp_name}
   - Fill in the description field with {cp_desc}

   For Processing Purpose dropdown:

   - Click on the dropdown field to open it
   - Look for {pp_name} in the visible options
    - If not immediately visible, scroll down up to 3 times
    - If still not found after scrolling, select ANY visible option
    - After 3 attempts, if you can't select any option, continue to the next step
    - Click Save button

### -- PII LABEL --
18. Navigate to /consent-management/ucm-lab/pii
    - Explore All existing "PII Label" for all the pages and save in existing_pii

19. Generate a realistic random value for "pii label name" as {pii_name} and "description" as {pii_desc}.
   Example: Name: Email | Description: Email Of The User
   Which does not exists in the list {existing_pii}

20. Fill  PII Label = pii label {pii_name} , Description: Description {pii_desc} then click Save.

### -- CONSENT COLLECTION TEMPLATE --
21. Now navigate to route: /consent-management/ucm-lab/add-collection-templates
   - Explore All existing "Template Name" for all the pages and save in existing_templates

22. Click "Create Consent Collection Template"
 
23. Generate a realistic random value for "Template name" and store in {template_name}.
   Which does not exists in the list {existing_templates}

24. Fill the following fields:
    - Template Name: {template_name}
    - Owner Name: {owner_name}
    - Email: {email}

25. Select from dropdowns or fill fields:
   For Entity dropdown:
    - Click the dropdown to open it
    - Wait 1 second
    - Click any visible option
    - Wait 1 second

   For Unique Data Identifier Type dropdown:
    - Click the dropdown to open it
    - Wait 1 second
    - Click any visible option
    - Wait 1 second
   
   Generate and Enter value for Department
   Generate andEnter value for Process
   Generate and Enter value for Vendor

26. If there's a toggle or radio for "Does this form involve minor consent", select "Yes"

27. Click "Continue to Step 2"

28. Click on "Add Consent Purpose" , then click on "Select Consent Purpose" and choose any listed consent purpose

29. Click "Add Pii" , Click "Select Pii" , Choose {pii_name} or any other label , Click "save" , Fill the "Expiry* with value 1 , Click save 

30. Now that the "Consent Purpose" has got created Click continue to step 3

31. Click Source , select Form , Fill "Consent form title" and "Consent form description" , Click "Next"

32. Click continue to step 4

33.Click "new" , Fill privacy Note Title {pn_title} , Click "Next" , "Add new section title" with {ns_title} , Click "Add Section" 

34. Click continue to step 5

35. Click yes , Add Preference Center Title {pc_title} , Click Next 

36. Click continue to step 6 

37. Click "Yes,proceed" for english

38. Click save

39. Now move to route : /consent-management/ucm-lab/preference-center 

40. Click on "Add Preference Center"

41. Now you are on route : /consent-management/ucm-lab/preference-center-add

42. Fill "Template Name" with {template_name} , "description" with {desc} , Fill "subject identity type" Email , "owner_email" with {email} , 
"Owner Name" with {owner_name} , "Privacy Policy Link" with http://google.com , Click "Next"

43. Click next button

44. Click Next 

45. Click save button

46. Now move to route : /consent-management/subject-consent-manager

47. Analyse and get all important dashboard details
''',

"ccm": '''
You are controlling a browser to **test the Cookie Consent Management (CCM) form** like a real user.

For each step:
- Retry up to **2 more times** (total 3 attempts) if the step fails (UI not found, timeout, etc.).
- **After 3 attempts**, log the failure and **move to the next step**.

---

## Global Cookie Handling

At any point, if a cookie consent popup appears (even after page navigation):
- Wait up to 5 seconds.
- Click on buttons labeled:
  - "Allow all", "Accept all", or "Accept"
  - If unavailable, try a dismiss or close button

---

## Workflow

### Step 1: Handle Initial Cookie Prompt

- Wait up to 5 seconds.
- If cookie popup appears, click "Allow all", "Accept all", or "Accept". Otherwise, look for close/dismiss.

---

### Step 2: Load the Main Page

- Wait for the page to fully load.

---

### Step 3: Navigate to CCM Module

- Go to: `/cookie-consent-management/cookie-consent-domain`
- Wait for the page to load.
- Click the **"Create"** button to open the form.

---

### Step 4: Domain Setup Form

>  If **cookie popup appears here again**, handle it before proceeding with form fields.

#### Fill the form fields:
- **Accept All (if banner appears again)** before proceeding.
- Analyze and store existing domain records as `{existing_records}`.

Then complete the following:
- Select a "Domain Group" from the dropdown.
- Generate a **unique, valid domain name** not in `{existing_records}` and fill in "Domain Name".
- Generate a **valid and unique URL** not present in `{existing_records}` and fill in "Url".
- Fill in realistic "Owner" and "Owner Email".
- Use a relevant "Compliance Policy Link" which is relevant to domain group and url.

#### Consent Framework:
- Locate the "Consent Framework" label or dropdown.
- Click to open the dropdown.
- Scroll and select any available option (e.g., "Digital Personal Data Protection Act, 2023 (DPDPA)").
- Close the dropdown after selection.

Click **"Next"** to proceed.

---

### Step 5: Website Scan (Auto Scan) Step

Click the dropdown element (usually labeled or near text "Select Frequency").
Wait for options like "Daily", "Monthly", "Yearly" to appear.
Click on "Yearly".



---

### Step 6: Category and Service Setup

- Review existing categories.
- Click **"Add Category"** and enter:
  - Unique Category Name
  - Relevant Description
  - Select necessary options
  - Click **"Create"**
- Click **"Service"** tab:
  - Explore entries
  - Click **"Add Service"**
  - Fill Service Name and Description
  - Select a Cookie Category
  - Click **"Create"**
- Click **"Next"**

---

### Step 7: Customize Form

- Explore the existing form
- At the end of the page there is **Is this the default banner?** checkbox , Click on it if not selected
- Click **"Next"**

---

### Step 8: Cookie Policy

- Choose **"New"** for cookie policy.
- Generate a unique Cookie Policy Title as {cookie_policy_title} and Fill in the Value
- Generate a new Section name as {section_name} and click "Add Section"
- Click "Save Changes"
- Click **"Next"**

---

### Step 9: Translation

- Change dropdown language to **English** (if not already).
- Click **"Save Translation"**
- Click **"Next"**

---

### Step 10: Final Save

- Click **"Save"** to submit the form.


''',


"data_mapping": '''
You are controlling a browser to manage data mapping module in the application which governs ROPA.
You need to first assing the "Assignee" , start the ROPA and then submit the ROPA for review and Review it.
Repeat Each Failed Step **only twice**, then **move to the next step** — no infinite retrying!

## General Instructions:
- For every step, if it fails (due to UI issues, no element found, or timeout), retry it up to **2 additional times**.
- After 3 total attempts (initial + 2 retries), **move on** to the next step even if it failed.
- Remember you need to interact with the components to test them , so store the logs accordingly 

## CRITICAL INSTRUCTIONS FOR HANDLING FAILURES:
1. For EACH step, if it fails, try up to 2 more times (3 attempts total)
2. Use DIFFERENT approaches for retries (e.g., try clicking differently, use different selectors)
3. After 3 failed attempts, LOG the failure and MOVE TO THE NEXT STEP

## UI INTERACTION GUIDELINES:
- For dropdowns: First click to open, then click the option (don't use select_dropdown_option)
- For form inputs: Try both by index and by placeholder text
- For buttons: Try clicking by text first, then by index
- Wait 1-2 seconds after page transitions before taking actions
- If elements aren't visible, scroll slowly to find them

 If a cookie consent popup appears, wait up to 5 seconds and look for a button labeled:
   - "Allow all"
   - "Accept all"
   - "Accept"
   If found, click it. If nothing matches, look for any dismiss or close button.

## Workflow:

1. If a cookie consent popup appears, wait up to 5 seconds and look for a button labeled:
   - "Allow all"
   - "Accept all"
   - "Accept"
   If found, click it. If nothing matches, look for any dismiss or close button.

2. Navigate to /data-mapping/ropa/ route

3.The dropdown label might be “Testing”, but may vary (e.g., “Production”, “Staging”, etc.).
    Do not depend on static label text.

    Locate the first dropdown near the top of the page.

        Use structure, position, or class hierarchy to identify it.

    Open the dropdown.

    Choose any option that results in:

        A table of records being shown, and

        At least one record with progress less than 100%.

    If multiple views meet this condition, pick the first one that does.

4. Pick the record, scroll the page to the right:
- Click "Assign" if not already selected.
- Click the "Select" dropdown to assign a user.
- Choose a user by clicking the name in the dropdown.
- After selection:
   - **Wait for the dropdown to collapse**
   - Wait 1-2 seconds for any updates
- Now click the "Submit" button to complete the assignment.

Role: You are an intelligent agent filling out a multi-step web form (ROPA form).

🔹 General Rules
- Fill **all visible fields**:  
  • Text inputs → "Test Value"  
  • Dates → Today or +30 days  
  • Checkboxes → Select all  
  • Radio/Dropdowns → Select first valid option  
- Never leave required fields empty.  
- After each page → Click **Save**, then **Next**.  
- If error “Answer all questions...” → Scroll down, re-check, and fill missed fields.

🔹 UI Handling
- If element not found, **scroll down 500px** and retry.  
- Expect form fields to **appear or change after radio/dropdown** clicks — re-scan page after such actions.

🔹 Progress Logic
- Do not attempt final submit unless **progress shows 29/29**.  
- Submit only if the **submit button is visible and enabled**.

🔹 Navigation Steps
1. **Start ROPA** → Click Start → Wait for form.
2. **Fill Pages 1–X** → Follow rules above.
3. **Tentative Completion Date** → Select date 30 days from today.
4. **ROPA Previously Performed** → Select "No".
5. **Continue** until progress = 29/29.

🔹 Review Phase
- Visit `/data-mapping/ropa/`  
- Click eye icon on last record.  
- On each review screen:  
  → Select all checkboxes  
  → Click **Next**  
- On last screen, click **Submit**.
''',

"dsr":'''  
You are controlling a browser to manage data subject rights module in the application which governs ROPA.
First you will be creating the workflow for the business unit , then you will be creating a form for the end user , the user will require to fill the form and make a request , this will enable a two way communication between the user and businesss unit
Repeat Each Failed Step **only twice**, then **move to the next step** — no infinite retrying!

## General Instructions:
- For every step, if it fails (due to UI issues, no element found, or timeout), retry it up to **2 additional times**.
- After 3 total attempts (initial + 2 retries), **move on** to the next step even if it failed.
- Remember you need to interact with the components to test them , so store the logs accordingly 

## CRITICAL INSTRUCTIONS FOR HANDLING FAILURES:
1. For EACH step, if it fails, try up to 2 more times (3 attempts total)
2. Use DIFFERENT approaches for retries (e.g., try clicking differently, use different selectors)
3. After 3 failed attempts, LOG the failure and MOVE TO THE NEXT STEP

## UI INTERACTION GUIDELINES:
- For dropdowns: First click to open, then click the option (don't use select_dropdown_option)
- For form inputs: Try both by index and by placeholder text
- For buttons: Try clicking by text first, then by index
- Wait 1-2 seconds after page transitions before taking actions
- If elements aren't visible, scroll slowly to find them

 If a cookie consent popup appears, wait up to 5 seconds and look for a button labeled:
   - "Allow all"
   - "Accept all"
   - "Accept"
   If found, click it. If nothing matches, look for any dismiss or close button.

## Workflow:
 
1. Navigate to /data-subject-rights/lab/workflow

2. Create a workflow by clicking "Add Workflow"

3. A pop up will appear , Fill the "Workflow Name" with a unique and non-existing name and save in {workflow_name} and select business unit by clicking the dropdown and select as {business_unit} , Click "Save"
   - Wait for 1-2 seconds for the page to load
   - Then click "Add"

4. You will be redirected to the workflow page , where you can customize the workflow

5. Click "Next" on each step and at the end "save" the workflow

6. A pop up will appear to publish the workflow , Click "Yes,Publish it!"

### After this your workflow will get published ###
### Now we will move to create a form for the end user ###

7. Navigate to /data-subject-rights/lab/form-builder

8. Click on "Create Form" to create new form

9. Enter the "Form Name" with a unique and non-existing name and save in {form_name}

10. Select the {business_unit} from the dropdown and then close it
    - Wait for 1-2 seconds

11. Select the regulations from the "Regulations" dropdown , click any regulation to select 
   - Wait for 1-2 seconds

12. Click the "submit" buttom

### After your form gets created ###

13. Navigate to /data-subject-rights/lab/form-builder to find your form with name {form_name}

14. Click on where it says {form_name} which is a draft for now 

15. Publish the form by clicking "Publish Form"

16. After this , a pop up will appear with a url copy and save the url as {url} , if you could not save the "form url" you can get it at route /data-subject-rights/lab/form-builder and under "Url" Column of that particular Form

17. Navigate to {url} on a new tab! and a form for the customer will appear
    - Incase you find "about:blank" , just paste the url on it , it is basically the new tab

18. Just fill all the required input fields while filling save the first_name in {user_name}, make selection from dropdown and checkboxes , remember to fill a valid yopmail email in the "email" field as {email}

19. Hit "Submit Request" , if fails then maybe you did not fill the whole form , go and fill the remaining fields and then "submit" again

20. A verification pop up will appear

21. Open a new tab to Navigate to https://yopmail.com/

22. Now add the {email}'s domain name only in the input field and hit "->" beside the field

23. you will be navigated to the inbox , find a verification mail from "noreply@gotrust.tech"

24. Click open the mail , get the verification code in the mail, save as {ver_otp}

25. Navigate back to the verification pop up page enter {ver_otp} and hit "verify"

26. Now Navigate back to /data-subject-rights/task-overview

27. You will see a request with {user_name} under "Requested By" , if not then  Find the dropdown , click it to select "Pending Requests" 

28. You should be able to see the request made with today's date and business unit as {business_unit}

'''
    }
