================================================================================
 ENTERPRISE AI DATA ASSISTANT
 Capstone Project - Contoso Trading Services (sample data)
================================================================================

--------------------------------------------------------------------------------
1. PROJECT OVERVIEW
--------------------------------------------------------------------------------

This project lets a business user ask a question in plain English and get:

  - The SQL query that answers it (auto-generated, read-only, safety-checked)
  - The actual result rows, run against a MySQL database
  - A plain-English explanation of what the query does

It also has a second mode where the user can ask questions about uploaded
policy documents (return policy, warranty terms, sales policy) and get
answers grounded only in those documents.

Architecture (four pieces, each only talking to the one next to it):

  React (UI)  -->  PHP REST layer  -->  FastAPI (AI service)  -->  MySQL + Chroma

  - React (frontend)      the web page the user interacts with
  - PHP REST layer        a thin proxy; forwards requests to FastAPI
  - FastAPI (ai-service)  does all the real work: English->SQL, running the
                          SQL safely, explaining it, and answering from docs
  - MySQL                 holds the business data (read-only access only)
  - Chroma                a local vector database holding the policy documents

--------------------------------------------------------------------------------
2. HOW TO RUN THE PROJECT
--------------------------------------------------------------------------------

All commands below are PowerShell, run on Windows. You need four things
running at the same time, each in its own PowerShell window (except the
one-time setup steps).

REQUIREMENTS (install first if not already installed):
  - Node.js 20+ and npm
  - Python 3.11
  - PHP 8.2
  - MySQL 8.x
  - A Groq API key (from console.groq.com)

STEP 0 - One-time setup (skip if already done)
------------------------------------------------
  1) Clone the project and go into it:

       git clone git@github.com:ChiragAnblicks/enterprise-ai-data-assistant.git
       cd enterprise-ai-data-assistant

  2) Create your secrets file:

       Copy-Item .env.example .env

     Open .env in a text editor and fill in:
       GROQ_API_KEY      = your Groq API key
       DB_RO_PASSWORD    = password for the read-only MySQL user

  3) Create the database (only needed once). Run these in order, from the
     repo root, against your local MySQL server:

       Get-Content db\00_CommandsToCreateNewDatabase.sql | mysql -u root -p
       Get-Content db\01_schema.sql | mysql -u root -p CapstoneCore
       Get-Content db\02_seed_data.sql | mysql -u root -p CapstoneCore
       Get-Content db\03_readonly_user.sql | mysql -u root -p

     This creates the CapstoneCore database, its 11 tables, sample data,
     and the read-only "capstone_ro" MySQL user the app uses.

STEP 1 - Start the AI service (FastAPI) - PowerShell window #1
------------------------------------------------------------------
       cd ai-service
       python -m venv .venv
       .venv\Scripts\Activate.ps1
       pip install -r requirements.txt
       python ingest_docs.py
       uvicorn main:app --reload --port 8000

     (python ingest_docs.py only needs to be run once, or again if a file
     in docs\samples\ changes - it builds the document search index.)

     Leave this window running. Check it worked by opening this in a
     browser: http://127.0.0.1:8000/docs

STEP 2 - Start the PHP REST layer - PowerShell window #2
------------------------------------------------------------
       cd backend-php
       php -S localhost:8080 index.php

     Leave this window running. Check it worked with:
       Invoke-RestMethod http://localhost:8080/health

     It should say fastapi_reachable: True (meaning Step 1 is working too).

STEP 3 - Start the frontend (React) - PowerShell window #3
----------------------------------------------------------------
       cd frontend
       npm install
       npm run dev

     Leave this window running. Open the URL it prints, normally:
       http://localhost:5173/

     Make sure the file frontend\.env.local contains this line:
       VITE_API_BASE_URL=http://localhost:8080

That's it - with all three windows running, the web page at
http://localhost:5173/ is the working app.

--------------------------------------------------------------------------------
3. TECHNOLOGY USED AND WHY
--------------------------------------------------------------------------------

React 19 + Vite (frontend)
  Purpose: the web page the user sees and types into. Vite is just the
  tool that runs and builds the React app quickly.

PHP 8.2 (backend-php)
  Purpose: a simple middle layer between the browser and the AI service.
  It exists mainly to sit in the middle of the request path and hide the
  AI service from the browser directly - it does no AI or database work
  itself, just forwards requests.

FastAPI (Python, ai-service)
  Purpose: the core of the project. Runs all the real logic - turning
  English into SQL, running that SQL safely, explaining it in plain
  English, and answering questions from the uploaded documents.

Groq (LLM: openai/gpt-oss-20b)
  Purpose: the actual AI model that reads the question and writes the
  SQL/explanations/document answers. Groq is used because it is fast and
  free-tier friendly for a student project.

MySQL 8
  Purpose: stores the actual business data (customers, orders, products,
  etc. for the fictional company "Contoso Trading Services"). The app
  only ever connects to it with a read-only user, so nothing the AI
  generates can change or delete data.

HuggingFace embeddings (all-MiniLM-L6-v2) + ChromaDB
  Purpose: used only for the "chat with documents" feature. HuggingFace
  turns each policy document into searchable numeric form (locally, no
  API cost); ChromaDB stores and searches those so the right document
  excerpt can be found and handed to the AI to answer from.

sqlparse (Python library)
  Purpose: used to double-check every piece of SQL the AI writes really
  is a single, safe SELECT statement before it is allowed to run - this
  is the main safety control in the project.

--------------------------------------------------------------------------------
For full details (API request/response formats, diagrams, database schema)
see the README.md and docs/ folder in the project repository, or the Word
document version if you have it.
================================================================================
