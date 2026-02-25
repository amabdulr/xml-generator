import streamlit as st
import os
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import io

def convert_to_kebab_case(text):
    """Convert text to kebab-case format."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

def update_xml_id(xml_content, file_id, content_type):
    """Update the ID attribute in the XML content."""
    # Map content types to their XML element names
    type_mapping = {
        'concept': 'ct_concept',
        'task': 'ct_task',
        'process': 'ct_process',
        'principle': 'ct_principle',
        'reference': 'ct_concept'  # reference uses ct_concept element
    }
    
    element_name = type_mapping.get(content_type, 'ct_concept')
    
    # Find and replace the id attribute
    pattern = f'<{element_name} id="[^"]*"'
    replacement = f'<{element_name} id="{file_id}"'
    updated_content = re.sub(pattern, replacement, xml_content)
    
    return updated_content

def update_xml_title(xml_content, title):
    """Update the title tag in the XML content."""
    # Pattern to match <title>...</title> including any comments or content inside
    pattern = r'<title>.*?</title>'
    replacement = f'<title>{title}</title>'
    updated_content = re.sub(pattern, replacement, xml_content, flags=re.DOTALL)
    
    return updated_content

def create_xml_file(template_path, output_path, file_name, content_type):
    """Create an XML file from a template."""
    try:
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Convert file name to kebab-case
        file_id = convert_to_kebab_case(file_name)
        
        # Update the ID attribute
        xml_content = update_xml_id(xml_content, file_id, content_type)
        
        # Update the title with the original file name
        xml_content = update_xml_title(xml_content, file_name)
        
        # Add content type prefix to filename
        prefix_mapping = {
            'concept': 'c-',
            'principle': 'pl-',
            'reference': 'r-',
            'process': 'pr-',
            'task': 't-'
        }
        prefix = prefix_mapping.get(content_type, '')
        
        # Create output filename with prefix
        output_filename = f"{prefix}{file_id}.xml"
        full_output_path = os.path.join(output_path, output_filename)
        
        # Write the file
        with open(full_output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return True, output_filename
    except Exception as e:
        return False, str(e)

def get_xml_info(xml_file_path):
    """Extract type and title from an XML file."""
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the root element type
        root_pattern = r'<(ct_\w+)\s'
        root_match = re.search(root_pattern, content)
        if root_match:
            xml_type = root_match.group(1)
        else:
            xml_type = "ct_concept"  # default
        
        # Extract title
        title_pattern = r'<title>(.*?)</title>'
        title_match = re.search(title_pattern, content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            # Remove any XML comments
            title = re.sub(r'<!--.*?-->', '', title, flags=re.DOTALL).strip()
        else:
            title = xml_file_path.stem
        
        return xml_type, title
    except Exception as e:
        return "ct_concept", xml_file_path.stem

def create_chapter_map(output_folder, chapter_name):
    """Create a chapter map XML file from all XML files in the output folder."""
    try:
        output_path = Path(output_folder)
        xml_files = sorted(output_path.glob("*.xml"))
        
        # Filter out any existing map files
        xml_files = [f for f in xml_files if not f.name.endswith('.ditamap')]
        
        if not xml_files:
            return False, "No XML files found in the output folder"
        
        # Group files by type
        files_by_type = {
            'ct_concept': [],
            'ct_task': [],
            'ct_process': [],
            'ct_principle': [],
            'ct_reference': []
        }
        
        for xml_file in xml_files:
            xml_type, title = get_xml_info(xml_file)
            # Map ct_concept references to ct_reference if filename starts with r-
            if xml_type == 'ct_concept' and xml_file.name.startswith('r-'):
                files_by_type['ct_reference'].append((xml_file, xml_type, title))
            else:
                if xml_type in files_by_type:
                    files_by_type[xml_type].append((xml_file, xml_type, title))
        
        # Create chapter map content
        map_id = f"map_{convert_to_kebab_case(chapter_name)}"
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<!DOCTYPE map PUBLIC "-//CISCO//DTD DITA 1.3 Map v1.0//EN" "cisco-map.dtd">\n'
        xml_content += f'<!-- Please change the title attribute of the <map> element using Attribute Inspector, whenever you change the <title> text. -->\n'
        xml_content += f'<map xml:lang="en_US" title="{chapter_name}" id="{map_id}">\n'
        xml_content += f'    <title>{chapter_name}</title>\n'
        
        # Add topicref in the specified order: concepts, tasks, processes, principles, references
        type_order = ['ct_concept', 'ct_task', 'ct_process', 'ct_principle', 'ct_reference']
        
        # Get the first concept file as parent
        first_concept = None
        if files_by_type['ct_concept']:
            sorted_concepts = sorted(files_by_type['ct_concept'], key=lambda x: x[0].name)
            first_concept = sorted_concepts[0]
            remaining_concepts = sorted_concepts[1:]
        else:
            remaining_concepts = []
        
        # If there's a first concept, create nested structure
        if first_concept:
            xml_file, file_type, title = first_concept
            xml_content += f'    <topicref href="{xml_file.name}" format="dita" scope="local" type="{file_type}" navtitle="{title}">\n'
            
            # Add remaining concepts first (nested)
            for xml_file, file_type, title in remaining_concepts:
                xml_content += f'        <topicref href="{xml_file.name}" format="dita" scope="local" type="{file_type}" navtitle="{title}"/>\n'
            
            # Add other types in order: principle, process, task, reference (nested)
            for xml_type in ['ct_principle', 'ct_process', 'ct_task', 'ct_reference']:
                for xml_file, file_type, title in sorted(files_by_type[xml_type], key=lambda x: x[0].name):
                    xml_content += f'        <topicref href="{xml_file.name}" format="dita" scope="local" type="{file_type}" navtitle="{title}"/>\n'
            
            # Close the parent topicref
            xml_content += f'    </topicref>\n'
        else:
            # If no concepts, add all files at root level
            for xml_type in type_order:
                for xml_file, file_type, title in sorted(files_by_type[xml_type], key=lambda x: x[0].name):
                    xml_content += f'    <topicref href="{xml_file.name}" format="dita" scope="local" type="{file_type}" navtitle="{title}"/>\n'
        
        xml_content += '</map>\n'
        
        # Save chapter map
        map_filename = f"{convert_to_kebab_case(chapter_name)}.ditamap"
        map_path = output_path / map_filename
        
        with open(map_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        return True, map_filename
    except Exception as e:
        return False, str(e)

def create_zip_file(output_folder, include_ditamap=False):
    """Create a ZIP file containing all XML files and optionally ditamap files."""
    try:
        output_path = Path(output_folder)
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all XML files
            xml_files = sorted(output_path.glob("*.xml"))
            for xml_file in xml_files:
                zip_file.write(xml_file, xml_file.name)
            
            # Add ditamap files if requested
            if include_ditamap:
                ditamap_files = sorted(output_path.glob("*.ditamap"))
                for ditamap_file in ditamap_files:
                    zip_file.write(ditamap_file, ditamap_file.name)
        
        zip_buffer.seek(0)
        return zip_buffer
    except Exception as e:
        return None

def main():
    st.set_page_config(page_title="XML File Generator", page_icon="📄", layout="wide")
    
    st.title("📄 XML File Generator")
    st.markdown("Generate XML files from templates based on Cisco Content Types")
    st.warning("⚠️ Files stored on this server will be automatically deleted after one week. Please download your files when done.")
    
    # Base directory
    base_dir = Path(__file__).parent
    template_dir = base_dir / "templates"
    default_output_dir = base_dir / "output"
    
    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'counts' not in st.session_state:
        st.session_state.counts = {}
    if 'file_names' not in st.session_state:
        st.session_state.file_names = {}
    if 'cec_id' not in st.session_state:
        st.session_state.cec_id = ''
    if 'output_folder' not in st.session_state:
        st.session_state.output_folder = str(default_output_dir)
    if 'chapter_map_created' not in st.session_state:
        st.session_state.chapter_map_created = False
    if 'chapter_map_result' not in st.session_state:
        st.session_state.chapter_map_result = None
    if 'validation_error' not in st.session_state:
        st.session_state.validation_error = None
    
    # Content types mapping
    content_types = {
        'Concepts': 'concept',
        'Tasks': 'task',
        'Processes': 'process',
        'Principles': 'principle',
        'References': 'reference'
    }
    
    # Step 1: Get counts for each content type
    if st.session_state.step == 1:
        st.header("Step 1: Enter CEC ID")
        
        # CEC ID input
        st.subheader("🔑 CEC ID")
        cec_id = st.text_input(
            "Enter your CEC ID:",
            value=st.session_state.cec_id,
            placeholder="e.g., sanjibha",
            help="Your unique CEC ID. A personal folder will be created under output/ for your files."
        )
        st.session_state.cec_id = cec_id.strip().lower()
        
        # Build per-user output folder path
        if st.session_state.cec_id:
            user_output_dir = default_output_dir / st.session_state.cec_id
            st.session_state.output_folder = str(user_output_dir)
            
            st.markdown(f"📁 **Your output folder:** `output/{st.session_state.cec_id}/`")
            
            # Show folder status and delete button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if user_output_dir.exists():
                    xml_count = len(list(user_output_dir.glob("*.xml")))
                    ditamap_count = len(list(user_output_dir.glob("*.ditamap")))
                    st.info(f"📂 Your folder contains {xml_count} XML file(s) and {ditamap_count} DITAMAP file(s)")
                else:
                    st.info("📂 Your folder will be created when files are generated.")
            
            with col2:
                st.write("")  # Spacing
                if st.button("🗑️ Clear My Folder", help="Delete all XML and DITAMAP files in your folder"):
                    if user_output_dir.exists():
                        xml_files = list(user_output_dir.glob("*.xml"))
                        ditamap_files = list(user_output_dir.glob("*.ditamap"))
                        all_files = xml_files + ditamap_files
                        if all_files:
                            for file in all_files:
                                file.unlink()
                            st.success(f"✅ Deleted {len(xml_files)} XML file(s) and {len(ditamap_files)} DITAMAP file(s)")
                            st.rerun()
                        else:
                            st.info("No XML or DITAMAP files found in your folder")
                    else:
                        st.info("Your folder does not exist yet")
            
            # List existing files in the folder
            if user_output_dir.exists():
                existing_xml = sorted(user_output_dir.glob("*.xml"))
                existing_ditamap = sorted(user_output_dir.glob("*.ditamap"))
                existing_files = existing_xml + existing_ditamap
                if existing_files:
                    with st.expander(f"📋 View existing files ({len(existing_files)})", expanded=False):
                        for f in existing_files:
                            fcol1, fcol2 = st.columns([5, 1])
                            with fcol1:
                                icon = "🗺️" if f.suffix == ".ditamap" else "📄"
                                st.markdown(f"{icon} `{f.name}`")
                            with fcol2:
                                if st.button("❌", key=f"del_{f.name}", help=f"Delete {f.name}"):
                                    f.unlink()
                                    st.rerun()
                    
                    # Download existing files
                    zip_buffer = create_zip_file(str(user_output_dir), include_ditamap=True)
                    if zip_buffer:
                        st.download_button(
                            label="📥 Download My Files",
                            data=zip_buffer,
                            file_name=f"{st.session_state.cec_id}-files.zip",
                            mime="application/zip",
                        )
        else:
            st.warning("⚠️ Please enter your CEC ID to continue.")
        
        st.divider()
        
        # File counts
        st.subheader("📝 How many files do you need?")
        st.markdown("Enter the number of files needed for each content type: (do not include H1)")
        
        with st.form("counts_form"):
            counts = {}
            for content_type in content_types.keys():
                counts[content_type] = st.number_input(
                    f"Number of {content_type}:",
                    min_value=0,
                    max_value=100,
                    value=0,
                    step=1
                )
            
            submitted = st.form_submit_button("Next →")
            
            if submitted:
                if not st.session_state.cec_id:
                    st.error("Please enter your CEC ID above before proceeding.")
                else:
                    # Store counts and filter out zeros
                    st.session_state.counts = {k: v for k, v in counts.items() if v > 0}
                    
                    if not st.session_state.counts:
                        st.error("Please enter at least one file count greater than 0")
                    else:
                        # Create output directory if it doesn't exist
                        Path(st.session_state.output_folder).mkdir(parents=True, exist_ok=True)
                        st.session_state.step = 2
                        st.rerun()
    
    # Step 2: Get file names
    elif st.session_state.step == 2:
        st.header("Step 2: Enter file names")
        
        with st.form("names_form"):
            file_names = {}
            
            for content_type, count in st.session_state.counts.items():
                st.subheader(f"{content_type} ({count} file{'s' if count > 1 else ''})")
                file_names[content_type] = []
                
                for i in range(count):
                    name = st.text_input(
                        f"{content_type} #{i+1} name:",
                        key=f"{content_type}_{i}",
                        placeholder=f"e.g., Understanding {content_type[:-1]}"
                    )
                    file_names[content_type].append(name)
            
            col1, col2 = st.columns([1, 5])
            with col1:
                back = st.form_submit_button("← Back")
            with col2:
                submitted = st.form_submit_button("Generate Files →")
            
            if back:
                st.session_state.validation_error = None
                st.session_state.step = 1
                st.rerun()
            
            if submitted:
                # Clear previous validation error
                st.session_state.validation_error = None
                
                # Validate all names are provided
                all_valid = True
                for content_type, names in file_names.items():
                    if any(not name.strip() for name in names):
                        st.session_state.validation_error = f"Please provide names for all {content_type}"
                        all_valid = False
                        break
                
                # Check for duplicate names within the same content type
                if all_valid:
                    for content_type, names in file_names.items():
                        kebab_names = [convert_to_kebab_case(n) for n in names]
                        seen = {}
                        for i, kname in enumerate(kebab_names):
                            if kname in seen:
                                st.session_state.validation_error = (
                                    f"Duplicate file name in **{content_type}**: "
                                    f"\"{names[i]}\" and \"{names[seen[kname]]}\" "
                                    f"would both generate the same file. Please use unique names."
                                )
                                all_valid = False
                                break
                            seen[kname] = i
                        if not all_valid:
                            break
                
                if all_valid:
                    st.session_state.file_names = file_names
                    st.session_state.step = 3
                    st.rerun()
        
        # Display validation error outside the form so it clears properly
        if st.session_state.validation_error:
            st.error(st.session_state.validation_error)
    
    # Step 3: Generate files
    elif st.session_state.step == 3:
        st.header("Step 3: Generating XML files")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = sum(len(names) for names in st.session_state.file_names.values())
        files_created = 0
        results = []
        
        output_dir = Path(st.session_state.output_folder)
        
        for content_type, names in st.session_state.file_names.items():
            # Get the template file
            template_key = content_types[content_type]
            template_file = template_dir / f"ct-{template_key}.xml"
            
            for name in names:
                status_text.text(f"Creating {name}...")
                
                success, result = create_xml_file(
                    template_file,
                    output_dir,
                    name,
                    template_key
                )
                
                files_created += 1
                progress_bar.progress(files_created / total_files)
                
                results.append({
                    'type': content_type,
                    'name': name,
                    'success': success,
                    'filename': result if success else None,
                    'error': result if not success else None
                })
        
        status_text.text("Complete!")
        
        # Display results
        st.success(f"✅ Successfully created {sum(1 for r in results if r['success'])} XML files")
        
        st.subheader("Generated Files")
        
        for result in results:
            if result['success']:
                st.markdown(f"✅ **{result['name']}** → `{result['filename']}`")
            else:
                st.markdown(f"❌ **{result['name']}** → Error: {result['error']}")
        
        display_path = f"output/{st.session_state.cec_id}/" if st.session_state.cec_id else "output/"
        st.info(f"📁 Files saved to: `{display_path}`")
        
        st.divider()
        
        # Download XML files button
        zip_buffer = create_zip_file(output_dir, include_ditamap=False)
        if zip_buffer:
            st.download_button(
                label="📥 Download XML Files",
                data=zip_buffer,
                file_name="xml-files.zip",
                mime="application/zip",
                use_container_width=True
            )
        
        st.divider()
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📘 Next: Chapter Map →", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
        
        with col2:
            if st.button("🔄 Create More Files", use_container_width=True):
                st.session_state.step = 1
                st.session_state.counts = {}
                st.session_state.file_names = {}
                st.rerun()
    
    # Step 4: Create Chapter Map
    elif st.session_state.step == 4:
        st.header("Step 4: Create Chapter Map")
        
        output_dir = Path(st.session_state.output_folder)
        
        # Count XML files (excluding maps)
        xml_files = [f for f in output_dir.glob("*.xml") if not f.name.endswith('.ditamap')]
        
        if not xml_files:
            st.error("❌ No XML files found in the output folder. Please generate files first.")
            if st.button("← Back to Results"):
                st.session_state.step = 3
                st.rerun()
        else:
            st.info(f"📄 Found {len(xml_files)} XML file(s) in the output folder")
            
            # Show files that will be included, with option to remove
            with st.expander("View / manage files to be included in map", expanded=True):
                for xml_file in sorted(xml_files):
                    fcol1, fcol2 = st.columns([4, 1])
                    with fcol1:
                        xml_type, title = get_xml_info(xml_file)
                        type_label = xml_type.replace('ct_', '').capitalize()
                        st.markdown(f"📄 `{xml_file.name}` — *{type_label}*: {title}")
                    with fcol2:
                        if st.button("🗑️ Remove", key=f"map_del_{xml_file.name}", help=f"Remove {xml_file.name}"):
                            xml_file.unlink()
                            st.rerun()
            
            st.divider()
            
            # Chapter name input
            with st.form("chapter_map_form"):
                chapter_name = st.text_input(
                    "Chapter Name:",
                    placeholder="e.g., Getting Started Guide",
                    help="Enter the name for your chapter map"
                )
                
                col1, col2 = st.columns([1, 5])
                
                with col1:
                    back = st.form_submit_button("← Back")
                with col2:
                    generate = st.form_submit_button("🗺️ Generate Chapter Map")
            
            # Handle form submissions outside the form
            if back:
                st.session_state.step = 3
                st.session_state.chapter_map_created = False
                st.rerun()
            
            if generate:
                if not chapter_name.strip():
                    st.error("Please enter a chapter name")
                else:
                    # Create chapter map
                    with st.spinner("Creating chapter map..."):
                        success, result = create_chapter_map(output_dir, chapter_name)
                    
                    if success:
                        st.session_state.chapter_map_created = True
                        st.session_state.chapter_map_result = {
                            'success': True,
                            'filename': result,
                            'output_dir': str(output_dir)
                        }
                        st.rerun()
                    else:
                        st.session_state.chapter_map_created = True
                        st.session_state.chapter_map_result = {
                            'success': False,
                            'error': result
                        }
                        st.rerun()
            
            # Show results outside the form
            if st.session_state.chapter_map_created and st.session_state.chapter_map_result:
                result = st.session_state.chapter_map_result
                
                if result['success']:
                    st.success(f"✅ Chapter map created successfully!")
                    st.markdown(f"**File:** `{result['filename']}`")
                    display_path = f"output/{st.session_state.cec_id}/" if st.session_state.cec_id else "output/"
                    st.info(f"📁 Saved to: `{display_path}`")
                    
                    # Show preview
                    with st.expander("Preview Chapter Map"):
                        map_path = Path(result['output_dir']) / result['filename']
                        with open(map_path, 'r', encoding='utf-8') as f:
                            st.code(f.read(), language='xml')
                    
                    st.divider()
                    
                    # Download button
                    zip_buffer = create_zip_file(result['output_dir'], include_ditamap=True)
                    if zip_buffer:
                        st.download_button(
                            label="📥 Download All Files (XML + DITAMAP)",
                            data=zip_buffer,
                            file_name="all-files.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    
                    st.divider()
                    
                    # Navigation buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🔄 Start Over", use_container_width=True):
                            st.session_state.step = 1
                            st.session_state.counts = {}
                            st.session_state.file_names = {}
                            st.session_state.chapter_map_created = False
                            st.session_state.chapter_map_result = None
                            st.rerun()
                    with col2:
                        if st.button("← Back to Files", use_container_width=True):
                            st.session_state.step = 3
                            st.session_state.chapter_map_created = False
                            st.session_state.chapter_map_result = None
                            st.rerun()
                    with col3:
                        if st.button("Next Steps →", use_container_width=True):
                            st.session_state.step = 5
                            st.rerun()
                else:
                    st.error(f"❌ Failed to create chapter map: {result['error']}")
    
    # Step 5: Instructions
    elif st.session_state.step == 5:
        st.header("Step 5: Add Content to Your Files")
        
        st.markdown("### 📝 Instructions")
        
        st.info("Now that you've created your XML files and chapter map, it's time to add content!")
        
        st.markdown("""
        **Use the Convert Tool to add content to your files:**
        
        🔗 **[CTWG Converter Tool](https://ctwg-converter.cloudapps.cisco.com/)**
        
        ### How to use the tool:
        
        1. **Copy content** from your Word files
        2. **Paste** the content into the Convert tool
        3. **Click AI mode** to generate XML
        4. **Copy the generated XML** from the tool
        5. **Paste it** into your XML files (in Text mode)
        
        The tool will automatically format your content according to DITA standards, making it ready to use in the files you just created.
        """)
        
        st.divider()
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Chapter Map", use_container_width=True):
                st.session_state.step = 4
                st.rerun()
        with col2:
            if st.button("🔄 Start Over", use_container_width=True):
                st.session_state.step = 1
                st.session_state.counts = {}
                st.session_state.file_names = {}
                st.session_state.chapter_map_created = False
                st.session_state.chapter_map_result = None
                st.rerun()

if __name__ == "__main__":
    main()
