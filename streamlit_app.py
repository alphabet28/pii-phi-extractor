"""
Streamlit UI for PII/PHI Detection and Extraction Pipeline
Provides interactive file upload, real-time detection, and visualization
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from io import StringIO

from extractors.file_extractor import FileExtractor
from detectors.pii_phi_detector import PiiPhiDetector

# Page configuration
st.set_page_config(
    page_title="PII/PHI Detection Pipeline",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .pii-entity { background-color: #ffcccc; padding: 2px 4px; border-radius: 3px; }
    .phi-entity { background-color: #ccffcc; padding: 2px 4px; border-radius: 3px; }
    .confidence-high { color: #d32f2f; font-weight: bold; }
    .confidence-medium { color: #f57c00; font-weight: bold; }
    .confidence-low { color: #fbc02d; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'file_extractor' not in st.session_state:
    st.session_state.file_extractor = FileExtractor()

if 'pii_phi_detector' not in st.session_state:
    st.session_state.pii_phi_detector = PiiPhiDetector()

if 'results' not in st.session_state:
    st.session_state.results = []

if 'confidence_threshold' not in st.session_state:
    st.session_state.confidence_threshold = 0.55

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")
st.session_state.confidence_threshold = st.sidebar.slider(
    "Confidence Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.55,
    step=0.05,
    help="Minimum confidence score for entity detection (0.0-1.0)"
)

st.sidebar.markdown("---")
st.sidebar.title("📋 About")
st.sidebar.info(
    """
    **PII/PHI Detection Pipeline**
    
    This tool detects and extracts Personally Identifiable Information (PII) and 
    Protected Health Information (PHI) from documents.
    
    **Supported Formats:**
    - Text files (.txt, .md)
    - Word documents (.docx)
    - Excel spreadsheets (.xlsx)
    - PDF files (.pdf)
    - Email messages (.eml)
    - Outlook messages (.msg)
    
    **Detection Entities:**
    - SSN, Phone, Credit Card, Passport
    - Medical Record Numbers, Insurance IDs
    - ICD-10 Codes, Dates of Birth
    - Bank Accounts, IP Addresses
    """
)

# Main header
st.title("🔍 PII/PHI Detection Pipeline")
st.markdown("Upload documents to detect and extract sensitive information")

# Tab interface
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload & Process", "📊 Results", "📈 Analytics", "📚 Batch History"])

# ============================================================================
# TAB 1: Upload & Process
# ============================================================================
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Documents")
        uploaded_files = st.file_uploader(
            "Choose files to analyze",
            type=["txt", "md", "docx", "xlsx", "pdf", "eml", "msg"],
            accept_multiple_files=True,
            help="Select one or multiple files"
        )
    
    with col2:
        st.metric("Files Uploaded", len(uploaded_files) if uploaded_files else 0)
    
    if uploaded_files:
        st.markdown("---")
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Save uploaded files to temp directory
            file_paths = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(file_path)
            
            # Process button
            if st.button("🚀 Process Files", key="process_button"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_container = st.container()
                
                st.session_state.results = []
                
                for idx, file_path in enumerate(file_paths):
                    # Update progress
                    progress = (idx) / len(file_paths)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing file {idx + 1}/{len(file_paths)}: {Path(file_path).name}")
                    
                    try:
                        # Stage 1: Extract text
                        extraction_result = st.session_state.file_extractor.extract(file_path)
                        
                        if extraction_result.extraction_status == "success":
                            # Stage 2: Triage and detect PII/PHI
                            triage_result = st.session_state.pii_phi_detector.triage(
                                extraction_result.text
                            )
                            
                            # Filter by confidence threshold
                            filtered_matches = [
                                m for m in triage_result.pii_phi_matches
                                if m.score >= st.session_state.confidence_threshold
                            ]
                            
                            result = {
                                "filename": extraction_result.filename,
                                "filepath": extraction_result.filepath,
                                "filetype": extraction_result.filetype,
                                "extraction_status": extraction_result.extraction_status,
                                "text_preview": extraction_result.text[:500] + "..." if len(extraction_result.text) > 500 else extraction_result.text,
                                "text_full": extraction_result.text,
                                "matches": [
                                    {
                                        "entity_type": m.entity_type,
                                        "value": m.text,
                                        "confidence": m.score,
                                        "start": m.start,
                                        "end": m.end,
                                        "classification": "PII" if m.entity_type in ["US_SSN", "PHONE_NUMBER", "CREDIT_CARD", "PASSPORT_NUMBER", "US_BANK_NUMBER", "IP_ADDRESS", "DATE_OF_BIRTH"] else "PHI"
                                    }
                                    for m in filtered_matches
                                ],
                                "match_count": len(filtered_matches),
                                "contains_pii": any(m["classification"] == "PII" for m in [{"classification": "PII" if x.entity_type in ["US_SSN", "PHONE_NUMBER", "CREDIT_CARD", "PASSPORT_NUMBER", "US_BANK_NUMBER", "IP_ADDRESS", "DATE_OF_BIRTH"] else "PHI"} for x in filtered_matches]),
                                "contains_phi": any(m["classification"] == "PHI" for m in [{"classification": "PII" if x.entity_type in ["US_SSN", "PHONE_NUMBER", "CREDIT_CARD", "PASSPORT_NUMBER", "US_BANK_NUMBER", "IP_ADDRESS", "DATE_OF_BIRTH"] else "PHI"} for x in filtered_matches]),
                                "timestamp": datetime.now().isoformat()
                            }
                            st.session_state.results.append(result)
                        else:
                            result = {
                                "filename": extraction_result.filename,
                                "filepath": extraction_result.filepath,
                                "filetype": extraction_result.filetype,
                                "extraction_status": extraction_result.extraction_status,
                                "error": extraction_result.error,
                                "matches": [],
                                "match_count": 0,
                                "timestamp": datetime.now().isoformat()
                            }
                            st.session_state.results.append(result)
                    
                    except Exception as e:
                        result = {
                            "filename": Path(file_path).name,
                            "filepath": file_path,
                            "extraction_status": "error",
                            "error": str(e),
                            "matches": [],
                            "match_count": 0,
                            "timestamp": datetime.now().isoformat()
                        }
                        st.session_state.results.append(result)
                
                progress_bar.progress(1.0)
                status_text.text("✅ Processing complete!")
                
                # Display results
                st.markdown("---")
                st.subheader("📋 Processing Results")
                
                for result in st.session_state.results:
                    with st.expander(f"📄 {result['filename']}", expanded=result['match_count'] > 0):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Entities Found", result['match_count'])
                        with col2:
                            status_color = "🔴" if result['extraction_status'] != 'success' else "🟢"
                            st.metric("Status", f"{status_color} {result['extraction_status'][:10]}")
                        with col3:
                            pii_count = sum(1 for m in result['matches'] if m['classification'] == 'PII')
                            st.metric("PII", pii_count)
                        with col4:
                            phi_count = sum(1 for m in result['matches'] if m['classification'] == 'PHI')
                            st.metric("PHI", phi_count)
                        
                        if result['extraction_status'] == 'success' and result['matches']:
                            st.markdown("**Detected Entities:**")
                            df_matches = pd.DataFrame(result['matches'])
                            
                            # Color code by entity type
                            def highlight_classification(row):
                                if row['classification'] == 'PII':
                                    return ['background-color: #ffcccc'] * len(row)
                                else:
                                    return ['background-color: #ccffcc'] * len(row)
                            
                            st.dataframe(
                                df_matches[['entity_type', 'value', 'confidence', 'classification']],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "entity_type": st.column_config.TextColumn("Entity Type", width="medium"),
                                    "value": st.column_config.TextColumn("Value", width="large"),
                                    "confidence": st.column_config.NumberColumn("Confidence", format="%.2f", width="small"),
                                    "classification": st.column_config.TextColumn("Type", width="small")
                                }
                            )
                            
                            # Show text preview with highlights
                            st.markdown("**Text Preview with Highlights:**")
                            text_preview = result['text_preview']
                            st.text_area("", value=text_preview, height=150, disabled=True)
                        
                        elif result['extraction_status'] != 'success':
                            st.warning(f"Error: {result.get('error', 'Unknown error')}")
                        else:
                            st.success("✅ No sensitive information detected!")
        
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)

# ============================================================================
# TAB 2: Results
# ============================================================================
with tab2:
    if st.session_state.results:
        st.subheader("All Results")
        
        # Summary statistics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_docs = len(st.session_state.results)
        total_entities = sum(r['match_count'] for r in st.session_state.results)
        flagged_docs = sum(1 for r in st.session_state.results if r['match_count'] > 0)
        total_pii = sum(sum(1 for m in r['matches'] if m['classification'] == 'PII') for r in st.session_state.results)
        total_phi = sum(sum(1 for m in r['matches'] if m['classification'] == 'PHI') for r in st.session_state.results)
        
        with col1:
            st.metric("Total Documents", total_docs)
        with col2:
            st.metric("Flagged Documents", flagged_docs)
        with col3:
            st.metric("Total Entities", total_entities)
        with col4:
            st.metric("PII Matches", total_pii)
        with col5:
            st.metric("PHI Matches", total_phi)
        
        st.markdown("---")
        
        # Results table
        st.subheader("Document Summary")
        
        results_data = []
        for r in st.session_state.results:
            pii_count = sum(1 for m in r['matches'] if m['classification'] == 'PII')
            phi_count = sum(1 for m in r['matches'] if m['classification'] == 'PHI')
            results_data.append({
                "Filename": r['filename'],
                "Type": r['filetype'],
                "Entities": r['match_count'],
                "PII": pii_count,
                "PHI": phi_count,
                "Status": "✅ Success" if r['extraction_status'] == 'success' else f"❌ {r['extraction_status']}"
            })
        
        df_results = pd.DataFrame(results_data)
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        # Export results
        st.markdown("---")
        st.subheader("📥 Export Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON export
            json_data = json.dumps(st.session_state.results, indent=2, default=str)
            st.download_button(
                label="📋 Download as JSON",
                data=json_data,
                file_name=f"pii_phi_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # CSV export
            csv_data = df_results.to_csv(index=False)
            st.download_button(
                label="📊 Download as CSV",
                data=csv_data,
                file_name=f"pii_phi_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No results yet. Upload and process files in the first tab.")

# ============================================================================
# TAB 3: Analytics
# ============================================================================
with tab3:
    if st.session_state.results:
        st.subheader("📊 Analytics Dashboard")
        
        # Entity type breakdown
        entity_counts = {}
        for result in st.session_state.results:
            for match in result['matches']:
                entity_type = match['entity_type']
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        if entity_counts:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Entity Type Distribution**")
                df_entities = pd.DataFrame(
                    list(entity_counts.items()),
                    columns=['Entity Type', 'Count']
                ).sort_values('Count', ascending=False)
                
                st.bar_chart(df_entities.set_index('Entity Type'))
            
            with col2:
                st.markdown("**Classification Breakdown**")
                classification_counts = {}
                for result in st.session_state.results:
                    for match in result['matches']:
                        classification = match['classification']
                        classification_counts[classification] = classification_counts.get(classification, 0) + 1
                
                df_classification = pd.DataFrame(
                    list(classification_counts.items()),
                    columns=['Classification', 'Count']
                )
                st.pie_chart(df_classification.set_index('Classification'))
            
            # Confidence score distribution
            st.markdown("---")
            st.markdown("**Confidence Score Distribution**")
            
            all_confidences = []
            for result in st.session_state.results:
                for match in result['matches']:
                    all_confidences.append(match['confidence'])
            
            if all_confidences:
                df_confidence = pd.DataFrame({'Confidence': all_confidences})
                st.histogram(df_confidence, x='Confidence', nbins=20)
            
            # File type analysis
            st.markdown("---")
            st.markdown("**File Type Analysis**")
            
            filetype_analysis = {}
            for result in st.session_state.results:
                filetype = result['filetype']
                if filetype not in filetype_analysis:
                    filetype_analysis[filetype] = {'count': 0, 'entities': 0}
                filetype_analysis[filetype]['count'] += 1
                filetype_analysis[filetype]['entities'] += result['match_count']
            
            df_filetype = pd.DataFrame([
                {
                    'File Type': ft,
                    'Files': data['count'],
                    'Total Entities': data['entities'],
                    'Avg Per File': round(data['entities'] / data['count'], 2) if data['count'] > 0 else 0
                }
                for ft, data in filetype_analysis.items()
            ])
            
            st.dataframe(df_filetype, use_container_width=True, hide_index=True)
        else:
            st.info("No entities detected. Process some files to see analytics.")
    else:
        st.info("No results yet. Upload and process files in the first tab.")

# ============================================================================
# TAB 4: Batch History
# ============================================================================
with tab4:
    st.subheader("📚 Session History")
    
    if st.session_state.results:
        st.info(f"Current session: {len(st.session_state.results)} files processed")
        
        # Detailed view of all processed files
        for idx, result in enumerate(st.session_state.results, 1):
            with st.expander(f"{idx}. {result['filename']} — {result['timestamp']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Filename:** {result['filename']}")
                    st.write(f"**File Type:** {result['filetype']}")
                    st.write(f"**Status:** {result['extraction_status']}")
                
                with col2:
                    st.write(f"**Entities Found:** {result['match_count']}")
                    st.write(f"**Contains PII:** {result.get('contains_pii', False)}")
                    st.write(f"**Contains PHI:** {result.get('contains_phi', False)}")
                
                if result['matches']:
                    st.write("**Detected Entities:**")
                    for match in result['matches']:
                        severity = "🔴" if match['confidence'] > 0.8 else "🟡" if match['confidence'] > 0.6 else "🟢"
                        st.write(
                            f"{severity} **{match['entity_type']}** ({match['classification']}) "
                            f"- Confidence: {match['confidence']:.2f}"
                        )
        
        # Clear history button
        st.markdown("---")
        if st.button("🗑️ Clear All Results"):
            st.session_state.results = []
            st.rerun()
    else:
        st.info("No processing history yet.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
    PII/PHI Detection Pipeline v1.0 | Powered by Presidio & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
