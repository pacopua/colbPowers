import streamlit as st
import os
import sys
import tempfile
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from github import Github, Auth
from loguru import logger

# --- PATH SETUP ---
current_dir = Path(__file__).resolve().parent
# ext_services_dir = current_dir / "ext_services" 
project_root = current_dir.parent.parent

# if str(ext_services_dir) not in sys.path:
#     sys.path.append(str(ext_services_dir))

if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- CONFIG ---
st.set_page_config(page_title="Project Assistant", layout="wide", page_icon="🤖")
load_dotenv()

# --- IMPORTS AFTER PATH SETUP ---
try:
    from issue_manager.azure_storage_manger.storage_manager import StorageManager
    from issue_manager.azure_storage_manger.backends.azure import AzureStorageBackend, AzureBackendConfig
    from issue_manager.organizador import AzureOrganizer
    # Imported moved function
    from issue_manager.add_issue import create_github_issues
    from speech_transcriptor.src.main import SpeechToText
    from transcription_preprocessing.processor import TranscriptionProcessor
    from github_manager.add_file import upload_file_to_repo
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "speech-issues")
config = AzureBackendConfig(
    protocol="az",
    connection_string=connection_string,
    create_parent_dirs=True
)

# Initialize backend
backend = AzureStorageBackend(config)

try:
    # Check if container exists using the underlying fsspec filesystem
    if not backend.fs.exists(container_name):
        logger.info(f"Container '{container_name}' does not exist. Creating it...")
        backend.fs.mkdir(container_name)
        logger.info(f"Container '{container_name}' created.")
    else:
        logger.info(f"Container '{container_name}' already exists.")
except Exception as e:
    logger.info(f"Warning: Could not check/create container: {e}")
    logger.info("Ensure the container exists manually if this fails.")

storage_client = StorageManager(backend, base_uri=f"az://{container_name}")
organizer = AzureOrganizer(storage_client)


# --- STATE MANAGEMENT ---
if 'transcript_text' not in st.session_state:
    st.session_state.transcript_text = None
if 'blob_url' not in st.session_state:
    st.session_state.blob_url = None
if 'issues' not in st.session_state:
    st.session_state.issues = None
if 'issues_chat_history' not in st.session_state:
    st.session_state.issues_chat_history = []
if 'created_issues_links' not in st.session_state:
    st.session_state.created_issues_links = None

# --- HELPER FUNCTIONS ---
def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def download_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"Error downloading text: {e}")
        return None

def reset_state():
    st.session_state.transcript_text = None
    st.session_state.blob_url = None
    st.session_state.issues = None
    st.session_state.issues_chat_history = []
    st.session_state.created_issues_links = None
    st.session_state.issues = None
    st.session_state.created_issues_links = None

# --- UI ---
st.title("Project Assistant 🤖")
st.markdown("Transcribe audio meetings and automatically convert them into GitHub Issues.")

# Sidebar Controls
st.sidebar.header("Configuration")
mode = st.sidebar.selectbox("Pipeline Mode", [
    "Audio -> Plan (Full)",
    "Text Context -> Issues",
    "JSON Issues -> GitHub"
], on_change=reset_state)

st.sidebar.markdown("---")
# project_name = st.sidebar.text_input("Project Name", "ProjectFolderCreationTrial")
# client_name = st.sidebar.text_input("Client Name", "ClientFolderCreationTrial")
repo_name = st.sidebar.text_input("Target GitHub Repo", "Adria-Colbai/issue-api")

# --- CLIENT & PROJECT SELECTION ---
existing_clients = organizer.list_clients()
client_selection = st.sidebar.selectbox("Client", ["++ Create New Client ++"] + existing_clients)

if client_selection == "++ Create New Client ++":
    client_name = st.sidebar.text_input("New Client Name")
else:
    client_name = client_selection

project_name = None
if client_name:
    # If client is known (exists in the list), show projects dropdown
    if client_name in existing_clients:
        existing_projects = organizer.list_projects(client_name)
        project_selection = st.sidebar.selectbox("Project", ["++ Create New Project ++"] + existing_projects)
        
        if project_selection == "++ Create New Project ++":
            project_name = st.sidebar.text_input("New Project Name")
        else:
            project_name = project_selection
    else:
        # New client -> Text input for project (cannot list existing projects for a new client)
        project_name = st.sidebar.text_input("New Project Name")

# --- MAIN FLOW ---

