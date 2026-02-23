"""
First Draft Tab Component
Handles the First Draft workflow including file upload and content generation
"""

import streamlit as st
import io
from app_functions import apply_prompt_file, format_output


def render_first_draft_tab(output_container):
    """Render the First Draft tab content"""
    # Add custom styling for section headers
    st.markdown("""
        <style>
        .section-header {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<p class="section-header">🎯 Actions</p>', unsafe_allow_html=True)
    
    # First Draft buttons with dynamic styling based on state
    col_draft1, col_draft2, col_draft3, col_draft4 = st.columns([1.2, 1.2, 1.2, 1])
    
    # Determine button types based on state
    find_button_type = "secondary" if st.session_state.find_internal_clicked else "primary"
    draft_button_type = "primary" if st.session_state.find_internal_clicked else "secondary"
    
    with col_draft1:
        explain_sfs_button = st.button(
            "💡 Explain the SFS",
            type="primary",
            use_container_width=True,
            help="Get an explanation of the SFS content"
        )
    
    with col_draft2:
        find_internal_button = st.button(
            "🔍 Find Internal Information", 
            type=find_button_type, 
            use_container_width=True,
            help="Analyze SFS content to identify internal/confidential information"
        )
    
    with col_draft3:
        # Generate First Draft button
        first_draft_button = st.button(
            "✍️ Generate First Draft", 
            type=draft_button_type, 
            use_container_width=True,
            help="Create a customer-facing draft"
        )
    
    with col_draft4:
        clear_button_draft = st.button(
            "🗑️ Clear", 
            use_container_width=True, 
            key="clear_draft",
            help="Reset and start over"
        )
    
    return first_draft_button, clear_button_draft, find_internal_button, explain_sfs_button


def handle_explain_sfs_button(extracted_text: str, product_name: str, output_container):
    """Handle the explain SFS button click"""
    if not extracted_text.strip():
        st.error("⚠️ Please provide SFS content to explain.")
    elif not product_name.strip():
        st.error("⚠️ Please select a product name.")
    else:
        with st.spinner("💡 Explaining SFS content..."):
            try:
                # Store in session state
                st.session_state.product_name = product_name
                st.session_state.current_extracted_text = extracted_text
                st.session_state.initial_analysis_done = True
                
                # Use the apply_prompt_file function with SFSExplainer.md
                explanation = apply_prompt_file("SFSExplainer.md", extracted_text, product_name)
                
                # Add to conversation history
                st.session_state.conversation_history.append({
                    "question": "Explain the SFS",
                    "answer": explanation
                })
                
                with output_container:
                    st.markdown("## 💡 SFS Explanation")
                    st.markdown(explanation)
                    st.info("💬 You can ask follow-up questions below to get more details about specific aspects.")
                
                st.success("✅ SFS explanation complete!")
                
            except Exception as e:
                st.error(f"❌ Error explaining SFS: {str(e)}")
                with st.expander("🐛 Error Details"):
                    st.exception(e)


def handle_first_draft_button(extracted_text: str, product_name: str, output_container):
    """Handle the first draft button click"""
    # Clear previous conversation context when starting First Draft workflow
    if st.session_state.conversation_history:
        # Check if last conversation was Explain SFS
        if st.session_state.conversation_history[-1].get('question') == 'Explain the SFS':
            st.session_state.conversation_history = []
    
    if not extracted_text.strip():
        st.error("⚠️ Please provide document to generate a first draft.")
    elif not product_name.strip():
        st.error("⚠️ Please select a product name.")
    elif not st.session_state.find_internal_clicked:
        st.error("⚠️ Please run 'Find Internal Information' first before generating the first draft.")
    else:
        with st.spinner("✍️ Generating first draft..."):
            try:
                # Store in session state
                st.session_state.product_name = product_name
                st.session_state.current_extracted_text = extracted_text
                st.session_state.initial_analysis_done = True
                
                # Build comprehensive context with internal information guidance
                context = f"Original Content:\n{extracted_text}\n\n"
                
                # Extract and include the internal information analysis
                internal_info_analysis = None
                if st.session_state.conversation_history:
                    for exchange in st.session_state.conversation_history:
                        if exchange.get('question') == 'Find Internal Information':
                            internal_info_analysis = exchange.get('answer')
                            break
                
                # Add clear instructions about internal information
                if internal_info_analysis:
                    context += "=" * 80 + "\n"
                    context += "INTERNAL INFORMATION IDENTIFIED (DO NOT INCLUDE IN CUSTOMER-FACING DRAFT):\n"
                    context += "=" * 80 + "\n"
                    context += internal_info_analysis + "\n"
                    context += "=" * 80 + "\n\n"
                    context += "INSTRUCTIONS: The above section identifies internal/confidential information found in the original content. "
                    context += "When generating the customer-facing first draft, you MUST exclude or rewrite any content that relates to the internal information listed above. "
                    context += "Focus on creating documentation suitable for external customers, removing implementation details, internal architecture, debug information, and any proprietary technical details.\n\n"
                
                # Use the apply_prompt_file function with FirstDraftCTWG.md
                first_draft = apply_prompt_file("FirstDraftCTWG.md", context, product_name)
                
                # Add to conversation history
                st.session_state.conversation_history.append({
                    "question": "Generate First Draft",
                    "answer": first_draft
                })
                
                with output_container:
                    st.markdown("## ✍️ First Draft")
                    st.markdown(first_draft)
                
                st.success("✅ First draft generated!")
                
            except Exception as e:
                st.error(f"❌ Error generating first draft: {str(e)}")
                with st.expander("🐛 Error Details"):
                    st.exception(e)


def handle_find_internal_button(extracted_text: str, product_name: str, output_container):
    """Handle the find internal information button click"""
    # Clear previous conversation context when starting Find Internal workflow
    if st.session_state.conversation_history:
        # Check if last conversation was Explain SFS
        if st.session_state.conversation_history[-1].get('question') == 'Explain the SFS':
            st.session_state.conversation_history = []
    
    if not extracted_text.strip():
        st.error("⚠️ Please provide SFS content to analyze.")
    elif not product_name.strip():
        st.error("⚠️ Please select a product name.")
    else:
        # Mark that Find Internal Information has been completed BEFORE processing
        # This ensures the state is set immediately for the next button click
        st.session_state.find_internal_clicked = True
        
        with st.spinner("🔍 Finding internal information..."):
            try:
                # Store in session state
                st.session_state.product_name = product_name
                st.session_state.current_extracted_text = extracted_text
                st.session_state.initial_analysis_done = True
                
                # Use the apply_prompt_file function with InternalAnalysis.md
                internal_info = apply_prompt_file("InternalAnalysis.md", extracted_text, product_name)
                
                # Add to conversation history
                st.session_state.conversation_history.append({
                    "question": "Find Internal Information",
                    "answer": internal_info
                })
                
                with output_container:
                    st.markdown("## 🔍 Internal Information Analysis")
                    st.markdown(internal_info)
                    st.info("💡 Review the internal information above. If you have questions or need clarification, ask a follow-up question below. Once ready, click **Generate First Draft**.")
                
                st.success("✅ Internal information analysis complete!")
                
            except Exception as e:
                st.error(f"❌ Error analyzing internal information: {str(e)}")
                with st.expander("🐛 Error Details"):
                    st.exception(e)
