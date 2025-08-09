"""
Delhi High Court Case Scraper - Streamlit Application
Automated case search and document retrieval system
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from court_scraper import CourtScraper, DatabaseManager
import logging
import requests
import hashlib
import math

# Configure application settings
st.set_page_config(
    page_title="Delhi High Court Case Tracker",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on startup
DatabaseManager.initialize()

def main():
    """Main application entry point"""
    render_header()
    render_sidebar()
    render_main_content()
    render_footer()

def render_header():
    """Render application header with branding"""
    st.markdown("""
    <div style='background: linear-gradient(90deg, #1f4e79, #2d5aa0); padding: 2rem; margin: -1rem -1rem 2rem -1rem; border-radius: 0 0 15px 15px;'>
        <h1 style='color: white; text-align: center; margin: 0; font-size: 2.5rem; font-weight: 300;'>
            ⚖️ Delhi High Court Case Tracker
        </h1>
        <p style='color: #e1e8f0; text-align: center; margin: 0.5rem 0 0 0; font-size: 1.1rem;'>
            <strong>Case Search & Document Retrieval System</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar with search statistics and recent searches"""
    with st.sidebar:
        # Dashboard header
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; margin: -1rem -1rem 1rem -1rem; border-radius: 0 0 15px 15px;'>
            <h2 style='color: white; margin: 0; text-align: center; font-size: 1.5rem;'>📊 Dashboard</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Display search statistics
        render_search_statistics()
        
        # Display recent searches (limited to 5)
        render_recent_searches()
        
        # Export functionality
        render_export_section()

def render_search_statistics():
    """Display search statistics"""
    st.markdown("### 📈 Search Statistics")
    stats = DatabaseManager.get_search_statistics()
    
    # Display metrics in two columns
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Searches", stats['total_searches'])
        st.metric("Failed", stats['failed_searches'], delta=None)
    
    with col2:
        st.metric("Successful", stats['successful_searches'])
        st.metric("Success Rate", f"{stats['success_rate']}%")

def render_recent_searches():
    """Display the 5 most recent successful searches"""
    st.markdown("### 🕒 Recent Searches")
    recent_searches = DatabaseManager.get_recent_searches(limit=5)
    
    if recent_searches:
        for i, search in enumerate(recent_searches):
            case_number = search['case_number']
            case_type = search['case_type']
            filing_year = search['filing_year']
            search_time = search['search_time']
            
            # Create unique key for each search button
            unique_key = f"repeat_{i}_{hashlib.md5(f'{case_number}_{search_time}'.encode()).hexdigest()[:8]}"
            
            with st.expander(f"📋 {case_number}", expanded=False):
                st.write(f"**Type:** {case_type}")
                st.write(f"**Year:** {filing_year}")
                st.write(f"**Searched:** {search_time}")
                
                # Allow users to repeat previous searches
                if st.button(f"🔄 Search Again", key=unique_key, help=f"Repeat search for {case_number}"):
                    # Store search parameters in session state
                    st.session_state.repeat_search = {
                        'case_type': case_type,
                        'case_number': case_number.split()[-1].split('/')[0],  # Extract number only
                        'filing_year': filing_year
                    }
                    st.rerun()
    else:
        st.info("No recent searches found")

def render_export_section():
    """Render export functionality"""
    st.markdown("### 📥 Export Data")
    
    # Export search history button
    if st.button("📄 Export History", help="Export search history to CSV"):
        export_search_history()

def export_search_history():
    """Export search history to CSV file"""
    try:
        searches = DatabaseManager.get_all_searches()
        if searches:
            # Convert to DataFrame for CSV export
            df = pd.DataFrame(searches)
            csv_data = df.to_csv(index=False)
            
            # Provide download button
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"court_search_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.success("✅ Export ready for download!")
        else:
            st.info("No search history to export")
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")

def render_main_content():
    """Render main application content with two tabs"""
    # Handle repeat search requests from sidebar
    if 'repeat_search' in st.session_state:
        # Pre-fill form with previous search parameters
        repeat_data = st.session_state.repeat_search
        st.session_state.form_case_type = repeat_data['case_type']
        st.session_state.form_case_number = repeat_data['case_number']
        st.session_state.form_filing_year = int(repeat_data['filing_year'])
        # Clear the repeat search flag
        del st.session_state.repeat_search
    
    # Create main application tabs
    tab1, tab2 = st.tabs(["🔍 Case Search", "📚 Search History"])
    
    with tab1:
        render_search_tab()
    
    with tab2:
        render_history_tab()

def render_search_tab():
    """Render case search form and results"""
    st.markdown("## 🔍 Case Information Search")
    
    # Create search form
    with st.form("case_search_form", clear_on_submit=False):
        # Input fields in three columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            case_type = st.selectbox(
                "📁 Case Type",
                ["ADMIN.REPORT","ARB.A.","ARB. A. (COMM.)","ARB.P.","BAIL APPLN.","CA","CA (COMM.IPD-CR)","C.A.(COMM.IPD-GI)","C.A.(COMM.IPD-PAT)","C.A.(COMM.IPD-PV)","C.A.(COMM.IPD-TM)","CAVEAT(CO.)","CC(ARB.)","CCP(CO.)","CCP(REF)","CEAC","CEAR","CHAT.A.C.","CHAT.A.REF","CMI","CM(M)","CM(M)-IPD","C.O.","CO.APP.","CO.APPL.(C)","CO.APPL.(M)","CO.A(SB)","C.O.(COMM.IPD-CR)","C.O.(COMM.IPD-GI)","C.O.(COMM.IPD-PAT)","C.O. (COMM.IPD-TM)","CO.EX.","CONT.APP.(C)","CONT.CAS(C)","CONT.CAS.(CRL)","CO.PET.","C.REF.(O)","CRL.A.","CRL.L.P.","CRL.M.C.","CRL.M.(CO.)","CRL.M.I.","CRL.O.","CRL.O.(CO.)","CRL.REF.","CRL.REV.P.","CRL.REV.P.(MAT.)","CRL.REV.P.(NDPS)","CRL.REV.P.(NI)","C.R.P.","CRP-IPD","C.RULE","CS(COMM)","CS(OS)","CS(OS) GP","CUSAA","CUS.A.C.","CUS.A.R.","CUSTOM A.","DEATH SENTENCE REF.","DEMO","EDC","EDR","EFA(COMM)","EFA(OS)","EFA(OS) (COMM)","EFA(OS)(IPD)","EL.PET.","ETR","EX.F.A.","EX.P.","EX.S.A.","FAO","FAO (COMM)","FAO-IPD","FAO(OS)","FAO(OS) (COMM)","FAO(OS)(IPD)","GCAC","GCAR","GTA","GTC","GTR","I.A.","I.P.A.","ITA","ITC","ITR","ITSA","LA.APP.","LPA","MAC.APP.","MAT.","MAT.APP.","MAT.APP.(F.C.)","MAT.CASE","MAT.REF.","MISC. APPEAL(PMLA)","OA","OCJA","O.M.P.","O.M.P. (COMM)","OMP (CONT.)","O.M.P. (E)","O.M.P. (E) (COMM.)","O.M.P.(EFA)(COMM.)","O.M.P. (ENF.)","OMP (ENF.) (COMM.)","O.M.P.(I)","O.M.P.(I) (COMM.)","O.M.P. (J) (COMM.)","O.M.P. (MISC.)","O.M.P.(MISC.)(COMM.)","O.M.P.(T)","O.M.P. (T) (COMM.)","O.REF.","RC.REV.","RC.S.A.","RERA APPEAL","REVIEW PET.","RFA","RFA(COMM)","RFA-IPD","RFA(OS)","RFA(OS)(COMM)","RF(OS)(IPD)","RSA","SCA","SDR","SERTA","ST.APPL.","STC","ST.REF.","SUR.T.REF.","TEST.CAS.","TR.P.(C)","TR.P.(C.)","TR.P.(CRL.)","VAT APPEAL","W.P.(C)","W.P.(C)-IPD","WP(C)(IPD)","W.P.(CRL)","WTA","WTC","WTR"],
                index=0,
                key="form_case_type",
                help="Select the type of case you want to search"
            )
        
        with col2:
            case_number = st.text_input(
                "🔢 Case Number",
                placeholder="Enter case number (e.g., 123)",
                key="form_case_number",
                help="Enter the case number without year or type"
            )
        
        with col3:
            current_year = datetime.now().year
            filing_year = st.selectbox(
                "📅 Filing Year",
                list(range(current_year, 1950, -1)),
                index=0,
                key="form_filing_year",
                help="Select the year when the case was filed"
            )
        
        # Form submission button
        submit_button = st.form_submit_button("🔍 Search Case Details", use_container_width=True)
        
        # Handle form submission
        if submit_button:
            # Validate input
            if not case_number.strip():
                st.error("❌ Please enter a case number")
                return
            
            if not case_number.isdigit():
                st.error("❌ Case number should contain only digits")
                return
            
            # Execute search
            perform_case_search(case_type, case_number.strip(), filing_year)

def perform_case_search(case_type: str, case_number: str, filing_year: int):
    """Execute case search with progress tracking and display results"""
    search_container = st.container()
    
    with search_container:
        st.markdown("### 🔄 Search Progress")
        
        # Initialize progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(message: str, percentage: int):
            """Update progress bar and status message"""
            progress_bar.progress(percentage)
            status_text.text(f"⏳ {message}")
        
        try:
            # Initialize court scraper
            scraper = CourtScraper()
            
            # Perform case search with progress updates
            case_data = scraper.search_case_details(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                progress_callback=update_progress
            )
            
            if case_data:
                # Display success status
                progress_bar.progress(100)
                status_text.markdown("✅ **Search completed successfully!**")
                
                # Show search results
                st.success(f"✅ Found case: **{case_data['case_number']}**")
                
                # Display case details
                display_case_details_compact(case_data, context="search")
                
                # Store in session state for reference
                st.session_state.latest_case_data = case_data
                
                # Provide user guidance
                st.info("💡 **Tip:** This search result has been automatically saved to your search history. Switch to 'Search History' tab to view all previous searches.")
                
            else:
                # Handle no results found
                progress_bar.progress(100)
                status_text.markdown("❌ **No case found**")
                st.error("❌ No case found with the provided details. Please verify case number, type, and filing year.")
                
        except Exception as e:
            # Handle search errors
            progress_bar.progress(100)
            status_text.markdown("❌ **Search failed**")
            error_msg = str(e)
            st.error(f"❌ Search failed: {error_msg}")
            
            # Provide error guidance
            if "Security verification failed" in error_msg:
                st.info("💡 **Tip:** The court website's security verification failed. Please try again in a few moments.")
            elif "No case found" in error_msg:
                st.info("💡 **Tip:** Please verify the case number, type, and filing year are correct.")
            elif "internet connection" in error_msg.lower():
                st.info("💡 **Tip:** Please check your internet connection and try again.")

def display_case_details_compact(case_data: dict, context: str = "search"):
    """Display case details in a compact format"""
    # Case header with case number
    st.markdown(f"### 📄 Case: {case_data['case_number']}")
    
    # Main case information in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Case Status")
        # Color-coded status display
        status_color = "green" if case_data.get('status') == 'ACTIVE' else "orange"
        st.markdown(f"**Status:** <span style='color: {status_color}; font-weight: bold;'>{case_data.get('status', 'N/A')}</span>", unsafe_allow_html=True)
        st.markdown(f"**Court Number:** {case_data.get('court_no', 'N/A')}")
        st.markdown(f"**Case Type:** {case_data.get('case_type', 'N/A')}")
        st.markdown(f"**Filing Year:** {case_data.get('filing_year', 'N/A')}")
    
    with col2:
        st.markdown("#### 📅 Important Dates")
        st.markdown(f"**Next Hearing:** {case_data.get('next_date', 'Not Scheduled')}")
        st.markdown(f"**Last Hearing:** {case_data.get('last_date', 'Not Available')}")
        st.markdown(f"**Data Retrieved:** {format_datetime(case_data.get('extracted_at', ''))}")
    
    # Parties information section
    if case_data.get('parties'):
        if context == "search":
            # Expandable section for search results
            with st.expander("👥 Parties Involved", expanded=False):
                st.text_area("Parties", case_data['parties'], height=100, disabled=True, 
                           key=f"parties_{context}_{hashlib.md5(case_data['case_number'].encode()).hexdigest()[:8]}")
        else:
            # Compact display for history
            st.markdown("#### 👥 Parties Involved")
            st.text_area("Parties", case_data['parties'], height=60, disabled=True, 
                       key=f"parties_{context}_{hashlib.md5(case_data['case_number'].encode()).hexdigest()[:8]}")
    
    # Orders and documents section
    if case_data.get('orders'):
        orders = case_data['orders']
        
        if context == "search":
            # Full display for search results
            with st.expander(f"📑 Orders & Documents ({len(orders)} orders)", expanded=True):
                display_orders_list(orders, case_data, context)
        else:
            # Compact display for history with pagination
            display_orders_compact(orders, case_data, context)

def display_orders_list(orders, case_data, context):
    """Display orders list for search results"""
    for i, order in enumerate(orders):
        display_single_order_compact(order, i, case_data, context)

def display_orders_compact(orders, case_data, context):
    """Display orders in compact format with show more/less functionality"""
    st.markdown(f"#### 📑 Orders & Documents ({len(orders)} orders)")
    
    # Show only first 2 orders by default
    orders_to_show = min(2, len(orders))
    
    for i in range(orders_to_show):
        order = orders[i]
        display_single_order_compact(order, i, case_data, context)
    
    # Show expansion option if more than 2 orders exist
    if len(orders) > 2:
        show_more_key = f"show_more_{context}_{hashlib.md5(case_data['case_number'].encode()).hexdigest()[:8]}"
        
        if st.button(f"📋 Show All {len(orders)} Orders", key=show_more_key):
            st.session_state[f"expanded_{context}_{case_data['case_number']}"] = True
            st.rerun()
        
        # Display all orders if expanded
        if st.session_state.get(f"expanded_{context}_{case_data['case_number']}", False):
            for i in range(2, len(orders)):
                order = orders[i]
                display_single_order_compact(order, i, case_data, context)
            
            # Show collapse option
            if st.button(f"📋 Show Less", key=f"show_less_{show_more_key}"):
                st.session_state[f"expanded_{context}_{case_data['case_number']}"] = False
                st.rerun()

def display_single_order_compact(order, i, case_data, context):
    """Display individual order in compact three-column format"""
    with st.container():
        order_col1, order_col2, order_col3 = st.columns([2, 2, 1])
        
        with order_col1:
            st.markdown(f"**📄 Order {order.get('order_index', i+1)}**")
            st.caption(f"Date: {order.get('date', 'Not available')}")
        
        with order_col2:
            # Truncate long descriptions for compact display
            case_info = order.get('case_info', 'Not available')
            display_info = case_info[:50] + '...' if len(case_info) > 50 else case_info
            st.caption(f"Details: {display_info}")
        
        with order_col3:
            if order.get('pdf_link'):
                # Generate unique key for download button
                download_key = f"download_{context}_{i}_{hashlib.md5(f'{case_data["case_number"]}_{i}'.encode()).hexdigest()[:8]}"
                
                # Attempt direct PDF download
                try:
                    response = requests.get(order['pdf_link'], timeout=5)
                    if response.status_code == 200:
                        filename = f"Order_{order.get('order_index', i+1)}_{case_data['case_number'].replace('/', '_')}.pdf"
                        
                        # Provide download button
                        st.download_button(
                            label="📥 PDF",
                            data=response.content,
                            file_name=filename,
                            mime="application/pdf",
                            key=download_key,
                            help="Download order document"
                        )
                    else:
                        # Fallback to view link
                        st.markdown(f"[🔗 View]({order['pdf_link']})")
                except:
                    # Error fallback to view link
                    st.markdown(f"[🔗 View]({order['pdf_link']})")
        
        st.markdown("---")

def render_history_tab():
    """Render search history with pagination"""
    st.markdown("## 📚 Search History")
    
    # Retrieve all search history from database
    all_searches = DatabaseManager.get_complete_search_history()
    
    if not all_searches:
        st.info("📝 **No search history found.** Search for cases to see them appear here.")
        return
    
    # Configure pagination
    items_per_page = 3  # Show 3 cases per page
    total_items = len(all_searches)
    total_pages = math.ceil(total_items / items_per_page)
    
    # Initialize current page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Render pagination navigation
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    
    with nav_col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_page <= 1):
            st.session_state.current_page -= 1
            st.rerun()
    
    with nav_col2:
        # Page information and jump functionality
        st.markdown(f"<div style='text-align: center; padding: 0.5rem;'><strong>Page {st.session_state.current_page} of {total_pages}</strong><br>({total_items} total searches)</div>", unsafe_allow_html=True)
        
        # Page jump dropdown
        new_page = st.selectbox("Jump to page:", range(1, total_pages + 1), 
                               index=st.session_state.current_page - 1, 
                               key="page_select", label_visibility="collapsed")
        if new_page != st.session_state.current_page:
            st.session_state.current_page = new_page
            st.rerun()
    
    with nav_col3:
        if st.button("➡️ Next", disabled=st.session_state.current_page >= total_pages):
            st.session_state.current_page += 1
            st.rerun()
    
    # Calculate pagination boundaries
    start_idx = (st.session_state.current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_page_searches = all_searches[start_idx:end_idx]
    
    # Display paginated search results
    for i, search in enumerate(current_page_searches, 1):
        case_number = search['case_number']
        search_time = search.get('search_time', search.get('created_at', 'Unknown'))
        
        # Create case card
        with st.container():
            st.markdown(f"""
            <div style='border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; background: linear-gradient(90deg, #f8f9fa, #ffffff);'>
                <h5 style='margin: 0; color: #1f4e79; font-size: 1.1rem;'>📋 {case_number}</h5>
                <p style='margin: 0.2rem 0; color: #666; font-size: 0.9rem;'>Searched: {search_time}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display case details in compact format
            display_case_details_compact(search, context=f"history_{start_idx + i}")
            
            # Add separator between cases
            st.markdown("<hr style='margin: 1.5rem 0; border: 1px solid #eee;'>", unsafe_allow_html=True)

def format_datetime(datetime_str: str) -> str:
    """Format datetime string for display"""
    try:
        if datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        return 'Not Available'
    except:
        return datetime_str or 'Not Available'

def render_footer():
    """Render application footer"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>Delhi High Court Case Tracker</strong></p>
        <p>Case search and document retrieval system</p>
    </div>
    """, unsafe_allow_html=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    main()