# ==========================================
# MODE 1: AUDIO -> TRANSCRIPTION
# ==========================================
if mode == "Audio -> Plan (Full)":
    st.header("1. Upload Audio & Transcribe")
    uploaded_audio = st.file_uploader("Upload Audio File", type=['m4a', 'mp3', 'wav', 'mp4'])
    
    if st.button("Start Transcription", type="primary", disabled=not uploaded_audio):
        with st.spinner("Processing Audio... (This may take a while)"):
             # Reset downstream state
            st.session_state.issues = None
            st.session_state.created_issues_links = None
            
            temp_path = save_uploaded_file(uploaded_audio)
            if temp_path:
                try:
                    stt = SpeechToText(project_name, client_name)
                    blob_url = stt.transcribe_and_blob(temp_path)
                    
                    st.session_state.blob_url = blob_url
                    st.session_state.transcript_text = download_text_from_url(blob_url)
                    
                    if st.session_state.transcript_text:
                        st.success("Transcription Complete!")
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

# ==========================================
# MODE 2: TRANSCRIPTION INPUT
# ==========================================
elif mode == "Text Context -> Issues":
    st.header("1. Input Project Context")
    
    st.info("Upload a meeting transcript, requirement document, or paste a project description.")
    
    tab1, tab2 = st.tabs(["Upload File", "Paste Text"])
    
    with tab1:
        uploaded_trans = st.file_uploader("Upload Document (.txt)", type=['txt'])
        if uploaded_trans:
            st.session_state.transcript_text = str(uploaded_trans.read(), "utf-8")
            
    with tab2:
        pasted_text = st.text_area("Paste Project Description/Context Here", height=300)
        if pasted_text:
            st.session_state.transcript_text = pasted_text

# ==========================================
# COMMON: SHOW TRANSCRIPT
# ==========================================
if st.session_state.transcript_text and mode != "JSON Issues -> GitHub":
    with st.expander("View Context / Transcript", expanded=False):
        st.text_area("Content", st.session_state.transcript_text, height=300, key="transcript_viewer")
    
    if st.session_state.blob_url:
        st.markdown(f"**Archive URL:** [Link]({st.session_state.blob_url})")


# ==========================================
# PART 2: SMART WORKFLOW (HITL)
# ==========================================
if mode != "JSON Issues -> GitHub":
    if st.session_state.transcript_text:
        st.markdown("---")
        st.header("2. AI Planning & Architecture")
        
        # --- INIT STEPS ---
        if 'workflow_step' not in st.session_state:
            st.session_state.workflow_step = 1  # 1: Plan Research, 2: Review Research, 3: Review Plan, 4: Issues
        if 'research_queries' not in st.session_state:
            st.session_state.research_queries = []
        if 'research_results' not in st.session_state:
            st.session_state.research_results = ""
        if 'arch_plan' not in st.session_state:
            st.session_state.arch_plan = ""
        
        # --- Chat Histories ---
        if 'queries_chat_history' not in st.session_state:
            st.session_state.queries_chat_history = []
        if 'plan_chat_history' not in st.session_state:
            st.session_state.plan_chat_history = []

        logger.info("Initialized workflow state variables.")
        if 'issues_chat_history' not in st.session_state:
            logger.info("Initializing issues_chat_history in session state.")
            st.session_state.issues_chat_history = []

        # Instanciar procesador
        processor = TranscriptionProcessor()

        # --- STEP 1: ANALYZE NEEDS ---
        if st.session_state.workflow_step == 1:
            st.subheader("Step 2.1: Analyze Needs & Research Questions")
            st.info("The AI will analyze the transcript to identify technical unknowns and propose queries.")
            
            max_queries = st.number_input("Max search queries", min_value=1, max_value=5, value=3)

            if st.button("Analyze Needs"):
                with st.spinner("Analyzing transcript..."):
                    try:
                        plan_data = processor.generate_research_plan(st.session_state.transcript_text, max_queries=max_queries)
                        st.session_state.research_queries = plan_data.get("queries", [])
                        st.session_state.workflow_step = 2
                        st.rerun()
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

        # --- STEP 2: REVIEW QUERIES & EXECUTE ---
        if st.session_state.workflow_step == 2:
            st.subheader("Step 2.2: Review Research Queries (HITL)")
            
            # --- AI Refinement for Queries ---
            col_refine, col_manual = st.columns([1, 1]) # Layout

            refine_queries_input = st.chat_input("Ask AI to change queries (e.g. 'Add a search about Next.js vs React')")
            if refine_queries_input:
                # Add to history
                st.session_state.queries_chat_history.append({"role": "user", "content": refine_queries_input})
                with st.spinner("Refining queries with AI..."):
                    try:
                        # Use processor to refine with history
                        new_queries_data = processor.refine_research_plan(
                            st.session_state.research_queries, 
                            refine_queries_input,
                            chat_history=st.session_state.queries_chat_history
                        )
                        st.session_state.research_queries = new_queries_data.get("queries", [])
                        # Augment history with "response"
                        st.session_state.queries_chat_history.append({"role": "assistant", "content": "Updated queries."})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Query refinement failed: {e}")
            
            # Show chat history for queries context
            if st.session_state.queries_chat_history:
                with st.expander("Conversation History", expanded=False):
                    for msg in st.session_state.queries_chat_history:
                        st.chat_message(msg["role"]).write(msg["content"])

            # Editable Dataframe for queries
            if st.session_state.research_queries:
                edited_queries = st.data_editor(
                    st.session_state.research_queries, 
                    num_rows="dynamic",
                    column_config={
                        "query": "Search Query",
                        "rationale": "Reason"
                    },
                    use_container_width=True,
                    key="queries_editor"
                )
                # Only update if user manually interacted with editor
                if edited_queries != st.session_state.research_queries:
                     st.session_state.research_queries = edited_queries
            else:
                st.warning("AI didn't find specific things to research. You can add queries manually.")
                # Allow adding manually even if empty
                st.session_state.research_queries = st.data_editor(
                    [{"query": "Enter query...", "rationale": "Manual entry"}],
                    num_rows="dynamic",
                    use_container_width=True,
                    key="queries_editor_empty"
                )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Run Research with Tavily"):
                    with st.spinner("Searching the web..."):
                        # Convert edited rows to list of dicts
                        queries_to_run = st.session_state.research_queries
                        
                        results = processor.execute_research(queries_to_run)
                        st.session_state.research_results = results
                        st.session_state.workflow_step = 3
                        st.rerun()
            with col2:
                if st.button("Skip Research (Go to Plan)"):
                    st.session_state.research_results = "Skipped research."
                    st.session_state.workflow_step = 3
                    st.rerun()
                    
        # --- STEP 3: GENERATE & REVIEW PLAN ---
        if st.session_state.workflow_step == 3:
            st.subheader("Step 2.3: Architectural Plan (HITL)")
            
            if not st.session_state.arch_plan:
                with st.spinner("Drafting Implementation Plan..."):
                    plan_md = processor.generate_architectural_plan(
                        st.session_state.transcript_text, 
                        st.session_state.research_results
                    )
                    st.session_state.arch_plan = plan_md
                    st.rerun()
            
            # --- AI Refinement for Plan ---
            refine_plan_input = st.chat_input("Ask AI to modify the plan (e.g. 'Use Azure SQL instead of PostgreSQL')")
            if refine_plan_input:
                # Add to history
                st.session_state.plan_chat_history.append({"role": "user", "content": refine_plan_input})
                with st.spinner("Refining plan with AI..."):
                    try:
                        updated_plan = processor.refine_architectural_plan(
                            st.session_state.arch_plan,
                            refine_plan_input,
                            chat_history=st.session_state.plan_chat_history
                        )
                        st.session_state.arch_plan = updated_plan
                        # Augment history
                        st.session_state.plan_chat_history.append({"role": "assistant", "content": "Updated architectural plan."})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Plan refinement failed: {e}")
            
            if st.session_state.plan_chat_history:
                with st.expander("Conversation History", expanded=False):
                    for msg in st.session_state.plan_chat_history:
                        st.chat_message(msg["role"]).write(msg["content"])

            st.write("Review and edit the proposed plan before generating issues:")
            edited_plan = st.text_area("Implementation Plan (Markdown)", st.session_state.arch_plan, height=500)
            if edited_plan != st.session_state.arch_plan:
                 st.session_state.arch_plan = edited_plan

            with st.expander("Preview Rendered Plan", expanded=False):
                st.markdown(edited_plan)
            
            if st.button("Approve Plan & Generate Issues"):
                with st.spinner("Extracting issues and uploading plan..."):
                    logger.info("Uploading arch plan to github...")

                    succes, url = upload_file_to_repo(
                        folder="plans",
                        file_name=f"{project_name}_plan.md",
                        content=st.session_state.arch_plan,
                        repo_name=repo_name,
                        branch="main"
                    )

                    if succes:
                        logger.info(f"Plan uploaded successfully: {url}")
                    else:
                        logger.error("Failed to upload plan to GitHub.")

                    result = processor.extract_issues_from_plan(st.session_state.arch_plan)
                    st.session_state.issues = result.get("issues", [])
                    st.session_state.workflow_step = 4
                    st.rerun()

        # --- STEP 4: ISSUES GENERATED ---
        if st.session_state.workflow_step == 4:
            st.success("Plan processed! Issues generated below.")
            if st.button("Restart Planning Phase"):
                st.session_state.workflow_step = 1
                st.rerun()

# ==========================================
# MODE 3: JSON INPUT
# ==========================================
elif mode == "JSON Issues -> GitHub":
    st.header("1. Input Issues JSON")
    
    tab1, tab2 = st.tabs(["Upload JSON", "Paste JSON"])
    
    json_content = None
    with tab1:
        uploaded_json = st.file_uploader("Upload Issues JSON", type=['json'])
        if uploaded_json:
            try:
                json_content = json.load(uploaded_json)
            except Exception as e:
                st.error(f"Invalid JSON file: {e}")

    with tab2:
        pasted_json = st.text_area("Paste JSON Here", height=300)
        if pasted_json:
            try:
                json_content = json.loads(pasted_json)
            except Exception as e:
                st.error(f"Invalid JSON text: {e}")

    if json_content:
        if st.button("Load Issues from JSON"):
            # Normalize structure: handle if root is list or dict with "issues" key
            if isinstance(json_content, dict) and "issues" in json_content:
                st.session_state.issues = json_content["issues"]
            elif isinstance(json_content, list):
                st.session_state.issues = json_content
            else:
                st.error("JSON must be a list of issues or a dict with an 'issues' key.")
                st.session_state.issues = None
            
            st.session_state.created_issues_links = None
            st.rerun()

# ==========================================
# COMMON: PREVIEW & UPLOAD
# ==========================================
if st.session_state.issues:
    st.info(f"Ready to upload {len(st.session_state.issues)} issues.")
    
    st.markdown("### 2.1 Refine & Edit")
    
    # --- AI Refinement ---
    refine_query = st.chat_input("Ask AI to modify issues (e.g. 'Change priority of issue 2 to High')")
    if refine_query:
        # Add to history
        st.session_state.issues_chat_history.append({"role": "user", "content": refine_query})
        with st.spinner("Refining issues with AI..."):
            try:
                logger.info(f"User query for refinement: '{refine_query}'")
                # Re-initialize processor if needed or reuse instance
                processor = TranscriptionProcessor()
                result_json = processor.refine_issues(
                    st.session_state.issues, 
                    refine_query,
                    chat_history=st.session_state.issues_chat_history
                )
                if "issues" in result_json:
                    st.session_state.issues = result_json["issues"]
                    # Augment history
                    st.session_state.issues_chat_history.append({"role": "assistant", "content": "Updated issues list."})
                    st.rerun()
            except Exception as e:
                st.error(f"Refinement failed: {e}")
                
    if st.session_state.issues_chat_history:
        with st.expander("Conversation History", expanded=False):
            for msg in st.session_state.issues_chat_history:
                st.chat_message(msg["role"]).write(msg["content"])

    # --- Manual Edition ---
    st.write("You can manually edit the table below:")
    edited_df = st.data_editor(
        st.session_state.issues,
        num_rows="dynamic",
        use_container_width=True,
        key="issue_editor"
    )
    
    # Update session state with manual edits if they differ
    # st.data_editor returns the current state of the data
    if edited_df != st.session_state.issues:
        logger.info("Issues manually edited by user.")
        st.session_state.issues = edited_df
        logger.info(f"Current number of issues after update: {len(st.session_state.issues)}")

    st.markdown("---")
    st.header("3. Sync to GitHub")
    
    if st.button(f"Upload {len(st.session_state.issues)} Issues to GitHub"):
        with st.spinner("Creating issues on GitHub..."):
            progress_bar = st.progress(0)
            
            def update_progress(p):
                progress_bar.progress(p)
                
            success, links = create_github_issues(
                st.session_state.issues, 
                repo_name,
                progress_callback=update_progress
            )
            
            progress_bar.empty()
            
            if success:
                st.session_state.created_issues_links = links
                st.success("Upload Successful!")
                st.balloons()
            else:
                st.error("Failed to upload issues.")

if st.session_state.created_issues_links:
    st.subheader("Created Issues:")
    for link in st.session_state.created_issues_links:
        st.markdown(f"- {link}")